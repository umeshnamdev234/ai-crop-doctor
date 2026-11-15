"""Smarter Crops AI — FastAPI backend.

Run:  docker compose up -d     Docs: http://localhost:8100/docs
"""
import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .db import DatabaseUnavailable, DirectoryRepository
from .directory import KIND_MODELS, Centre, Expert, Location, Product, rank_centres, rank_experts, rank_products
from .llm_client import LLMClient, LLMError, LLMUnavailable
from .prompts import DEFAULT_IMAGE_QUESTION, LANGUAGE_RULES, SYSTEM_PROMPT
from .safety import detect_emergency, emergency_notice, safety_reminder
from .schemas import ChatRequest, ChatResponse, HealthResponse, ImageInput, Message, RecommendRequest
from .triage import TriageResult, triage

settings = get_settings()
# Never log message content or images.
log = logging.getLogger("smarter_crops")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = LLMClient(settings.llm_base_url, settings.llm_model, settings.llm_api_key, settings.llm_timeout_s)
    app.state.repo = DirectoryRepository(settings.database_url)
    log.info("Using model %s at %s", settings.llm_model, settings.llm_base_url)
    if await app.state.repo.connect():  # the API still starts without the DB; directory routes return 503
        revision = await app.state.repo.migration_revision()
        if revision is None:
            log.error("Database has no schema. Run: alembic upgrade head")
        else:
            log.info("Directory database at migration %s: %s", revision, (await app.state.repo.meta())["counts"])
    yield
    await app.state.llm.aclose()
    await app.state.repo.close()


app = FastAPI(
    title="Smarter Crops AI API",
    version="1.0.0",
    description="Crop health assistant: chat, crop photo diagnosis and recommendations of experts, treatments and centres.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


# ---------- dependencies & helpers ----------
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if settings.app_api_key and x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def require_admin_key(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin API disabled: set ADMIN_API_KEY")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


def get_repo(request: Request) -> DirectoryRepository:
    return request.app.state.repo


def to_http_error(e: Exception) -> HTTPException:
    if isinstance(e, LLMUnavailable):
        return HTTPException(status_code=503, detail=f"{e}. Is Ollama running?")
    return HTTPException(status_code=502, detail=str(e))


def validate_images(messages: list[Message]) -> None:
    max_bytes = int(settings.max_image_mb * 1024 * 1024)
    for m in messages:
        if len(m.images) > settings.max_images_per_message:
            raise HTTPException(422, f"At most {settings.max_images_per_message} images per message")
        for im in m.images:
            if im.approx_bytes > max_bytes:
                raise HTTPException(413, f"Image larger than {settings.max_image_mb} MB")


def system_prompt(reply_language: str) -> str:
    return SYSTEM_PROMPT.format(language_rule=LANGUAGE_RULES.get(reply_language, LANGUAGE_RULES["auto"]))


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.exception_handler(DatabaseUnavailable)
async def db_unavailable(_: Request, exc: DatabaseUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ---------- system ----------
@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health(llm: LLMClient = Depends(get_llm), repo: DirectoryRepository = Depends(get_repo)):
    try:
        models = await llm.list_models()
        reachable = True
    except (LLMUnavailable, LLMError):
        models, reachable = [], False
    available = any(m == settings.llm_model or m.startswith(settings.llm_model + ":") for m in models)
    db_ok = await repo.ping()
    return HealthResponse(
        status="ok" if reachable and available and db_ok else "degraded",
        model=settings.llm_model,
        model_server=settings.llm_base_url,
        model_server_reachable=reachable,
        model_available=available,
        database_reachable=db_ok,
    )


@app.get("/api/models", dependencies=[Depends(require_api_key)], tags=["system"])
async def models(llm: LLMClient = Depends(get_llm)):
    try:
        return {"default": settings.llm_model, "models": await llm.list_models()}
    except (LLMUnavailable, LLMError) as e:
        raise to_http_error(e)


# ---------- chat ----------
@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)], tags=["chat"])
async def chat(req: ChatRequest, llm: LLMClient = Depends(get_llm)):
    """Full reply in one response."""
    validate_images(req.messages)
    emergency = detect_emergency(req.messages[-1].content)
    started = time.perf_counter()
    try:
        result = await llm.chat(
            LLMClient.build_messages(system_prompt(req.reply_language), req.messages),
            temperature=req.temperature if req.temperature is not None else settings.default_temperature,
            max_tokens=req.max_tokens or settings.default_max_tokens,
            model=req.model,
        )
    except (LLMUnavailable, LLMError) as e:
        raise to_http_error(e)
    log.info("chat ok msgs=%d emergency=%s %.1fs", len(req.messages), emergency, time.perf_counter() - started)
    notice = emergency_notice(req.messages[-1].content, req.reply_language) if emergency else None
    return ChatResponse(reply=result["content"], model=result["model"], emergency=emergency,
                        emergency_notice=notice, usage=result["usage"])


