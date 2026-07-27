import sys
import os

# Ensure repo root is on sys.path so `src/` is importable without pip install -e .
sys.path.insert(0, os.path.dirname(__file__))

import torch
import gradio as gr
from pathlib import Path
from huggingface_hub import hf_hub_download

from src.inference.predict import load_model, predict
from src.data.dataset import load_waveform
from src.data.transforms import MelSpectrogramTransform
from src.explainability.gradcam import GradCAM

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# TODO: Replace with your own HuggingFace model repo once you've uploaded the
# checkpoint. See NEXT_STEPS.md — Step 3 for exact commands.
_HF_REPO = "imsoumya18/audio-deepfake-detector"
CHECKPOINT = Path(hf_hub_download(repo_id=_HF_REPO, filename="lcnn_best.pt"))


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


device    = get_device()
model     = load_model(CHECKPOINT, device)
gradcam   = GradCAM(model, device)
transform = MelSpectrogramTransform(augment=False)


def run_inference(audio_path: str):
    if audio_path is None:
        return "No file uploaded", 0.0, None

    result     = predict(audio_path, model, device)
    label      = "Genuine — Real human speech" if result["label"] == "bonafide" else "Synthetic — AI-generated audio"
    confidence = result["confidence"]

    waveform = load_waveform(audio_path)
    mel      = transform(waveform).unsqueeze(0)
    cam      = gradcam.compute(mel, target_class=1)
    mel_np   = mel.squeeze().cpu().detach().numpy()

    # ── Apple Pro dark plot styling ───────────────────────────────────────────
    BG     = "#0A0A0A"
    MUTED  = "#86868B"
    BORDER = "#1F1F1F"

    plt.rcParams.update({
        "font.family":       "sans-serif",
        "font.sans-serif":   ["Inter", "SF Pro Text", "Helvetica Neue", "Arial"],
        "axes.unicode_minus": False,
    })

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.2))
    fig.patch.set_facecolor(BG)

    # Mel-spectrogram — greyscale
    axes[0].imshow(mel_np, origin="lower", aspect="auto", cmap="Greys_r")
    axes[0].set_title("Acoustic Fingerprint", fontsize=10, fontweight="500",
                      loc="left", color="#F5F5F7", pad=10)
    axes[0].set_xlabel("Time", fontsize=8, color=MUTED)
    axes[0].set_ylabel("Mel band", fontsize=8, color=MUTED)

    # Grad-CAM overlay — inferno on greyscale base
    axes[1].imshow(mel_np, origin="lower", aspect="auto", cmap="Greys_r", alpha=0.55)
    axes[1].imshow(cam,    origin="lower", aspect="auto", cmap="inferno", alpha=0.55)
    axes[1].set_title("Model Attention  ·  Grad-CAM", fontsize=10, fontweight="500",
                      loc="left", color="#F5F5F7", pad=10)
    axes[1].set_xlabel("Time", fontsize=8, color=MUTED)
    axes[1].set_ylabel("Mel band", fontsize=8, color=MUTED)

    for ax in axes:
        ax.set_facecolor(BG)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BORDER)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["left"].set_linewidth(0.5)
        ax.spines["bottom"].set_linewidth(0.5)
        ax.tick_params(colors=MUTED, labelsize=7)

    plt.tight_layout(pad=1.6)
    return label, round(confidence, 4), fig


# ── VoiceGuard — Apple Pro dark design system ─────────────────────────────────

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@600&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500&display=swap');

:root {
  --bg:           #0A0A0A;
  --surface:      #111111;
  --surface-2:    #161616;
  --border:       #1F1F1F;
  --border-hover: #2E2E2E;
  --text:         #F5F5F7;
  --muted:        #86868B;
  --success:      #30D158;
  --alert:        #FF453A;
  --radius-card:  10px;
  --radius-btn:   8px;
  --radius-input: 6px;
  --ease-out:     cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Shell ─────────────────────────────────────────────────────────────────── */
html, body {
  background: var(--bg) !important;
  color: var(--text) !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
}

.gradio-container, .main {
  background: var(--bg) !important;
  max-width: 720px !important;
  margin: 0 auto !important;
  padding: 48px 32px 80px !important;
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}

/* ── Hero header ────────────────────────────────────────────────────────────── */
.vg-title {
  font-family: 'Inter Tight', system-ui, -apple-system, sans-serif !important;
  font-size: 52px !important;
  font-weight: 600 !important;
  letter-spacing: -0.03em !important;
  color: var(--text) !important;
  line-height: 1.04 !important;
  margin: 0 0 12px !important;
}

.vg-tagline {
  font-family: 'Inter', system-ui, sans-serif !important;
  font-size: 18px !important;
  font-weight: 400 !important;
  letter-spacing: -0.01em !important;
  color: var(--muted) !important;
  line-height: 1.5 !important;
  margin: 0 0 48px !important;
}

/* ── Panels / cards ─────────────────────────────────────────────────────────── */
.gap, .block, .gr-form, .gr-panel {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-card) !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06) !important;
}

