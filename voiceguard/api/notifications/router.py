from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import require_authenticated
from api.core.responses import success_envelope
from api.notifications import service
from api.notifications.schemas import NotificationResponse, UnreadCountResponse
from api.user.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    notifications = await service.list_notifications(db, user.id)
    # Returned as a bare list (not {"notifications": [...]}) — the frontend's
    # notificationApi.list() was scaffolded against this exact envelope shape
    # ahead of this slice landing (see frontend/src/services/api.ts).
    return success_envelope([NotificationResponse.from_notification(n).model_dump(mode="json") for n in notifications])


@router.get("/unread-count")
async def get_unread_count(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    count = await service.unread_count(db, user.id)
    return success_envelope(UnreadCountResponse(unread_count=count).model_dump(mode="json"))


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    notification = await service.mark_read(db, notification_id, user.id)
    await db.commit()
    return success_envelope({"notification": NotificationResponse.from_notification(notification).model_dump(mode="json")})


@router.post("/mark-all-read")
async def mark_all_read(user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)):
    await service.mark_all_read(db, user.id)
    await db.commit()
    return success_envelope({})


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID, user: User = Depends(require_authenticated), db: AsyncSession = Depends(get_db)
):
    await service.delete_notification(db, notification_id, user.id)
    await db.commit()
    return success_envelope({})
