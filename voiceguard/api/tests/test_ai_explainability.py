from __future__ import annotations

from api.inference.confidence import ConfidenceResult
from api.inference.explainability import generate_explanation
from api.inference.feature_extraction import extract_features
from api.inference.inference import InferenceResult, run_inference
from api.inference.model_loader import LoadedModel


def _loaded_model():
    import torch

    from src.models.lcnn import LCNN

    return LoadedModel(model=LCNN().eval(), device=torch.device("cpu"), model_version_id=None)


def _feature():
    from src.data.dataset import MAX_SAMPLES
    import torch

    waveform = torch.randn(1, MAX_SAMPLES) * 0.1
    return extract_features(waveform, extractor_name="logmel", extractor_version="v1")


def test_generate_explanation_returns_salient_regions_and_notes():
    loaded_model = _loaded_model()
    feature = _feature()
    inference_result = run_inference(loaded_model, feature)
    confidence_result = ConfidenceResult(verdict="human", confidence=0.9, threshold_used=0.6, is_below_threshold=False)

    explanation = generate_explanation(
        loaded_model,
        feature,
        inference_result,
        confidence_result,
        silence_ratio=0.1,
        model_version_label="lcnn:v1",
    )

    assert len(explanation.notes) >= 1
    assert explanation.feature_extractor == "logmel:v1"
    assert explanation.model_version == "lcnn:v1"
    # Grad-CAM ran successfully against a real model — some salient regions
    # should come back (not asserting *which* ones: the model is untrained,
    # so specific saliency values are meaningless, only that the mechanism
    # produces well-formed output).
    for region in explanation.salient_regions:
        assert region.start_s <= region.end_s
        assert 0.0 <= region.importance <= 1.0 + 1e-6


def test_generate_explanation_notes_mention_uncertain_verdict_when_below_threshold():
    loaded_model = _loaded_model()
    feature = _feature()
    inference_result = run_inference(loaded_model, feature)
    confidence_result = ConfidenceResult(
        verdict="uncertain", confidence=0.55, threshold_used=0.6, is_below_threshold=True
    )

    explanation = generate_explanation(
        loaded_model, feature, inference_result, confidence_result, silence_ratio=0.0, model_version_label="lcnn:v1"
    )
    assert any("threshold" in note.lower() for note in explanation.notes)


def test_repeated_explanations_do_not_leak_gradcam_hooks_on_the_shared_model():
    """Regression test: src.explainability.gradcam.GradCAM originally
    registered forward/backward hooks in __init__ with no way to remove
    them. Harmless for its original one-instance-per-process callers
    (scripts/run_gradcam.py, app.py, demo/app.py), but api.inference.jobs
    creates a new GradCAM per scan against a *cached, long-lived* model —
    without cleanup, every explanation call would add one more forward and
    one more backward hook to the same layer forever. Confirms the fix
    (GradCAM.close()/__exit__, used as a context manager in
    api.inference.explainability._compute_salient_regions) actually keeps
    the hook count bounded across repeated calls."""
    loaded_model = _loaded_model()
    target_layer = loaded_model.model.features[9]

    baseline_forward = len(target_layer._forward_hooks)
    baseline_backward = len(target_layer._backward_hooks)

    for _ in range(5):
        feature = _feature()
        inference_result = run_inference(loaded_model, feature)
        confidence_result = ConfidenceResult(
            verdict="human", confidence=0.8, threshold_used=0.6, is_below_threshold=False
        )
        generate_explanation(
            loaded_model,
            feature,
            inference_result,
            confidence_result,
            silence_ratio=0.0,
            model_version_label="lcnn:v1",
        )

    assert len(target_layer._forward_hooks) == baseline_forward
    assert len(target_layer._backward_hooks) == baseline_backward


def test_generate_explanation_degrades_gracefully_on_gradcam_failure(monkeypatch):
    """A Grad-CAM failure must not raise out of generate_explanation — the
    verdict was already decided upstream and does not depend on this
    succeeding; it should degrade to an empty region list plus a warning."""
    import api.inference.explainability as explainability_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated Grad-CAM failure")

    monkeypatch.setattr(explainability_module, "_compute_salient_regions", _boom)

    loaded_model = _loaded_model()
    feature = _feature()
    inference_result = InferenceResult(label="bonafide", bonafide_score=0.8, spoof_score=0.2, inference_time_ms=5)
    confidence_result = ConfidenceResult(verdict="human", confidence=0.8, threshold_used=0.6, is_below_threshold=False)

    explanation = generate_explanation(
        loaded_model, feature, inference_result, confidence_result, silence_ratio=0.0, model_version_label="lcnn:v1"
    )
    assert explanation.salient_regions == []
    assert len(explanation.warnings) == 1
