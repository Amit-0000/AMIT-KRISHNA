from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_serializer


class ShareCreateResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime | None

    @field_serializer("expires_at")
    def _serialize_expires_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
