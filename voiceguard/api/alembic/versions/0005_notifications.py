"""Notifications slice: notifications table.

Revision ID: 0005_notifications
Revises: 0004_scan_status_enum_values
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0005_notifications"
down_revision: Union[str, None] = "0004_scan_status_enum_values"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(1024), nullable=False),
        sa.Column("read", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("action_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read"])
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_table("notifications")
