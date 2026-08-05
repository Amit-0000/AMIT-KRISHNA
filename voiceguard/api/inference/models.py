from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelVersion(Base):
    """The model registry (BATCH_06-style model lifecycle metadata, scoped to
    what this slice needs: which checkpoint is active, what it expects, and
    whether it has passed an integrity check). One row per trained checkpoint
    ever registered — never mutated after creation except `status` and
    `loaded_at`, so historical scan_results can always resolve exactly which
    weights produced them."""

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    architecture: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # 'active': eligible to be selected by get_active_model(). 'inactive':
    # registered but not served. 'deprecated': was active, superseded — kept
    # so old scan_results.model_version_id still resolves. Enforced by
    # ck_model_versions_status, not the Python enum pattern api.scans.models
    # uses for `Scan.status` — there is no scan-style state *machine* here
    # (no ordered transitions to validate), just a small closed set of flags,
    # so a plain CheckConstraint is the right-sized tool (see api.scans.models
    # ProcessingJob.status for the same reasoning applied to job status).
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="inactive")
    feature_extractor_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    feature_extractor_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    model_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    loaded_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    results: Mapped[list["ScanResult"]] = relationship(back_populates="model_version")

    __table_args__ = (
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
        sa.CheckConstraint("status IN ('active', 'inactive', 'deprecated')", name="ck_model_versions_status"),
        sa.Index("ix_model_versions_status", "status"),
    )


class ScanResult(Base):
    """The AI Processing Pipeline's terminal artifact — one row per scan that
    reaches COMPLETED, written exactly once by api.inference.result_writer
    inside the SAVING_RESULTS stage. `verdict` is the calibrated, thresholded
    call surfaced to users (mirrors frontend/src/types/index.ts's pre-existing
    `Verdict` union); `label`/raw scores are kept alongside it for technical
    transparency (GET /scans/{id}/technical) rather than making callers
    re-derive them from confidence + threshold_used."""

    __tablename__ = "scan_results"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Denormalized from scans.user_id — every ownership check this slice does
    # (GET result/technical/explanation) can then filter on scan_results
    # directly instead of joining back to scans, same tradeoff api.scans
    # already made for its own indexes.
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False
    )

    label: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    verdict: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(sa.Float, nullable=False)
    raw_bonafide_score: Mapped[float] = mapped_column(sa.Float, nullable=False)
    raw_spoof_score: Mapped[float] = mapped_column(sa.Float, nullable=False)
    threshold_used: Mapped[float] = mapped_column(sa.Float, nullable=False)
    is_below_threshold: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Structured explainability payload (see api.inference.explainability) —
    # salient regions, detection notes, warnings, feature/model version tags.
    # A JSON column for the same reason Scan.scan_metadata is one: this slice
    # has exactly one producer/consumer and no query filters on individual
    # keys inside it.
    explanation: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    feature_extractor_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    feature_extractor_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    inference_time_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    model_version: Mapped[ModelVersion] = relationship(back_populates="results")

    __table_args__ = (
        sa.CheckConstraint("label IN ('bonafide', 'spoof')", name="ck_scan_results_label"),
        sa.CheckConstraint("verdict IN ('human', 'ai_generated', 'uncertain')", name="ck_scan_results_verdict"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_scan_results_confidence_range"),
        sa.CheckConstraint(
            "raw_bonafide_score >= 0 AND raw_bonafide_score <= 1", name="ck_scan_results_bonafide_range"
        ),
        sa.CheckConstraint("raw_spoof_score >= 0 AND raw_spoof_score <= 1", name="ck_scan_results_spoof_range"),
        sa.Index("ix_scan_results_user_id", "user_id"),
        sa.Index("ix_scan_results_verdict", "verdict"),
    )


class FeatureVector(Base):
    """Metadata for one extractor's output on one scan. The array itself is
    persisted through the existing StorageBackend abstraction (same as the
    original audio — see api.core.storage) under a `features/` key rather
    than inline in Postgres: a 128x313 float32 log-mel array is ~160KB,
    too large to store per-row without bloating the table, and storage is
    already the right abstraction for "large binary blob keyed by scan".
    `storage_key` is null when FEATURE_VECTOR_STORAGE_ENABLED=False —
    `summary_stats` still gives enough to debug without the full array."""

    __tablename__ = "feature_vectors"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    extractor_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    shape: Mapped[list[int]] = mapped_column(sa.JSON(), nullable=False)
    dtype: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    summary_stats: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint(
            "scan_id", "extractor_name", "extractor_version", name="uq_feature_vectors_scan_extractor"
        ),
        sa.Index("ix_feature_vectors_scan_id", "scan_id"),
    )


class ProcessingMetric(Base):
    """One row per AI-pipeline stage attempt (see
    api.scans.state_machine.AI_PIPELINE_STAGES) — the timing data behind
    "Performance Metrics" / "Stage Timing" observability. Deliberately
    separate from scan_events (which is the state-transition audit trail,
    one row per *status change*): a single stage can retry — and therefore
    record several ProcessingMetric rows — before it produces the one
    transition scan_events records for it."""

    __tablename__ = "processing_metrics"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    duration_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        sa.CheckConstraint("status IN ('succeeded', 'failed')", name="ck_processing_metrics_status"),
        sa.Index("ix_processing_metrics_scan_id", "scan_id"),
        sa.Index("ix_processing_metrics_stage", "stage"),
    )


class ProcessingFailure(Base):
    """Structured diagnostic detail for one failed stage attempt — the
    engineering-triage counterpart to scan_events' user-facing `reason`
    string. Kept distinct from scan_events (see ProcessingMetric docstring
    for the same scan_events-vs-per-attempt reasoning) so a stage that fails
    twice before succeeding on a third attempt leaves both failures
    diagnosable, not just the transition scan_events would show if it had
    failed permanently."""

    __tablename__ = "processing_failures"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    error_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    error_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    retryable: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        sa.Index("ix_processing_failures_scan_id", "scan_id"),
        sa.Index("ix_processing_failures_occurred_at", "occurred_at"),
    )