/* ── Labels ─────────────────────────────────────────────────────────────────── */
.label-wrap > span, label > span, .gr-label span {
  font-family: 'Inter', sans-serif !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.07em !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}

/* ── Audio upload zone ──────────────────────────────────────────────────────── */
.gr-audio, [data-testid="audio"] {
  background: var(--surface-2) !important;
  border: 1px dashed var(--border-hover) !important;
  border-radius: var(--radius-input) !important;
  transition: border-color var(--ease-out) 300ms !important;
}

.gr-audio:hover, [data-testid="audio"]:hover {
  border-color: #3A3A3A !important;
}

/* ── Text / number outputs ──────────────────────────────────────────────────── */
.gr-textbox textarea, .gr-textbox input,
textarea, .svelte-1f354aw {
  font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  color: var(--text) !important;
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-input) !important;
  letter-spacing: -0.01em !important;
}

input[type="number"] {
  font-family: 'JetBrains Mono', 'SF Mono', monospace !important;
  font-size: 20px !important;
  font-weight: 500 !important;
  color: var(--text) !important;
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-input) !important;
}

/* ── Primary button ─────────────────────────────────────────────────────────── */
button.primary, .gr-button-primary, button[data-testid*="primary"] {
  background: var(--text) !important;
  color: var(--bg) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  border: none !important;
  border-radius: var(--radius-btn) !important;
  padding: 12px 28px !important;
  cursor: pointer !important;
  transition: opacity var(--ease-out) 400ms,
              transform 100ms ease !important;
}

button.primary:hover, .gr-button-primary:hover {
  opacity: 0.80 !important;
  transform: translateY(-1px) !important;
}

button.primary:active, .gr-button-primary:active {
  transform: scale(0.98) !important;
  opacity: 1 !important;
}

/* ── Secondary / clear buttons ──────────────────────────────────────────────── */
button.secondary, .gr-button-secondary {
  background: transparent !important;
  color: var(--muted) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-btn) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  transition: color var(--ease-out) 400ms,
              border-color var(--ease-out) 400ms !important;
}

button.secondary:hover, .gr-button-secondary:hover {
  color: var(--text) !important;
  border-color: var(--border-hover) !important;
}

/* ── Plot box ───────────────────────────────────────────────────────────────── */
.gr-plot, .plot-container, [data-testid="plot"] {
  background: var(--bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-card) !important;
}

/* ── Output reveal stagger ──────────────────────────────────────────────────── */
.gr-textbox {
  animation: vg-reveal 600ms var(--ease-out) both;
}
.gr-number {
  animation: vg-reveal 600ms var(--ease-out) 80ms both;
}
.gr-plot {
  animation: vg-reveal 600ms var(--ease-out) 160ms both;
}

@keyframes vg-reveal {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0);   }
}

/* ── Dividers ───────────────────────────────────────────────────────────────── */
hr, .gr-divider {
  border-color: var(--border) !important;
  margin: 32px 0 !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ── Hide Gradio footer ─────────────────────────────────────────────────────── */
footer, .footer, .built-with, #footer {
  display: none !important;
}
"""

_HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
"""

# ── Layout ────────────────────────────────────────────────────────────────────

with gr.Blocks(css=_CSS, head=_HEAD, title="VoiceGuard") as demo:

    gr.HTML("""
        <h1 class="vg-title">VoiceGuard</h1>
        <p class="vg-tagline">Detect AI-generated speech in seconds.</p>
    """)

    with gr.Row():
        audio_in = gr.Audio(
            type="filepath",
            label="Audio File",
        )

    with gr.Row():
        run_btn = gr.Button("Analyze", variant="primary")

    with gr.Row():
        with gr.Column(scale=2):
            result_box = gr.Textbox(label="Verdict", interactive=False)
        with gr.Column(scale=1):
            confidence_n = gr.Number(label="Confidence", interactive=False)

    plot_out = gr.Plot(label="Spectrogram  ·  Model Attention")

    run_btn.click(
        fn=run_inference,
        inputs=audio_in,
        outputs=[result_box, confidence_n, plot_out],
    )

if __name__ == "__main__":
    demo.launch()
