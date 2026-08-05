import torch

# Both transforms are procedurally generated (no external noise/RIR corpus
# needed — none is present in data/) and operate on the raw waveform, after
# serving_equivalent_preprocess and before the mel transform. Train-only:
# never applied to dev/eval, so the inference pipeline is untouched.


def add_gaussian_noise(waveform: torch.Tensor, snr_db_range: tuple[float, float] = (5.0, 20.0)) -> torch.Tensor:
    """Additive white Gaussian noise at a randomly drawn SNR (dB) per call.
    Approximates varying recording-environment noise floors without needing
    a real noise corpus (e.g. MUSAN)."""
    signal_power = waveform.pow(2).mean()
    if signal_power <= 0:
        return waveform
    snr_db = torch.empty(1).uniform_(*snr_db_range).item()
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = torch.randn_like(waveform) * noise_power.sqrt()
    return waveform + noise


def apply_random_channel_response(waveform: torch.Tensor, filter_len_range: tuple[int, int] = (3, 7)) -> torch.Tensor:
    """Convolves the waveform with a short random FIR filter to simulate
    microphone/channel/codec frequency-response variation — a simplified,
    self-contained analogue of RawBoost's linear convolutive-noise component
    (Tak et al. 2021), procedurally generated rather than drawn from a
    device/impulse-response corpus. The first tap is biased so the direct
    path still dominates (this perturbs timbre, it isn't meant to destroy
    the signal), and the output is rescaled to the input's peak amplitude so
    it stays consistent with the peak-normalization serving_equivalent_preprocess
    already applied upstream."""
    filter_len = int(torch.randint(filter_len_range[0], filter_len_range[1] + 1, (1,)).item())
    coeffs = torch.randn(filter_len)
    coeffs[0] += 2.0
    coeffs = coeffs / coeffs.abs().sum()

    x = waveform.unsqueeze(0)  # [1, 1, T]
    padded = torch.nn.functional.pad(x, (filter_len - 1, 0))
    out = torch.nn.functional.conv1d(padded, coeffs.view(1, 1, -1)).squeeze(0)

    orig_peak = waveform.abs().max().clamp(min=1e-8)
    new_peak = out.abs().max().clamp(min=1e-8)
    return out * (orig_peak / new_peak)


class WaveformAugmentation:
    """Composable train-time waveform augmentation for the ablation in
    scripts/compare_augmentation.py. Each flag is independent so the 4
    variants (baseline / noise / channel / noise+channel) change exactly
    one thing relative to each other."""

    def __init__(self, use_noise: bool = False, use_channel: bool = False):
        self.use_noise = use_noise
        self.use_channel = use_channel

    def __call__(self, waveform: torch.Tensor) -> torch.Tensor:
        if self.use_noise:
            waveform = add_gaussian_noise(waveform)
        if self.use_channel:
            waveform = apply_random_channel_response(waveform)
        return waveform
