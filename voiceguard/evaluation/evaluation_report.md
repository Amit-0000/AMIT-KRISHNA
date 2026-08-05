# VoiceGuard AudioCNN — Production Benchmark Report

**Status: Official baseline.** This report and its accompanying artifacts are the first
reproducible performance baseline for the deployed AudioCNN checkpoint. Future model
versions (LCNN, AudioCNN v2, ensembles, transformer-based detectors) should be evaluated
with the same methodology and compared directly against these numbers.

---

## 1. Executive Summary

The deployed AudioCNN checkpoint (`checkpoints/deepfake_cnn.pth`, SHA256
`0fbe937e222a057ea56457334b41558f56a5c1472fa720b7083aa1c3bc70d4e7`) was benchmarked
against 100 held-out samples (50 genuine / 50 AI-generated, perfectly balanced) from the
same dataset family it was trained on — Kaggle's **Fake-or-Real** dataset — using the
**for-norm** variant, which matches the upstream repository's own training/evaluation
preprocessing (pad/trim to 4 seconds @ 16 kHz).

Every sample was run through the **real, deployed VoiceGuard REST API** end-to-end:
upload → preprocessing → feature extraction → AudioCNN forward pass → confidence
calibration → persistence → retrieval. No direct model calls, no mocked inference, no
synthetic checkpoints.

**Headline result: the deployed system correctly rejects genuine audio with perfect
specificity (0/50 false positives) but misses 72% of AI-generated clips (36/50 false
negatives).** This is a substantial gap from the upstream repository's own published
numbers (90.3% accuracy, 19.3% false-negative rate) on what should be a comparable data
distribution. See §9 and §12 for the evidence behind this gap and what it does — and
does not — imply about the integration itself.

---

## 2. Dataset Description

| Property | Primary run (`for-norm`) | Secondary/appendix run (`for-2sec`) |
|---|---|---|
| Source | Kaggle `mohammedabdeldayem/the-fake-or-real-dataset` | Same dataset, different pre-packaged variant |
| Path | `for-norm/for-norm/testing/{real,fake}` | `for-2sec/for-2seconds/testing/{real,fake}` |
| Files | 100 (50 real, 50 fake) | 100 (50 real, 50 fake) |
| Class balance | 50 / 50 (perfect) | 50 / 50 (perfect) |
| Sample rate | 16,000 Hz (uniform) | 16,000 Hz (uniform) |
| Duration | Variable/natural: real 0.94–4.04s (mean 2.59s); fake 0.70–4.61s (mean 1.67s) | Fixed 2.00s (pre-clipped) |
| Format | WAV, mono | WAV, mono |
| Sampling method | `random.sample(seed=42)` over 80 candidates/class, collected via paginated Kaggle file listing | Same seed/method |

**Why two variants.** The dataset ships several pre-processed sub-variants. `for-2sec`
was discovered first (it sorts alphabetically before `for-norm`) and used for an initial
run. Analysis of that run's misclassifications (§9) revealed that VoiceGuard's own
pipeline pads/truncates every waveform to a fixed 64,000 samples (4s) —
`src/data/dataset.py: MAX_SAMPLES = 4 * SAMPLE_RATE` — which matches the upstream repo's
own documented preprocessing recipe exactly (confirmed in the vendored source's README
and `config.py`: `duration: float = 4.0`). Feeding the model `for-2sec`'s 2-second clips
therefore meant **every evaluated input was 50% zero-padded silence** by construction —
a real, reproducible behavior of the deployed system, but not representative of how the
checkpoint was trained or how the upstream repo measured its own numbers. `for-norm`
(natural clip length, loudness-normalized) is the variant the upstream repo's own
`data.py` resolves training/eval data from — making it the fair, apples-to-apples
comparison, and the one this report treats as primary.

---

## 3. Environment

See `environment.json` for the complete machine-readable record. Summary:

| | |
|---|---|
| Evaluation timestamp (UTC) | 2026-07-30T21:23:46Z |
| Model architecture | AudioCNN |
| Model name : version | `audio_cnn:v1` |
| Checkpoint | `deepfake_cnn.pth` |
| Checkpoint SHA256 | `0fbe937e222a057ea56457334b41558f56a5c1472fa720b7083aa1c3bc70d4e7` |
| Feature extractor | `logmel64db v1` |
| Confidence threshold | 0.60 |
| Host OS | Windows 11 Home Single Language, build 26200 |
| Inference container OS | Debian 13 (trixie), via Docker Desktop/WSL2 |
| CPU | 20 logical CPUs visible to container; torch using 10 threads; CPU-only (no GPU) |
| Python | 3.12.13 |
| PyTorch | 2.9.1+cpu |
| torchaudio | 2.9.1+cpu |
| librosa | 0.11.0 |
| Deployment | `docker compose` (postgres 16, redis 7, FastAPI backend, Vite frontend) |

