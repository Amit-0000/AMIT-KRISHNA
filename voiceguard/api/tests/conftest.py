from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.core import database as database_module
from api.core import redis as redis_module
from api.core import storage as storage_module
from api.core.config import get_settings
from api.inference import model_loader as model_loader_module

# db_session (below) calls Base.metadata.create_all before any test body —
# and therefore before anything else — has a chance to import the model
# modules that populate Base.metadata. Whether that create_all sees every
# table (auth, scans, inference, ...) depended on which test files pytest
# had already collected/imported first, i.e. on run order: `pytest
# api/tests/` happened to work because some earlier-collected file imported
# api.main (pulling in every router and its models) before this fixture
# ever ran, but `pytest api/tests/test_scans.py` alone failed with
# "no such table: email_verifications" — the auth tables were never
# registered. Importing api.main here, once, at conftest import time (which
# pytest always does before collecting any test in this directory) makes
# every model module's tables present in Base.metadata unconditionally, so
# `db_session` behaves the same whether the whole suite runs or a single
# file does.
import api.main  # noqa: E402,F401


class FakeRedis:
    """In-memory double for the subset of redis.asyncio.Redis used by
    core.rate_limit — lets the auth rate limiters run for real in tests
    without a Redis server (BATCH_04 rate-limit logic is exercised, just
    against an in-process store instead of a network one)."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._expiry: dict[str, float] = {}
        self._values: dict[str, str] = {}

    def _expired(self, name: str) -> bool:
        exp = self._expiry.get(name)
        return exp is not None and exp < time.time()

    async def incr(self, name: str) -> int:
        if self._expired(name):
            self._counters.pop(name, None)
            self._expiry.pop(name, None)
        self._counters[name] = self._counters.get(name, 0) + 1
        return self._counters[name]

    async def expire(self, name: str, seconds: int) -> bool:
        self._expiry[name] = time.time() + seconds
        return True

    async def ttl(self, name: str) -> int:
        exp = self._expiry.get(name)
        if exp is None:
            return -1
        return max(int(exp - time.time()), 0)

    async def get(self, name: str) -> str | None:
        if self._expired(name):
            self._values.pop(name, None)
            return None
        return self._values.get(name)

    async def setex(self, name: str, seconds: int, value: str) -> bool:
        self._values[name] = value
        self._expiry[name] = time.time() + seconds
        return True

    async def delete(self, *names: str) -> int:
        count = 0
        for name in names:
            if self._counters.pop(name, None) is not None:
                count += 1
            self._values.pop(name, None)
            self._expiry.pop(name, None)
        return count


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(database_module.Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    get_settings.cache_clear()

    from api.main import app

    fake_redis = FakeRedis()
    redis_module.set_redis_client(fake_redis)

    async def _override_get_db():
        yield db_session

    async def _override_get_redis():
        yield fake_redis

    app.dependency_overrides[database_module.get_db] = _override_get_db
    app.dependency_overrides[redis_module.get_redis] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    # Malware scanning: no real clamd daemon runs in this test environment
    # (see docker-compose.yml's `clamav` service, only present under real
    # Docker Compose) — default every test to a CLEAN result so the upload
    # pipeline's existing happy-path tests don't need a live scanner, exactly
    # the same reasoning EMAIL_PROVIDER=console fakes email delivery here.
    # api/tests/test_malware_scan.py exercises the real scanning logic
    # directly (importing scan_file's underlying implementation by name, not
    # through this patched module attribute) against an in-process fake
    # clamd socket server; tests that need MALICIOUS/UNAVAILABLE pipeline
    # behavior override this patch for just that test via their own
    # monkeypatch.setattr(malware_scan, "scan_file", ...).
    from api.scans import malware_scan as malware_scan_module
    from api.scans.malware_scan import MalwareScanResult, MalwareScanStatus

    async def _fake_clean_scan(storage, storage_key):
        return MalwareScanResult(status=MalwareScanStatus.CLEAN, engine="fake-clean-default")

    monkeypatch.setattr(malware_scan_module, "scan_file", _fake_clean_scan)
    # Scans slice: point uploads at a per-test tmp dir instead of the real
    # data/uploads, and clear get_storage_backend's own lru_cache (separate
    # from get_settings') so it re-reads UPLOAD_STORAGE_ROOT every test.
    monkeypatch.setenv("UPLOAD_STORAGE_ROOT", str(tmp_path / "uploads"))
    # AI Processing Pipeline slice: no real trained checkpoint ships in this
    # repo (checkpoints/ is empty — see api.main's own best-effort model
    # load), so point at a path that doesn't exist by default. Tests that
    # actually exercise the pipeline opt in via the `ai_checkpoint` fixture,
    # which overrides this to a real (untrained) checkpoint it writes to
    # tmp_path. Every test also gets a clean api.inference.model_loader
    # cache — that module-level dict would otherwise leak a loaded model
    # (and its checkpoint path) across tests the same way an un-reset
    # get_storage_backend cache would leak a storage root.
    monkeypatch.setenv("MODEL_CHECKPOINT_PATH", str(tmp_path / "no-checkpoint-here.pt"))
    # Second architecture (AudioCNN) — same reasoning, opt in via the
    # `audio_cnn_checkpoint` fixture.
    monkeypatch.setenv("AUDIO_CNN_CHECKPOINT_PATH", str(tmp_path / "no-audio-cnn-checkpoint-here.pth"))
    get_settings.cache_clear()
    storage_module.get_storage_backend.cache_clear()
    model_loader_module.reset_model_cache()
    yield
    get_settings.cache_clear()
    storage_module.get_storage_backend.cache_clear()
    model_loader_module.reset_model_cache()


@pytest.fixture
def ai_checkpoint(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Path:
    """Writes a real, small, randomly-initialized (untrained) LCNN
    checkpoint to a per-test temp path and points MODEL_CHECKPOINT_PATH at
    it. Deliberately not a mock: every AI-pipeline test using this fixture
    exercises the real decode -> feature-extraction -> model-forward-pass
    code path end to end — it just doesn't assert anything about detection
    *accuracy*, since an untrained model's predictions are meaningless.
    That's the right boundary for this test suite (mechanics, not ML
    quality) — see the slice's Testing Report for why."""
    import torch

    from src.models.lcnn import LCNN

    path = tmp_path / "test-checkpoint.pt"
    torch.save(LCNN().state_dict(), path)

    monkeypatch.setenv("MODEL_CHECKPOINT_PATH", str(path))
    get_settings.cache_clear()
    model_loader_module.reset_model_cache()
    return path


@pytest.fixture
def audio_cnn_checkpoint(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Path:
    """AudioCNN counterpart to `ai_checkpoint` above — same reasoning
    (real, small, randomly-initialized, untrained checkpoint; mechanics not
    accuracy). Both fixtures can be requested together by a test that wants
    both architectures registered simultaneously."""
    import torch

    from src.models.audio_cnn import AudioCNN

    path = tmp_path / "test-audio-cnn-checkpoint.pth"
    torch.save(AudioCNN().state_dict(), path)

    monkeypatch.setenv("AUDIO_CNN_CHECKPOINT_PATH", str(path))
    get_settings.cache_clear()
    model_loader_module.reset_model_cache()
    return path
