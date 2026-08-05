from __future__ import annotations

import uuid

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import service as auth_service
from api.core.database import get_db
from api.core.exceptions import EmailNotVerifiedError, InsufficientPermissionsError, InvalidTokenError, SessionExpiredError
from api.core.middleware import client_ip
from api.core.security import ExpiredAccessTokenError, InvalidAccessTokenError, decode_access_token, hash_ip
from api.user import repository as user_repository
from api.user.models import User, UserRole


async def _try_silent_refresh(request: Request, response: Response, db: AsyncSession) -> User | None:
    """BATCH_04 §10.4: expired access token + valid refresh token → transparently
    re-issue both cookies and let the request proceed as authenticated."""
    refresh_raw = request.cookies.get(auth_service.REFRESH_COOKIE_NAME)
    if not refresh_raw:
        return None
    try:
        user, access_token, refresh_token_new = await auth_service.rotate_refresh_token(
            db,
            refresh_token_raw=refresh_raw,
            user_agent=request.headers.get("user-agent"),
            ip_hash=hash_ip(client_ip(request)),
        )
    except SessionExpiredError:
        return None
    auth_service.set_session_cookies(response, access_token=access_token, refresh_token_raw=refresh_token_new)
    await db.commit()
    return user


async def get_current_user_optional(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> User | None:
    access_token = request.cookies.get(auth_service.ACCESS_COOKIE_NAME)
    if not access_token:
        return await _try_silent_refresh(request, response, db)

    try:
        payload = decode_access_token(access_token)
    except ExpiredAccessTokenError:
        return await _try_silent_refresh(request, response, db)
    except InvalidAccessTokenError:
        return None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
    return await user_repository.get_by_id(db, user_id)


async def require_authenticated(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise InvalidTokenError("Authentication required")
    return user


async def require_verified(user: User = Depends(require_authenticated)) -> User:
    if not user.email_verified:
        raise EmailNotVerifiedError("Please verify your email address")
    return user


async def require_admin(user: User = Depends(require_authenticated)) -> User:
    """Reused wherever a route needs admin-only access (e.g. GET
    /feedback) — the same UserRole.ADMIN column api.user.models already
    defines, just never gated on before now."""
    if user.role != UserRole.ADMIN:
        raise InsufficientPermissionsError("Admin access required")
    return user
