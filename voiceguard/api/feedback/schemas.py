from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator

from api.feedback.models import CATEGORIES, Feedback


class FeedbackSubmitRequest(BaseModel):
    category: str
    message: str
    # security-review.md F-28: these now match the DB column limits
    # (api/feedback/models.py: scan_id String(64), email String(254)) and
    # email is format-validated, instead of silently reaching Postgres as
    # unconstrained strings and risking a raw DataError there.
    scan_id: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None

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
