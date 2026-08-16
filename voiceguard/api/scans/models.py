from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, enum_values
from api.scans.state_machine import ScanStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ScanStatus] = mapped_column(
        sa.Enum(ScanStatus, name="scan_status", values_callable=enum_values),
        nullable=False,
        default=ScanStatus.CREATED,
    )

    # original_filename is display-only (sanitized, never used to build a
    # filesystem path). storage_key is always generated from `id` + extension
    # (see api.scans.service), which is what actually makes path traversal
    # from a malicious filename impossible.
    original_filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    storage_backend: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    file_extension: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    declared_mime_type: Mapped[str | None] = mapped_column(sa.String(127), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, default=0)
    sha256_checksum: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="")
    duration_seconds: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    # Free-form preprocessing output (e.g. {"sample_rate": ..., "channels": ...})
    # — deliberately a JSON column rather than a normalized `metadata` table:
    # this slice has exactly one producer/consumer of it and no query needs to
    # filter/join on individual keys, so a table would be pure ceremony.
    scan_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    # NULL until the malware-scan step actually runs (still CREATED/VALIDATING/
    # UPLOADING). One of "clean" | "malicious" | "unavailable" | "not_scanned"
    # thereafter — see api.scans.malware_scan.MalwareScanRecordStatus. Never
    # "clean" for a file the scanner didn't actually clear: MALWARE_SCAN_REQUIRED
    # =false records "not_scanned" instead, kept distinct from a real CLEAN
    # verdict at every layer.
    malware_scan_status: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)

    error_code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    queued_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    preprocessing_started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    # Set when entering QUEUED: the deadline by which the scan must be picked
    # up for preprocessing and then claimed by the (future) AI engine before
    # it's reaped as EXPIRED. See api.scans.service.expire_stale_scans.
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    events: Mapped[list["ScanEvent"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan", order_by="ScanEvent.occurred_at"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_scans_file_size_non_negative"),
        sa.CheckConstraint(
            "malware_scan_status IN ('clean', 'malicious', 'unavailable', 'not_scanned')",
            name="ck_scans_malware_scan_status",
        ),
        sa.Index("ix_scans_user_id", "user_id"),
        sa.Index("ix_scans_user_status", "user_id", "status"),
        sa.Index("ix_scans_user_created", "user_id", "created_at"),
        sa.Index("ix_scans_user_checksum", "user_id", "sha256_checksum"),
        sa.Index("ix_scans_expires_at", "expires_at"),
    )


class ScanEvent(Base):
    """Append-only state-transition log for a scan — the domain-specific
    counterpart to the global audit_logs table (which tracks account/auth
    events, not per-resource lifecycle detail)."""

    __tablename__ = "scan_events"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    actor: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="system")
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)

    scan: Mapped[Scan] = relationship(back_populates="events")

    __table_args__ = (
        sa.CheckConstraint("actor IN ('user', 'system')", name="ck_scan_events_actor"),
        sa.Index("ix_scan_events_scan_id", "scan_id"),
        sa.Index("ix_scan_events_occurred_at", "occurred_at"),
    )


class ProcessingJob(Base):
    """One row per preprocessing attempt-series for a scan. Executed in-process
    today (see api.scans.jobs, invoked via FastAPI BackgroundTasks) rather than
    by a real worker queue, but the row shape is written so a future Celery/RQ
    worker (or the AI-inference slice, job_type="ai_inference") can claim rows
    from this table without a schema change."""

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="preprocessing")
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    scan: Mapped[Scan] = relationship(back_populates="jobs")

    __table_args__ = (
        sa.CheckConstraint("status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_processing_jobs_status"),
        sa.Index("ix_processing_jobs_scan_id", "scan_id"),
        sa.Index("ix_processing_jobs_status", "status"),
    )
