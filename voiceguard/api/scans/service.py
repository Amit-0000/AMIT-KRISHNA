from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.core.config import get_settings
from api.core.exceptions import (
    DuplicateUploadError,
    EmptyFileError,
    FileTooLargeError,
    FileTooSmallError,
    MalwareDetectedError,
    MalwareScanUnavailableError,
    ScanNotFoundError,
    UploadFailedError,
)
from api.core.storage import StorageBackend, get_storage_backend
from api.scans import malware_scan, repository
from api.scans.malware_scan import MalwareScanStatus
from api.scans.models import Scan
from api.scans.state_machine import ScanStatus, is_terminal, validate_transition
from api.scans.validation import validate_upload_request, validate_upload_size
from api.user.models import User

UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def get_owned_scan_or_404(db: AsyncSession, scan_id: uuid.UUID, user: User) -> Scan:
    """Shared by every router that operates on a single scan by id — this
    slice's own api.scans.router and api.inference.router alike. Same shape
    for "doesn't exist" and "exists but belongs to someone else": a 403 here
    would confirm the id is valid for another account, an enumeration leak
    (BATCH_04 S5.3 applies the same principle to login)."""
    scan = await repository.get_owned(db, scan_id, user.id)
    if scan is None:
        raise ScanNotFoundError("Scan not found")
    return scan


async def transition(
    db: AsyncSession,
    scan: Scan,
    target: ScanStatus,
    *,
    reason: str | None = None,
    actor: str = "system",
) -> Scan:
    """The only place scan.status is ever assigned. Validates the edge, stamps
    the matching lifecycle timestamp, and appends a scan_events row — so
    every transition, everywhere in the codebase, is both enforced and
    audited by construction rather than by convention."""
    validate_transition(scan.status, target)
    previous = scan.status
    scan.status = target
    _stamp_timestamp(scan, target)
    await db.flush()
    await repository.record_event(db, scan, from_status=previous, to_status=target, reason=reason, actor=actor)
    return scan


def _stamp_timestamp(scan: Scan, target: ScanStatus) -> None:
    now = datetime.now(timezone.utc)
    if target is ScanStatus.QUEUED:
        scan.queued_at = now
        # Single deadline covering both "waiting for preprocessing" (QUEUED)
        # and, once preprocessing succeeds, "waiting for the AI engine to
        # claim it" (READY_FOR_AI) — see expire_stale_scans.
        scan.expires_at = now + timedelta(hours=get_settings().SCAN_EXPIRY_HOURS)
    elif target is ScanStatus.PREPROCESSING:
        scan.preprocessing_started_at = now
    elif target is ScanStatus.READY_FOR_AI:
        scan.ready_at = now
    elif target is ScanStatus.COMPLETED:
        scan.completed_at = now
    elif target is ScanStatus.FAILED:
        scan.failed_at = now
    elif target is ScanStatus.CANCELLED:
        scan.cancelled_at = now
    # VALIDATION_FAILED / UPLOAD_FAILED / EXPIRED have no dedicated timestamp
    # column — `updated_at` (onupdate) plus the scan_events row already this
    # transition produces are the record of when/why it happened.


async def _fail_and_persist(
    db: AsyncSession,
    scan: Scan,
    *,
    target: ScanStatus,
    error_code: str,
    error_message: str,
    reason: str,
) -> None:
    """Used only on create_scan's failure branches. Commits immediately —
    rather than leaving the commit to the router, which only runs on the
    success path — so this terminal failure state survives
    api.core.database.get_db's rollback-on-exception. Same reasoning as the
    write_audit_log fix: a record of what happened must outlive the
    exception that reports it."""
    scan.error_code = error_code
    scan.error_message = error_message
    await transition(db, scan, target, reason=reason, actor="system")
    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_SUBMITTED,
        outcome=AuditOutcome.FAILURE,
        user_id=scan.user_id,
        details={"scan_id": str(scan.id), "error_code": error_code},
    )
    await db.commit()


async def store_upload(
    upload_file: UploadFile,
    storage_key: str,
    storage: StorageBackend,
    *,
    max_size_bytes: int,
) -> tuple[int, str]:
    """Streams `upload_file` into `storage`, hashing as it goes. Enforces
    `max_size_bytes` *while* streaming — the DOS protection for this
    endpoint: an oversized upload is aborted the moment it crosses the limit,
    never fully buffered first. Returns (total_bytes_written, sha256_hex);
    raises FileTooLargeError (after deleting the partial write) or
    UploadFailedError on a genuine I/O fault."""
    hasher = hashlib.sha256()
    total_size = 0
    size_exceeded = False

    async def _chunks() -> AsyncIterator[bytes]:
        nonlocal total_size, size_exceeded
        while True:
            chunk = await upload_file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                return
            total_size += len(chunk)
            if total_size > max_size_bytes:
                size_exceeded = True
                return
            hasher.update(chunk)
            yield chunk

    try:
        await storage.save_stream(storage_key, _chunks())
    except OSError as exc:
        raise UploadFailedError(f"Failed to store upload: {exc}") from exc

    if size_exceeded:
        await storage.delete(storage_key)
        raise FileTooLargeError(f"File is too large (maximum {max_size_bytes} bytes).")

    return total_size, hasher.hexdigest()


