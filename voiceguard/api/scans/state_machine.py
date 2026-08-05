from __future__ import annotations

from enum import Enum

from api.core.exceptions import InvalidScanStateError


class ScanStatus(str, Enum):
    """The upload lifecycle (CREATED..READY_FOR_AI, plus its failure/terminal
    states) is Slice 02's. Everything from PREPARING_MODEL onward is Slice 03
    (AI Processing Pipeline & Detection Engine): it picks up exactly at
    READY_FOR_AI and ends at COMPLETED, per that slice's design.

    Naming note: the AI pipeline's own preprocessing stage is named
    AI_PREPROCESSING rather than PREPROCESSING — PREPROCESSING already exists
    above as Slice 02's post-upload step (QUEUED -> PREPROCESSING ->
    READY_FOR_AI, wav-metadata extraction). Reusing that name for a completely
    different stage later in the same enum would collide with an existing,
    tested state and make `scan_events` history ambiguous about which
    "preprocessing" a given row refers to."""

    CREATED = "created"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    READY_FOR_AI = "ready_for_ai"

    # ── AI Processing Pipeline (Slice 03) ───────────────────────────────────
    PREPARING_MODEL = "preparing_model"
    LOADING_MODEL = "loading_model"
    AI_PREPROCESSING = "ai_preprocessing"
    FEATURE_EXTRACTION = "feature_extraction"
    RUNNING_INFERENCE = "running_inference"
    POSTPROCESSING = "postprocessing"
    GENERATING_EXPLANATION = "generating_explanation"
    SAVING_RESULTS = "saving_results"

    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"
    UPLOAD_FAILED = "upload_failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    # ── AI Processing failure states (Slice 03) ─────────────────────────────
    MODEL_LOAD_FAILED = "model_load_failed"
    AI_PREPROCESSING_FAILED = "ai_preprocessing_failed"
    FEATURE_EXTRACTION_FAILED = "feature_extraction_failed"
    INFERENCE_FAILED = "inference_failed"
    POSTPROCESSING_FAILED = "postprocessing_failed"
    RESULT_PERSISTENCE_FAILED = "result_persistence_failed"


TERMINAL_STATUSES: frozenset[ScanStatus] = frozenset(
    {
        ScanStatus.COMPLETED,
        ScanStatus.FAILED,
        ScanStatus.VALIDATION_FAILED,
        ScanStatus.UPLOAD_FAILED,
        ScanStatus.CANCELLED,
        ScanStatus.EXPIRED,
        ScanStatus.MODEL_LOAD_FAILED,
        ScanStatus.AI_PREPROCESSING_FAILED,
        ScanStatus.FEATURE_EXTRACTION_FAILED,
        ScanStatus.INFERENCE_FAILED,
        ScanStatus.POSTPROCESSING_FAILED,
        ScanStatus.RESULT_PERSISTENCE_FAILED,
    }
)

