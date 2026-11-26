from typing import Literal
from pydantic import BaseModel, Field, field_validator

Language = Literal["en", "hi", "auto"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Language = "auto"
    conversation_id: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value.strip()


class Source(BaseModel):
    title: str
    page: int | None = None
    category: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    language: Literal["en", "hi"]
    sources: list[Source] = []
    verified: bool = False
    provider: str
    follow_up: str | None = None
    suggestions: list[str] = []
    error: Literal["database_unavailable", "model_unavailable"] | None = None
    session_reset: bool = False
