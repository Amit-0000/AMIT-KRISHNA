"""Feedback slice: feedback table.

Revision ID: 0006_feedback
Revises: 0005_notifications
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0006_feedback"
down_revision: Union[str, None] = "0005_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("scan_id", sa.String(64), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("browser", sa.String(256), nullable=True),
        sa.Column("application_version", sa.String(32), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open', 'reviewed', 'resolved')", name="ck_feedback_status"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index(op.f("ix_feedback_created_at"), "feedback", ["created_at"])


def downgrade() -> None:
    op.drop_table("feedback")