async def create_scan(db: AsyncSession, *, user: User, upload_file: UploadFile) -> Scan:
    """The full upload pipeline for one multipart file: validate request
    metadata -> stream+hash to storage -> validate size -> duplicate check ->
    malware-scan integration point -> QUEUED + a preprocessing job row.
    Every failure branch leaves behind a terminal-state scan row (persisted
    via _fail_and_persist) rather than just an error response, so a failed
    attempt is still visible in the user's scan history."""
    settings = get_settings()
    storage = get_storage_backend()

    validated = validate_upload_request(upload_file.filename, upload_file.content_type)

    scan = await repository.create(
        db,
        user_id=user.id,
        original_filename=validated.original_filename,
        file_extension=validated.extension,
        declared_mime_type=validated.declared_mime_type,
    )
    # storage_key depends on scan.id, which only exists after the initial flush.
    scan.storage_key = f"{scan.id}{validated.extension}"
    await db.flush()

    await transition(db, scan, ScanStatus.VALIDATING, actor="system")
    await transition(db, scan, ScanStatus.UPLOADING, actor="system")

    try:
        size, checksum = await store_upload(
            upload_file, scan.storage_key, storage, max_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES
        )
    except FileTooLargeError as exc:
        await _fail_and_persist(
            db, scan, target=ScanStatus.VALIDATION_FAILED,
            error_code=exc.code, error_message=exc.message, reason="file exceeds maximum size",
        )
        raise
    except UploadFailedError as exc:
        await _fail_and_persist(
            db, scan, target=ScanStatus.UPLOAD_FAILED,
            error_code=exc.code, error_message=exc.message, reason="storage write failed",
        )
        raise

    scan.file_size_bytes = size
    scan.sha256_checksum = checksum
    await db.flush()

    try:
        validate_upload_size(size, min_bytes=settings.MIN_UPLOAD_SIZE_BYTES, max_bytes=settings.MAX_UPLOAD_SIZE_BYTES)
    except (EmptyFileError, FileTooSmallError) as exc:
        await storage.delete(scan.storage_key)
        await _fail_and_persist(
            db, scan, target=ScanStatus.VALIDATION_FAILED,
            error_code=exc.code, error_message=exc.message, reason="failed size validation",
        )
        raise

    duplicate = await repository.find_active_duplicate(
        db, user_id=user.id, sha256_checksum=checksum, exclude_scan_id=scan.id
    )
    if duplicate is not None:
        await storage.delete(scan.storage_key)
        exc = DuplicateUploadError(
            "An identical file has already been uploaded.",
            details=[{"field": "file", "message": f"duplicate of scan {duplicate.id}"}],
        )
        await _fail_and_persist(
            db, scan, target=ScanStatus.VALIDATION_FAILED,
            error_code=exc.code, error_message=exc.message, reason=f"duplicate of scan {duplicate.id}",
        )
        raise exc

    scan_result = await malware_scan.scan_file(storage, scan.storage_key)
    if scan_result.status is MalwareScanStatus.MALICIOUS:
        await storage.delete(scan.storage_key)
        exc = MalwareDetectedError("The uploaded file was flagged as malicious and cannot be processed.")
        await _fail_and_persist(
            db, scan, target=ScanStatus.VALIDATION_FAILED,
            error_code=exc.code, error_message=exc.message,
            reason=f"malware scan ({scan_result.engine}) detected: {scan_result.detail}",
        )
        raise exc
    if scan_result.status is MalwareScanStatus.UNAVAILABLE:
        await storage.delete(scan.storage_key)
        exc = MalwareScanUnavailableError("The malware scanner is temporarily unavailable. Please try again shortly.")
        await _fail_and_persist(
            db, scan, target=ScanStatus.UPLOAD_FAILED,
            error_code=exc.code, error_message=exc.message,
            reason=f"malware scan unavailable ({scan_result.engine}): {scan_result.detail}",
        )
        raise exc

    await transition(db, scan, ScanStatus.QUEUED, actor="system")
    await repository.create_job(
        db, scan_id=scan.id, job_type="preprocessing", max_attempts=settings.PREPROCESSING_MAX_ATTEMPTS
    )
    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_SUBMITTED,
        outcome=AuditOutcome.SUCCESS,
        user_id=user.id,
        details={"scan_id": str(scan.id), "size_bytes": size, "extension": validated.extension},
    )
    return scan


async def cancel_scan(db: AsyncSession, scan: Scan) -> Scan:
    """validate_transition (inside transition()) is what actually makes
    cancelling an already-terminal scan impossible — raises
    InvalidScanStateError rather than needing a redundant is_terminal check
    here."""
    scan = await transition(db, scan, ScanStatus.CANCELLED, actor="user", reason="cancelled by user")
    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_CANCELLED,
        outcome=AuditOutcome.SUCCESS,
        user_id=scan.user_id,
        details={"scan_id": str(scan.id)},
    )
    return scan


async def delete_scan(db: AsyncSession, scan: Scan) -> Scan:
    if not is_terminal(scan.status):
        await transition(db, scan, ScanStatus.CANCELLED, actor="user", reason="deleted by user")
    scan.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    storage = get_storage_backend()
    await storage.delete(scan.storage_key)

    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_DELETED,
        outcome=AuditOutcome.SUCCESS,
        user_id=scan.user_id,
        details={"scan_id": str(scan.id)},
    )
    return scan


async def expire_stale_scans(db: AsyncSession) -> int:
    """Transitions QUEUED/PREPROCESSING/READY_FOR_AI scans whose expires_at
    has passed to EXPIRED. Not wired to a scheduler (no Celery beat / cron
    exists in this stack) — called from api.scans.jobs.expire_stale_scans_on_startup
    at process boot as a stopgap, and available here for a future periodic
    job or admin endpoint to call directly."""
    candidates = await repository.find_expired_candidates(db, now=datetime.now(timezone.utc))
    for scan in candidates:
        await transition(db, scan, ScanStatus.EXPIRED, actor="system", reason="expiry deadline passed")
    return len(candidates)