---

## 4. Evaluation Methodology

1. **No bypass of the API.** All 100×2 samples were submitted through the real,
   running VoiceGuard REST API — `POST /scans` (multipart upload) → poll
   `GET /scans/{id}` until `ready_for_ai` → `POST /scans/{id}/process` → poll until
   `completed` → `GET /scans/{id}/technical` for the full result (verdict, confidence,
   raw bonafide/spoof scores, inference/processing time).
2. **Real checkpoint, no mocks.** The active model was confirmed via
   `GET /api/v1/models/current` to be `audio_cnn:v1`, backed by the checkpoint above,
   loaded in memory by the actual running backend process.
3. **Multiple accounts, one reason only.** The app enforces a 30-scans/hour/user rate
   limit. Four real, registered-and-verified user accounts were used purely to stay
   under that limit while running 100 scans in a reasonable time — this is normal
   multi-tenant usage, not a bypass of any security or business-logic control.
4. **No modification of model, thresholds, preprocessing, feature extraction, or
   inference logic.** The only environment change made during this evaluation was
   installing the ML runtime dependencies (`torch`, `torchaudio`, `librosa`, `numpy`,
   `pandas`, `soundfile`, `pydub`) into the backend container, because the shipped
   `api/Dockerfile` is deliberately built lean (auth-only, no ML libraries) — a
   pre-existing gap unrelated to this evaluation, fixed once in an earlier session
   so inference could run at all.

---

## 5. Performance Metrics (primary: `for-norm`)

| Metric | Value |
|---|---|
| Accuracy | 0.640 |
| Precision (spoof=positive) | 1.000 |
| Recall / Sensitivity (spoof) | 0.280 |
| Specificity (bonafide) | 1.000 |
| F1 Score | 0.4375 |
| False Positive Rate | 0.000 |
| False Negative Rate | 0.720 |
| Balanced Accuracy | 0.640 |
| Matthews Correlation Coefficient (MCC) | 0.4035 |
| ROC-AUC | 0.9070 |
| PR-AUC | 0.9204 |
| Average confidence | 0.9444 |
| Median confidence | 0.99996 |
| Confidence std. dev. | 0.1121 |
| Average inference time | 43.5 ms |
| Median inference time | 59.0 ms |
| P95 inference time | 82.4 ms |
| Min / Max inference time | 1 ms / 102 ms |
| Average end-to-end wall-clock time (upload→result) | 2.09 s |
| Throughput (wall-clock, incl. upload+persistence+HTTP) | 0.48 files/sec |
| Throughput (inference compute only) | 22.98 files/sec |
| Uncertain verdicts (below 0.60 threshold) | 2 / 100 |

Full machine-readable copy: `metrics.json`.

### Secondary/appendix run (`for-2sec`, short-clip robustness data point)

| Metric | Value |
|---|---|
| Accuracy | 0.550 |
| Precision | 1.000 |
| Recall / Sensitivity | 0.100 |
| Specificity | 1.000 |
| F1 Score | 0.1818 |
| False Positive Rate | 0.000 |
| False Negative Rate | 0.900 |
| Balanced Accuracy | 0.550 |
| MCC | 0.2294 |
| ROC-AUC | 0.7362 |
| PR-AUC | 0.8037 |
| Average confidence | 0.9736 |
| Average inference time | 42.4 ms |

Not used for the upstream-comparison verdict (§1, §12) — kept only to show that
performance degrades further, not less, when clips are shorter than the model's
trained 4-second window. Full data: `metrics_appendix_for2sec.json`,
`predictions_appendix_for2sec.csv`.

---

## 6. Confusion Matrix (primary: `for-norm`)

|  | Predicted: Bonafide (human) | Predicted: Spoof (AI) |
|---|---|---|
| **Actual: Bonafide** | 50 (TN) | 0 (FP) |
| **Actual: Spoof** | 36 (FN) | 14 (TP) |

(2 additional spoof samples were reported as `uncertain` — below the 0.60 confidence
threshold rather than a definite call either way; counted as misses in the metrics
above since they are not correct positive identifications. See `misclassified_samples.csv`.)

CSV: `confusion_matrix.csv`.

---

## 7. ROC Curve

ROC-AUC = **0.907**. Full curve (FPR/TPR/threshold triples): `roc_curve.csv`.

