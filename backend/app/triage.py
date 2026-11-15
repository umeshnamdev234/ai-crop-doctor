"""Crop triage: the model classifies the problem (crop, type, likely issues, severity).

Falls back to keyword matching (English + Hindi) if the model is unreachable or returns
unusable output, so recommendations keep working either way.
"""
import json
import re
from typing import Literal

from pydantic import BaseModel

from .directory import PROBLEM_TYPES, ProblemType
from .llm_client import LLMClient, LLMError, LLMUnavailable
from .prompts import TRIAGE_PROMPT
from .safety import detect_emergency
from .schemas import Message

Severity = Literal["low", "medium", "high", "critical"]

KEYWORDS: dict[str, list[str]] = {
    "disease": ["spot", "blight", "rot", "wilt", "mildew", "rust", "mosaic", "curl", "lesion", "fungus", "fungal", "blast",
                "धब्बे", "झुलसा", "सड़", "मुरझा", "फफूंद", "रोग", "dhabbe"],
    "pest": ["insect", "worm", "caterpillar", "aphid", "whitefly", "thrips", "borer", "mite", "jassid", "bug", "larva",
             "armyworm", "hopper", "कीड़", "कीट", "इल्ली", "सुंडी", "माहू", "सफेद मक्खी", "keeda", "illi"],
    "nutrient": ["yellow", "chlorosis", "deficiency", "purple", "stunted", "fertilizer", "fertiliser", "urea", "npk",
                 "पीली", "पीला", "खाद", "कमी", "peeli", "khad"],
    "water": ["irrigation", "drought", "waterlog", "dry", "flood", "watering", "सिंचाई", "पानी", "सूखा", "sinchai", "paani"],
    "weed": ["weed", "grass", "खरपतवार", "घास", "kharpatwar"],
    "soil": ["soil", "ph", "saline", "alkaline", "acidic", "soil test", "मिट्टी", "mitti"],
}
CROPS = {
    "tomato": ["tomato", "टमाटर", "tamatar"], "potato": ["potato", "आलू", "aloo"], "wheat": ["wheat", "गेहूं", "गेहूँ", "gehu"],
    "rice": ["rice", "paddy", "धान", "चावल", "dhan"], "cotton": ["cotton", "कपास", "kapas"], "soybean": ["soybean", "soya", "सोयाबीन"],
    "maize": ["maize", "corn", "मक्का", "makka"], "chilli": ["chilli", "chili", "मिर्च", "mirch"], "onion": ["onion", "प्याज", "pyaz"],
    "sugarcane": ["sugarcane", "गन्ना", "ganna"], "brinjal": ["brinjal", "eggplant", "बैंगन", "baingan"],
    "chickpea": ["chickpea", "gram", "चना", "chana"], "mustard": ["mustard", "सरसों", "sarson"],
    "groundnut": ["groundnut", "peanut", "मूंगफली"], "grapes": ["grape", "अंगूर"], "banana": ["banana", "केला", "kela"],
}


class TriageResult(BaseModel):
    crop: str
    problem_type: ProblemType
    likely_issues: list[str]
    severity: Severity
    source: Literal["ai", "keywords"]
    emergency: bool = False


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))


def detect_crop(text: str) -> str:
    t = text.lower()
    for crop, words in CROPS.items():
        if any(w in t for w in words):
            return crop
    return ""


def keyword_triage(text: str) -> tuple[str, str]:
    t = text.lower()
    scores = {pt: sum(1 for w in words if w in t) for pt, words in KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    return (best if scores[best] else "general"), detect_crop(text)


async def triage(llm: LLMClient, messages: list[Message]) -> TriageResult:
    user_text = "\n".join(m.content for m in messages if m.role == "user")
    emergency = detect_emergency(user_text)
    transcript = "\n".join(
        f"{'Farmer' if m.role == 'user' else 'Assistant'}: {m.content.strip()}" for m in messages if m.content.strip()
    )[-6000:]
    images = [im for m in messages if m.role == "user" for im in m.images][-2:]
    prompt = TRIAGE_PROMPT.format(problem_types=", ".join(PROBLEM_TYPES), transcript=transcript or "(farmer shared a photo)")
    content: str | list[dict] = prompt
    if images:
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": f"data:{im.mime_type};base64,{im.data}"}} for im in images
        ]

    try:
        res = await llm.chat([{"role": "user", "content": content}], temperature=0, max_tokens=250, json_mode=True)
        data = _parse_json(res["content"])
        pt = str(data.get("problem_type", "")).strip().lower()
        if pt not in PROBLEM_TYPES:
            raise ValueError(f"invalid problem_type {pt!r}")
        issues = [str(i).strip() for i in (data.get("likely_issues") or []) if str(i).strip()][:3]
        sev = str(data.get("severity", "medium")).lower()
        result = TriageResult(
            crop=(str(data.get("crop") or "").strip().lower() or detect_crop(user_text)),
            problem_type=pt,  # type: ignore[arg-type]
            likely_issues=issues,
            severity=sev if sev in ("low", "medium", "high", "critical") else "medium",  # type: ignore[arg-type]
            source="ai",
        )
    except (LLMUnavailable, LLMError, ValueError, json.JSONDecodeError):
        pt, crop = keyword_triage(user_text)
        result = TriageResult(crop=crop, problem_type=pt, likely_issues=[], severity="medium", source="keywords")  # type: ignore[arg-type]

    result.emergency = emergency
    if emergency:
        result.severity = "critical"
    return result
