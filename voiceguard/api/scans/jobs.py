from __future__ import annotations

import logging
import uuid
import wave
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.core.config import get_settings
from api.core.database import get_engine, get_session_factory
from api.core.storage import LocalStorageBackend, get_storage_backend
from api.scans import repository
from api.scans.models import Scan
from api.scans.service import expire_stale_scans, transition
from api.scans.state_machine import ScanStatus

logger = logging.getLogger("voiceguard.scans")


async def _run_preprocessing_once(scan: Scan) -> None:
    """Stub preprocessing: confirm the file is actually readable from storage
    and best-effort-extract audio metadata for real .wav files using only the
    stdlib `wave` module (no audio-decoding libraries are installed in this
    image — see api/requirements.txt — real waveform/feature extraction
    belongs to the AI-inference slice). Raises on any hard failure so the
    caller's retry loop can retry it; a wav file that merely can't be parsed
    for metadata is not fatal (metadata is best-effort, not a requirement to
    reach READY_FOR_AI)."""
    storage = get_storage_backend()
    if not await storage.exists(scan.storage_key):
        raise FileNotFoundError(f"storage key {scan.storage_key!r} not found")

    metadata: dict[str, object] = {}
    if scan.file_extension == ".wav" and isinstance(storage, LocalStorageBackend):
        path = storage.resolve_path(scan.storage_key)
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    scan.duration_seconds = round(frames / float(rate), 3)
                metadata["sample_rate"] = rate
                metadata["channels"] = wf.getnchannels()
                metadata["sample_width_bytes"] = wf.getsampwidth()
        except (wave.Error, EOFError, OSError) as exc:
            logger.info("wav_metadata_extraction_skipped", extra={"scan_id": str(scan.id), "error": str(exc)})

    scan.scan_metadata = metadata or None


async def run_preprocessing_job(scan_id: uuid.UUID, bind: AsyncEngine | None = None) -> None:
    """Invoked as a FastAPI BackgroundTask right after a successful upload
    response is prepared, passed the *same engine the request's session was
    bound to* (see api.scans.router.create_scan) rather than reaching for the
    global engine — a real client's request session is already closed by the
    time this actually runs (Starlette runs background tasks right after the
    response bytes are sent), but it must still be the same database (this
    is also what makes the job runnable against the isolated per-test SQLite
    engine rather than silently querying a different, real one). Drives
    QUEUED -> PREPROCESSING -> READY_FOR_AI, retrying up to the job's
    max_attempts before giving up and marking the scan FAILED."""
    engine = bind if bind is not None else get_engine()
    async with AsyncSession(bind=engine, expire_on_commit=False) as db:
        scan = await repository.get_by_id(db, scan_id)
        if scan is None or scan.status != ScanStatus.QUEUED:
            return  # cancelled/deleted/expired before we got here

        job = await repository.get_latest_job(db, scan.id, job_type="preprocessing")

        await transition(db, scan, ScanStatus.PREPROCESSING, actor="system")
        await db.commit()

        max_attempts = job.max_attempts if job else get_settings().PREPROCESSING_MAX_ATTEMPTS
        last_error: str | None = None

        for attempt in range(1, max_attempts + 1):
            if job is not None:
                job.attempts = attempt
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                await db.commit()
            try:
                await _run_preprocessing_once(scan)
            except Exception as exc:  # noqa: BLE001 - stub preprocessing must never crash the background task
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "preprocessing_attempt_failed",
                    extra={"scan_id": str(scan_id), "attempt": attempt, "error": last_error},
                )
                if job is not None:
                    job.last_error = last_error
                    await db.commit()
                continue
            else:
                if job is not None:
                    job.status = "succeeded"
                    job.finished_at = datetime.now(timezone.utc)
                    await db.flush()
                await transition(db, scan, ScanStatus.READY_FOR_AI, actor="system")
                await db.commit()
                return

        scan.retry_count = max_attempts
        scan.error_code = "PREPROCESSING_FAILED"
        scan.error_message = last_error or "preprocessing failed"
        if job is not None:
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            await db.flush()
        await transition(db, scan, ScanStatus.FAILED, actor="system", reason=last_error)
        await db.commit()


async def expire_stale_scans_on_startup() -> int:
    """Called once from api.main's lifespan on process boot. See
    api.scans.service.expire_stale_scans for why this is a startup stopgap
    rather than a real periodic job."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        count = await expire_stale_scans(db)
        await db.commit()
        return count
