from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from api.notifications.models import Notification


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str
    read: bool
    created_at: datetime
    action_url: str | None

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @classmethod
    def from_notification(cls, notification: Notification) -> "NotificationResponse":
        return cls.model_validate(notification)


class UnreadCountResponse(BaseModel):
    unread_count: int