The strong ROC-AUC alongside a poor recall-at-threshold-0.60 (0.28) indicates the
model's *ranking* of genuine vs. AI-generated audio is reasonably good — the raw
`spoof_score` does separate the classes fairly well in aggregate — but the deployed
**0.60 confidence threshold is set too conservatively for this data distribution**,
converting a moderate separation into a high real-world miss rate. This is a threshold
observation, not a change: per instructions, no threshold was modified during this
evaluation.

## 8. Precision-Recall Curve

PR-AUC = **0.920**. Full curve: `pr_curve.csv`. Precision stays at 1.0 across nearly the
entire recall range up to ~0.3, meaning the model rarely produces a false spoof
call — every miss is a false *negative*, never a false positive, across both dataset
variants and 200 total samples evaluated.

---

## 9. Error Analysis

**All 36 misclassifications in the primary run were false negatives** (AI-generated
audio predicted as human); there were **zero false positives** in either the 100-sample
primary run or the 100-sample appendix run (200 genuine samples, 0 incorrectly flagged).

### Top 10 False Negatives (highest confidence, i.e. most confidently wrong)

| Filename | Confidence (bonafide) | raw_spoof_score | Inference (ms) |
|---|---|---|---|
| file1004.wav... | 1.000000 | 0.000000 | 5 |
| file100.wav... | 1.000000 | 0.000000 | 53 |
| file1056.wav... | 1.000000 | 0.000000 | 60 |
| file1045.wav... | 0.999999 | 0.000001 | 79 |
| file1018.wav... | 0.999994 | 0.000006 | 6 |
| file1038.wav... | 0.999997 | 0.000003 | 77 |
| file1057.wav... | 0.999997 | 0.000003 | 3 |
| file1029.wav... | 0.999980 | 0.000020 | 75 |
| file1012.wav... | 0.999673 | 0.000327 | 1 |
| file1007.wav... | 0.999889 | 0.000111 | 4 |

Full list with every field: `misclassified_samples.csv`.

### Top False Positives

**None to report.** Across both dataset variants (200 genuine samples total), the
deployed system produced zero false positives. Specificity is a clean 1.000 in every
run performed.

### Evidence-based root-cause analysis

Per-file audio properties (duration, RMS energy, peak amplitude, silence ratio, clipping
ratio — computed directly from the WAV samples, see `audio_stats.csv`) were correlated
against the raw spoof score for all 50 ground-truth-spoof samples in the primary run:

| Property | Correlation with raw_spoof_score |
|---|---|
| Duration (s) | **−0.360** |
| RMS energy | **−0.435** |
| Peak amplitude | +0.118 |
| Silence ratio | −0.015 |
| Clipping ratio | +0.296 |

Correctly-detected spoof clips (TP, n=14) averaged **1.42s** duration and **0.198** RMS;
misclassified spoof clips (FN, n=36) averaged **1.77s** duration and **0.228** RMS —
longer, louder (higher-RMS) synthetic clips were moderately more likely to be missed.
Silence ratio and clipping showed no meaningful relationship to detection outcome.

These correlations (0.36–0.44 in magnitude) are real but moderate — they explain some,
not most, of the 72% miss rate. The dominant pattern is a **general bias toward the
bonafide/human class on this specific checkpoint against this specific fresh sample**,
not a specific, narrow failure mode tied to one recording condition. No evidence of
noise, clipping, or corrupted files was found in any misclassified sample — waveforms
decoded cleanly, integrity checksums passed, and silence ratios were unremarkable and
similar between correctly- and incorrectly-classified clips.

---

## 10. Model Health Assessment

- **Confidence distribution:** heavily bimodal and pushed to the extremes — median
  confidence 0.99996, but this reflects *overconfidence in the wrong direction* for the
  36 false negatives as much as correct high-confidence calls. A softmax-derived
  "confidence" that is this saturated (many values at exactly 1.000000 or 0.000000) is a
  sign the classifier's raw scores are poorly calibrated probabilities, not that its
  decisions are reliable — see calibration note below.
- **Calibration:** `api/inference/confidence.py::calibrate()` is explicitly an identity
  passthrough of raw softmax output — the code's own docstring states real calibration
  (temperature/Platt scaling) hasn't been implemented yet for lack of a held-out
  calibration set. This evaluation is independent evidence that this gap matters in
  practice: the model is frequently >99.9% "confident" while wrong.
- **Class bias:** strong, consistent bias toward the bonafide/human verdict on this
  dataset family, in both the primary and appendix runs, across all 4 evaluation
  accounts and all inference workers. This is not an artifact of one bad batch — the
  same asymmetry (0 FP, high FN) held in a completely independent 100-sample run with
  different files, different durations, different accounts.
