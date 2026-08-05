from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import service as auth_service
from api.auth.schemas import ChangePasswordRequest
from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.responses import success_envelope
from api.user import service as user_service
from api.user.models import User
from api.user.schemas import UpdateProfileRequest, UserResponse

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile")
async def get_profile(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    scan_count_today = await user_service.get_scan_count_today(db, user.id)
    return success_envelope(
        {"user": UserResponse.from_user(user, scan_count_today=scan_count_today).model_dump(mode="json")}
    )


@router.patch("/profile")
async def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    updated = await user_service.update_user(db, user.id, payload)
    await db.commit()
    scan_count_today = await user_service.get_scan_count_today(db, updated.id)
    return success_envelope(
        {"user": UserResponse.from_user(updated, scan_count_today=scan_count_today).model_dump(mode="json")}
    )


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(
        db, user=user, current_password=payload.current_password, new_password=payload.new_password
    )
    await db.commit()
    return success_envelope({})
