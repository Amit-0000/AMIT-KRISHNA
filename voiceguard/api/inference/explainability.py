from __future__ import annotations

import logging
from dataclasses import dataclass

from api.inference.confidence import ConfidenceResult
from api.inference.feature_extraction import ExtractedFeature
from api.inference.inference import InferenceResult
from api.inference.model_loader import LoadedModel

logger = logging.getLogger("voiceguard.inference")


@dataclass(frozen=True)
class SalientRegion:
    start_s: float
    end_s: float
    importance: float


@dataclass(frozen=True)
class ExplanationResult:
    salient_regions: list[SalientRegion]
    notes: list[str]
    warnings: list[str]
    feature_extractor: str
    model_version: str


def _compute_salient_regions(
    loaded_model: LoadedModel, feature: ExtractedFeature, inference_result: InferenceResult, *, top_k: int = 3
) -> list[SalientRegion]:
    """Grad-CAM over the mel-spectrogram (src.explainability.gradcam,
    reused as-is) reduced to the top-k highest-importance time windows —
    "Important Signal Regions" per the design doc. Runs as its own
    forward+backward pass, separate from the no_grad inference pass in
    api.inference.inference (Grad-CAM needs gradients w.r.t. the input)."""
    from src.data.transforms import HOP_LENGTH, SAMPLE_RATE
    from src.explainability.gradcam import GradCAM

    target_class = 1 if inference_result.label == "spoof" else 0
    mel = feature.tensor.unsqueeze(0).clone().to(loaded_model.device)

    with GradCAM(loaded_model.model, loaded_model.device) as cam_engine:
        cam = cam_engine.compute(mel, target_class=target_class)  # [128, T] numpy, values in [0, 1]

    energy_per_frame = cam.mean(axis=0)  # [T]
    total_frames = energy_per_frame.shape[0]
    if total_frames == 0:
        return []

    window = max(1, total_frames // 10)
    windows = []
    for start in range(0, total_frames, window):
        end = min(start + window, total_frames)
        windows.append((float(energy_per_frame[start:end].mean()), start, end))
    windows.sort(key=lambda w: w[0], reverse=True)

    return [
        SalientRegion(
            start_s=round(start * HOP_LENGTH / SAMPLE_RATE, 3),
            end_s=round(end * HOP_LENGTH / SAMPLE_RATE, 3),
            importance=round(importance, 4),
        )
        for importance, start, end in windows[:top_k]
    ]


def _build_notes(inference_result: InferenceResult, confidence_result: ConfidenceResult, silence_ratio: float) -> list[str]:
    notes = [f"Model classified this clip as {inference_result.label} with {confidence_result.confidence:.0%} confidence."]
    if confidence_result.is_below_threshold:
        notes.append(
            f"Confidence fell below the {confidence_result.threshold_used:.0%} decision threshold — "
            "reported as uncertain rather than a definite verdict."
        )
    if silence_ratio > 0.5:
        notes.append(f"{silence_ratio:.0%} of the analyzed clip was detected as silence.")
    return notes


def generate_explanation(
    loaded_model: LoadedModel,
    feature: ExtractedFeature,
    inference_result: InferenceResult,
    confidence_result: ConfidenceResult,
    *,
    silence_ratio: float,
    model_version_label: str,
) -> ExplanationResult:
    """Best-effort by design: a Grad-CAM failure (e.g. an unexpected feature
    shape) degrades to an empty region list plus a warning rather than
    failing the whole scan — the verdict itself was already decided upstream
    in api.inference.confidence and does not depend on this succeeding.
    Synchronous — see api.inference.preprocessing.run_preprocessing for why."""
    warnings: list[str] = []
    try:
        regions = _compute_salient_regions(loaded_model, feature, inference_result)
    except Exception as exc:  # noqa: BLE001 - explanation is supplementary, never fatal to the scan
        logger.warning("explanation_generation_degraded", extra={"error": str(exc)})
        regions = []
        warnings.append("Signal region highlighting is unavailable for this scan.")

    notes = _build_notes(inference_result, confidence_result, silence_ratio)

    return ExplanationResult(
        salient_regions=regions,
        notes=notes,
        warnings=warnings,
        feature_extractor=f"{feature.name}:{feature.version}",
        model_version=model_version_label,
    )
