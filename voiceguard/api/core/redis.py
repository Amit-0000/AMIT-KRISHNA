from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol

import redis.asyncio as redis_async

from api.core.config import get_settings


class RateLimitBackend(Protocol):
    """Minimal surface core.rate_limit needs. Satisfied by redis.asyncio.Redis
    and by the in-memory FakeRedis test double in tests/conftest.py."""

    async def incr(self, name: str) -> int: ...
    async def expire(self, name: str, seconds: int) -> bool: ...
    async def ttl(self, name: str) -> int: ...
    async def get(self, name: str) -> str | bytes | None: ...
    async def setex(self, name: str, seconds: int, value: str) -> bool: ...
    async def delete(self, *names: str) -> int: ...


_pool: redis_async.ConnectionPool | None = None
_client: redis_async.Redis | None = None


def init_redis(redis_url: str | None = None) -> redis_async.Redis:
    global _pool, _client
    settings = get_settings()
    url = redis_url or settings.REDIS_URL
    _pool = redis_async.ConnectionPool.from_url(
        url,
        max_connections=settings.REDIS_POOL_MAX_SIZE,
        socket_connect_timeout=settings.REDIS_COMMAND_TIMEOUT_S,
        socket_timeout=settings.REDIS_COMMAND_TIMEOUT_S,
        decode_responses=True,
    )
    _client = redis_async.Redis(connection_pool=_pool)
    return _client


def get_redis_client() -> redis_async.Redis:
    if _client is None:
        return init_redis()
    return _client


def set_redis_client(client: object) -> None:
    """Test-only hook: install a FakeRedis double instead of a real connection."""
    global _client
    _client = client  # type: ignore[assignment]


async def close_redis() -> None:
    global _pool, _client
    if _client is not None:
        await _client.aclose()
    if _pool is not None:
        await _pool.disconnect()
    _client = None
    _pool = None


async def get_redis() -> AsyncGenerator[RateLimitBackend, None]:
    yield get_redis_client()  # type: ignore[misc]
