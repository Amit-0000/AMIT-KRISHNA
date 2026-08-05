from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.inference.adapters.base import AdapterMetadata, ModelAdapter
from api.inference.adapters.registry import register_adapter
from api.inference.exceptions import InferenceError
from api.inference.inference import InferenceResult

# AudioCNN's own label vocabulary (models/model_config.json in the source
# repository, index order 0=Genuine/1=Deepfake) -> VoiceGuard's canonical
# label strings. Applied inside convert_prediction() — see
# ModelAdapter.convert_prediction's docstring for why that's the one place
# this translation is allowed to happen.
_LABEL_MAPPING = {"Genuine": "bonafide", "Deepfake": "spoof"}


@dataclass(frozen=True)
class _SigmoidPrediction:
    """AudioCNN's raw predict() output — a single deepfake probability, not
    yet translated into VoiceGuard's canonical InferenceResult shape. Exists
    only to carry that probability + timing from predict() to
    convert_prediction(); nothing outside this adapter ever sees it."""

    deepfake_probability: float
    inference_time_ms: int


@register_adapter("AudioCNN")
class AudioCNNAdapter(ModelAdapter):
    """Adapter for Devil-92/Fake-Audio-Detector's AudioCNN — vendored at
    src.models.audio_cnn.AudioCNN. Unlike LCNNAdapter, this one can't just
    delegate to a pre-existing inference/explainability module, because none
    existed for this architecture before this adapter: the sigmoid forward
    pass and the Genuine/Deepfake label translation are new, but scoped
    entirely to this file — nothing in api.inference.jobs, confidence,
    result_writer, or the API had to change shape to accommodate them (see
    convert_prediction)."""

    architecture = "AudioCNN"

    def load_model(self, checkpoint_path: Path, device: Any) -> Any:
        import torch

        from src.models.audio_cnn import AudioCNN

        model = AudioCNN()
        # weights_only=True: this is new code with no existing call site to
        # stay bit-for-bit consistent with (unlike src.inference.predict.
        # load_model's own torch.load, which this deliberately does not
        # touch) — the checkpoint is a plain state_dict and loads cleanly
        # under the stricter, safer loader.
        state_dict = torch.load(checkpoint_path, map_location=device, weights_only=True)
        model.load_state_dict(state_dict)
        model.to(device).eval()
        return model

    def feature_extractor(self) -> tuple[str, str]:
        return ("logmel64db", "v1")

    def predict(self, loaded_model: Any, feature: Any) -> _SigmoidPrediction:
        import torch

        try:
            started = time.perf_counter()
            x = feature.tensor.unsqueeze(0).to(loaded_model.device)
            with torch.no_grad():
                logit = loaded_model.model(x)
                probability = float(torch.sigmoid(logit).item())
            elapsed_ms = int((time.perf_counter() - started) * 1000)
        except Exception as exc:  # noqa: BLE001 - any forward-pass failure (shape mismatch, OOM, backend error)
            raise InferenceError(f"AudioCNN forward pass failed: {exc}") from exc

        return _SigmoidPrediction(deepfake_probability=probability, inference_time_ms=elapsed_ms)

    def convert_prediction(self, raw_prediction: _SigmoidPrediction) -> InferenceResult:
        probability = raw_prediction.deepfake_probability
        native_label = "Deepfake" if probability >= 0.5 else "Genuine"
        return InferenceResult(
            label=_LABEL_MAPPING[native_label],
            bonafide_score=round(1.0 - probability, 6),
            spoof_score=round(probability, 6),
            inference_time_ms=raw_prediction.inference_time_ms,
        )

    # supports_explainability() and generate_explanation() intentionally not
    # overridden — ModelAdapter's defaults (False / "unavailable" result)
    # are exactly the Phase 8 requirement: no rushed Grad-CAM port, graceful
    # degradation, the scan never fails because of it.

    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            architecture="AudioCNN",
            checkpoint_filename="deepfake_cnn.pth",
            feature_extractor_name="logmel64db",
            feature_extractor_version="v1",
            input_shape=(1, 64, 251),
            preprocessing_version="v1",
            supports_explainability=False,
            label_mapping=dict(_LABEL_MAPPING),
            default_threshold=0.60,
        )
