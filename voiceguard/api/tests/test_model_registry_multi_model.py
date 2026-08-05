from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.inference import model_registry, repository
from api.inference.exceptions import ModelIntegrityError, ModelNotAvailableError

pytestmark = pytest.mark.asyncio


async def test_register_model_version_creates_inactive_row_using_adapter_metadata(
    db_session: AsyncSession, audio_cnn_checkpoint
):
    model_version = await model_registry.register_model_version(
        db_session,
        architecture="AudioCNN",
        name="audio_cnn",
        version="v1",
        checkpoint_path=audio_cnn_checkpoint,
    )
    assert model_version.architecture == "AudioCNN"
    assert model_version.status == "inactive"  # registering never auto-activates
    # feature_extractor_name/version came from the adapter's own metadata(),
    # not a caller-supplied argument — Phase 10's "metadata should drive
    # behavior instead of hardcoded constants."
    assert model_version.feature_extractor_name == "logmel64db"
    assert model_version.feature_extractor_version == "v1"
    assert len(model_version.sha256_checksum) == 64


async def test_register_model_version_is_idempotent(db_session: AsyncSession, audio_cnn_checkpoint):
    first = await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    second = await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    assert first.id == second.id
    rows = await repository.list_model_versions(db_session)
    assert len([r for r in rows if r.name == "audio_cnn"]) == 1


async def test_register_model_version_rejects_checksum_drift(db_session: AsyncSession, audio_cnn_checkpoint):
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    audio_cnn_checkpoint.write_bytes(audio_cnn_checkpoint.read_bytes() + b"\x00")

    with pytest.raises(ModelIntegrityError):
        await model_registry.register_model_version(
            db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
        )


async def test_register_model_version_raises_for_missing_checkpoint(db_session: AsyncSession, tmp_path):
    with pytest.raises(ModelNotAvailableError):
        await model_registry.register_model_version(
            db_session,
            architecture="AudioCNN",
            name="audio_cnn",
            version="v1",
            checkpoint_path=tmp_path / "does-not-exist.pth",
        )


async def test_register_model_version_raises_for_unknown_architecture(db_session: AsyncSession, audio_cnn_checkpoint):
    with pytest.raises(ModelNotAvailableError):
        await model_registry.register_model_version(
            db_session,
            architecture="ECAPA-TDNN",  # not registered in api.inference.adapters
            name="ecapa",
            version="v1",
            checkpoint_path=audio_cnn_checkpoint,
        )


async def test_both_models_coexist_after_registration(db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint):
    lcnn = await model_registry.get_active_model_version(db_session)  # bootstraps LCNN
    audio_cnn = await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )

    rows = await repository.list_model_versions(db_session)
    architectures = {r.architecture for r in rows}
    assert architectures == {"LCNN", "AudioCNN"}
    assert lcnn.status == "active"
    assert audio_cnn.status == "inactive"


async def test_switch_active_model_deactivates_the_previous_one(
    db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint
):
    await model_registry.get_active_model_version(db_session)  # bootstraps + activates LCNN
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )

    switched = await model_registry.switch_active_model(db_session, name="audio_cnn", version="v1")
    assert switched.status == "active"
    assert switched.architecture == "AudioCNN"

    settings = get_settings()
    lcnn_row = await repository.get_model_version_by_name_version(
        db_session, name=settings.MODEL_NAME, version=settings.MODEL_VERSION
    )
    assert lcnn_row.status == "inactive"


async def test_get_active_model_version_honors_a_switch_no_code_changes_needed(
    db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint
):
    """Regression test for the exact bug this refactor had to avoid: the
    original get_active_model_version() tried ensure_default_model_registered
    (LCNN) *first*, unconditionally — which would force LCNN back to
    "active" on every call whenever its checkpoint file exists on disk,
    silently undoing switch_active_model(). This is Phase 13's "switch
    active model using ModelVersion only, no code changes required to
    switch" verified end to end: after switching, the pipeline's own entry
    point (get_active_model_version, exactly what api.inference.jobs calls)
    must keep returning AudioCNN, not silently revert to LCNN."""
    await model_registry.get_active_model_version(db_session)  # bootstraps + activates LCNN
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    await model_registry.switch_active_model(db_session, name="audio_cnn", version="v1")

    # The exact call api.inference.jobs._stage_prepare_model makes.
    active = await model_registry.get_active_model_version(db_session)
    assert active.architecture == "AudioCNN"

    # Calling it again (as a second scan's pipeline run would) must not
    # flip it back to LCNN.
    active_again = await model_registry.get_active_model_version(db_session)
    assert active_again.architecture == "AudioCNN"


async def test_switch_active_model_back_to_lcnn(db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint):
    """Switching is reversible in both directions purely through data."""
    settings = get_settings()
    await model_registry.get_active_model_version(db_session)  # LCNN active
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    await model_registry.switch_active_model(db_session, name="audio_cnn", version="v1")
    await model_registry.switch_active_model(db_session, name=settings.MODEL_NAME, version=settings.MODEL_VERSION)

    active = await model_registry.get_active_model_version(db_session)
    assert active.architecture == "LCNN"


async def test_switch_active_model_raises_for_unregistered_target(db_session: AsyncSession, ai_checkpoint):
    with pytest.raises(ModelNotAvailableError):
        await model_registry.switch_active_model(db_session, name="does-not-exist", version="v1")
