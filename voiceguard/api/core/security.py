from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from api.core.config import get_settings

BCRYPT_ROUNDS = 12

# Top of the "10,000 most common passwords" list, trimmed to a set that catches
# the overwhelming majority of real-world weak submissions without shipping a
# 10k-line file into the repo. Extend this file if/when a full list is sourced.
_COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password", "password1", "password123", "12345678", "123456789",
        "qwerty123", "letmein1", "welcome1", "admin1234", "iloveyou1",
        "sunshine1", "princess1", "football1", "baseball1", "dragon123",
        "monkey123", "trustno1", "master123", "shadow123", "superman1",
        "michael1", "abcd1234", "passw0rd", "p@ssw0rd", "changeme1",
    }
)


def _hash_password_sync(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def _verify_password_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash. Fail closed rather than raising, keeping the caller's
        # constant-shape error handling intact (BATCH_04 S5.3 login_user step 3).
        return False


async def hash_password(password: str) -> str:
    """bcrypt at BCRYPT_ROUNDS=12 costs ~150-300ms of pure CPU time per call.
    Run synchronously inside a route coroutine, that blocks the single
    asyncio event loop thread for the whole duration — every other in-flight
    request (DB queries, JWT issuance, unrelated routes, everything) stalls
    behind it too, since none of that work can be scheduled while the loop
    thread is stuck inside OpenSSL's blowfish routine. Offloading to a worker
    thread via asyncio.to_thread is the standard fix for a CPU-bound stdlib
    call with no native async API: it moves the block off the loop thread
    without changing the algorithm, cost factor, or resulting hash in any
    way — same bcrypt, same 12 rounds, same $2b$ hash format, verified
    byte-for-byte compatible with hashes this function already produced
    before this change (see api/tests/test_auth.py's login-after-register
    round trip)."""
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(password: str, password_hash: str) -> bool:
    """See hash_password's docstring — same asyncio.to_thread rationale,
    same guarantee that this is bit-for-bit the same bcrypt.checkpw call
    login_user's constant-time-shaped dummy-hash comparison already relied
    on, just no longer running on the event loop thread."""
    return await asyncio.to_thread(_verify_password_sync, password, password_hash)


def validate_password_strength(password: str, email: str | None = None) -> list[str]:
    """Returns a list of human-readable violations (empty list = valid), per
    BATCH_04 S11.5 entropy requirements."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    if password.lower() in _COMMON_PASSWORDS:
        errors.append("Password is too common; please choose a stronger password")
    if email and password.lower() == email.lower():
        errors.append("Password must not be the same as your email address")
    return errors


def generate_opaque_token() -> str:
    """32 random bytes, hex-encoded (64 chars) — used for refresh, email
    verification, and password reset tokens (BATCH_04 S10.2 / BATCH_05 §5)."""
    return secrets.token_hex(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_expired(expires_at: datetime) -> bool:
    """SQLite (used for tests) drops tzinfo on round-trip even for
    DateTime(timezone=True) columns; Postgres never does. Normalize to UTC
    before comparing so expiry checks are correct on both backends."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


def hash_ip(ip_address: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{ip_address}{settings.AUDIT_IP_SALT}".encode("utf-8")).hexdigest()


ALLOWED_JWT_ALGORITHMS = ["HS256"]


def create_access_token(*, user_id: str, role: str, email_verified: bool) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "email_verified": email_verified,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_TTL_S),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class InvalidAccessTokenError(Exception):
    pass


class ExpiredAccessTokenError(Exception):
    pass


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError("Malformed token") from exc

    # Defense against alg-confusion attacks (BATCH_04 S10.3 step 4): never trust
    # the algorithm embedded in the token itself beyond checking it's allowed.
    if header.get("alg") not in ALLOWED_JWT_ALGORITHMS:
        raise InvalidAccessTokenError("Disallowed token algorithm")

    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=ALLOWED_JWT_ALGORITHMS)
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError("Invalid token") from exc
