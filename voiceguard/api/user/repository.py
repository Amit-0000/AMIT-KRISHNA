from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.user.models import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, email: str, password_hash: str | None, display_name: str | None) -> User:
    user = User(email=email.lower().strip(), password_hash=password_hash, display_name=display_name)
    db.add(user)
    await db.flush()
    return user


async def update_display_name(db: AsyncSession, user: User, display_name: str) -> User:
    user.display_name = display_name.strip()
    await db.flush()
    return user


async def set_onboarding_completed(db: AsyncSession, user: User, *, completed: bool) -> User:
    user.onboarding_completed = completed
    await db.flush()
    return user


async def set_email_verified(db: AsyncSession, user: User, *, verified: bool = True) -> User:
    user.email_verified = verified
    await db.flush()
    return user


async def set_password_hash(db: AsyncSession, user: User, password_hash: str) -> User:
    user.password_hash = password_hash
    await db.flush()
    return user
