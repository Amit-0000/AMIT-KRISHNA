from __future__ import annotations

import time
from dataclasses import dataclass

from api.inference.exceptions import InferenceError
from api.inference.feature_extraction import ExtractedFeature
from api.inference.model_loader import LoadedModel

LABEL_NAMES = {0: "bonafide", 1: "spoof"}


@dataclass(frozen=True)
class InferenceResult:
    label: str
    bonafide_score: float
    spoof_score: float
    inference_time_ms: int


def run_inference(loaded_model: LoadedModel, feature: ExtractedFeature) -> InferenceResult:
    """The model forward pass. Deliberately reimplements the tensor glue
    from src.inference.predict.predict() rather than calling it directly:
    predict() re-does waveform loading *and* feature extraction from a file
    path in one monolithic call, which is exactly the "giant processing
    function" this pipeline decomposes into independently-replaceable
    stages (api.inference.preprocessing / feature_extraction already did
    that work). What's reused here instead is predict()'s label convention
    (LABEL_NAMES) and the model class it loads (src.models.lcnn.LCNN via
    api.inference.model_loader, itself built on src.inference.predict.load_model).
    Synchronous by design — see api.inference.preprocessing.run_preprocessing;
    api.inference.jobs wraps this in asyncio.to_thread."""
    import torch

    try:
        started = time.perf_counter()
        mel = feature.tensor.unsqueeze(0).to(loaded_model.device)
        with torch.no_grad():
            logits = loaded_model.model(mel)
            probs = torch.softmax(logits, dim=1)[0]
        elapsed_ms = int((time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001 - any forward-pass failure (shape mismatch, OOM, backend error)
        raise InferenceError(f"Model forward pass failed: {exc}") from exc

    bonafide_score = float(probs[0].item())
    spoof_score = float(probs[1].item())
    label = LABEL_NAMES[int(probs.argmax().item())]

    return InferenceResult(
        label=label,
        bonafide_score=round(bonafide_score, 6),
        spoof_score=round(spoof_score, 6),
        inference_time_ms=elapsed_ms,
    )
