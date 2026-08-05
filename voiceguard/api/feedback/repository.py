from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.feedback.models import Feedback


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    category: str,
    message: str,
    scan_id: str | None,
    email: str | None,
    browser: str | None,
    application_version: str | None,
    priority: str,
) -> Feedback:
    feedback = Feedback(
        user_id=user_id,
        category=category,
        message=message,
        scan_id=scan_id,
        email=email,
        browser=browser,
        application_version=application_version,
        priority=priority,
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def list_paginated(db: AsyncSession, *, page: int, page_size: int) -> tuple[list[Feedback], int]:
    count_result = await db.execute(select(func.count()).select_from(Feedback))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total
