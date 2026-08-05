from __future__ import annotations

from fastapi import status

from api.core.exceptions import BaseVoiceGuardError, BusinessLogicError, NotFoundError, ServiceUnavailableError


class AIStageTimeoutError(BaseVoiceGuardError):
    """Raised by api.inference.jobs when a stage's asyncio.wait_for deadline
    (AI_STAGE_TIMEOUT_S) elapses — the generic timeout counterpart to each
    stage's own specific error classes below, used uniformly for every stage
    since a hang can happen anywhere (a wedged torch call, a slow storage
    backend, ...), not just in inference."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    code = "AI_STAGE_TIMEOUT"
    retryable = True


class AIPipelineError(BaseVoiceGuardError):
    """Base for every error raised inside the AI Processing Pipeline
    (api.inference.*) — failures discovered *after* a scan already reached
    READY_FOR_AI, as opposed to api.core.exceptions' upload-time validation
    errors. `retryable` tells api.inference.jobs whether re-running the same
    stage from scratch is worth attempting before giving up; a corrupted file
    or a threshold-shape mismatch will fail identically every time, so those
    are marked non-retryable to avoid burning AI_STAGE_MAX_ATTEMPTS on a
    guaranteed repeat failure."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "AI_PROCESSING_ERROR"
    retryable = True


# ── Orchestration / request-time (surfaced directly over HTTP) ────────────────


class ScanNotReadyForProcessingError(BusinessLogicError):
    """POST /scans/{id}/process called on a scan that isn't READY_FOR_AI (or
    is already mid-pipeline / terminal)."""

    code = "SCAN_NOT_READY_FOR_PROCESSING"


class ResultNotFoundError(NotFoundError):
    """GET .../result | .../technical | .../explanation before a scan_results
    row exists — distinct from ScanNotFoundError, which means the scan itself
    doesn't exist or isn't owned by the caller."""

    code = "RESULT_NOT_FOUND"


# ── Model lifecycle ─────────────────────────────────────────────────────────


class ModelNotAvailableError(ServiceUnavailableError, AIPipelineError):
    """No active, loadable model version exists (missing checkpoint file,
    empty registry, or every registered version is inactive)."""

    code = "MODEL_NOT_AVAILABLE"
    retryable = False


class ModelIntegrityError(ServiceUnavailableError, AIPipelineError):
    """The checkpoint on disk does not match the sha256 recorded for this
    model_versions row at registration time — refuse to load it rather than
    run inference against a possibly-tampered or corrupted file."""

    code = "MODEL_INTEGRITY_FAILED"
    retryable = False


class ModelLoadTimeoutError(AIPipelineError):
    code = "MODEL_LOAD_TIMEOUT"
    retryable = True


# ── Preprocessing ────────────────────────────────────────────────────────────


class AudioRetrievalError(AIPipelineError):
    """The scan's storage_key could not be read back from the storage
    backend (file missing, storage layer error) — distinct from a corrupted
    file, which does read but fails to decode."""

    code = "AUDIO_RETRIEVAL_FAILED"
    retryable = True


class AudioIntegrityError(AIPipelineError):
    """The stored file's sha256 no longer matches Scan.sha256_checksum —
    tampering or on-disk corruption between upload and AI processing."""

    code = "AUDIO_INTEGRITY_FAILED"
    retryable = False


class AudioDecodeError(AIPipelineError):
    """The audio codec/container could not be decoded at all."""

    code = "AUDIO_DECODE_FAILED"
    retryable = False


class AudioTooShortError(AIPipelineError):
    """After silence trimming, less than AI_MIN_AUDIO_DURATION_S of audio
    signal remains — too little to run detection on meaningfully."""

    code = "AUDIO_TOO_SHORT"
    retryable = False


# ── Feature extraction ───────────────────────────────────────────────────────


class FeatureExtractionError(AIPipelineError):
    code = "FEATURE_EXTRACTION_FAILED"
    retryable = True


class FeatureValidationError(AIPipelineError):
    """A produced feature tensor has the wrong shape/dtype or contains
    NaN/Inf — a bug or a pathological input, never worth retrying as-is."""

    code = "FEATURE_VALIDATION_FAILED"
    retryable = False


# ── Inference ─────────────────────────────────────────────────────────────────


class InferenceError(AIPipelineError):
    code = "INFERENCE_FAILED"
    retryable = True


class InferenceTimeoutError(AIPipelineError):
    code = "INFERENCE_TIMEOUT"
    retryable = True


# ── Postprocessing / results ────────────────────────────────────────────────


class ResultValidationError(AIPipelineError):
    """Confidence/verdict failed a sanity check (e.g. probabilities that
    don't sum to ~1, confidence outside [0, 1]) before being persisted."""

    code = "RESULT_VALIDATION_FAILED"
    retryable = False


class ResultPersistenceError(AIPipelineError):
    code = "RESULT_PERSISTENCE_FAILED"
    retryable = True
