from __future__ import annotations

import pytest

from api.inference.exceptions import FeatureExtractionError
from api.inference.feature_extraction import available_extractors, extract_features, validate_feature


def _waveform():
    import torch

    return torch.randn(1, 64000) * 0.1  # matches AudioCNN's AudioConfig: 16kHz, 4.0s


def test_logmel64db_is_registered():
    assert ("logmel64db", "v1") in available_extractors()
    # Original LCNN extractor must still be present, unmodified — Phase 4:
    # "Never modify LCNN preprocessing."
    assert ("logmel", "v1") in available_extractors()


def test_logmel64db_produces_expected_shape():
    feature = extract_features(_waveform(), extractor_name="logmel64db", extractor_version="v1")
    assert feature.name == "logmel64db"
    assert feature.version == "v1"
    assert feature.shape[0] == 1  # channel dim, matches logmel:v1's convention
    assert feature.shape[1] == 64  # n_mels — the detector's own config, not LCNN's 128
    assert feature.tensor.shape == tuple(feature.shape)


def test_logmel64db_is_per_clip_z_score_normalized():
    """Must match Devil-92/Fake-Audio-Detector's features.py exactly:
    (db - mean) / (std + 1e-6) — verified numerically, not just structurally,
    since a subtly wrong normalization would silently degrade the
    checkpoint's real-world accuracy without ever raising an error."""
    feature = extract_features(_waveform(), extractor_name="logmel64db", extractor_version="v1")
    tensor = feature.tensor
    assert float(tensor.mean()) == pytest.approx(0.0, abs=1e-4)
    assert float(tensor.std()) == pytest.approx(1.0, abs=1e-3)


def test_logmel64db_passes_validation():
    feature = extract_features(_waveform(), extractor_name="logmel64db", extractor_version="v1")
    validate_feature(feature)  # must not raise


def test_logmel_v1_output_is_unaffected_by_the_new_extractor():
    """Phase 4: "Never modify LCNN preprocessing." — logmel:v1's own shape
    convention (128 mels, natural-log, no z-score) must be exactly what it
    was before logmel64db existed."""
    feature = extract_features(_waveform(), extractor_name="logmel", extractor_version="v1")
    assert feature.shape[1] == 128
    # LCNN's transform is NOT z-score normalized — a real assertion that the
    # two extractors weren't accidentally unified into one code path.
    assert float(feature.tensor.std()) != pytest.approx(1.0, abs=1e-3)


def test_unknown_extractor_still_raises():
    with pytest.raises(FeatureExtractionError):
        extract_features(_waveform(), extractor_name="mfcc", extractor_version="v1")
