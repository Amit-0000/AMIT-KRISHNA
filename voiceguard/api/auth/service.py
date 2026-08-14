from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import repository
from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.core.config import get_settings
from api.core.email import send_password_changed_email, send_password_reset_email, send_verification_email
from api.core.exceptions import (
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordValidationError,
    SessionExpiredError,
)
from api.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    is_expired,
    validate_password_strength,
    verify_password,
)
from api.notifications import repository as notifications_repository
from api.user import repository as user_repository
from api.user.models import User

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
GUEST_COOKIE_NAME = "guest_token"
# Scoped to /api/v1/auth (not just /api/v1/auth/refresh) so the cookie is also
# sent on POST /api/v1/auth/logout — a Path of just .../refresh means no
# spec-compliant client ever sends it to logout, so logout could never
# actually revoke the session server-side (it always saw refresh_raw=None).
REFRESH_COOKIE_PATH = "/api/v1/auth"
EMAIL_VERIFICATION_TTL = timedelta(hours=24)
PASSWORD_RESET_TTL = timedelta(hours=1)


def _cookie_kwargs(*, path: str, max_age: int) -> dict[str, object]:
    settings = get_settings()
    return {
        "httponly": True,
        "samesite": "strict",
        "secure": settings.COOKIE_SECURE,
        "path": path,
        "max_age": max_age,
    }


def set_session_cookies(response: Response, *, access_token: str, refresh_token_raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE_NAME, access_token, **_cookie_kwargs(path="/", max_age=settings.JWT_ACCESS_TOKEN_TTL_S)
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token_raw,
        **_cookie_kwargs(path=REFRESH_COOKIE_PATH, max_age=settings.JWT_REFRESH_TOKEN_TTL_S),
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


async def _issue_session(
    db: AsyncSession, user: User, *, user_agent: str | None, ip_hash: str | None
) -> tuple[str, str]:
    settings = get_settings()
    access_token = create_access_token(user_id=str(user.id), role=user.role.value, email_verified=user.email_verified)
    refresh_token_raw = generate_opaque_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_REFRESH_TOKEN_TTL_S)
    await repository.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_token_raw),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_hash=ip_hash,
    )
    await write_audit_log(
        db, event_type=AuditEventType.REFRESH_TOKEN_ISSUED, outcome=AuditOutcome.SUCCESS, user_id=user.id
    )
    return access_token, refresh_token_raw


async def register_user(
    db: AsyncSession, *, email: str, password: str, display_name: str, ip_hash: str | None
) -> User:
    email_normalized = email.lower().strip()

    errors = validate_password_strength(password, email=email_normalized)
    if errors:
        raise PasswordValidationError(errors[0], details=[{"field": "password", "message": e} for e in errors])

    existing = await user_repository.get_by_email(db, email_normalized)
    if existing is not None:
        # BATCH_04 §5.3: identical externally-visible error to a generic
        # validation failure would be ideal for enumeration resistance, but
        # the frontend contract requires a distinguishable field error here;
        # we accept that documented tradeoff (see report) rather than silently
        # deviate from the given API contract.
        raise EmailAlreadyExistsError(
            "An account with this email already exists", details=[{"field": "email", "message": "Email already registered"}]
        )

    user = await user_repository.create(
        db, email=email_normalized, password_hash=await hash_password(password), display_name=display_name
    )

    raw_token = generate_opaque_token()
    await repository.create_email_verification(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + EMAIL_VERIFICATION_TTL,
        email_address=email_normalized,
    )
    settings = get_settings()
    verification_url = f"{settings.APP_BASE_URL}/verify-email?token={raw_token}"
    await send_verification_email(to=email_normalized, verification_url=verification_url)

    await write_audit_log(db, event_type=AuditEventType.USER_REGISTERED, outcome=AuditOutcome.SUCCESS, user_id=user.id, ip_address=None)
    return user


