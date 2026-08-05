from __future__ import annotations

import pytest

from api.inference.exceptions import InferenceError
from api.inference.feature_extraction import ExtractedFeature, extract_features
from api.inference.inference import run_inference
from api.inference.model_loader import LoadedModel


def _loaded_model():
    import torch

    from src.models.lcnn import LCNN

    model = LCNN().eval()
    return LoadedModel(model=model, device=torch.device("cpu"), model_version_id=None)


def _feature():
    from src.data.dataset import MAX_SAMPLES
    import torch

    waveform = torch.randn(1, MAX_SAMPLES) * 0.1
    return extract_features(waveform, extractor_name="logmel", extractor_version="v1")


def test_run_inference_returns_a_valid_probability_distribution():
    result = run_inference(_loaded_model(), _feature())
    assert result.label in ("bonafide", "spoof")
    assert 0.0 <= result.bonafide_score <= 1.0
    assert 0.0 <= result.spoof_score <= 1.0
    assert result.bonafide_score + result.spoof_score == pytest.approx(1.0, abs=1e-4)
    assert result.inference_time_ms >= 0


def test_run_inference_label_matches_the_higher_score():
    result = run_inference(_loaded_model(), _feature())
    if result.label == "bonafide":
        assert result.bonafide_score >= result.spoof_score
    else:
        assert result.spoof_score >= result.bonafide_score


def test_run_inference_raises_inference_error_on_shape_mismatch():
    """A feature tensor with the wrong shape must surface as InferenceError
    (mapped to INFERENCE_FAILED by api.inference.jobs), not an unhandled
    RuntimeError bubbling out of torch."""
    import torch

    bad_feature = ExtractedFeature(
        name="logmel", version="v1", tensor=torch.randn(1, 4, 4), shape=[1, 4, 4], dtype="float32"
    )
    with pytest.raises(InferenceError):
        run_inference(_loaded_model(), bad_feature)
