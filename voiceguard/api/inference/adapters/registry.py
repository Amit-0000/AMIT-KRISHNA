from __future__ import annotations

from api.inference.adapters.base import ModelAdapter
from api.inference.exceptions import ModelNotAvailableError

_ADAPTERS: dict[str, ModelAdapter] = {}


def register_adapter(architecture: str):
    """Class decorator: registers a ModelAdapter subclass under
    `architecture` (must match ModelVersion.architecture exactly for every
    model that should be routed to it). This is the *only* place a new
    detector architecture needs to announce itself — no other module in
    api.inference imports concrete adapter classes or branches on
    architecture names. Mirrors api.inference.feature_extraction's existing
    register_extractor decorator, the same plugin idiom already established
    in this codebase."""

    def decorator(cls: type[ModelAdapter]) -> type[ModelAdapter]:
        _ADAPTERS[architecture] = cls()
        return cls

    return decorator


def _ensure_builtin_adapters_registered() -> None:
    """Imports every built-in adapter module purely for its @register_adapter
    side effect. Deferred to first use (called from get_adapter, not at this
    module's own import time) for the same reason api.inference.model_loader
    imports this package lazily — see that module's load_model() — rather
    than because these adapter modules themselves need torch to import; they
    don't (torch stays lazily imported inside each adapter's own methods,
    same discipline as everywhere else in api.inference)."""
    from api.inference.adapters import audio_cnn_adapter, lcnn_adapter  # noqa: F401


_builtins_registered = False


def get_adapter(architecture: str) -> ModelAdapter:
    global _builtins_registered
    if not _builtins_registered:
        _ensure_builtin_adapters_registered()
        _builtins_registered = True

    adapter = _ADAPTERS.get(architecture)
    if adapter is None:
        raise ModelNotAvailableError(
            f"No registered adapter for architecture {architecture!r}. "
            f"Registered architectures: {available_architectures()}"
        )
    return adapter


def available_architectures() -> list[str]:
    return sorted(_ADAPTERS.keys())


def reset_registry_for_tests() -> None:
    """Test-only hook: clears registered adapters and the built-ins-loaded
    flag so a test can register a throwaway adapter without leaking into
    other tests, then re-import the real built-ins on next access. Mirrors
    api.inference.model_loader.reset_model_cache / api.core.storage's
    reset_storage_backend_cache."""
    global _builtins_registered
    _ADAPTERS.clear()
    _builtins_registered = False
