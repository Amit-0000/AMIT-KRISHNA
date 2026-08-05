from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShareToken(Base):
    """One row per public, read-only link generated for a completed scan's
    result. `token` is the only thing GET /scans/shared/{token} accepts —
    never the scan's own id — so a share link can't be guessed from (or
    used to enumerate) a user's scan history."""

    __tablename__ = "share_tokens"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        sa.Index("ix_share_tokens_scan_id", "scan_id"),
        sa.Index("ix_share_tokens_user_id", "user_id"),
    )

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None:
            # SQLite (the test suite's engine) round-trips DateTime(timezone=True)
            # values as naive — Postgres does not. Normalize to UTC-aware before
            # comparing so this behaves the same against either backend.
            expires_at = self.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return False
        return True
