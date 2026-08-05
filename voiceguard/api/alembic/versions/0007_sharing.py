"""Sharing slice: share_tokens table.

Revision ID: 0007_sharing
Revises: 0006_feedback
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007_sharing"
down_revision: Union[str, None] = "0006_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "share_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_share_tokens_scan_id", "share_tokens", ["scan_id"])
    op.create_index("ix_share_tokens_user_id", "share_tokens", ["user_id"])
    op.create_index(op.f("ix_share_tokens_token"), "share_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("share_tokens")
