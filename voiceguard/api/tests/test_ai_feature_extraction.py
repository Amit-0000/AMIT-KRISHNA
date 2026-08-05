from __future__ import annotations

import pytest

from api.inference.exceptions import FeatureExtractionError, FeatureValidationError
from api.inference.feature_extraction import (
    ExtractedFeature,
    available_extractors,
    extract_features,
    register_extractor,
    summarize,
    validate_feature,
)


def _waveform():
    from src.data.dataset import MAX_SAMPLES
    import torch

    return torch.randn(1, MAX_SAMPLES) * 0.1


def test_logmel_v1_is_registered_by_default():
    assert ("logmel", "v1") in available_extractors()


def test_extract_features_produces_expected_shape():
    feature = extract_features(_waveform(), extractor_name="logmel", extractor_version="v1")
    assert feature.name == "logmel"
    assert feature.version == "v1"
    assert feature.shape[0] == 1  # channel dim
    assert feature.shape[1] == 128  # N_MELS
    assert feature.tensor.shape == tuple(feature.shape)


def test_extract_features_raises_for_unknown_extractor():
    with pytest.raises(FeatureExtractionError):
        extract_features(_waveform(), extractor_name="does-not-exist", extractor_version="v99")


def test_validate_feature_rejects_nan_tensor():
    import torch

    tensor = torch.full((1, 4, 4), float("nan"))
    feature = ExtractedFeature(name="test", version="v1", tensor=tensor, shape=[1, 4, 4], dtype="float32")
    with pytest.raises(FeatureValidationError):
        validate_feature(feature)


def test_validate_feature_rejects_empty_tensor():
    import torch

    tensor = torch.empty(0)
    feature = ExtractedFeature(name="test", version="v1", tensor=tensor, shape=[0], dtype="float32")
    with pytest.raises(FeatureValidationError):
        validate_feature(feature)


def test_validate_feature_accepts_finite_tensor():
    import torch

    tensor = torch.randn(1, 4, 4)
    feature = ExtractedFeature(name="test", version="v1", tensor=tensor, shape=[1, 4, 4], dtype="float32")
    validate_feature(feature)  # must not raise


def test_summarize_returns_finite_aggregate_stats():
    feature = extract_features(_waveform(), extractor_name="logmel", extractor_version="v1")
    stats = summarize(feature)
    assert set(stats.keys()) == {"mean", "std", "min", "max"}
    assert all(isinstance(v, float) for v in stats.values())


def test_register_extractor_adds_a_new_pluggable_extractor_without_touching_existing_code():
    """Demonstrates the extension point: a brand-new extractor is one
    decorated function away, with zero changes to extract_features or any
    existing extractor."""

    @register_extractor("dummy", "v1")
    def _dummy(waveform):
        tensor = waveform.mean(dim=-1, keepdim=True)
        return ExtractedFeature(name="dummy", version="v1", tensor=tensor, shape=list(tensor.shape), dtype="float32")

    try:
        assert ("dummy", "v1") in available_extractors()
        feature = extract_features(_waveform(), extractor_name="dummy", extractor_version="v1")
        assert feature.name == "dummy"
    finally:
        from api.inference import feature_extraction as fe_module

        fe_module._EXTRACTORS.pop(("dummy", "v1"), None)