async def login_user(
    db: AsyncSession, *, email: str, password: str, user_agent: str | None, ip_hash: str | None
) -> tuple[User, str, str]:
    email_normalized = email.lower().strip()
    user = await user_repository.get_by_email(db, email_normalized)

    # Constant-shape failure path (BATCH_04 §5.3 login_user step 2-3): always
    # run a bcrypt check even for a nonexistent user, against a fixed dummy
    # hash, so response timing doesn't leak whether the email exists.
    dummy_hash = "$2b$12$CwaG5still.Not.A.Real.Hash.Just.For.TimingXXXXXXXXXXXX"
    password_ok = await verify_password(password, user.password_hash if user and user.password_hash else dummy_hash)

    if user is None or user.password_hash is None or not password_ok:
        await write_audit_log(
            db,
            event_type=AuditEventType.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            user_id=user.id if user else None,
            details={"reason": "invalid_credentials"},
        )
        raise InvalidCredentialsError("Incorrect email or password")

    if not user.email_verified:
        raise EmailNotVerifiedError("Please verify your email address before logging in")

    access_token, refresh_token_raw = await _issue_session(db, user, user_agent=user_agent, ip_hash=ip_hash)
    await write_audit_log(db, event_type=AuditEventType.LOGIN_SUCCESS, outcome=AuditOutcome.SUCCESS, user_id=user.id)
    return user, access_token, refresh_token_raw


async def logout(db: AsyncSession, *, refresh_token_raw: str | None, user_id: uuid.UUID | None) -> None:
    if refresh_token_raw:
        token = await repository.get_refresh_token_by_hash(db, hash_token(refresh_token_raw))
        if token is not None and not token.revoked:
            await repository.revoke_refresh_token(db, token)
    await write_audit_log(db, event_type=AuditEventType.LOGOUT, outcome=AuditOutcome.SUCCESS, user_id=user_id)


async def rotate_refresh_token(
    db: AsyncSession, *, refresh_token_raw: str, user_agent: str | None, ip_hash: str | None
) -> tuple[User, str, str]:
    token_hash = hash_token(refresh_token_raw)
    token = await repository.get_refresh_token_by_hash(db, token_hash)

    if token is None or is_expired(token.expires_at):
        raise SessionExpiredError("Session expired, please log in again")

    if token.revoked:
        # Reuse of an already-rotated/revoked token: signal of theft. Nuke
        # every session for this user (BATCH_04 §5.3 rotate_refresh_token step 4).
        await repository.revoke_all_refresh_tokens_for_user(db, token.user_id)
        await write_audit_log(
            db,
            event_type=AuditEventType.REFRESH_TOKEN_REUSE_DETECTED,
            outcome=AuditOutcome.FAILURE,
            user_id=token.user_id,
        )
        raise SessionExpiredError("Session invalidated for security reasons, please log in again")

    user = await user_repository.get_by_id(db, token.user_id)
    if user is None:
        raise SessionExpiredError("Session expired, please log in again")

    await repository.revoke_refresh_token(db, token)
    await repository.touch_refresh_token(db, token)

    access_token, refresh_token_raw_new = await _issue_session(db, user, user_agent=user_agent, ip_hash=ip_hash)
    await write_audit_log(
        db, event_type=AuditEventType.REFRESH_TOKEN_ROTATED, outcome=AuditOutcome.SUCCESS, user_id=user.id
    )
    return user, access_token, refresh_token_raw_new


async def verify_email(db: AsyncSession, *, raw_token: str) -> User:
    record = await repository.get_email_verification_by_hash(db, hash_token(raw_token))
    if record is None or record.used or is_expired(record.expires_at):
        raise InvalidTokenError("This verification link is invalid or has expired")

    user = await user_repository.get_by_id(db, record.user_id)
    if user is None:
        raise InvalidTokenError("This verification link is invalid or has expired")

    await repository.mark_email_verification_used(db, record)
    user = await user_repository.set_email_verified(db, user)
    await write_audit_log(db, event_type=AuditEventType.EMAIL_VERIFIED, outcome=AuditOutcome.SUCCESS, user_id=user.id)
    return user


