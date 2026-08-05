from __future__ import annotations

import hashlib
import io
import struct
import uuid
import wave

import pytest

from api.core.storage import LocalStorageBackend
from api.inference.exceptions import AudioDecodeError, AudioIntegrityError, AudioTooShortError
from api.inference.preprocessing import (
    detect_and_trim_silence,
    normalize_amplitude,
    retrieve_audio_tempfile,
    run_preprocessing,
    validate_duration,
    verify_integrity,
)
from api.scans.models import Scan


def _wav_bytes(seconds: float = 1.0, rate: int = 16000, tone: int = 1000, amplitude: int = 8000) -> bytes:
    n_frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([amplitude] * n_frames)))
    return buf.getvalue()


def _silent_wav_bytes(seconds: float = 1.0, rate: int = 16000) -> bytes:
    n_frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))
    return buf.getvalue()


def _make_scan(*, storage_key: str, file_extension: str, checksum: str) -> Scan:
    return Scan(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        original_filename="test.wav",
        storage_key=storage_key,
        file_extension=file_extension,
        sha256_checksum=checksum,
    )


# ── Retrieve Stored Audio ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_audio_tempfile_round_trips_bytes(tmp_path):
    storage = LocalStorageBackend(tmp_path)
    data = _wav_bytes()

    async def _chunks():
        yield data

    await storage.save_stream("a.wav", _chunks())
    scan = _make_scan(storage_key="a.wav", file_extension=".wav", checksum=hashlib.sha256(data).hexdigest())

    with retrieve_audio_tempfile(scan, storage) as path:
        assert path.exists()
        assert path.read_bytes() == data
    assert not path.exists()  # cleaned up after the context manager exits


# ── Integrity Validation ─────────────────────────────────────────────────────


def test_verify_integrity_passes_on_matching_checksum(tmp_path):
    data = _wav_bytes()
    path = tmp_path / "clip.wav"
    path.write_bytes(data)
    scan = _make_scan(storage_key="x", file_extension=".wav", checksum=hashlib.sha256(data).hexdigest())
    verify_integrity(scan, path)  # must not raise


def test_verify_integrity_rejects_mismatched_checksum(tmp_path):
    data = _wav_bytes()
    path = tmp_path / "clip.wav"
    path.write_bytes(data)
    scan = _make_scan(storage_key="x", file_extension=".wav", checksum="0" * 64)
    with pytest.raises(AudioIntegrityError):
        verify_integrity(scan, path)


# ── Amplitude Normalization ─────────────────────────────────────────────────


def test_normalize_amplitude_scales_to_unit_peak():
    import torch

    waveform = torch.tensor([[0.1, -0.4, 0.2]])
    normalized = normalize_amplitude(waveform)
    assert float(normalized.abs().max()) == pytest.approx(1.0)


def test_normalize_amplitude_leaves_silent_waveform_untouched():
    import torch

    waveform = torch.zeros(1, 100)
    normalized = normalize_amplitude(waveform)
    assert float(normalized.abs().max()) == 0.0


# ── Silence Detection / Trimming ─────────────────────────────────────────────


def test_detect_and_trim_silence_trims_leading_and_trailing_silence():
    import torch

    rate = 16000
    silence = torch.zeros(1, rate // 2)  # 0.5s silence
    voiced = torch.full((1, rate), 0.5)  # 1.0s loud tone
    waveform = torch.cat([silence, voiced, silence], dim=1)

    trimmed, stats = detect_and_trim_silence(waveform, sample_rate=rate)

    assert trimmed.shape[-1] < waveform.shape[-1]
    assert stats.trimmed_leading_samples > 0
    assert stats.trimmed_trailing_samples > 0
    # Trimmed region should be close to the 1.0s voiced segment.
    assert trimmed.shape[-1] == pytest.approx(rate, rel=0.1)


def test_detect_and_trim_silence_collapses_pure_silence_to_empty():
    """Regression test: entirely-silent audio must collapse to zero length so
    validate_duration actually rejects it — an earlier version of this
    function returned the full-length untouched waveform for pure silence,
    which made a 2-second silent clip look like valid, sufficiently-long
    audio to the duration check that runs right after it."""
    import torch

    rate = 16000
    waveform = torch.zeros(1, rate)
    trimmed, stats = detect_and_trim_silence(waveform, sample_rate=rate)
    assert stats.silence_ratio == 1.0
    assert trimmed.shape[-1] == 0


# ── Duration Validation ──────────────────────────────────────────────────────


def test_validate_duration_rejects_too_short_audio():
    import torch

    waveform = torch.zeros(1, 10)  # far under AI_MIN_AUDIO_DURATION_S at 16kHz
    with pytest.raises(AudioTooShortError):
        validate_duration(waveform, sample_rate=16000)


def test_validate_duration_accepts_sufficient_audio():
    import torch

    waveform = torch.zeros(1, 16000)  # 1s at 16kHz
    duration = validate_duration(waveform, sample_rate=16000)
    assert duration == pytest.approx(1.0)


# ── Decode failure ────────────────────────────────────────────────────────────


def test_decode_and_normalize_rate_raises_on_garbage_bytes(tmp_path):
    from api.inference.preprocessing import decode_and_normalize_rate

    path = tmp_path / "not-audio.wav"
    path.write_bytes(b"this is not a wav file at all, just garbage bytes")
    with pytest.raises(AudioDecodeError):
        decode_and_normalize_rate(path)


# ── Full orchestration ───────────────────────────────────────────────────────


def test_run_preprocessing_end_to_end_returns_fixed_length_waveform(tmp_path):
    from src.data.dataset import MAX_SAMPLES

    storage = LocalStorageBackend(tmp_path)
    data = _wav_bytes(seconds=2.0)
    (tmp_path / "clip.wav").write_bytes(data)  # LocalStorageBackend keys are relative to its own root

    import asyncio

    async def _save():
        async def _chunks():
            yield data

        await storage.save_stream("clip.wav", _chunks())

    asyncio.run(_save())

    scan = _make_scan(storage_key="clip.wav", file_extension=".wav", checksum=hashlib.sha256(data).hexdigest())
    result = run_preprocessing(scan, storage)

    assert result.waveform.shape[-1] == MAX_SAMPLES  # model's fixed-input contract, restored after trimming
    assert result.sample_rate == 16000
    assert result.duration_seconds > 0


def test_run_preprocessing_rejects_entirely_silent_clip(tmp_path):
    storage = LocalStorageBackend(tmp_path)
    data = _silent_wav_bytes(seconds=2.0)

    import asyncio

    async def _save():
        async def _chunks():
            yield data

        await storage.save_stream("silent.wav", _chunks())

    asyncio.run(_save())

    scan = _make_scan(storage_key="silent.wav", file_extension=".wav", checksum=hashlib.sha256(data).hexdigest())
    with pytest.raises(AudioTooShortError):
        run_preprocessing(scan, storage)
