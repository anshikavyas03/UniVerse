from typing import Literal
from pydantic import BaseModel, Field

Language = Literal["en", "hi", "auto"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Language = "auto"
    conversation_id: str | None = Field(default=None, max_length=100)


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
