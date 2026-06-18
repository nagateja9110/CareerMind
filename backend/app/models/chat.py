from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessagePayload(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ToolCallRecord(BaseModel):
    tool: str
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)


class RecommendedJob(BaseModel):
    title: str
    company: str
    location: str
    matched_skills: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    chat_id: str | None = None
    message: str = Field(min_length=2, max_length=2000)


class ChatSummary(BaseModel):
    chat_id: str
    title: str
    updated_at: datetime


class ChatResponse(BaseModel):
    chat_id: str
    answer: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    recommended_jobs: list[RecommendedJob] = Field(default_factory=list)


class ChatThread(BaseModel):
    chat_id: str
    messages: list[ChatMessagePayload]
    updated_at: datetime


class AgentRunResult(BaseModel):
    answer: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    recommended_jobs: list[RecommendedJob] = Field(default_factory=list)
