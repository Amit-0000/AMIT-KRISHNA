from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.sharing.models import ShareToken


async def create(
    db: AsyncSession, *, scan_id: uuid.UUID, user_id: uuid.UUID, token: str, expires_at: datetime | None
) -> ShareToken:
    share = ShareToken(scan_id=scan_id, user_id=user_id, token=token, expires_at=expires_at)
    db.add(share)
    await db.flush()
    return share


async def get_active_for_scan(db: AsyncSession, scan_id: uuid.UUID) -> ShareToken | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ShareToken)
        .where(
            ShareToken.scan_id == scan_id,
            ShareToken.revoked_at.is_(None),
            (ShareToken.expires_at.is_(None)) | (ShareToken.expires_at > now),
        )
        .order_by(ShareToken.created_at.desc())
    )
    return result.scalars().first()


async def get_by_token(db: AsyncSession, token: str) -> ShareToken | None:
    result = await db.execute(select(ShareToken).where(ShareToken.token == token))
    return result.scalar_one_or_none()


async def revoke(db: AsyncSession, share: ShareToken) -> ShareToken:
    share.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return share
