from __future__ import annotations

import math
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.rate_limit import require_scan_create_rate_limit
from api.core.responses import success_envelope
from api.scans import repository
from api.scans import service as scan_service
from api.scans.jobs import run_preprocessing_job
from api.scans.schemas import PaginationMeta, ScanResponse, ScanStatusResponse
from api.scans.service import get_owned_scan_or_404
from api.scans.state_machine import ScanStatus
from api.user.models import User

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_scan_create_rate_limit)])
async def create_scan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    scan = await scan_service.create_scan(db, user=user, upload_file=file)
    await db.commit()
    background_tasks.add_task(run_preprocessing_job, scan.id, db.bind)
    return success_envelope({"scan": ScanResponse.from_scan(scan).model_dump(mode="json")})


@router.get("")
async def list_scans(
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
    status_filter: ScanStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Literal["created_at", "-created_at"] = Query("-created_at"),
):
    scans, total = await repository.list_for_user(
        db,
        user_id=user.id,
        status=status_filter,
        page=page,
        page_size=page_size,
        newest_first=sort == "-created_at",
    )
    meta = PaginationMeta(
        page=page, page_size=page_size, total=total, total_pages=max(1, math.ceil(total / page_size))
    ).model_dump()
    return success_envelope(
        {"scans": [ScanResponse.from_scan(s).model_dump(mode="json") for s in scans]}, meta=meta
    )


@router.get("/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    return success_envelope({"scan": ScanResponse.from_scan(scan).model_dump(mode="json")})


@router.get("/{scan_id}/status")
async def get_scan_status(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    return success_envelope({"scan": ScanStatusResponse.from_scan(scan).model_dump(mode="json")})


@router.post("/{scan_id}/cancel")
async def cancel_scan(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    scan = await scan_service.cancel_scan(db, scan)
    await db.commit()
    return success_envelope({"scan": ScanResponse.from_scan(scan).model_dump(mode="json")})


@router.delete("/{scan_id}")
async def delete_scan(
    scan_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    await scan_service.delete_scan(db, scan)
    await db.commit()
    return success_envelope({})
