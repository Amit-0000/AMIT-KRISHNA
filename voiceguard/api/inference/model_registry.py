from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.inference import repository
from api.inference.exceptions import ModelIntegrityError, ModelNotAvailableError
from api.inference.models import ModelVersion

logger = logging.getLogger("voiceguard.inference")


def _checkpoint_path() -> Path:
    """Resolved to an absolute path from settings rather than the bare
    relative "checkpoints/best.pt" api/main.py's legacy /predict endpoint
    uses — see Vulnerability Test Results/security_review.md F-13. A process
    started from an unexpected working directory fails clearly here instead
    of silently missing the checkpoint."""
    return Path(get_settings().MODEL_CHECKPOINT_PATH).resolve()


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def ensure_default_model_registered(db: AsyncSession) -> ModelVersion | None:
    """Idempotent bootstrap: registers settings.MODEL_NAME/MODEL_VERSION
    against whatever checkpoint currently sits at MODEL_CHECKPOINT_PATH, the
    first time it's needed. Returns None (never raises) if no checkpoint file
    exists — mirrors api.main's lifespan, which loads the model best-effort
    and lets /predict report 503 rather than crashing the whole app on a
    machine with no trained checkpoint. Raises ModelIntegrityError if a row
    already exists for this name+version but the on-disk file's checksum has
    since changed — that means the checkpoint was replaced without bumping
    MODEL_VERSION, which this registry treats as a tamper/misconfiguration
    signal rather than silently re-registering."""
    settings = get_settings()
    path = _checkpoint_path()

    existing = await repository.get_model_version_by_name_version(
        db, name=settings.MODEL_NAME, version=settings.MODEL_VERSION
    )

    if not path.exists():
        if existing is not None and existing.status == "active":
            # Registered previously (checkpoint existed at some point in this
            # DB's history) but missing now — deactivate so callers get a
            # clear MODEL_NOT_AVAILABLE instead of an active row nothing can
            # actually load.
            await repository.set_model_status(db, existing, "inactive")
            await db.commit()
        return None

    checksum = _sha256_of(path)

    if existing is not None:
        if existing.sha256_checksum != checksum:
            raise ModelIntegrityError(
                f"Checkpoint at {path} changed since {settings.MODEL_NAME}:{settings.MODEL_VERSION} was "
                f"registered (checksum drift) — bump MODEL_VERSION for a new checkpoint instead of "
                "replacing the file in place."
            )
        if existing.status != "active":
            await repository.set_model_status(db, existing, "active")
            await db.commit()
        return existing

    model_version = await repository.create_model_version(
        db,
        name=settings.MODEL_NAME,
        version=settings.MODEL_VERSION,
        architecture="LCNN",
        checkpoint_path=str(path),
        sha256_checksum=checksum,
        feature_extractor_name=settings.FEATURE_EXTRACTOR_NAME,
        feature_extractor_version=settings.FEATURE_EXTRACTOR_VERSION,
        status="active",
    )
    await db.commit()
    logger.info(
        "model_version_registered",
        extra={"model_version_id": str(model_version.id), "name": model_version.name, "version": model_version.version},
    )
    return model_version


async def get_active_model_version(db: AsyncSession) -> ModelVersion:
    """The PREPARING_MODEL stage's entry point: returns whatever
    model_versions row is currently active, bootstrapping the default LCNN
    registration only if the database has no active row at all yet.

    Deliberately checks the database *first* and only falls back to
    ensure_default_model_registered as a last resort — the reverse order
    (try the LCNN bootstrap first, unconditionally) would force LCNN back to
    "active" on every single call whenever its checkpoint file happens to
    exist on disk, which would silently undo switch_active_model() the very
    next time a scan is processed. Checking the database first is what
    actually makes "switch active model using ModelVersion only" true: once
    any row is active, it stays the one this returns until something
    explicitly changes that row's status.

    Raises ModelNotAvailableError — never returns None — so callers
    (api.inference.jobs) can treat "no model" as just another
    AIPipelineError landing the scan in MODEL_LOAD_FAILED."""
    model_version = await repository.get_active_model_version(db)
    if model_version is None:
        model_version = await ensure_default_model_registered(db)
    if model_version is None:
        raise ModelNotAvailableError(
            f"No active model version available (checkpoint not found at {_checkpoint_path()})"
        )
    return model_version


