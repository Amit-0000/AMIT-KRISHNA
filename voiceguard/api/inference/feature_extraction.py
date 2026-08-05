from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from api.inference.exceptions import FeatureExtractionError, FeatureValidationError


@dataclass(frozen=True)
class ExtractedFeature:
    name: str
    version: str
    tensor: object  # torch.Tensor — kept loosely typed so callers don't need torch to hold a reference
    shape: list[int]
    dtype: str


# ── Pluggable extractor registry ────────────────────────────────────────────
# Adding MFCC / raw spectral / temporal / embedding extractors later means
# writing one function and calling register_extractor on it — nothing here
# or in api.inference.jobs needs to change. Only "logmel" is implemented in
# this slice; the others named in the design doc are documented extension
# points, not speculative code with no caller.

_ExtractorFn = Callable[[object], ExtractedFeature]
_EXTRACTORS: dict[tuple[str, str], _ExtractorFn] = {}


def register_extractor(name: str, version: str) -> Callable[[_ExtractorFn], _ExtractorFn]:
    def decorator(fn: _ExtractorFn) -> _ExtractorFn:
        _EXTRACTORS[(name, version)] = fn
        return fn

    return decorator


def available_extractors() -> list[tuple[str, str]]:
    return sorted(_EXTRACTORS.keys())


@register_extractor("logmel", "v1")
def _logmel_v1(waveform) -> ExtractedFeature:
    """Log-mel spectrogram — the exact transform src.models.lcnn.LCNN was
    trained against (src.data.transforms.MelSpectrogramTransform), reused
    rather than reimplemented so training and inference can never drift."""
    from src.data.transforms import MelSpectrogramTransform

    transform = MelSpectrogramTransform(augment=False)
    mel = transform(waveform)
    return ExtractedFeature(name="logmel", version="v1", tensor=mel, shape=list(mel.shape), dtype=str(mel.dtype))


# Devil-92/Fake-Audio-Detector's own AudioConfig defaults
# (models/model_config.json in that repository) — src.models.audio_cnn's
# checkpoint was trained against exactly these parameters. Kept as named
# constants (mirroring src/data/transforms.py's own top-level constants for
# the LCNN extractor above) rather than reading from VoiceGuard's Settings,
# since this extractor's whole purpose is to reproduce one specific
# upstream training pipeline precisely, not to be independently reconfigured.
_LOGMEL64DB_SAMPLE_RATE = 16_000
_LOGMEL64DB_N_FFT = 1024
_LOGMEL64DB_HOP_LENGTH = 256
_LOGMEL64DB_N_MELS = 64
_LOGMEL64DB_FMIN = 20
_LOGMEL64DB_FMAX = 7_600


@register_extractor("logmel64db", "v1")
def _logmel64db_v1(waveform) -> ExtractedFeature:
    """Log-mel spectrogram in dB, per-clip z-score normalized — the exact
    transform Devil-92/Fake-Audio-Detector's AudioCNN was trained against
    (src/audio_detection/features.py: log_mel_spectrogram in that
    repository). Computed with librosa rather than torchaudio because
    reproducing librosa's mel filterbank and power_to_db conversion
    numerically exactly via torchaudio isn't guaranteed — using the same
    library the checkpoint was trained with is what makes "exactly match
    the detector" actually true rather than approximately true (see the
    AudioCNN compatibility audit's feature-extraction findings)."""
    import librosa
    import numpy as np
    import torch

    y = waveform.squeeze(0).detach().cpu().numpy().astype(np.float32)
    mel = librosa.feature.melspectrogram(
        y=y,
        sr=_LOGMEL64DB_SAMPLE_RATE,
        n_fft=_LOGMEL64DB_N_FFT,
        hop_length=_LOGMEL64DB_HOP_LENGTH,
        n_mels=_LOGMEL64DB_N_MELS,
        fmin=_LOGMEL64DB_FMIN,
        fmax=_LOGMEL64DB_FMAX,
        power=2.0,
    )
    db = librosa.power_to_db(mel, ref=np.max)
    db = (db - db.mean()) / (db.std() + 1e-6)

    tensor = torch.from_numpy(db.astype(np.float32)).unsqueeze(0)  # [1, 64, T] — same channel-first convention as logmel:v1
    return ExtractedFeature(
        name="logmel64db", version="v1", tensor=tensor, shape=list(tensor.shape), dtype=str(tensor.dtype)
    )


# ── Feature Validation ───────────────────────────────────────────────────────


def validate_feature(feature: ExtractedFeature) -> None:
    import torch

    if feature.tensor.numel() == 0:
        raise FeatureValidationError(f"{feature.name}:{feature.version} produced an empty tensor")
    if not torch.isfinite(feature.tensor).all():
        raise FeatureValidationError(f"{feature.name}:{feature.version} tensor contains NaN/Inf")


def summarize(feature: ExtractedFeature) -> dict[str, float]:
    """Cheap aggregate stats persisted in feature_vectors.summary_stats even
    when the full array isn't (FEATURE_VECTOR_STORAGE_ENABLED=False) —
    enough to sanity-check a scan's features without re-running extraction."""
    tensor = feature.tensor
    return {
        "mean": round(float(tensor.mean()), 6),
        "std": round(float(tensor.std()), 6),
        "min": round(float(tensor.min()), 6),
        "max": round(float(tensor.max()), 6),
    }


# ── Orchestration ────────────────────────────────────────────────────────────


def extract_features(waveform, *, extractor_name: str, extractor_version: str) -> ExtractedFeature:
    """Synchronous by design — see api.inference.preprocessing.run_preprocessing
    for why (api.inference.jobs wraps this in asyncio.to_thread)."""
    fn = _EXTRACTORS.get((extractor_name, extractor_version))
    if fn is None:
        raise FeatureExtractionError(f"No registered feature extractor for {extractor_name}:{extractor_version}")
    try:
        feature = fn(waveform)
    except FeatureExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001 - any extractor-internal failure
        raise FeatureExtractionError(f"{extractor_name}:{extractor_version} failed: {exc}") from exc

    validate_feature(feature)
    return feature
