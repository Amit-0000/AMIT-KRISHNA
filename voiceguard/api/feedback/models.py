from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base

CATEGORIES = frozenset({"incorrect_result", "bug", "feature_request", "general"})
_HIGH_PRIORITY_CATEGORIES = frozenset({"incorrect_result", "bug"})


def priority_for_category(category: str) -> str:
    return "high" if category in _HIGH_PRIORITY_CATEGORIES else "normal"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Feedback(Base):
    """General product feedback (Give Feedback page) — distinct from a
    per-scan verdict correction (no backend consumer yet; see
    frontend/src/services/api.ts's scanApi.submitFeedback, still
    unimplemented). `user_id` is nullable: the frontend lets a signed-out
    visitor submit feedback with just an email address."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    message: Mapped[str] = mapped_column(sa.String(2000), nullable=False)
    # Free-text, not a scans.id foreign key: the frontend field is a plain
    # optional text input a visitor can type anything into (see
    # frontend/src/pages/Feedback/index.tsx), not a validated scan picker.
    scan_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(sa.String(254), nullable=True)
    browser: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
    application_version: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    priority: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        sa.CheckConstraint("status IN ('open', 'reviewed', 'resolved')", name="ck_feedback_status"),
        sa.Index("ix_feedback_user_id", "user_id"),
    )
