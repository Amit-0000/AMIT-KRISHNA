from __future__ import annotations

from collections.abc import AsyncGenerator
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.core.config import get_settings


class Base(DeclarativeBase):
    pass


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Pass as `values_callable` to every `sa.Enum(SomeEnum, ...)` column.
    Without it, SQLAlchemy binds/reads a Python enum member's .name ("USER")
    instead of its .value ("user") — every Alembic migration in this project
    creates the Postgres enum type from members' .value strings, so omitting
    this makes every insert and every read of a populated row fail (see
    api/user/models.py history: this exact gap blocked registration and
    login entirely until it was added everywhere)."""
    return [member.value for member in enum_cls]


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> AsyncEngine:
    global _engine, _session_factory
    settings = get_settings()
    url = database_url or settings.DATABASE_URL
    connect_args: dict[str, object] = {}
    if url.startswith("postgresql"):
        connect_args["timeout"] = settings.DB_CONNECT_TIMEOUT_S
        connect_args["command_timeout"] = settings.DB_STATEMENT_TIMEOUT_S

    engine_kwargs: dict[str, object] = {"echo": False, "connect_args": connect_args}
    # SQLite (used for tests / lightweight local runs) has no server-side pool.
    if not url.startswith("sqlite"):
        engine_kwargs["pool_size"] = settings.DB_POOL_MIN_SIZE
        engine_kwargs["max_overflow"] = settings.DB_POOL_MAX_SIZE - settings.DB_POOL_MIN_SIZE

    _engine = create_async_engine(url, **engine_kwargs)
    _session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
