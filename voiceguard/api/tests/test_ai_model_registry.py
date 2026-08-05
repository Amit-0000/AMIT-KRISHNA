from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.inference import model_registry, repository
from api.inference.exceptions import ModelIntegrityError, ModelNotAvailableError

pytestmark = pytest.mark.asyncio


async def test_ensure_default_model_registered_returns_none_without_a_checkpoint(db_session: AsyncSession):
    # _isolated_settings (conftest) points MODEL_CHECKPOINT_PATH at a
    # non-existent file by default — no ai_checkpoint fixture used here.
    result = await model_registry.ensure_default_model_registered(db_session)
    assert result is None


async def test_get_active_model_version_raises_when_none_registered(db_session: AsyncSession):
    with pytest.raises(ModelNotAvailableError):
        await model_registry.get_active_model_version(db_session)


async def test_ensure_default_model_registered_creates_active_row(db_session: AsyncSession, ai_checkpoint):
    model_version = await model_registry.ensure_default_model_registered(db_session)
    assert model_version is not None
    assert model_version.status == "active"
    assert model_version.checkpoint_path == str(ai_checkpoint)
    assert len(model_version.sha256_checksum) == 64


async def test_ensure_default_model_registered_is_idempotent(db_session: AsyncSession, ai_checkpoint):
    first = await model_registry.ensure_default_model_registered(db_session)
    second = await model_registry.ensure_default_model_registered(db_session)
    assert first.id == second.id

    all_versions = await repository.list_model_versions(db_session)
    assert len(all_versions) == 1  # no duplicate row on the second call


async def test_get_active_model_version_bootstraps_and_returns_it(db_session: AsyncSession, ai_checkpoint):
    model_version = await model_registry.get_active_model_version(db_session)
    assert model_version.status == "active"


async def test_checksum_drift_raises_integrity_error(db_session: AsyncSession, ai_checkpoint):
    await model_registry.ensure_default_model_registered(db_session)

    # Simulate the checkpoint file being replaced in place without bumping
    # MODEL_VERSION — this must be treated as a tamper/misconfiguration
    # signal, not silently re-registered.
    ai_checkpoint.write_bytes(ai_checkpoint.read_bytes() + b"\x00")

    with pytest.raises(ModelIntegrityError):
        await model_registry.ensure_default_model_registered(db_session)


async def test_health_check_reports_unavailable_without_checkpoint(db_session: AsyncSession):
    health = await model_registry.health_check(db_session)
    assert health["available"] is False


async def test_health_check_reports_available_with_checkpoint(db_session: AsyncSession, ai_checkpoint):
    health = await model_registry.health_check(db_session)
    assert health["available"] is True
    assert health["status"] == "active"
    assert health["loaded_in_memory"] is False  # registry row exists, but model_loader hasn't loaded weights yet
