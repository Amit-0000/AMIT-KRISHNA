from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.scans.models import ProcessingJob, Scan, ScanEvent
from api.scans.state_machine import ScanStatus

# Statuses that do NOT block a fresh upload of the same bytes from the same
# user — i.e. the previous attempt didn't end in a usable result, so a retry
# is a normal re-submission rather than an accidental duplicate.
_DUPLICATE_EXEMPT_STATUSES = frozenset(
    {ScanStatus.VALIDATION_FAILED, ScanStatus.UPLOAD_FAILED, ScanStatus.CANCELLED, ScanStatus.EXPIRED}
)


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    original_filename: str,
    file_extension: str,
    declared_mime_type: str | None,
) -> Scan:
    scan = Scan(
        user_id=user_id,
        original_filename=original_filename,
        file_extension=file_extension,
        declared_mime_type=declared_mime_type,
        storage_key="",  # filled in once `scan.id` is known — see api.scans.service.create_scan
    )
    db.add(scan)
    await db.flush()
    return scan


async def get_by_id(db: AsyncSession, scan_id: uuid.UUID) -> Scan | None:
    result = await db.execute(select(Scan).where(Scan.id == scan_id, Scan.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_owned(db: AsyncSession, scan_id: uuid.UUID, user_id: uuid.UUID) -> Scan | None:
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id, Scan.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def find_active_duplicate(
    db: AsyncSession, *, user_id: uuid.UUID, sha256_checksum: str, exclude_scan_id: uuid.UUID
) -> Scan | None:
    """`exclude_scan_id` must always be the scan currently being validated:
    by the time this runs it's already an inserted, non-terminal-status row
    with this same checksum, so without excluding it, every first-time
    upload would match — and "block" — itself."""
    result = await db.execute(
        select(Scan)
        .where(
            Scan.user_id == user_id,
            Scan.sha256_checksum == sha256_checksum,
            Scan.id != exclude_scan_id,
            Scan.deleted_at.is_(None),
            Scan.status.notin_(list(_DUPLICATE_EXEMPT_STATUSES)),
        )
        .order_by(Scan.created_at.desc())
    )
    return result.scalars().first()


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: ScanStatus | None,
    page: int,
    page_size: int,
    newest_first: bool,
) -> tuple[list[Scan], int]:
    filters = [Scan.user_id == user_id, Scan.deleted_at.is_(None)]
    if status is not None:
        filters.append(Scan.status == status)

    count_result = await db.execute(select(func.count()).select_from(Scan).where(*filters))
    total = count_result.scalar_one()

    order = Scan.created_at.desc() if newest_first else Scan.created_at.asc()
    result = await db.execute(
        select(Scan).where(*filters).order_by(order).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def count_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Scan).where(Scan.user_id == user_id, Scan.deleted_at.is_(None))
    )
    return result.scalar_one()


async def count_created_since(db: AsyncSession, *, user_id: uuid.UUID, since: datetime) -> int:
    """Backs both the Profile page's "today's usage" bar and the Dashboard's
    stats card — real usage in place of api.user.schemas.UserResponse's old
    hardcoded scan_count_today=0 placeholder."""
    result = await db.execute(
        select(func.count())
        .select_from(Scan)
        .where(Scan.user_id == user_id, Scan.created_at >= since, Scan.deleted_at.is_(None))
    )
    return result.scalar_one()


async def find_expired_candidates(db: AsyncSession, *, now: datetime) -> list[Scan]:
    result = await db.execute(
        select(Scan).where(
            Scan.status.in_([ScanStatus.QUEUED, ScanStatus.PREPROCESSING, ScanStatus.READY_FOR_AI]),
            Scan.expires_at.isnot(None),
            Scan.expires_at < now,
            Scan.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def record_event(
    db: AsyncSession,
    scan: Scan,
    *,
    from_status: ScanStatus | None,
    to_status: ScanStatus,
    reason: str | None,
    actor: str,
) -> ScanEvent:
    event = ScanEvent(
        scan_id=scan.id,
        from_status=from_status.value if from_status else None,
        to_status=to_status.value,
        reason=reason,
        actor=actor,
    )
    db.add(event)
    await db.flush()
    return event


async def create_job(db: AsyncSession, *, scan_id: uuid.UUID, job_type: str, max_attempts: int) -> ProcessingJob:
    job = ProcessingJob(scan_id=scan_id, job_type=job_type, max_attempts=max_attempts)
    db.add(job)
    await db.flush()
    return job


async def get_latest_job(db: AsyncSession, scan_id: uuid.UUID, *, job_type: str) -> ProcessingJob | None:
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.scan_id == scan_id, ProcessingJob.job_type == job_type)
        .order_by(ProcessingJob.created_at.desc())
    )
    return result.scalars().first()
