from __future__ import annotations

import pytest

from api.inference.confidence import (
    VERDICT_AI_GENERATED,
    VERDICT_HUMAN,
    VERDICT_UNCERTAIN,
    CalibratedScores,
    calibrate,
    calibrate_and_decide,
    decide,
    validate_result,
)
from api.inference.exceptions import ResultValidationError
from api.inference.inference import InferenceResult


def _inference_result(*, bonafide: float, spoof: float, label: str) -> InferenceResult:
    return InferenceResult(label=label, bonafide_score=bonafide, spoof_score=spoof, inference_time_ms=5)


def test_calibrate_is_currently_an_identity_passthrough():
    raw = _inference_result(bonafide=0.7, spoof=0.3, label="bonafide")
    scores = calibrate(raw)
    assert scores.bonafide_score == raw.bonafide_score
    assert scores.spoof_score == raw.spoof_score


def test_decide_returns_human_for_confident_bonafide():
    scores = CalibratedScores(bonafide_score=0.9, spoof_score=0.1)
    result = decide(scores, label="bonafide", threshold=0.6)
    assert result.verdict == VERDICT_HUMAN
    assert result.confidence == pytest.approx(0.9)
    assert result.is_below_threshold is False


def test_decide_returns_ai_generated_for_confident_spoof():
    scores = CalibratedScores(bonafide_score=0.1, spoof_score=0.9)
    result = decide(scores, label="spoof", threshold=0.6)
    assert result.verdict == VERDICT_AI_GENERATED
    assert result.is_below_threshold is False


def test_decide_returns_uncertain_below_threshold():
    scores = CalibratedScores(bonafide_score=0.52, spoof_score=0.48)
    result = decide(scores, label="bonafide", threshold=0.6)
    assert result.verdict == VERDICT_UNCERTAIN
    assert result.is_below_threshold is True


def test_decide_at_exact_threshold_is_not_below():
    scores = CalibratedScores(bonafide_score=0.6, spoof_score=0.4)
    result = decide(scores, label="bonafide", threshold=0.6)
    assert result.is_below_threshold is False
    assert result.verdict == VERDICT_HUMAN


def test_validate_result_rejects_scores_not_summing_to_one():
    scores = CalibratedScores(bonafide_score=0.9, spoof_score=0.9)
    result = decide(scores, label="bonafide", threshold=0.6)
    with pytest.raises(ResultValidationError):
        validate_result(scores, result)


def test_validate_result_accepts_well_formed_result():
    scores = CalibratedScores(bonafide_score=0.7, spoof_score=0.3)
    result = decide(scores, label="bonafide", threshold=0.6)
    validate_result(scores, result)  # must not raise


def test_calibrate_and_decide_end_to_end():
    raw = _inference_result(bonafide=0.2, spoof=0.8, label="spoof")
    scores, result = calibrate_and_decide(raw, threshold=0.6)
    assert scores.spoof_score == 0.8
    assert result.verdict == VERDICT_AI_GENERATED
    assert result.threshold_used == 0.6
