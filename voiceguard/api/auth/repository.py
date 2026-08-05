from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.models import EmailVerification, PasswordResetToken, RefreshToken

# ── Refresh tokens ───────────────────────────────────────────────────────────


async def create_refresh_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None,
    ip_hash: str | None,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at, user_agent=user_agent, ip_hash=ip_hash
    )
    db.add(token)
    await db.flush()
    return token


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    token.revoked = True
    token.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def revoke_all_refresh_tokens_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True, revoked_at=datetime.now(timezone.utc))
    )
    await db.flush()


async def touch_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    token.last_used_at = datetime.now(timezone.utc)
    await db.flush()


# ── Email verification ──────────────────────────────────────────────────────


async def invalidate_pending_email_verifications(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(EmailVerification)
        .where(EmailVerification.user_id == user_id, EmailVerification.used.is_(False))
        .values(used=True, used_at=datetime.now(timezone.utc))
    )
    await db.flush()


async def create_email_verification(
    db: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime, email_address: str
) -> EmailVerification:
    record = EmailVerification(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at, email_address=email_address
    )
    db.add(record)
    await db.flush()
    return record


async def get_email_verification_by_hash(db: AsyncSession, token_hash: str) -> EmailVerification | None:
    result = await db.execute(select(EmailVerification).where(EmailVerification.token_hash == token_hash))
    return result.scalar_one_or_none()


async def mark_email_verification_used(db: AsyncSession, record: EmailVerification) -> None:
    record.used = True
    record.used_at = datetime.now(timezone.utc)
    await db.flush()


# ── Password reset ───────────────────────────────────────────────────────────


async def invalidate_pending_password_resets(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used.is_(False))
        .values(used=True, used_at=datetime.now(timezone.utc))
    )
    await db.flush()


async def create_password_reset_token(
    db: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime, ip_hash: str | None
) -> PasswordResetToken:
    record = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at, ip_hash=ip_hash)
    db.add(record)
    await db.flush()
    return record


async def get_password_reset_token_by_hash(db: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def mark_password_reset_used(db: AsyncSession, record: PasswordResetToken) -> None:
    record.used = True
    record.used_at = datetime.now(timezone.utc)
    await db.flush()
