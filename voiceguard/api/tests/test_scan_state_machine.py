from __future__ import annotations

import itertools

import pytest

from api.core.exceptions import InvalidScanStateError
from api.scans.state_machine import (
    TERMINAL_STATUSES,
    ScanStatus,
    _ALLOWED_TRANSITIONS,
    can_transition,
    is_terminal,
    validate_transition,
)

ALL_STATUSES = list(ScanStatus)

# The explicit, human-reviewable edge list this slice's design specifies.
# test_exhaustive_transition_matrix below cross-checks every possible
# (from, to) pair against this — not just the handful exercised by
# test_valid_transitions_succeed — so an accidentally-added edge is caught
# just as reliably as an accidentally-removed one.
EXPECTED_EDGES: set[tuple[ScanStatus, ScanStatus]] = {
    (ScanStatus.CREATED, ScanStatus.VALIDATING),
    (ScanStatus.CREATED, ScanStatus.CANCELLED),
    (ScanStatus.VALIDATING, ScanStatus.UPLOADING),
    (ScanStatus.VALIDATING, ScanStatus.VALIDATION_FAILED),
    (ScanStatus.VALIDATING, ScanStatus.CANCELLED),
    (ScanStatus.UPLOADING, ScanStatus.QUEUED),
    (ScanStatus.UPLOADING, ScanStatus.UPLOAD_FAILED),
    (ScanStatus.UPLOADING, ScanStatus.VALIDATION_FAILED),
    (ScanStatus.UPLOADING, ScanStatus.CANCELLED),
    (ScanStatus.QUEUED, ScanStatus.PREPROCESSING),
    (ScanStatus.QUEUED, ScanStatus.CANCELLED),
    (ScanStatus.QUEUED, ScanStatus.EXPIRED),
    (ScanStatus.PREPROCESSING, ScanStatus.READY_FOR_AI),
    (ScanStatus.PREPROCESSING, ScanStatus.FAILED),
    (ScanStatus.PREPROCESSING, ScanStatus.CANCELLED),
    (ScanStatus.READY_FOR_AI, ScanStatus.PREPARING_MODEL),
    (ScanStatus.READY_FOR_AI, ScanStatus.CANCELLED),
    (ScanStatus.READY_FOR_AI, ScanStatus.EXPIRED),
    # ── AI Processing Pipeline (Slice 03) ───────────────────────────────────
    (ScanStatus.PREPARING_MODEL, ScanStatus.LOADING_MODEL),
    (ScanStatus.PREPARING_MODEL, ScanStatus.MODEL_LOAD_FAILED),
    (ScanStatus.PREPARING_MODEL, ScanStatus.CANCELLED),
    (ScanStatus.LOADING_MODEL, ScanStatus.AI_PREPROCESSING),
    (ScanStatus.LOADING_MODEL, ScanStatus.MODEL_LOAD_FAILED),
    (ScanStatus.LOADING_MODEL, ScanStatus.CANCELLED),
    (ScanStatus.AI_PREPROCESSING, ScanStatus.FEATURE_EXTRACTION),
    (ScanStatus.AI_PREPROCESSING, ScanStatus.AI_PREPROCESSING_FAILED),
    (ScanStatus.AI_PREPROCESSING, ScanStatus.CANCELLED),
    (ScanStatus.FEATURE_EXTRACTION, ScanStatus.RUNNING_INFERENCE),
    (ScanStatus.FEATURE_EXTRACTION, ScanStatus.FEATURE_EXTRACTION_FAILED),
    (ScanStatus.FEATURE_EXTRACTION, ScanStatus.CANCELLED),
    (ScanStatus.RUNNING_INFERENCE, ScanStatus.POSTPROCESSING),
    (ScanStatus.RUNNING_INFERENCE, ScanStatus.INFERENCE_FAILED),
    (ScanStatus.RUNNING_INFERENCE, ScanStatus.CANCELLED),
    (ScanStatus.POSTPROCESSING, ScanStatus.GENERATING_EXPLANATION),
    (ScanStatus.POSTPROCESSING, ScanStatus.POSTPROCESSING_FAILED),
    (ScanStatus.POSTPROCESSING, ScanStatus.CANCELLED),
    (ScanStatus.GENERATING_EXPLANATION, ScanStatus.SAVING_RESULTS),
    (ScanStatus.GENERATING_EXPLANATION, ScanStatus.POSTPROCESSING_FAILED),
    (ScanStatus.GENERATING_EXPLANATION, ScanStatus.CANCELLED),
    (ScanStatus.SAVING_RESULTS, ScanStatus.COMPLETED),
    (ScanStatus.SAVING_RESULTS, ScanStatus.RESULT_PERSISTENCE_FAILED),
}


def test_every_status_has_an_explicit_entry():
    assert set(_ALLOWED_TRANSITIONS.keys()) == set(ALL_STATUSES)


def test_exhaustive_transition_matrix():
    """Every one of the 12*12 (from, to) pairs must match EXPECTED_EDGES
    exactly — this is what "invalid transitions must be impossible" means in
    a way a couple of spot-checks can't guarantee."""
    for frm, to in itertools.product(ALL_STATUSES, ALL_STATUSES):
        expected = (frm, to) in EXPECTED_EDGES
        assert can_transition(frm, to) is expected, f"{frm.value} -> {to.value} expected={expected}"


def test_terminal_statuses_have_no_outgoing_transitions():
    for status in TERMINAL_STATUSES:
        for target in ALL_STATUSES:
            assert not can_transition(status, target), f"{status.value} must have no outgoing transitions"


def test_no_self_transitions():
    for status in ALL_STATUSES:
        assert not can_transition(status, status)


def test_is_terminal_matches_expected_set():
    expected = {
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
    assert {s for s in ALL_STATUSES if is_terminal(s)} == expected


def test_validate_transition_raises_on_invalid_edge():
    with pytest.raises(InvalidScanStateError) as exc_info:
        validate_transition(ScanStatus.CREATED, ScanStatus.READY_FOR_AI)
    assert exc_info.value.code == "INVALID_SCAN_STATE"


def test_validate_transition_silent_on_valid_edge():
    validate_transition(ScanStatus.CREATED, ScanStatus.VALIDATING)  # must not raise


def test_completed_is_reachable_only_from_saving_results():
    """COMPLETED is the AI Processing Pipeline's terminal success state
    (Slice 03) — it must only ever be reached after a scan_results row has
    actually been persisted (SAVING_RESULTS), never as a shortcut from
    earlier in the pipeline or from READY_FOR_AI directly."""
    sources = [frm for frm in ALL_STATUSES if can_transition(frm, ScanStatus.COMPLETED)]
    assert sources == [ScanStatus.SAVING_RESULTS]


def test_ready_for_ai_enters_ai_pipeline_via_preparing_model():
    sources = [frm for frm in ALL_STATUSES if can_transition(frm, ScanStatus.PREPARING_MODEL)]
    assert sources == [ScanStatus.READY_FOR_AI]


def test_ai_stage_failure_target_covers_every_pipeline_stage():
    from api.scans.state_machine import AI_PIPELINE_STAGES, AI_STAGE_FAILURE_TARGET

    assert set(AI_STAGE_FAILURE_TARGET.keys()) == set(AI_PIPELINE_STAGES)
    for stage, failure_target in AI_STAGE_FAILURE_TARGET.items():
        assert can_transition(stage, failure_target), f"{stage.value} -> {failure_target.value} must be a valid edge"
