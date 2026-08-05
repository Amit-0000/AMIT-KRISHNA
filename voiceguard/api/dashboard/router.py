from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.responses import success_envelope
from api.dashboard import service
from api.user.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    data = await service.get_dashboard(db, user.id)
    return success_envelope(data.model_dump(mode="json"))


@router.get("/recent-scans")
async def get_recent_scans(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    scans = await service.get_recent_scans(db, user.id)
    return success_envelope([s.model_dump(mode="json") for s in scans])
