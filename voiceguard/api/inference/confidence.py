from __future__ import annotations

from dataclasses import dataclass

from api.inference.exceptions import ResultValidationError
from api.inference.inference import InferenceResult

VERDICT_HUMAN = "human"
VERDICT_AI_GENERATED = "ai_generated"
VERDICT_UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class CalibratedScores:
    bonafide_score: float
    spoof_score: float


@dataclass(frozen=True)
class ConfidenceResult:
    verdict: str
    confidence: float
    threshold_used: float
    is_below_threshold: bool


def calibrate(raw: InferenceResult) -> CalibratedScores:
    """Confidence Calibration extension point. The softmax output of an
    uncalibrated classifier is not a true probability — proper calibration
    (temperature scaling / Platt scaling) needs a held-out calibration
    dataset this project doesn't have yet, so this is currently an identity
    passthrough of the raw softmax scores. Kept as its own function (rather
    than folding calibration into `decide`) so plugging in real temperature
    scaling later is a one-function change with no caller updates."""
    return CalibratedScores(bonafide_score=raw.bonafide_score, spoof_score=raw.spoof_score)


def decide(scores: CalibratedScores, *, label: str, threshold: float) -> ConfidenceResult:
    """Threshold Decision: the winning class's score must clear `threshold`
    to be reported as a definite human/ai_generated verdict; anything lower
    is surfaced as 'uncertain' rather than forcing a low-confidence call."""
    confidence = max(scores.bonafide_score, scores.spoof_score)
    below = confidence < threshold

    if below:
        verdict = VERDICT_UNCERTAIN
    elif label == "bonafide":
        verdict = VERDICT_HUMAN
    else:
        verdict = VERDICT_AI_GENERATED

    return ConfidenceResult(verdict=verdict, confidence=confidence, threshold_used=threshold, is_below_threshold=below)


def validate_result(scores: CalibratedScores, result: ConfidenceResult) -> None:
    """Result Validation — a sanity check on the numbers about to be
    persisted, independent of whatever produced them."""
    total = scores.bonafide_score + scores.spoof_score
    if not (0.98 <= total <= 1.02):
        raise ResultValidationError(f"Class scores do not sum to ~1 (bonafide+spoof={total:.4f})")
    if not (0.0 <= result.confidence <= 1.0):
        raise ResultValidationError(f"Confidence out of range: {result.confidence}")
    if result.verdict not in (VERDICT_HUMAN, VERDICT_AI_GENERATED, VERDICT_UNCERTAIN):
        raise ResultValidationError(f"Unknown verdict: {result.verdict!r}")


def calibrate_and_decide(raw: InferenceResult, *, threshold: float) -> tuple[CalibratedScores, ConfidenceResult]:
    scores = calibrate(raw)
    result = decide(scores, label=raw.label, threshold=threshold)
    validate_result(scores, result)
    return scores, result
