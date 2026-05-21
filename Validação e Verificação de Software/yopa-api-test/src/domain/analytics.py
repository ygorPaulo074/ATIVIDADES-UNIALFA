"""
Analytics domain entities: user context and AI-generated insights per session.
"""
from typing import Any
from pydantic import BaseModel


class UserContextRecord(BaseModel):
    user_id: str
    agent_id: str
    segment: str | None = None
    language: str | None = None
    form_answers: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class InsightRecord(BaseModel):
    session_id: str
    generated_at: str
    key_points: list[str] = []
    suggested_actions: list[str] = []
    summary: str