# ── Generic, architecture-agnostic registration (Phase 10/13) ──────────────
# ensure_default_model_registered above stays exactly as it was — it is
# specifically "how LCNN bootstraps itself from Settings on first use", a
# behavior with its own tests pinning its exact semantics (idempotency,
# checksum-drift rejection, auto-deactivation when the file disappears).
# register_model_version below is the architecture-agnostic counterpart used
# for every *other* model: it takes its checkpoint path and identity as
# plain parameters instead of reading them from Settings, and asks the
# model's own adapter (see api.inference.adapters) for feature-extractor and
# threshold metadata instead of hardcoding them — this is what Phase 10
# means by "metadata should drive behavior instead of hardcoded constants."
# The two functions intentionally do not share implementation: collapsing
# them into one would risk changing ensure_default_model_registered's
# already-tested behavior for a refactor that saves a dozen lines.


async def register_model_version(
    db: AsyncSession,
    *,
    architecture: str,
    name: str,
    version: str,
    checkpoint_path: str | Path,
    status: str = "inactive",
) -> ModelVersion:
    """Registers (or returns the existing row for) `name`:`version`, using
    `architecture`'s adapter metadata for feature_extractor_name/version —
    the adapter is the single source of truth for that pairing, not a
    caller-supplied argument, so a checkpoint can never accidentally be
    registered against the wrong extractor. Raises ModelIntegrityError on
    checksum drift against an existing row, exactly like
    ensure_default_model_registered. New rows default to status="inactive"
    (unlike the LCNN bootstrap, which activates immediately) — registering a
    second model should never silently change which one is currently
    serving; see switch_active_model for that as a deliberate, separate
    step."""
    from api.inference.adapters import registry as adapter_registry

    path = Path(checkpoint_path).resolve()
    if not path.exists():
        raise ModelNotAvailableError(f"Checkpoint not found at {path}")

    adapter = adapter_registry.get_adapter(architecture)
    meta = adapter.metadata()

    existing = await repository.get_model_version_by_name_version(db, name=name, version=version)
    checksum = _sha256_of(path)

    if existing is not None:
        if existing.sha256_checksum != checksum:
            raise ModelIntegrityError(
                f"Checkpoint at {path} changed since {name}:{version} was registered (checksum drift) — "
                "register a new version instead of replacing the file in place."
            )
        return existing

    model_version = await repository.create_model_version(
        db,
        name=name,
        version=version,
        architecture=architecture,
        checkpoint_path=str(path),
        sha256_checksum=checksum,
        feature_extractor_name=meta.feature_extractor_name,
        feature_extractor_version=meta.feature_extractor_version,
        status=status,
    )
    await db.commit()
    logger.info(
        "model_version_registered",
        extra={
            "model_version_id": str(model_version.id),
            "name": model_version.name,
            "version": model_version.version,
            "architecture": architecture,
        },
    )
    return model_version


async def switch_active_model(db: AsyncSession, *, name: str, version: str) -> ModelVersion:
    """Deactivates every currently-active model_versions row and activates
    exactly `name`:`version`. This is the entire "switch active model"
    operation Phase 13 asks for — a data change through the registry, not a
    code change: nothing in api.inference.jobs, model_loader, or the API
    needs to be touched or redeployed for the next scan to pick up the
    newly-active model."""
    target = await repository.get_model_version_by_name_version(db, name=name, version=version)
    if target is None:
        raise ModelNotAvailableError(f"No registered model version {name}:{version} to activate")

    for row in await repository.list_model_versions(db):
        if row.status == "active" and row.id != target.id:
            await repository.set_model_status(db, row, "inactive")

    if target.status != "active":
        await repository.set_model_status(db, target, "active")
    await db.commit()
    return target


async def health_check(db: AsyncSession) -> dict[str, object]:
    """Backs GET /api/v1/models/current — reports whether a model is
    registered/active without actually loading weights into memory (that
    happens lazily in api.inference.model_loader on first real use)."""
    try:
        model_version = await get_active_model_version(db)
    except ModelNotAvailableError as exc:
        return {"available": False, "reason": str(exc)}

    from api.inference import model_loader

    return {
        "available": True,
        "model_version_id": str(model_version.id),
        "name": model_version.name,
        "version": model_version.version,
        "status": model_version.status,
        "loaded_in_memory": model_loader.is_cached(model_version.id),
    }
