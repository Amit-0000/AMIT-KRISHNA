from __future__ import annotations

import uuid

import pytest

from api.inference import model_loader
from api.inference.exceptions import ModelIntegrityError, ModelNotAvailableError
from api.inference.models import ModelVersion


def _fake_model_version(*, checkpoint_path, sha256_checksum: str) -> ModelVersion:
    return ModelVersion(
        id=uuid.uuid4(),
        name="lcnn",
        version="v1",
        architecture="LCNN",
        checkpoint_path=str(checkpoint_path),
        sha256_checksum=sha256_checksum,
        feature_extractor_name="logmel",
        feature_extractor_version="v1",
        status="active",
    )


def test_load_model_raises_when_checkpoint_missing(tmp_path):
    model_version = _fake_model_version(checkpoint_path=tmp_path / "missing.pt", sha256_checksum="0" * 64)
    with pytest.raises(ModelNotAvailableError):
        model_loader.load_model(model_version, device_preference="cpu")


def test_load_model_raises_on_checksum_mismatch(ai_checkpoint):
    model_version = _fake_model_version(checkpoint_path=ai_checkpoint, sha256_checksum="0" * 64)
    with pytest.raises(ModelIntegrityError):
        model_loader.load_model(model_version, device_preference="cpu")


def test_load_model_succeeds_and_caches(ai_checkpoint):
    from api.inference.model_loader import verify_checksum

    checksum_path = ai_checkpoint
    import hashlib

    expected = hashlib.sha256(checksum_path.read_bytes()).hexdigest()
    model_version = _fake_model_version(checkpoint_path=ai_checkpoint, sha256_checksum=expected)

    assert model_loader.is_cached(model_version.id) is False
    loaded = model_loader.load_model(model_version, device_preference="cpu")
    assert loaded.model is not None
    assert str(loaded.device) == "cpu"
    assert model_loader.is_cached(model_version.id) is True

    # Second call hits the cache — same object, no re-read of the checkpoint.
    loaded_again = model_loader.load_model(model_version, device_preference="cpu")
    assert loaded_again is loaded

    verify_checksum(checksum_path, expected)  # sanity: the helper itself doesn't raise on a match


def test_reset_model_cache_clears_state(ai_checkpoint):
    import hashlib

    expected = hashlib.sha256(ai_checkpoint.read_bytes()).hexdigest()
    model_version = _fake_model_version(checkpoint_path=ai_checkpoint, sha256_checksum=expected)
    model_loader.load_model(model_version, device_preference="cpu")
    assert model_loader.is_cached(model_version.id) is True

    model_loader.reset_model_cache()
    assert model_loader.is_cached(model_version.id) is False


def test_load_model_raises_model_not_available_when_ml_runtime_missing(ai_checkpoint, monkeypatch):
    """Regression test for the "Computing confidence" hang: the lean
    api/Dockerfile image (api/requirements.txt only, no torch/torchaudio) is
    what actually runs in docker-compose — but the test suite runs against a
    dev venv that DOES have torch installed, so nothing here previously
    exercised a real missing-torch condition. (An earlier version of this
    test monkeypatched `src.inference.predict` — the legacy api/main.py
    /predict path, unrelated to this module entirely — and so always passed
    without covering anything.)

    Force the *real* `import torch` to fail the way it does in the lean
    image, via the standard sys.modules-sentinel technique: setting
    sys.modules['torch'] = None makes any subsequent `import torch`
    statement raise, regardless of whether torch is actually installed.

    Before the fix, model_loader.load_model() called `_resolve_device()`
    (which does `import torch`) *outside* its try/except block, so this
    raised an unhandled ModuleNotFoundError straight out of load_model()
    instead of the clean, catchable ModelNotAvailableError every other
    failure path in this pipeline produces — see api.inference.jobs._run_stage,
    which only catches AIPipelineError/asyncio.TimeoutError and lets
    anything else escape uncaught, wedging the scan in LOADING_MODEL forever
    with no processing_failure row, no scan_events entry, and no terminal
    status. ModelNotAvailableError IS an AIPipelineError, so _run_stage
    handles it exactly like every other load failure (see
    test_ai_pipeline_jobs.test_pipeline_fails_with_model_load_failed_when_no_checkpoint).
    """
    import sys

    monkeypatch.setitem(sys.modules, "torch", None)

    import hashlib

    expected = hashlib.sha256(ai_checkpoint.read_bytes()).hexdigest()
    model_version = _fake_model_version(checkpoint_path=ai_checkpoint, sha256_checksum=expected)

    with pytest.raises(ModelNotAvailableError):
        model_loader.load_model(model_version, device_preference="cpu")


def test_load_model_rejects_forced_cuda_when_unavailable(ai_checkpoint):
    import torch

    if torch.cuda.is_available():
        pytest.skip("CUDA is available on this host — the forced-cuda rejection path can't be exercised")

    import hashlib

    expected = hashlib.sha256(ai_checkpoint.read_bytes()).hexdigest()
    model_version = _fake_model_version(checkpoint_path=ai_checkpoint, sha256_checksum=expected)
    with pytest.raises(ModelNotAvailableError):
        model_loader.load_model(model_version, device_preference="cuda")
