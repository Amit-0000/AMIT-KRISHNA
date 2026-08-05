from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.notifications.models import Notification


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    action_url: str | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, type=type, title=title, body=body, action_url=action_url)
    db.add(notification)
    await db.flush()
    return notification


async def list_for_user(db: AsyncSession, user_id: uuid.UUID, *, limit: int = 100) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def mark_read(db: AsyncSession, notification: Notification) -> Notification:
    notification.read = True
    await db.flush()
    return notification


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(Notification).where(Notification.user_id == user_id, Notification.read.is_(False)).values(read=True)
    )


async def delete(db: AsyncSession, notification: Notification) -> None:
    await db.delete(notification)
    await db.flush()


async def count_unread(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read.is_(False))
    )
    return result.scalar_one()
