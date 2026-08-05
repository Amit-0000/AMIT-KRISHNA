from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from api.feedback.models import CATEGORIES, Feedback


class FeedbackSubmitRequest(BaseModel):
    category: str
    message: str
    scan_id: str | None = None
    email: str | None = None

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
        return v

    @field_validator("message")
    @classmethod
    def _message_length(cls, v: str) -> str:
        stripped = v.strip()
        if not (10 <= len(stripped) <= 2000):
            raise ValueError("message must be 10-2000 characters")
        return stripped


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    category: str
    message: str
    scan_id: str | None
    email: str | None
    priority: str
    status: str
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @classmethod
    def from_feedback(cls, feedback: Feedback) -> "FeedbackResponse":
        return cls.model_validate(feedback)