async def resend_verification(db: AsyncSession, *, email: str) -> None:
    email_normalized = email.lower().strip()
    user = await user_repository.get_by_email(db, email_normalized)
    # Same-response-regardless-of-existence posture as forgot_password.
    if user is None or user.email_verified:
        return

    await repository.invalidate_pending_email_verifications(db, user.id)
    raw_token = generate_opaque_token()
    await repository.create_email_verification(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + EMAIL_VERIFICATION_TTL,
        email_address=email_normalized,
    )
    settings = get_settings()
    verification_url = f"{settings.APP_BASE_URL}/verify-email?token={raw_token}"
    await send_verification_email(to=email_normalized, verification_url=verification_url)


async def forgot_password(db: AsyncSession, *, email: str, ip_hash: str | None) -> None:
    email_normalized = email.lower().strip()
    user = await user_repository.get_by_email(db, email_normalized)
    if user is None:
        return  # Enumeration resistance (BATCH_04 §5.3 forgot_password philosophy)

    await repository.invalidate_pending_password_resets(db, user.id)
    raw_token = generate_opaque_token()
    await repository.create_password_reset_token(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + PASSWORD_RESET_TTL,
        ip_hash=ip_hash,
    )
    settings = get_settings()
    reset_url = f"{settings.APP_BASE_URL}/reset-password?token={raw_token}"
    await send_password_reset_email(to=email_normalized, reset_url=reset_url)
    await write_audit_log(
        db, event_type=AuditEventType.PASSWORD_RESET_REQUESTED, outcome=AuditOutcome.SUCCESS, user_id=user.id
    )


async def reset_password(db: AsyncSession, *, raw_token: str, new_password: str) -> User:
    record = await repository.get_password_reset_token_by_hash(db, hash_token(raw_token))
    if record is None or record.used or is_expired(record.expires_at):
        raise InvalidTokenError("This password reset link is invalid or has expired")

    user = await user_repository.get_by_id(db, record.user_id)
    if user is None:
        raise InvalidTokenError("This password reset link is invalid or has expired")

    errors = validate_password_strength(new_password, email=user.email)
    if errors:
        raise PasswordValidationError(errors[0], details=[{"field": "password", "message": e} for e in errors])

    await repository.mark_password_reset_used(db, record)
    await user_repository.set_password_hash(db, user, await hash_password(new_password))
    # Password change invalidates every existing session (BATCH_04 §11.5).
    await repository.revoke_all_refresh_tokens_for_user(db, user.id)

    await write_audit_log(
        db, event_type=AuditEventType.PASSWORD_RESET_COMPLETED, outcome=AuditOutcome.SUCCESS, user_id=user.id
    )
    await notifications_repository.create(
        db,
        user_id=user.id,
        type="alert",
        title="Password reset",
        body="Your password was reset. If this wasn't you, contact support immediately.",
        action_url="/settings/account",
    )
    await send_password_changed_email(to=user.email)
    return user


async def change_password(db: AsyncSession, *, user: User, current_password: str, new_password: str) -> None:
    if user.password_hash is None or not await verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Current password is incorrect")

    errors = validate_password_strength(new_password, email=user.email)
    if errors:
        raise PasswordValidationError(errors[0], details=[{"field": "new_password", "message": e} for e in errors])

    await user_repository.set_password_hash(db, user, await hash_password(new_password))
    await repository.revoke_all_refresh_tokens_for_user(db, user.id)
    await write_audit_log(db, event_type=AuditEventType.PASSWORD_CHANGED, outcome=AuditOutcome.SUCCESS, user_id=user.id)
    await notifications_repository.create(
        db,
        user_id=user.id,
        type="alert",
        title="Password changed",
        body="Your password was changed. If this wasn't you, contact support immediately.",
        action_url="/settings/account",
    )
    await send_password_changed_email(to=user.email)
