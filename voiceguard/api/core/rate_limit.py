from __future__ import annotations

import time

from fastapi import Depends, Request

from api.core.config import get_settings
from api.core.deps import require_authenticated
from api.core.exceptions import RateLimitError
from api.core.middleware import client_ip
from api.core.redis import RateLimitBackend, get_redis
from api.user.models import User

WINDOW_SECONDS = 3600


async def _check_and_increment(redis: RateLimitBackend, key: str, limit: int, window_s: int) -> tuple[int, int]:
    """Atomic-enough sliding-window-by-fixed-bucket counter (BATCH_04 S11.6):
    INCR then EXPIRE-if-new-key. Returns (current_count, seconds_until_reset)."""
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_s)
        ttl = window_s
    else:
        ttl = await redis.ttl(key)
        if ttl < 0:
            # Key exists but has no TTL (should not happen, but don't wedge the
            # limiter open forever if it does).
            await redis.expire(key, window_s)
            ttl = window_s
    if current > limit:
        raise RateLimitError(
            "Too many requests. Please try again later.",
            retry_after_s=max(ttl, 1),
        )
    return current, ttl


def rate_limit(bucket: str, *, limit_attr: str, by: str = "ip") -> object:
    """Returns a FastAPI dependency enforcing `limit_attr`-many requests per
    hour for the given route bucket. `by="ip"` keys the bucket by client IP
    (pre-auth routes: register/login/etc); `by="user"` keys it by the
    authenticated user's id instead (routes that require auth, where
    per-user is the meaningful abuse boundary — e.g. scan creation, where
    many legitimate users can share one IP)."""
    if by == "user":

        async def _dependency_by_user(
            redis: RateLimitBackend = Depends(get_redis), user: User = Depends(require_authenticated)
        ) -> None:
            settings = get_settings()
            limit = getattr(settings, limit_attr)
            window_bucket = int(time.time()) // WINDOW_SECONDS
            key = f"rl:{bucket}:{user.id}:{window_bucket}"
            await _check_and_increment(redis, key, limit, WINDOW_SECONDS)

        return _dependency_by_user

    async def _dependency(request: Request, redis: RateLimitBackend = Depends(get_redis)) -> None:
        settings = get_settings()
        limit = getattr(settings, limit_attr)
        ip = client_ip(request)
        window_bucket = int(time.time()) // WINDOW_SECONDS
        key = f"rl:{bucket}:{ip}:{window_bucket}"
        await _check_and_increment(redis, key, limit, WINDOW_SECONDS)

    return _dependency


require_register_rate_limit = rate_limit("register", limit_attr="RATE_LIMIT_REGISTER_PER_HOUR_PER_IP")
require_login_rate_limit = rate_limit("login", limit_attr="RATE_LIMIT_LOGIN_PER_HOUR_PER_IP")
require_forgot_password_rate_limit = rate_limit("forgot-password", limit_attr="RATE_LIMIT_RESET_PER_HOUR_PER_IP")
require_reset_password_rate_limit = rate_limit("reset-password", limit_attr="RATE_LIMIT_RESET_PER_HOUR_PER_IP")
require_resend_verification_rate_limit = rate_limit(
    "resend-verification", limit_attr="RATE_LIMIT_RESEND_VERIFICATION_PER_HOUR_PER_IP"
)
require_verify_email_rate_limit = rate_limit("verify-email", limit_attr="RATE_LIMIT_VERIFY_EMAIL_PER_HOUR_PER_IP")
require_scan_create_rate_limit = rate_limit(
    "scan-create", limit_attr="RATE_LIMIT_SCAN_CREATE_PER_HOUR_PER_USER", by="user"
)
require_predict_rate_limit = rate_limit(
    "predict", limit_attr="RATE_LIMIT_PREDICT_PER_HOUR_PER_USER", by="user"
)
require_feedback_rate_limit = rate_limit("feedback", limit_attr="RATE_LIMIT_FEEDBACK_PER_HOUR_PER_IP")