@app.post("/api/chat/stream", dependencies=[Depends(require_api_key)], tags=["chat"])
async def chat_stream(req: ChatRequest, llm: LLMClient = Depends(get_llm)):
    """Server-Sent Events: `meta` → `delta`… → `done` (or `error`)."""
    validate_images(req.messages)
    emergency = detect_emergency(req.messages[-1].content)
    model = req.model or settings.llm_model
    messages = LLMClient.build_messages(system_prompt(req.reply_language), req.messages)

    async def events():
        yield sse({"type": "meta", "model": model, "emergency": emergency,
                   "emergency_notice": emergency_notice(req.messages[-1].content, req.reply_language) if emergency else None})
        started, first_token, usage, chars = time.perf_counter(), None, None, 0
        try:
            async for ev in llm.stream(
                messages,
                temperature=req.temperature if req.temperature is not None else settings.default_temperature,
                max_tokens=req.max_tokens or settings.default_max_tokens,
                model=req.model,
            ):
                if "delta" in ev:
                    first_token = first_token or time.perf_counter()
                    chars += len(ev["delta"])
                    yield sse({"type": "delta", "text": ev["delta"]})
                elif "usage" in ev:
                    usage = ev["usage"]
        except (LLMUnavailable, LLMError) as e:
            log.warning("stream failed: %s", e)
            yield sse({"type": "error", "message": str(to_http_error(e).detail)})
            return
        end = time.perf_counter()
        n = (usage or {}).get("completion_tokens") or 0
        gen = end - first_token if first_token else 0
        log.info("stream ok msgs=%d emergency=%s chars=%d %.1fs", len(req.messages), emergency, chars, end - started)
        yield sse({"type": "done", "usage": usage, "elapsed_s": round(end - started, 2),
                   "time_to_first_token_s": round(first_token - started, 2) if first_token else None,
                   "tokens_per_s": round((n - 1) / gen, 1) if n > 1 and gen > 0 else None})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/analyze-image", response_model=ChatResponse, dependencies=[Depends(require_api_key)], tags=["chat"])
async def analyze_image(
    file: UploadFile = File(..., description="Photo of a leaf, fruit, stem, field or soil test report"),
    question: str = Form(DEFAULT_IMAGE_QUESTION),
    reply_language: Literal["auto", "en", "hi"] = Form("auto"),
    llm: LLMClient = Depends(get_llm),
):
    """Upload one crop photo (multipart/form-data) and get a diagnosis."""
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "File must be an image")
    raw = await file.read()
    if len(raw) > settings.max_image_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_image_mb} MB")
    req = ChatRequest(reply_language=reply_language, messages=[Message(
        role="user", content=question,
        images=[ImageInput(mime_type=file.content_type, data=base64.b64encode(raw).decode())],
    )])
    return await chat(req, llm)


# ---------- recommendations ----------
@app.get("/api/directory/meta", dependencies=[Depends(require_api_key)], tags=["directory"])
async def directory_meta(repo: DirectoryRepository = Depends(get_repo)):
    """Counts plus filter options: states → districts, and languages."""
    return await repo.meta()


