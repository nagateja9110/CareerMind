from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    raw_text: str
    parsed_skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    uploaded_at: datetime
