# Benchmark Summary — AudioCNN v1 (baseline)

**Date:** 2026-07-30 | **Checkpoint:** `deepfake_cnn.pth`
(`0fbe937e222a057ea56457334b41558f56a5c1472fa720b7083aa1c3bc70d4e7`) | **Model:** `audio_cnn:v1`

**Dataset:** Kaggle `mohammedabdeldayem/the-fake-or-real-dataset`, `for-norm` variant,
100 samples (50 bonafide / 50 spoof), matching upstream's own preprocessing recipe.

**Path:** Real production REST API, no bypass, no mocks — upload → preprocess →
feature-extract → AudioCNN → confidence → persist → retrieve.

## Headline numbers

| Metric | Value |
|---|---|
| Accuracy | 64.0% |
| Precision | 100.0% |
| Recall (sensitivity, spoof) | 28.0% |
| Specificity (bonafide) | 100.0% |
| F1 | 0.4375 |
| MCC | 0.4035 |
| ROC-AUC | 0.907 |
| PR-AUC | 0.920 |
| False Positive Rate | 0.0% |
| False Negative Rate | 72.0% |
| Avg. inference time | 43.5 ms |
| Avg. end-to-end (upload→result) | 2.09 s |
| Throughput (inference-only) | ~23 files/sec |

## One-line verdict

Zero false positives, but misses ~7 in 10 deepfakes from this dataset — a large gap
from upstream's own claimed 90.3% accuracy / 19.3% FNR on the same checkpoint. **Not
yet cleared for production deepfake-detection use**; root cause (split difference vs.
genuine regression) needs further isolation before re-baselining. Full detail:
`evaluation_report.md`.

## Artifact index

- `evaluation_report.md` — full report (this benchmark's source of truth)
- `predictions.csv` / `metrics.json` / `confusion_matrix.csv` / `roc_curve.csv` /
  `pr_curve.csv` / `misclassified_samples.csv` — primary (`for-norm`) run
- `*_appendix_for2sec.*` — secondary short-clip run (not used for the upstream
  comparison; robustness data point only)
- `audio_stats.csv` — per-file duration/RMS/silence/clipping used in error analysis
- `environment.json` — full reproducibility record (hardware, OS, Python/Torch
  versions, checkpoint identity, dataset provenance)
- `dataset/`, `dataset_fornorm/` — the actual 200 sampled audio files + manifests
