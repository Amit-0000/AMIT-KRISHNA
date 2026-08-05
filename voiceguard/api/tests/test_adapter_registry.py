from __future__ import annotations

import pytest

from api.inference.adapters import registry as adapter_registry
from api.inference.adapters.audio_cnn_adapter import AudioCNNAdapter
from api.inference.adapters.base import AdapterMetadata, ModelAdapter
from api.inference.adapters.lcnn_adapter import LCNNAdapter
from api.inference.exceptions import ModelNotAvailableError


def test_builtin_architectures_are_registered():
    assert set(adapter_registry.available_architectures()) >= {"LCNN", "AudioCNN"}


def test_get_adapter_returns_the_correct_class():
    assert isinstance(adapter_registry.get_adapter("LCNN"), LCNNAdapter)
    assert isinstance(adapter_registry.get_adapter("AudioCNN"), AudioCNNAdapter)


def test_get_adapter_raises_for_unknown_architecture():
    with pytest.raises(ModelNotAvailableError):
        adapter_registry.get_adapter("SomeFutureTransformerDetector")


def test_get_adapter_is_idempotent_same_instance():
    """The registry stores one adapter instance per architecture (adapters
    are stateless routers, not per-request objects) — repeated lookups must
    return the identical object, not a fresh one each time."""
    first = adapter_registry.get_adapter("LCNN")
    second = adapter_registry.get_adapter("LCNN")
    assert first is second


def test_lcnn_adapter_metadata_matches_registered_defaults():
    meta = adapter_registry.get_adapter("LCNN").metadata()
    assert isinstance(meta, AdapterMetadata)
    assert meta.architecture == "LCNN"
    assert meta.feature_extractor_name == "logmel"
    assert meta.feature_extractor_version == "v1"
    assert meta.supports_explainability is True
    assert meta.label_mapping == {"bonafide": "bonafide", "spoof": "spoof"}


def test_audio_cnn_adapter_metadata_matches_source_repo_config():
    meta = adapter_registry.get_adapter("AudioCNN").metadata()
    assert meta.architecture == "AudioCNN"
    assert meta.feature_extractor_name == "logmel64db"
    assert meta.feature_extractor_version == "v1"
    assert meta.supports_explainability is False
    assert meta.label_mapping == {"Genuine": "bonafide", "Deepfake": "spoof"}


def test_lcnn_adapter_feature_extractor_key():
    assert adapter_registry.get_adapter("LCNN").feature_extractor() == ("logmel", "v1")


def test_audio_cnn_adapter_feature_extractor_key():
    assert adapter_registry.get_adapter("AudioCNN").feature_extractor() == ("logmel64db", "v1")


def test_audio_cnn_adapter_does_not_support_explainability():
    assert adapter_registry.get_adapter("AudioCNN").supports_explainability() is False


def test_lcnn_adapter_supports_explainability():
    assert adapter_registry.get_adapter("LCNN").supports_explainability() is True


def test_default_generate_explanation_is_gracefully_unavailable():
    """ModelAdapter's own default implementation (not overridden by
    AudioCNNAdapter) must never raise — this is Phase 8's "the scan must
    never fail because explainability is unavailable" guarantee, verified
    directly against the base-class default rather than only indirectly
    through a full pipeline run."""
    from api.inference.confidence import ConfidenceResult
    from api.inference.feature_extraction import ExtractedFeature
    from api.inference.inference import InferenceResult

    adapter = adapter_registry.get_adapter("AudioCNN")
    feature = ExtractedFeature(name="logmel64db", version="v1", tensor=object(), shape=[1, 64, 251], dtype="float32")
    inference_result = InferenceResult(label="bonafide", bonafide_score=0.9, spoof_score=0.1, inference_time_ms=5)
    confidence_result = ConfidenceResult(verdict="human", confidence=0.9, threshold_used=0.6, is_below_threshold=False)

    explanation = adapter.generate_explanation(
        loaded_model=None,
        feature=feature,
        inference_result=inference_result,
        confidence_result=confidence_result,
        silence_ratio=0.0,
        model_version_label="audio_cnn:v1",
    )
    assert explanation.salient_regions == []
    assert len(explanation.warnings) == 1
    assert "AudioCNN" in explanation.warnings[0]


# ── Registering a throwaway third adapter (Phase 14 — future-proofing) ──────


class _DummyAdapter(ModelAdapter):
    architecture = "DummyFutureModel"

    def load_model(self, checkpoint_path, device):
        return object()

    def feature_extractor(self):
        return ("logmel", "v1")

    def predict(self, loaded_model, feature):
        return None

    def convert_prediction(self, raw_prediction):
        from api.inference.inference import InferenceResult

        return InferenceResult(label="bonafide", bonafide_score=1.0, spoof_score=0.0, inference_time_ms=0)

    def metadata(self):
        return AdapterMetadata(
            architecture="DummyFutureModel",
            checkpoint_filename="dummy.pt",
            feature_extractor_name="logmel",
            feature_extractor_version="v1",
            input_shape=(1, 1, 1),
            preprocessing_version="v1",
            supports_explainability=False,
            label_mapping={},
            default_threshold=0.5,
        )


def test_registering_a_new_adapter_requires_no_orchestration_changes():
    """Demonstrates Phase 14/Final Report item #14: a third architecture is
    exactly one class + one decorator, with zero changes to
    api.inference.model_loader, api.inference.jobs, or anything else in the
    orchestration layer — this test only touches the registry."""
    adapter_registry.register_adapter("DummyFutureModel")(_DummyAdapter)
    try:
        assert "DummyFutureModel" in adapter_registry.available_architectures()
        adapter = adapter_registry.get_adapter("DummyFutureModel")
        assert isinstance(adapter, _DummyAdapter)
        result = adapter.convert_prediction(adapter.predict(None, None))
        assert result.label == "bonafide"
    finally:
        adapter_registry._ADAPTERS.pop("DummyFutureModel", None)
