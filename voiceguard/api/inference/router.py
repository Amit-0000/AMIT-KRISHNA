from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.responses import success_envelope
from api.inference import model_registry, repository, service
from api.inference.jobs import run_ai_pipeline_job
from api.inference.schemas import (
    ModelVersionResponse,
    ProcessResponse,
    ScanExplanationResponse,
    ScanResultResponse,
    ScanTechnicalResponse,
    StageTimingEntry,
)
from api.scans.service import get_owned_scan_or_404
from api.user.models import User

router = APIRouter(prefix="/scans", tags=["inference"])
models_router = APIRouter(prefix="/models", tags=["models"])


@router.post("/{scan_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_scan(
    scan_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Starts the AI Processing Pipeline for a READY_FOR_AI scan. Mirrors
    api.scans.router.create_scan's own request/background split: this
    request only validates + transitions to PREPARING_MODEL and returns;
    api.inference.jobs.run_ai_pipeline_job does the actual work afterward."""
    scan = await get_owned_scan_or_404(db, scan_id, user)
    scan = await service.start_processing(db, scan)
    await db.commit()
    background_tasks.add_task(run_ai_pipeline_job, scan.id, db.bind)
    return success_envelope({"scan": ProcessResponse(scan_id=scan.id, status=scan.status.value).model_dump(mode="json")})


@router.get("/{scan_id}/result")
async def get_scan_result(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    result, model_version = await service.get_result(db, scan)
    return success_envelope({"result": ScanResultResponse.from_result(result, model_version).model_dump(mode="json")})


@router.get("/{scan_id}/technical")
async def get_scan_technical(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    result, model_version = await service.get_result(db, scan)
    metrics = await repository.list_metrics_for_scan(db, scan.id)
    stage_timings = [
        StageTimingEntry(stage=m.stage, attempt=m.attempt, status=m.status, duration_ms=m.duration_ms)
        for m in metrics
    ]
    return success_envelope(
        {
            "technical": ScanTechnicalResponse.from_result(result, model_version, stage_timings).model_dump(
                mode="json"
            )
        }
    )


@router.get("/{scan_id}/explanation")
async def get_scan_explanation(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    result, _ = await service.get_result(db, scan)
    return success_envelope({"explanation": ScanExplanationResponse.from_result(result).model_dump(mode="json")})


@models_router.get("")
async def list_models(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    versions = await repository.list_model_versions(db)
    return success_envelope(
        {"models": [ModelVersionResponse.model_validate(v).model_dump(mode="json") for v in versions]}
    )


@models_router.get("/current")
async def current_model(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    health = await model_registry.health_check(db)
    return success_envelope({"model": health})