@app.post("/api/recommend", dependencies=[Depends(require_api_key)], tags=["directory"])
async def recommend(req: RecommendRequest, llm: LLMClient = Depends(get_llm), repo: DirectoryRepository = Depends(get_repo)):
    """Recommend agri experts, treatments/products and nearby centres for a conversation.

    1. The model classifies the problem (crop, problem type, likely issues, severity); keyword fallback.
       Pass `previous` (the earlier `triage`) to re-rank with new filters without calling the model.
    2. Experts, products and centres are ranked deterministically with explanations.
    """
    validate_images(req.messages)
    started = time.perf_counter()
    user_text = "\n".join(m.content for m in req.messages if m.role == "user")
    if req.previous:
        result = TriageResult(**req.previous.model_dump(),
                              emergency=detect_emergency("\n".join(m.content for m in req.messages if m.role == "user")))
    else:
        result = await triage(llm, req.messages)
    loc = Location(state=req.state, district=req.district)
    experts = rank_experts(await repo.experts(), result.problem_type, result.crop, result.likely_issues, loc, req.language)
    products = rank_products(await repo.products(), result.problem_type, result.crop, result.likely_issues, req.organic_only)
    centres = rank_centres(await repo.centres(), result.problem_type, loc, req.language)
    log.info("recommend source=%s type=%s crop=%s results=%d/%d/%d %.1fs", result.source, result.problem_type,
             result.crop or "-", len(experts), len(products), len(centres), time.perf_counter() - started)
    return {
        "triage": result.model_dump(),
        "emergency_notice": emergency_notice(user_text, req.reply_language) if result.emergency else None,
        "safety_reminder": safety_reminder(user_text, req.reply_language) if products else None,
        "filters": {"state": req.state, "district": req.district, "language": req.language, "organic_only": req.organic_only},
        "experts": [e.model_dump() for e in experts],
        "products": [p.model_dump() for p in products],
        "centres": [c.model_dump() for c in centres],
    }


# ---------- directory browse & admin ----------
Kind = Literal["experts", "products", "centres"]


@app.get("/api/{kind}", dependencies=[Depends(require_api_key)], tags=["directory"])
async def list_items(kind: Kind, state: Optional[str] = None, district: Optional[str] = None,
                     limit: int = 100, repo: DirectoryRepository = Depends(get_repo)):
    items = await repo.all_active(kind)
    if state:
        items = [i for i in items if getattr(i, "state", "").lower() == state.lower()]
    if district:
        items = [i for i in items if getattr(i, "district", "").lower() == district.lower()]
    return [i.model_dump() for i in items[: max(1, min(limit, 500))]]


@app.get("/api/{kind}/{item_id}", dependencies=[Depends(require_api_key)], tags=["directory"])
async def get_item(kind: Kind, item_id: str, repo: DirectoryRepository = Depends(get_repo)):
    item = await repo.get(kind, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    return item.model_dump()


async def _upsert(kind: str, item, item_id: str, repo: DirectoryRepository):
    if item.id != item_id:
        raise HTTPException(422, "id in body must match the URL")
    await repo.upsert_many(kind, [item])
    return (await repo.get(kind, item_id)).model_dump()  # type: ignore[union-attr]


@app.put("/api/experts/{item_id}", dependencies=[Depends(require_admin_key)], tags=["admin"])
async def upsert_expert(item_id: str, item: Expert, repo: DirectoryRepository = Depends(get_repo)):
    return await _upsert("experts", item, item_id, repo)


@app.put("/api/products/{item_id}", dependencies=[Depends(require_admin_key)], tags=["admin"])
async def upsert_product(item_id: str, item: Product, repo: DirectoryRepository = Depends(get_repo)):
    return await _upsert("products", item, item_id, repo)


@app.put("/api/centres/{item_id}", dependencies=[Depends(require_admin_key)], tags=["admin"])
async def upsert_centre(item_id: str, item: Centre, repo: DirectoryRepository = Depends(get_repo)):
    return await _upsert("centres", item, item_id, repo)


@app.delete("/api/{kind}/{item_id}", status_code=204, dependencies=[Depends(require_admin_key)], tags=["admin"])
async def delete_item(kind: Kind, item_id: str, repo: DirectoryRepository = Depends(get_repo)):
    """Soft delete: kept in the database, never recommended."""
    if kind not in KIND_MODELS or not await repo.deactivate(kind, item_id):
        raise HTTPException(404, "Not found")