# The complete, explicit transition graph. Every key must be present (even
# terminal states, mapped to an empty set) so `can_transition`/`validate_transition`
# never has to guess about an omitted state — that's what "invalid transitions
# must be impossible" means in practice: there is no code path that reaches a
# transition not listed here.
_ALLOWED_TRANSITIONS: dict[ScanStatus, frozenset[ScanStatus]] = {
    ScanStatus.CREATED: frozenset({ScanStatus.VALIDATING, ScanStatus.CANCELLED}),
    ScanStatus.VALIDATING: frozenset(
        {ScanStatus.UPLOADING, ScanStatus.VALIDATION_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.UPLOADING: frozenset(
        {
            ScanStatus.QUEUED,
            ScanStatus.UPLOAD_FAILED,
            ScanStatus.VALIDATION_FAILED,  # duplicate-checksum / size limits only knowable post-stream
            ScanStatus.CANCELLED,
        }
    ),
    ScanStatus.QUEUED: frozenset({ScanStatus.PREPROCESSING, ScanStatus.CANCELLED, ScanStatus.EXPIRED}),
    ScanStatus.PREPROCESSING: frozenset({ScanStatus.READY_FOR_AI, ScanStatus.FAILED, ScanStatus.CANCELLED}),
    # COMPLETED is no longer reached directly from READY_FOR_AI — Slice 03's
    # pipeline now owns that edge. Picking a scan up for AI processing means
    # entering PREPARING_MODEL; a scan can still be CANCELLED while waiting,
    # or EXPIRED if nothing claims it before its deadline (see
    # api.scans.service.expire_stale_scans).
    ScanStatus.READY_FOR_AI: frozenset(
        {ScanStatus.PREPARING_MODEL, ScanStatus.CANCELLED, ScanStatus.EXPIRED}
    ),
    # ── AI Processing Pipeline (Slice 03) ───────────────────────────────────
    # Each forward stage may go on to the next stage, fail into its own
    # dedicated terminal *_FAILED state, or be cancelled by the user. Retries
    # happen *inside* a stage's own runner (api.inference.jobs) rather than as
    # extra graph edges — the state machine only ever sees one forward
    # transition per stage, keeping this table exhaustive and readable rather
    # than growing an edge per retry attempt.
    ScanStatus.PREPARING_MODEL: frozenset(
        {ScanStatus.LOADING_MODEL, ScanStatus.MODEL_LOAD_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.LOADING_MODEL: frozenset(
        {ScanStatus.AI_PREPROCESSING, ScanStatus.MODEL_LOAD_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.AI_PREPROCESSING: frozenset(
        {ScanStatus.FEATURE_EXTRACTION, ScanStatus.AI_PREPROCESSING_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.FEATURE_EXTRACTION: frozenset(
        {ScanStatus.RUNNING_INFERENCE, ScanStatus.FEATURE_EXTRACTION_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.RUNNING_INFERENCE: frozenset(
        {ScanStatus.POSTPROCESSING, ScanStatus.INFERENCE_FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.POSTPROCESSING: frozenset(
        {ScanStatus.GENERATING_EXPLANATION, ScanStatus.POSTPROCESSING_FAILED, ScanStatus.CANCELLED}
    ),
    # Explanation generation is best-effort commentary on an already-decided
    # verdict (see api.inference.explainability) — the spec lists no dedicated
    # "explanation failed" terminal state, so a hard failure here is reported
    # as POSTPROCESSING_FAILED rather than growing a seventh failure state for
    # a stage that never changes the verdict itself.
    ScanStatus.GENERATING_EXPLANATION: frozenset(
        {ScanStatus.SAVING_RESULTS, ScanStatus.POSTPROCESSING_FAILED, ScanStatus.CANCELLED}
    ),
    # No CANCELLED here: once a result write has started, letting it finish
    # (or fail outright into RESULT_PERSISTENCE_FAILED) avoids leaving a
    # half-written scan_results row behind.
    ScanStatus.SAVING_RESULTS: frozenset({ScanStatus.COMPLETED, ScanStatus.RESULT_PERSISTENCE_FAILED}),
    ScanStatus.COMPLETED: frozenset(),
    ScanStatus.FAILED: frozenset(),
    ScanStatus.VALIDATION_FAILED: frozenset(),
    ScanStatus.UPLOAD_FAILED: frozenset(),
    ScanStatus.CANCELLED: frozenset(),
    ScanStatus.EXPIRED: frozenset(),
    ScanStatus.MODEL_LOAD_FAILED: frozenset(),
    ScanStatus.AI_PREPROCESSING_FAILED: frozenset(),
    ScanStatus.FEATURE_EXTRACTION_FAILED: frozenset(),
    ScanStatus.INFERENCE_FAILED: frozenset(),
    ScanStatus.POSTPROCESSING_FAILED: frozenset(),
    ScanStatus.RESULT_PERSISTENCE_FAILED: frozenset(),
}


# Stages whose *_FAILED terminal state a retry-exhausted job should land in.
# api.inference.jobs uses this to map "which macro-stage was running when the
# final attempt failed" to the correct transition target without a long
# if/elif chain at the call site.
AI_STAGE_FAILURE_TARGET: dict[ScanStatus, ScanStatus] = {
    ScanStatus.PREPARING_MODEL: ScanStatus.MODEL_LOAD_FAILED,
    ScanStatus.LOADING_MODEL: ScanStatus.MODEL_LOAD_FAILED,
    ScanStatus.AI_PREPROCESSING: ScanStatus.AI_PREPROCESSING_FAILED,
    ScanStatus.FEATURE_EXTRACTION: ScanStatus.FEATURE_EXTRACTION_FAILED,
    ScanStatus.RUNNING_INFERENCE: ScanStatus.INFERENCE_FAILED,
    ScanStatus.POSTPROCESSING: ScanStatus.POSTPROCESSING_FAILED,
    ScanStatus.GENERATING_EXPLANATION: ScanStatus.POSTPROCESSING_FAILED,
    ScanStatus.SAVING_RESULTS: ScanStatus.RESULT_PERSISTENCE_FAILED,
}

# The AI pipeline's own linear stage order — the sequence run_ai_pipeline_job
# walks forward through on a clean attempt. Kept next to the transition table
# so the two can never silently drift apart.
AI_PIPELINE_STAGES: tuple[ScanStatus, ...] = (
    ScanStatus.PREPARING_MODEL,
    ScanStatus.LOADING_MODEL,
    ScanStatus.AI_PREPROCESSING,
    ScanStatus.FEATURE_EXTRACTION,
    ScanStatus.RUNNING_INFERENCE,
    ScanStatus.POSTPROCESSING,
    ScanStatus.GENERATING_EXPLANATION,
    ScanStatus.SAVING_RESULTS,
)


def is_terminal(current: ScanStatus) -> bool:
    return current in TERMINAL_STATUSES


def can_transition(current: ScanStatus, target: ScanStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def validate_transition(current: ScanStatus, target: ScanStatus) -> None:
    if not can_transition(current, target):
        raise InvalidScanStateError(
            f"Cannot transition scan from {current.value!r} to {target.value!r}",
            details=[{"field": "status", "message": f"invalid transition: {current.value} -> {target.value}"}],
        )
