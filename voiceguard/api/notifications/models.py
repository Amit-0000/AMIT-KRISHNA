from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """In-app notifications surfaced by the header NotificationCenter and the
    /notifications page. `type` is a free-text tag (mirrors
    frontend/src/types/index.ts's NotificationType union) rather than a DB
    enum — this slice has no server-side branching on it, only display
    logic on the frontend, so a CheckConstraint would just be ceremony (same
    reasoning api.scans.models.ProcessingJob.status uses)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    read: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    action_url: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        sa.Index("ix_notifications_user_id", "user_id"),
        sa.Index("ix_notifications_user_read", "user_id", "read"),
    )
