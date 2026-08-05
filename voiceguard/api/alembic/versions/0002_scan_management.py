"""Audio Upload & Scan Management: scans, scan_events, processing_jobs.

Revision ID: 0002_scan_management
Revises: 0001_product_foundation
Create Date: 2026-07-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_scan_management"
down_revision: Union[str, None] = "0001_product_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match ScanStatus's .value strings exactly (api.scans.state_machine) —
# sa.Enum(ScanStatus, ..., values_callable=enum_values) binds/reads members by
# .value, not .name. See api/user/models.py history for what happens when a
# migration and a model's Enum column drift apart on this point.
_SCAN_STATUS_VALUES = (
    "created",
    "validating",
    "uploading",
    "queued",
    "preprocessing",
    "ready_for_ai",
    "completed",
    "failed",
    "validation_failed",
    "upload_failed",
    "cancelled",
    "expired",
)


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status", sa.Enum(*_SCAN_STATUS_VALUES, name="scan_status"), nullable=False, server_default="created"
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_backend", sa.String(32), nullable=False, server_default="local"),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_extension", sa.String(16), nullable=False),
        sa.Column("declared_mime_type", sa.String(127), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("sha256_checksum", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("scan_metadata", postgresql.JSONB, nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preprocessing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_scans_file_size_non_negative"),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_user_status", "scans", ["user_id", "status"])
    op.create_index("ix_scans_user_created", "scans", ["user_id", "created_at"])
    op.create_index("ix_scans_user_checksum", "scans", ["user_id", "sha256_checksum"])
    op.create_index("ix_scans_expires_at", "scans", ["expires_at"])

    op.create_table(
        "scan_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor", sa.String(16), nullable=False, server_default="system"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("actor IN ('user', 'system')", name="ck_scan_events_actor"),
    )
    op.create_index("ix_scan_events_scan_id", "scan_events", ["scan_id"])
    op.create_index("ix_scan_events_occurred_at", "scan_events", ["occurred_at"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(32), nullable=False, server_default="preprocessing"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("last_error", sa.String(1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_processing_jobs_status"
        ),
    )
    op.create_index("ix_processing_jobs_scan_id", "processing_jobs", ["scan_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("scan_events")
    op.drop_table("scans")
    sa.Enum(name="scan_status").drop(op.get_bind(), checkfirst=True)
