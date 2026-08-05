from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.core.config import get_settings
from api.inference import repository
from api.inference.exceptions import ResultNotFoundError, ScanNotReadyForProcessingError
from api.inference.models import ModelVersion, ScanResult
from api.scans import repository as scans_repository
from api.scans.models import Scan
from api.scans.service import transition
from api.scans.state_machine import ScanStatus

AI_JOB_TYPE = "ai_inference"


async def start_processing(db: AsyncSession, scan: Scan) -> Scan:
    """POST /scans/{id}/process's synchronous half — validates the scan is
    actually READY_FOR_AI, transitions it into PREPARING_MODEL, and records a
    ProcessingJob row (job_type="ai_inference", the exact slot
    api.scans.models.ProcessingJob's docstring reserved for this slice — see
    that file). Mirrors api.scans.service.create_scan's own division of
    labor: cheap, request-scoped state changes happen here and are committed
    before responding; the actual pipeline work runs in the background job
    api.inference.jobs.run_ai_pipeline_job, scheduled by the router exactly
    like api.scans.router.create_scan schedules run_preprocessing_job."""
    if scan.status is not ScanStatus.READY_FOR_AI:
        raise ScanNotReadyForProcessingError(
            f"Scan {scan.id} is not ready for AI processing (current status: {scan.status.value})",
            details=[{"field": "status", "message": f"expected ready_for_ai, got {scan.status.value}"}],
        )

    scan = await transition(db, scan, ScanStatus.PREPARING_MODEL, actor="user", reason="AI processing requested")
    await scans_repository.create_job(
        db, scan_id=scan.id, job_type=AI_JOB_TYPE, max_attempts=get_settings().AI_STAGE_MAX_ATTEMPTS
    )
    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_PROCESSING_STARTED,
        outcome=AuditOutcome.SUCCESS,
        user_id=scan.user_id,
        details={"scan_id": str(scan.id)},
    )
    return scan


async def get_result(db: AsyncSession, scan: Scan) -> tuple[ScanResult, ModelVersion]:
    result = await repository.get_result_by_scan_id(db, scan.id)
    if result is None:
        raise ResultNotFoundError(f"No AI result available yet for scan {scan.id}")
    model_version = await repository.get_model_version_by_id(db, result.model_version_id)
    assert model_version is not None  # scan_results.model_version_id is NOT NULL + FK-enforced
    return result, model_version
