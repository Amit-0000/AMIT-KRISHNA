"""AI Processing Pipeline & Detection Engine: model_versions, scan_results,
feature_vectors, processing_metrics, processing_failures.

Revision ID: 0003_ai_processing_pipeline
Revises: 0002_scan_management
Create Date: 2026-07-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_ai_processing_pipeline"
down_revision: Union[str, None] = "0002_scan_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("architecture", sa.String(64), nullable=False),
        sa.Column("checkpoint_path", sa.String(1024), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="inactive"),
        sa.Column("feature_extractor_name", sa.String(64), nullable=False),
        sa.Column("feature_extractor_version", sa.String(16), nullable=False),
        sa.Column("model_metadata", postgresql.JSONB, nullable=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
        sa.CheckConstraint("status IN ('active', 'inactive', 'deprecated')", name="ck_model_versions_status"),
    )
    op.create_index("ix_model_versions_status", "model_versions", ["status"])

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "scan_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("label", sa.String(16), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("raw_bonafide_score", sa.Float, nullable=False),
        sa.Column("raw_spoof_score", sa.Float, nullable=False),
        sa.Column("threshold_used", sa.Float, nullable=False),
        sa.Column("is_below_threshold", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("explanation", postgresql.JSONB, nullable=True),
        sa.Column("feature_extractor_name", sa.String(64), nullable=False),
        sa.Column("feature_extractor_version", sa.String(16), nullable=False),
        sa.Column("processing_time_ms", sa.Integer, nullable=False),
        sa.Column("inference_time_ms", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("label IN ('bonafide', 'spoof')", name="ck_scan_results_label"),
        sa.CheckConstraint("verdict IN ('human', 'ai_generated', 'uncertain')", name="ck_scan_results_verdict"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_scan_results_confidence_range"),
        sa.CheckConstraint(
            "raw_bonafide_score >= 0 AND raw_bonafide_score <= 1", name="ck_scan_results_bonafide_range"
        ),
        sa.CheckConstraint("raw_spoof_score >= 0 AND raw_spoof_score <= 1", name="ck_scan_results_spoof_range"),
    )
    op.create_index("ix_scan_results_user_id", "scan_results", ["user_id"])
    op.create_index("ix_scan_results_verdict", "scan_results", ["verdict"])

    op.create_table(
        "feature_vectors",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extractor_name", sa.String(64), nullable=False),
        sa.Column("extractor_version", sa.String(16), nullable=False),
        sa.Column("shape", postgresql.JSONB, nullable=False),
        sa.Column("dtype", sa.String(16), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("summary_stats", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "scan_id", "extractor_name", "extractor_version", name="uq_feature_vectors_scan_extractor"
        ),
    )
    op.create_index("ix_feature_vectors_scan_id", "feature_vectors", ["scan_id"])

    op.create_table(
        "processing_metrics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('succeeded', 'failed')", name="ck_processing_metrics_status"),
    )
    op.create_index("ix_processing_metrics_scan_id", "processing_metrics", ["scan_id"])
    op.create_index("ix_processing_metrics_stage", "processing_metrics", ["stage"])

    op.create_table(
        "processing_failures",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("scan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("error_type", sa.String(128), nullable=False),
        sa.Column("error_message", sa.String(1024), nullable=False),
        sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processing_failures_scan_id", "processing_failures", ["scan_id"])
    op.create_index("ix_processing_failures_occurred_at", "processing_failures", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("processing_failures")
    op.drop_table("processing_metrics")
    op.drop_table("feature_vectors")
    op.drop_table("scan_results")
    op.drop_table("model_versions")
