from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.middleware import client_ip
from api.core.responses import success_envelope
from api.scans.service import get_owned_scan_or_404
from api.sharing import service
from api.sharing.schemas import ShareCreateResponse
from api.user.models import User

router = APIRouter(prefix="/scans", tags=["sharing"])


@router.post("/{scan_id}/share")
async def create_share(
    scan_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    share = await service.create_share(
        db, scan, ip_address=client_ip(request), request_id=getattr(request.state, "request_id", None)
    )
    await db.commit()
    share_url = f"{get_settings().APP_BASE_URL}/r/{share.token}"
    return success_envelope(
        ShareCreateResponse(share_url=share_url, token=share.token, expires_at=share.expires_at).model_dump(
            mode="json"
        )
    )


@router.delete("/{scan_id}/share")
async def revoke_share(
    scan_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    scan = await get_owned_scan_or_404(db, scan_id, user)
    await service.revoke_share(
        db, scan, ip_address=client_ip(request), request_id=getattr(request.state, "request_id", None)
    )
    await db.commit()
    return success_envelope({})


@router.get("/shared/{token}")
async def get_shared_result(token: str, db: AsyncSession = Depends(get_db)):
    result = await service.get_shared_result(db, token)
    return success_envelope({"result": result.model_dump(mode="json")})
