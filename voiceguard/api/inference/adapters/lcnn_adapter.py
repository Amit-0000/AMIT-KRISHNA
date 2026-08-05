from __future__ import annotations

from pathlib import Path
from typing import Any

from api.inference import explainability as explainability_module
from api.inference import inference as inference_module
from api.inference.adapters.base import AdapterMetadata, ModelAdapter
from api.inference.adapters.registry import register_adapter


@register_adapter("LCNN")
class LCNNAdapter(ModelAdapter):
    """The original architecture VoiceGuard shipped with. Every method here
    delegates to the pre-existing, independently-tested modules
    (api.inference.inference, api.inference.explainability,
    src.inference.predict) rather than reimplementing anything — this
    adapter is a thin routing shim, not a rewrite, which is what guarantees
    LCNN's behavior is byte-for-byte unchanged by the adapter architecture's
    introduction. Delegation goes through the module objects
    (`inference_module.run_inference(...)`, not a bare imported name) so
    that tests monkeypatching `api.inference.jobs.inference.run_inference`
    keep working exactly as before — module objects are singletons, so that
    patch and this adapter's own `inference_module` reference are the same
    object."""

    architecture = "LCNN"

    def load_model(self, checkpoint_path: Path, device: Any) -> Any:
        from src.inference.predict import load_model as _load_lcnn

        return _load_lcnn(checkpoint_path, device)

    def feature_extractor(self) -> tuple[str, str]:
        return ("logmel", "v1")

    def predict(self, loaded_model: Any, feature: Any) -> Any:
        return inference_module.run_inference(loaded_model, feature)

    def convert_prediction(self, raw_prediction: Any) -> Any:
        # run_inference() already returns the canonical InferenceResult
        # shape (label is always 'bonafide'/'spoof' — LCNN's own native
        # vocabulary already matches VoiceGuard's canonical one, so there is
        # nothing to translate) — nothing to convert.
        return raw_prediction

    def supports_explainability(self) -> bool:
        return True

    def generate_explanation(
        self,
        loaded_model: Any,
        feature: Any,
        inference_result: Any,
        confidence_result: Any,
        *,
        silence_ratio: float,
        model_version_label: str,
    ) -> Any:
        return explainability_module.generate_explanation(
            loaded_model,
            feature,
            inference_result,
            confidence_result,
            silence_ratio=silence_ratio,
            model_version_label=model_version_label,
        )

    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            architecture="LCNN",
            checkpoint_filename="best.pt",
            feature_extractor_name="logmel",
            feature_extractor_version="v1",
            input_shape=(1, 128, 251),
            preprocessing_version="v1",
            supports_explainability=True,
            label_mapping={"bonafide": "bonafide", "spoof": "spoof"},
            default_threshold=0.60,
        )
