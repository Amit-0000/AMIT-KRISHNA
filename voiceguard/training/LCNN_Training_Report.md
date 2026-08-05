# LCNN Training Report — ASVspoof2019 LA

**Experiment IDs:** `LCNN_20260801T124604Z` (epochs 1–12, paused), `LCNN_20260801T193127Z` (resumed, epochs 13–28, early stopped)
**Git commit:** `bf8cc78f2a541af0059b985f49c0630447820761` (working tree dirty — see [Modified Files](#modified-files))
**Dataset:** Official ASVspoof2019 LA (train 25,380 / dev 24,844 / eval 71,237 files)
**Architecture:** `src.models.lcnn.LCNN` — unchanged. No architecture redesign, no new model introduced, per the governing constraint.

---

## 1. Training duration

28 epochs completed (1 run of 12 epochs, paused, resumed for 16 more, then early-stopped). Total epoch compute time: **21,647s (~6.01 hours)** on CPU (Intel, 14 physical/20 logical cores, 31.7GB RAM, no CUDA/MPS available — mixed precision correctly disabled). Individual epoch times ranged 598s–1,243s, reflecting normal CPU load variance, not instability.

## 2. Epochs completed & why training stopped

28 of the configured 50-epoch budget. **Stopped by early stopping**: `patience=10` — 10 consecutive epochs (19–28) with no improvement in dev EER over the best value set at epoch 18. This is the mechanism working as designed, not a failure.

## 3. Best epoch / checkpoint

**Epoch 18** — `checkpoints/best.pt` (bare `state_dict`, adapter-compatible, 2.82MB / 699,938 parameters). Selected by lowest dev EER (0.000135), the model-selection metric used throughout for its immunity to this dataset's ~9:1 class imbalance.

## 4. Final metrics

**Dev split (epoch 18, in-distribution — attack types A01–A06, same as train):** EER 0.0135%, accuracy 99.92%, precision 99.91%, recall 100%, F1 0.99955, ROC-AUC 1.0000.

**Eval split (official held-out test, attack types A07–A19, disjoint from train/dev — the trustworthy generalization measurement):**

| Metric | Value |
|---|---|
| Accuracy | 63.45% |
| Precision | 99.56% |
| Recall (spoof) | 59.51% |
| Specificity | 97.73% |
| Balanced Accuracy | 78.62% |
| F1 | 0.7449 |
| ROC-AUC | 0.8547 |
| PR-AUC | 0.9821 |
| **EER** | **22.83%** (baseline LFCC-GMM: 8.09%) |
| FPR | 2.27% |
| FNR | 40.49% |
| Avg / median / P95 / P99 latency | 4.56 / 4.59 / 5.37 / 5.95 ms/sample |

## 5. Learning curve analysis

See `Loss_Curve.png`, `Accuracy_Curve.png`. Train loss fell monotonically from 0.380 (epoch 1) to ~0.001 (epoch 28) with no spikes or NaNs. Dev loss tracked it down to ~epoch 10, then plateaued with minor noise (0.0003–0.017 range) rather than diverging — consistent with a well-conditioned optimization, not instability.

## 6. Convergence / overfitting evidence

No overfitting on the dev split itself: dev EER stayed low (0.01–0.26%) throughout epochs 10–28 with no sustained upward trend: early stopping triggered on a patience exhaustion, not a blowup. **However, the large dev→eval EER gap (0.0135% → 22.83%) is real and is the central finding of this run.** Root cause, confirmed via `Dataset_Analysis.md`: train and dev share attack types A01–A06; eval's A07–A19 are entirely unseen. The model converged well on the training distribution; the gap reflects a **dataset-design generalization boundary**, not a training defect — no amount of additional training on A01–A06 data would close it, since the eval attacks are algorithmically different (per-attack breakdown shows the weak spots cluster on voice-conversion attacks A10/A12/A13/A15/A17/A18, a family absent from A01–A06's TTS-only attacks).

## 7. Resource usage

CPU-only training, 31.7GB RAM available. Approximate inference-time memory footprint (isolated-process RSS delta, single measurement): **418.5MB** for LCNN vs 52.4MB for AudioCNN — LCNN is heavier per-inference, consistent with its larger parameter count (699,938 vs 23,585, a ~30x difference) but latency is still sub-6ms/sample even at P99.

## 8. Comparison with AudioCNN

Both models evaluated identically (same eval split, same `src.evaluation.metrics` code) — see `Benchmark_Comparison.xlsx`.

| Metric | LCNN | AudioCNN (deployed) |
|---|---|---|
| EER | **22.83%** | 51.02% |
| Balanced Accuracy | **78.62%** | 52.22% |
| Recall (spoof) | **59.51%** | 10.39% |
| Precision | **99.56%** | 93.81% |
| ROC-AUC | **0.8547** | 0.4827 (≈chance) |
| Avg latency | 4.56ms | 1.95ms |

AudioCNN performs at approximately chance level on this benchmark. Important context: AudioCNN is a vendored checkpoint from a different upstream project, never trained on ASVspoof data — this is an out-of-domain test for it. That context doesn't change the measured numbers, which are what matters for a deployment decision on VoiceGuard's actual detection task.

## 9. Production readiness recommendation

**Recommend deploying LCNN (`checkpoints/best.pt`, epoch 18) to replace AudioCNN as the active model.** All 5 stated criteria are met: lower EER, higher balanced accuracy, higher recall, comparable-or-better precision, comparable latency (both sub-10ms). See `Benchmark_Comparison.xlsx`'s `production_readiness` sheet.

**Caveat that should inform the deployment decision, not block it:** a 22.83% eval EER is a large absolute error rate for a production spoof detector — it is a major improvement over AudioCNN's near-chance performance, but not yet a "solved" detector. The per-attack breakdown shows this concentrates in voice-conversion-style attacks; if VoiceGuard's real-world threat model includes VC-based deepfakes, this gap matters operationally even though LCNN is still the better of the two available checkpoints.

**No checkpoint has been switched in production.** This report presents the recommendation per the constraint against auto-replacing the deployed model; integration verification (§below) confirms LCNN loads and runs correctly through the real serving path, but activating it (`switch_active_model`, bumping `MODEL_VERSION`) is a deliberate step for you to authorize.

## 10. Modified files

| File | Why |
|---|---|
| `src/training/trainer.py` | Added deterministic seeding, resume support, full per-epoch metric suite (accuracy/precision/recall/F1/ROC-AUC/EER), best/last checkpointing, CSV+TensorBoard logging, early stopping — all required by the Phase 5 spec. Fixed a pre-existing Windows console-encoding crash (`↳` → `->`). |
| `scripts/train.py` | Added `--resume` flag, experiment-record initialization call, wired in `WeightedRandomSampler` (the empirically-validated winning imbalance strategy) in place of weighted-loss. |
| `configs/lcnn.yaml` | Added `training.seed: 42` for reproducibility. |
| `src/data/dataset.py` | Added `serving_equivalent_preprocess` + `match_serving_preprocessing` flag, closing the Phase 4 train/serve preprocessing mismatch (measured mean log-mel difference of 5.75 pre-fix). |
| `src/data/transforms.py` | Fixed stale docstring (`[1,128,313]` → verified actual `[1,128,251]`). |
| `api/inference/adapters/lcnn_adapter.py` | Fixed `AdapterMetadata.input_shape` to match the corrected `[1,128,251]` shape. |
| `pyproject.toml` | Added `"api*"` to the editable-install package list (fixed a `ModuleNotFoundError` inside DataLoader worker subprocesses); added `psutil`, `openpyxl` dependencies. |
| `scripts/evaluate.py` | Rewritten for full Phase 5 post-training evaluation methodology (all required metrics, per-attack EER, latency percentiles, plots, `Benchmark_Results.xlsx`). |
| `src/evaluation/metrics.py` *(new)* | Shared metric/plotting code so LCNN and AudioCNN are evaluated with byte-identical logic. |
| `scripts/audit_asvspoof.py` *(new)* | Phase 3 full-dataset integrity audit. |
| `scripts/compare_class_imbalance.py` *(new)* | Empirical class-imbalance ablation (Task 2). |
| `scripts/init_experiment.py` *(new)* | Experiment-record generation (Task 3). |
| `scripts/evaluate_audio_cnn.py` *(new)* | AudioCNN benchmark harness, reusing the production `logmel64db` extractor and `src.evaluation.metrics` for parity with LCNN's evaluation. |
| `scripts/build_benchmark_comparison.py` *(new)* | Compiles `Benchmark_Comparison.xlsx` from both models' results. |
| `data/` directory | Reorganized from the Kaggle mirror's nested `LA/LA/...` layout to the flat official structure the codebase expects (Phase 2/3). `data/PA` left untouched (unused, disclosed, not deleted). |

No changes were made to `src/models/lcnn.py` (architecture), the frontend, or any file outside what's listed above and the generated `training/` deliverables.

## 11. Limitations

- Eval EER (22.83%) remains well above the classical LFCC-GMM baseline (8.09%) — LCNN beats AudioCNN decisively but has not surpassed the published baseline on this benchmark.
- Weak spots concentrate on voice-conversion-style attacks (A10, A12, A13, A15, A17, A18) — the model has not seen any VC-family spoofing during training (A01–A06 are TTS-only).
- Docker build regression could not be verified in this environment — Docker Desktop's daemon was not running (`docker info` shows no server connection). All other regression checks (191 backend tests, 39 targeted model/registry/inference tests, manual end-to-end integration test through the real `model_loader` → `LCNNAdapter` → `run_inference` path) passed.
- Approximate memory figures are single-run, isolated-process RSS deltas, not averaged over repeated trials — treat as directional, not precise.

## 12. Future improvements

- Training data augmentation or fine-tuning specifically targeting voice-conversion-style spoofing would likely close a meaningful part of the eval-EER gap, given the clean split between TTS-strong / VC-weak per-attack results.
- Consider whether a broader/more diverse spoofing-attack training corpus (beyond ASVspoof2019 LA's 6 training attack types) is available, since the dev-split metric is structurally incapable of detecting this gap during training (train/dev share attack types).
- Verify Docker build once Docker Desktop's daemon is available, to complete the regression checklist.
