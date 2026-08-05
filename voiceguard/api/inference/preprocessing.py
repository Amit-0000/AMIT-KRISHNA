from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from api.core.config import get_settings
from api.core.storage import StorageBackend
from api.inference.exceptions import (
    AudioDecodeError,
    AudioIntegrityError,
    AudioRetrievalError,
    AudioTooShortError,
)
from api.scans.models import Scan

# ── Retrieve Stored Audio ───────────────────────────────────────────────────
# Goes through StorageBackend.open_read rather than LocalStorageBackend's
# resolve_path() escape hatch (see api.core.storage) — everything downstream
# in this pipeline (torchaudio/soundfile) needs a real filesystem path, so we
# copy into a temp file once here. That keeps this module storage-backend
# agnostic: a future S3/Blob backend still works, it just makes open_read()
# do a network fetch instead of a local open.


@contextmanager
def retrieve_audio_tempfile(scan: Scan, storage: StorageBackend) -> Iterator[Path]:
    """Copies the scan's stored audio into a temp file for the duration of
    the `with` block, then deletes it — same delete=False + explicit unlink
    pattern api.main's /predict endpoint already uses for the same reason
    (Safe Temporary Files / Resource Cleanup)."""
    tmp_path: Path | None = None
    try:
        try:
            with storage.open_read(scan.storage_key) as src:
                data = src.read()
        except OSError as exc:
            raise AudioRetrievalError(f"Could not read stored audio for scan {scan.id}: {exc}") from exc

        with tempfile.NamedTemporaryFile(suffix=scan.file_extension, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        yield tmp_path
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


# ── Integrity Validation ────────────────────────────────────────────────────


def verify_integrity(scan: Scan, audio_path: Path) -> None:
    """Recomputes sha256 over the retrieved bytes and compares against
    Scan.sha256_checksum (recorded at upload time by api.scans.service). A
    mismatch means the stored file was corrupted or tampered with between
    upload and AI processing — never worth retrying as-is."""
    digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    if digest != scan.sha256_checksum:
        raise AudioIntegrityError(
            f"Stored audio checksum mismatch for scan {scan.id}: expected {scan.sha256_checksum}, got {digest}"
        )


# ── Decode / Sample-rate Conversion / Mono Conversion ───────────────────────
# Delegates to src.data.dataset.load_waveform, the same primitive the
# existing training pipeline and the legacy /predict endpoint both use — it
# already does decode (soundfile, pydub/ffmpeg fallback) -> mono-downmix ->
# resample to 16kHz -> fixed-length pad/truncate. Reused, not reimplemented.


def decode_and_normalize_rate(audio_path: Path):
    import torch  # local import — see api.main._get_device for why

    from src.data.dataset import load_waveform

    try:
        waveform = load_waveform(audio_path)
    except Exception as exc:  # noqa: BLE001 - any decode failure (bad codec, corrupt container, unreadable)
        raise AudioDecodeError(f"Could not decode audio for {audio_path.name}: {exc}") from exc

    if not torch.isfinite(waveform).all():
        raise AudioDecodeError("Decoded waveform contains non-finite samples (NaN/Inf)")
    return waveform


# ── Amplitude Normalization ─────────────────────────────────────────────────


def normalize_amplitude(waveform):
    """Peak-normalizes to [-1, 1]. soundfile already returns roughly-scaled
    float32 PCM, but doesn't guarantee the clip actually uses the full
    range — peak normalization gives the model a consistent input scale
    regardless of how quietly the source was recorded."""
    peak = waveform.abs().max()
    if float(peak) == 0.0:
        return waveform  # silent clip — nothing to normalize, silence detection handles this next
    return waveform / peak


# ── Silence Detection / Trimming ────────────────────────────────────────────


@dataclass(frozen=True)
class SilenceStats:
    silence_ratio: float
    trimmed_leading_samples: int
    trimmed_trailing_samples: int


def detect_and_trim_silence(waveform, *, sample_rate: int, frame_ms: int = 20):
    """RMS-per-frame silence detection: any frame whose RMS falls below
    AI_SILENCE_RMS_THRESHOLD is treated as silence. Trims leading/trailing
    silence only (interior silence is left alone — it's part of the signal,
    e.g. natural pauses in speech) and reports the overall silence ratio for
    the explanation stage's warnings."""
    import torch

    threshold = get_settings().AI_SILENCE_RMS_THRESHOLD
    frame_len = max(1, int(sample_rate * frame_ms / 1000))
    samples = waveform.shape[-1]

    frames = samples // frame_len
    if frames == 0:
        return waveform, SilenceStats(silence_ratio=1.0, trimmed_leading_samples=0, trimmed_trailing_samples=0)

    reshaped = waveform[0, : frames * frame_len].reshape(frames, frame_len)
    frame_rms = reshaped.pow(2).mean(dim=1).sqrt()
    is_voiced = frame_rms >= threshold
    silence_ratio = 1.0 - (is_voiced.sum().item() / frames)

    voiced_frames = torch.nonzero(is_voiced, as_tuple=True)[0]
    if voiced_frames.numel() == 0:
        # Entirely silent — collapse to a zero-length waveform so
        # validate_duration (called right after) actually rejects it.
        # Returning the untouched full-length waveform here would report a
        # normal-looking duration for audio that is 100% silence.
        empty = waveform[:, :0]
        return empty, SilenceStats(silence_ratio=1.0, trimmed_leading_samples=0, trimmed_trailing_samples=samples)

    first_voiced = int(voiced_frames[0]) * frame_len
    last_voiced = (int(voiced_frames[-1]) + 1) * frame_len
    trimmed = waveform[:, first_voiced:last_voiced]

    stats = SilenceStats(
        silence_ratio=round(silence_ratio, 4),
        trimmed_leading_samples=first_voiced,
        trimmed_trailing_samples=samples - last_voiced,
    )
    return trimmed, stats


# ── Duration Validation ─────────────────────────────────────────────────────


def validate_duration(waveform, *, sample_rate: int) -> float:
    duration_s = waveform.shape[-1] / float(sample_rate)
    if duration_s < get_settings().AI_MIN_AUDIO_DURATION_S:
        raise AudioTooShortError(
            f"Audio too short after silence trimming: {duration_s:.3f}s "
            f"(minimum {get_settings().AI_MIN_AUDIO_DURATION_S}s)"
        )
    return duration_s


# ── Orchestration ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PreprocessResult:
    waveform: object  # torch.Tensor — typed loosely so this module never needs torch at import time
    sample_rate: int
    duration_seconds: float
    silence: SilenceStats


def _fix_length(waveform, *, target_samples: int):
    """Restores the model's required fixed input length after silence
    trimming may have shortened it. Mirrors src.data.dataset.load_waveform's
    own pad-with-zeros-or-truncate behavior (not reused directly — that logic
    lives inline in load_waveform, not exposed as a callable) because
    src.models.lcnn.LCNN's classifier head hardcodes the flattened feature
    size for a specific frame count; feeding it a variable-length waveform
    after trimming would break the very first Linear layer, not fail
    gracefully. Detection still runs on genuinely-trimmed audio — this only
    restores the *shape* the model contract requires, on the already-trimmed
    signal."""
    import torch

    length = waveform.shape[-1]
    if length < target_samples:
        return torch.nn.functional.pad(waveform, (0, target_samples - length))
    return waveform[:, :target_samples]


def run_preprocessing(scan: Scan, storage: StorageBackend) -> PreprocessResult:
    """Thin sequencer over the independently-testable steps above — every
    step can be called and verified on its own; this just chains them in the
    documented order (Integrity Validation -> Retrieve -> Decode -> Normalize
    -> Silence Detection/Trim -> Duration Validation -> re-fix length).
    Synchronous by design: api.inference.jobs runs this inside
    asyncio.to_thread so the event loop isn't blocked by torchaudio/
    soundfile's blocking I/O and CPU work."""
    from src.data.dataset import MAX_SAMPLES, SAMPLE_RATE

    with retrieve_audio_tempfile(scan, storage) as audio_path:
        verify_integrity(scan, audio_path)
        waveform = decode_and_normalize_rate(audio_path)

    waveform = normalize_amplitude(waveform)
    trimmed, silence = detect_and_trim_silence(waveform, sample_rate=SAMPLE_RATE)
    duration_s = validate_duration(trimmed, sample_rate=SAMPLE_RATE)
    fixed = _fix_length(trimmed, target_samples=MAX_SAMPLES)

    return PreprocessResult(waveform=fixed, sample_rate=SAMPLE_RATE, duration_seconds=duration_s, silence=silence)
