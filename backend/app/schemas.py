"""Request / response models."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ImageInput(BaseModel):
    mime_type: str = Field("image/jpeg", examples=["image/png"])
    data: str = Field(..., description="Base64-encoded image (a data: URL is also accepted)")

    @model_validator(mode="before")
    @classmethod
    def strip_data_url(cls, values):
        # Accept "data:image/png;base64,AAAA..." and split it into mime_type + data
        if isinstance(values, dict):
            data = values.get("data", "")
            if isinstance(data, str) and data.startswith("data:") and "," in data:
                header, b64 = data.split(",", 1)
                values = {**values, "data": b64, "mime_type": header[5:].split(";")[0] or values.get("mime_type")}
        return values

    @field_validator("mime_type")
    @classmethod
    def must_be_image(cls, v: str) -> str:
        if not v.startswith("image/"):
            raise ValueError("mime_type must be an image/* type")
        return v

    @property
    def approx_bytes(self) -> int:
        return len(self.data) * 3 // 4


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = ""
    images: list[ImageInput] = Field(default_factory=list)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="Conversation so far; last message must be from the user")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    model: Optional[str] = Field(None, description="Override the configured model")
    reply_language: Literal["auto", "en", "hi"] = Field("auto", description="auto = same language as the farmer")

    @model_validator(mode="after")
    def last_is_user(self):
        last = self.messages[-1]
        if last.role != "user":
            raise ValueError("last message must have role 'user'")
        if not last.content.strip() and not last.images:
            raise ValueError("last message must contain text or an image")
        return self


class ChatResponse(BaseModel):
    reply: str
    model: str
    emergency: bool = False
    emergency_notice: Optional[str] = None
    usage: Optional[dict] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str
    model_server: str
    model_server_reachable: bool
    model_available: bool
    database_reachable: bool


class PreviousTriage(BaseModel):
    """Pass back a previous triage to re-rank with new filters without calling the model again."""
    crop: str = ""
    problem_type: Literal["disease", "pest", "nutrient", "water", "weed", "soil", "general"]
    likely_issues: list[str] = Field(default_factory=list, max_length=3)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    source: Literal["ai", "keywords"] = "ai"


class RecommendRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="The conversation to base suggestions on")
    state: Optional[str] = None
    district: Optional[str] = None
    language: Optional[str] = None
    organic_only: bool = False
    reply_language: Literal["auto", "en", "hi"] = "auto"
    previous: Optional[PreviousTriage] = None

    @model_validator(mode="after")
    def has_user_input(self):
        if not any(m.role == "user" and (m.content.strip() or m.images) for m in self.messages):
            raise ValueError("conversation must include at least one user message")
        return self
