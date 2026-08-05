from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import NotFoundError
from api.notifications import repository
from api.notifications.models import Notification


class NotificationNotFoundError(NotFoundError):
    code = "NOTIFICATION_NOT_FOUND"


async def list_notifications(db: AsyncSession, user_id: uuid.UUID) -> list[Notification]:
    return await repository.list_for_user(db, user_id)


async def get_owned_notification_or_404(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = await repository.get_owned(db, notification_id, user_id)
    if notification is None:
        raise NotificationNotFoundError("Notification not found")
    return notification


async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = await get_owned_notification_or_404(db, notification_id, user_id)
    return await repository.mark_read(db, notification)


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> None:
    await repository.mark_all_read(db, user_id)


async def delete_notification(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
    notification = await get_owned_notification_or_404(db, notification_id, user_id)
    await repository.delete(db, notification)


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    return await repository.count_unread(db, user_id)
