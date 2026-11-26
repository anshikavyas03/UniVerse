from typing import Literal

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    language: Literal["en", "hi"]
    provider: str


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "hi"] = "en"
