import torch
from torch import nn


class AudioCNN(nn.Module):
    """Compact 2D CNN for genuine/deepfake audio classification, operating on
    a single-channel log-mel spectrogram. Vendored from
    Devil-92/Fake-Audio-Detector (src/audio_detection/model.py) — architecture
    definition only, byte-for-byte identical so its published checkpoint
    (deepfake_cnn.pth) loads without modification. See
    api.inference.adapters.audio_cnn_adapter for how VoiceGuard drives this
    model; training/evaluation/Streamlit/kagglehub code from the source
    repository is deliberately not included here — VoiceGuard only performs
    inference against an already-trained checkpoint.

    Input:  [B, 1, 64, T]  (64-mel-band log spectrogram; T is not fixed —
            AdaptiveAvgPool2d makes the classifier head shape-independent of
            time-frame count, unlike src.models.lcnn.LCNN's fixed Linear
            input)
    Output: [B]  (a single logit per example; sigmoid at inference time)
    """

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x).squeeze(1)
