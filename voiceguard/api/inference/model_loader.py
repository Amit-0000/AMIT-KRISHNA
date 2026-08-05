from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from api.inference.exceptions import ModelIntegrityError, ModelNotAvailableError
from api.inference.models import ModelVersion

logger = logging.getLogger("voiceguard.inference")


@dataclass
class LoadedModel:
    model: object  # torch.nn.Module — kept loosely typed so this module is importable without torch installed
    device: object  # torch.device
    model_version_id: uuid.UUID


_MODEL_CACHE: dict[uuid.UUID, LoadedModel] = {}


def _resolve_device(preference: str):
    import torch

    if preference == "cpu":
        return torch.device("cpu")
    if preference == "cuda":
        if not torch.cuda.is_available():
            raise ModelNotAvailableError("MODEL_DEVICE=cuda but no CUDA device is available on this host")
        return torch.device("cuda")
    if preference == "mps":
        if not torch.backends.mps.is_available():
            raise ModelNotAvailableError("MODEL_DEVICE=mps but MPS is not available on this host")
        return torch.device("mps")
    # "auto" — mirrors api.main._get_device exactly, so the legacy /predict
    # endpoint and this pipeline always land on the same device by default.
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def verify_checksum(path: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ModelIntegrityError(
            f"Checkpoint at {path} does not match its registered checksum "
            f"(expected {expected_sha256}, got {digest}) — refusing to load"
        )


def load_model(model_version: ModelVersion, *, device_preference: str) -> LoadedModel:
    """Lazy + warm: the first call for a given model_version pays the full
    torch.load() + checksum cost; every call after that (including from
    other requests/background jobs in the same process) hits _MODEL_CACHE.
    Mirrors api.core.storage.get_storage_backend's @lru_cache pattern, keyed
    by model_version.id instead of taking no arguments since — unlike the
    single storage backend — more than one registered model can exist.

    Dispatches to whichever ModelAdapter is registered for
    model_version.architecture (see api.inference.adapters.registry) —
    this function itself has no architecture-specific knowledge anymore;
    adding a new architecture never requires touching this file. The
    adapters.registry import is deliberately inside this function, not at
    module level: api.inference.inference imports LoadedModel from this
    module, and adapter modules import api.inference.inference — importing
    the registry at module level here would try to import those adapter
    modules while this module is still mid-import, before LoadedModel even
    exists yet. Deferring the import to call time (well after every module
    has finished its own top-level import) avoids that cycle entirely.

    Synchronous by design — see api.inference.preprocessing.run_preprocessing
    for why (api.inference.jobs wraps this call in asyncio.to_thread so a
    ~second-long torch.load() on a cache miss doesn't block the event loop)."""
    cached = _MODEL_CACHE.get(model_version.id)
    if cached is not None:
        return cached

    from api.inference.adapters import registry as adapter_registry

    adapter = adapter_registry.get_adapter(model_version.architecture)

    path = Path(model_version.checkpoint_path)
    if not path.exists():
        raise ModelNotAvailableError(f"Checkpoint not found at {path}")

    try:
        # Catches everything from here, not just a missing ML runtime: a
        # missing torch install (ModuleNotFoundError — raised by
        # _resolve_device()'s own `import torch` just as much as from inside
        # the adapter's own load_model; the lean api/Dockerfile image never
        # installs torch, exactly like api/main.py's own lifespan guards its
        # best-effort model load) and a corrupt/incompatible checkpoint both
        # land here as the same clean, catchable ModelNotAvailableError every
        # other failure path in this pipeline produces — one try/except
        # covers every architecture uniformly instead of each adapter
        # needing its own. verify_checksum and _resolve_device must stay
        # inside this block too: either can raise the same class of
        # environment-dependent error (unreadable file, missing torch), and
        # a bare raise from either previously escaped uncaught, propagating
        # out of asyncio.to_thread as a raw exception _run_stage doesn't
        # recognize (it only catches AIPipelineError/asyncio.TimeoutError) —
        # silently wedging the scan in LOADING_MODEL forever instead of
        # landing in MODEL_LOAD_FAILED like every other load failure here.
        verify_checksum(path, model_version.sha256_checksum)
        device = _resolve_device(device_preference)
        model = adapter.load_model(path, device)
    except (ModelNotAvailableError, ModelIntegrityError):
        # Already the pipeline's own well-typed AIPipelineError subclasses
        # (raised deliberately by verify_checksum/adapter.load_model) — pass
        # through as-is rather than re-wrapping and losing their specific
        # error_code (MODEL_INTEGRITY_FAILED vs MODEL_NOT_AVAILABLE).
        raise
    except Exception as exc:  # noqa: BLE001 - see comment above
        raise ModelNotAvailableError(f"Failed to load checkpoint at {path}: {exc}") from exc

    loaded = LoadedModel(model=model, device=device, model_version_id=model_version.id)
    _MODEL_CACHE[model_version.id] = loaded
    logger.info(
        "model_loaded",
        extra={"model_version_id": str(model_version.id), "architecture": model_version.architecture, "device": str(device)},
    )
    return loaded


def reset_model_cache() -> None:
    """Test-only hook — mirrors api.core.storage.reset_storage_backend_cache."""
    _MODEL_CACHE.clear()


def is_cached(model_version_id: uuid.UUID) -> bool:
    return model_version_id in _MODEL_CACHE