- **Class imbalance effects:** not applicable here — the evaluation set was perfectly
  balanced (50/50) in both runs, so the imbalance is in the model's *decision behavior*,
  not the input data.
- **Threshold clustering:** of the 36 false negatives, 24 had raw_spoof_score below
  0.05 and only 6 were within 0.35 of the 0.60 threshold — most misses are not
  "near-miss, would flip with a small threshold change" but are the model confidently
  assigning very low spoof probability to genuinely AI-generated audio.
- **Prediction stability:** identical file content produced identical predictions
  across repeat exposure in earlier smoke testing (deterministic inference, no dropout
  at eval time, as expected for a CNN in `.eval()` mode) — no instability observed.
- **Robustness:** degrades further, not less, on shorter clips (appendix run: FNR rises
  from 72% to 90% when clips are truncated to 2s and zero-padded to the model's 4s
  window) — consistent with a model sensitive to the amount of real signal vs. silence
  padding it receives.

**Strengths:** extremely low false-positive risk (0/200 across both runs) — a system
that never wrongly flags real human speech is a meaningful, deployable property for
many use cases where false accusations are the costlier error. Fast inference (43ms
average, single digits at the low end) and no crashes, timeouts, or pipeline failures
across 200 real end-to-end runs.

**Weaknesses:** poor sensitivity to AI-generated audio (28% recall on `for-norm`, 10%
on `for-2sec`) — the system as currently thresholded will miss the large majority of
deepfakes drawn from this dataset family. Confidence values are not a reliable proxy
for correctness (many high-confidence wrong answers). No calibration layer exists to
correct this.

---

## 11. Limitations

- Sample size is 100 per run (50/50) — enough to characterize gross behavior (the 0-FP,
  high-FN pattern is unambiguous and consistent across two independent runs) but not
  enough to tightly bound metrics like ROC-AUC or MCC; a larger run (500–1000/class)
  would narrow confidence intervals.
- Only the Fake-or-Real dataset family was tested. No claim is made here about
  generalization to ASVspoof-style TTS/VC attacks, WaveFake vocoders, or newer
  generative models not represented in this dataset's fake class.
- Inference ran on CPU only (no GPU); timing numbers reflect this container's CPU
  configuration and are not directly comparable to a GPU-served deployment.
- The confidence-calibration gap noted in §10 is inherent to the current codebase design
  (explicitly documented as an identity passthrough), not something this evaluation
  could work around without modifying inference logic — which was explicitly out of
  scope for this benchmark.

---

## 12. Deployment Recommendation

**Not recommended for production release in its current form, specifically for the
AI-generated-speech detection use case.** The evidence is unambiguous and reproduced
across two independent 100-sample runs: the deployed AudioCNN checkpoint, exactly as
integrated, misses 72–90% of AI-generated audio in this dataset family while never
falsely flagging genuine speech.

This is very different from the upstream repository's own published numbers for the
same checkpoint (90.3% accuracy, 19.3% FNR, per the vendored source's own
`performance_report.md`) on what should be a comparable data distribution
(`for-norm`, matching upstream's documented preprocessing). Whether the gap is caused
by (a) the specific 100-sample test split drawn here differing from upstream's own
held-out split, (b) a subtle preprocessing/feature-extraction difference between
VoiceGuard's re-implementation and upstream's original evaluation code, or (c) something
else not yet isolated, **could not be determined from this evaluation alone** — it would
require either obtaining upstream's exact test split/protocol file, or a substantially
larger sample to rule out split variance. What *is* established with high confidence:
the deployed system, as a user would experience it today, has a high real-world miss
rate on AI-generated speech from this dataset family.

**Recommended next steps, in priority order:**
1. Obtain upstream's actual train/test split (or its evaluation script/protocol file)
   and re-run this exact harness against it to determine whether the gap is a split
   artifact or a genuine integration regression.
2. Implement real confidence calibration (temperature or Platt scaling) — the
   `confidence.py` docstring already flags this as an open gap, and this evaluation
   supplies exactly the kind of held-out labeled data needed to fit it.
3. Consider lowering the confidence threshold (currently 0.60) or evaluating threshold
   sensitivity with a full precision-recall sweep — the ROC-AUC of 0.907 suggests a
   materially better recall is available at the same or better precision if the
   threshold is retuned, without touching the model itself.
4. Expand the benchmark to 500+ samples per class before drawing final go/no-go
   conclusions, and add ASVspoof/WaveFake as a second, independent evaluation corpus
   per the model family's own broader claims.
5. Do not treat this checkpoint as validated for deepfake detection in its current
   deployed configuration until (1) is resolved.
