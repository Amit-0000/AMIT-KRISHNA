from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import UserNotFoundError
from api.scans import repository as scans_repository
from api.user import repository
from api.user.models import User
from api.user.schemas import UpdateProfileRequest


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await repository.get_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError("User not found")
    return user


async def get_scan_count_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return await scans_repository.count_created_since(db, user_id=user_id, since=start_of_day)


async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UpdateProfileRequest) -> User:
    data.validate_display_name()
    user = await get_user(db, user_id)
    if data.display_name is not None:
        user = await repository.update_display_name(db, user, data.display_name)
    if data.onboarding_completed is not None:
        user = await repository.set_onboarding_completed(db, user, completed=data.onboarding_completed)
    return user
