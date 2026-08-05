# RawNet2 Training Plan

**Status: contingent.** The Go/No-Go decision (`RawNet2_Go_NoGo_Report.md`) is **NO-GO on this machine's current CPU-only hardware** — the plan below is what to execute *if/when GPU compute is obtained*, not something to start now. No training has been started.

## Phase 3 — Data pipeline verification (LCNN vs. serving vs. RawNet2 training vs. RawNet2 inference)

| Stage | Steps applied | Output shape |
|---|---|---|
| LCNN training | `load_waveform` → `serving_equivalent_preprocess` (peak-normalize, silence-trim, fix to 64,000 samples @16kHz) → `MelSpectrogramTransform` (log-mel + SpecAugment on train) | `[1, 128, 251]` |
| Live serving (`api.inference.preprocessing.run_preprocessing`) | decode → resample to 16kHz → mono → silence-trim → fix-length | `[1, 64000]` waveform (this is what `serving_equivalent_preprocess` in `src/data/dataset.py` wraps — verified same underlying functions: `detect_and_trim_silence`, `normalize_amplitude`, `_fix_length`) |
| RawNet2 training (`scripts/train_rawnet2.py`) | `ASVspoofDataset(df, transform=None)` — **verified the `match_serving_preprocessing=True` default is not overridden**, so this *does* apply the same `serving_equivalent_preprocess` as LCNN, then skips the mel transform entirely (`transform=None`) | `[1, 64000]` raw waveform |
| RawNet2 inference (not yet implemented) | Would be: `api.inference.preprocessing.run_preprocessing` (already-shared, already-tested) → new `("raw","v1")` extractor → adapter's default no-op `preprocess()` | `[1, 64000]` raw waveform |

**Finding: no mismatch identified.** RawNet2's training path already reuses the exact same serving-equivalent preprocessing LCNN uses (peak-norm/silence-trim/fix-length) — it simply omits the mel transform, which is correct since RawNet2 is designed to consume raw waveform directly. If the inference-side extractor is implemented following the pattern above (which is how `("logmel","v1")` already works), training and serving preprocessing will be identical by construction, not by coincidence. This is the one area of the audit where the existing design is already correct and needs no remediation.

## Phase 4 — Training readiness numbers (measured this session, not estimated from docs)

| Metric | RawNet2 | LCNN (measured) |
|---|---|---|
| Parameters | 4,908,026 | 699,938 |
| Checkpoint size | ~19.7 MB | ~2.82 MB |
| CPU single-sample inference latency (mean) | ~237 ms | ~4.56 ms |
| Measured batch=32 train step (forward+backward+optimizer) | **121.3 s** | ~1 s (implied from full-epoch average) |
| Estimated full-epoch time (25,380 files, batch 32) | **~26.7 hours** | ~773 s (~12.9 min), measured |
| Configured epochs (`configs/rawnet2.yaml`) | 100 | 28 (actual, early-stopped) |
| **Estimated full configured run** | **~111 days of continuous CPU compute** | ~6.0 hours, measured |
| GPU available in this environment | No (`torch.cuda.is_available()` = False; no MPS on this Windows/CPU box) | Same |

Root cause, isolated by direct profiling (not assumed): forward pass is fast (~0.87s for a batch of 32, no grad tracking). Backward through the SincConv+residual stack alone is fast (0.13s at batch 4). **Backward through the single GRU layer is responsible for essentially all of the slowdown** (full-model backward at batch 4 = 17.0s vs. 0.13s without the GRU) — consistent with the well-known fact that CPU backpropagation-through-time for RNNs has no equivalent to cuDNN's fused GPU RNN kernels, and does not parallelize the way convolutions do.

## Contingent plan, if GPU compute becomes available

1. **Fix the identified code gaps first** (all small, from `RawNet2_Readiness_Report.md`):
   - Add `set_seed(cfg["training"].get("seed", 42))` to `scripts/train_rawnet2.py`; add `seed: 42` to `configs/rawnet2.yaml`.
   - Pass `metrics_csv_path=Path("training")/"RawNet2_Training_Log.csv"` to the `Trainer(...)` call.
   - Replace the naive unconditional checkpoint auto-load with real resume support (`load_training_checkpoint`, gated behind an explicit `--resume` flag), mirroring `scripts/train.py`.
   - Switch imbalance handling from `build_loss()` (weighted CE) to `WeightedRandomSampler`, matching the already-established winner from `training/imbalance_experiments/class_imbalance_comparison.md` — there is no reason to re-litigate that ablation for a different model architecture; the imbalance mechanism is orthogonal to model choice.
   - Fix or remove `evaluate_rawnet2.py`'s hardcoded, stale `lcnn_eer` comparison numbers (they do not match the real LCNN checkpoint — see Readiness Report §2) before ever using this script's console output for a real comparison.
   - Extend `evaluate_rawnet2.py` to the same metric suite as `scripts/evaluate.py` (reuse `src.evaluation.metrics.compute_full_metrics` — already shared, already imports cleanly) so RawNet2 and LCNN are judged on identical criteria.
2. **Cheap correctness smoke test first** (minutes, on GPU): 2-3 epochs on a small stratified subset (e.g. 200-500 train files), purely to confirm the fixed script trains end-to-end without error and loss decreases — not a generalization signal, sample size is far too small for that.
3. **Subset-scale ablation, mirroring the LCNN methodology exactly** (`compare_augmentation.py`'s protocol: 2,000 train / 1,000 dev, seed 42, 8 epochs, evaluated on the same fixed 3,000-file eval subset spanning A07–A19) — this is the fast, cheap directional check the LCNN experiments used throughout, and the same discipline should apply here before any full run. On GPU this should take minutes, not the ~2.1 hours/epoch the CPU benchmark implies for this subset size.
4. **Only if the subset signal is positive**, proceed to a full run at the corrected config (seed set, CSV logging on, `weighted_sampler`, real resume support) — with checkpoints under `checkpoints/experiments/rawnet2_<version>/`, never touching `checkpoints/best.pt`.
5. **Evaluate on the full official eval split**, using the extended `evaluate_rawnet2.py` (full metric suite, plots, per-attack breakdown), and compare directly against the real, verified LCNN numbers (22.83% eval EER) — not against the stale hardcoded constants currently in the script.
6. **Integrate only after a full run beats LCNN on eval EER**: implement the adapter + extractor from `RawNet2_Compatibility_Report.md`, register via `register_model_version` with `status="inactive"`, and leave `switch_active_model` as a separate, deliberate step for you to authorize — never automatic.

No step above should be started until GPU compute is confirmed available; see `RawNet2_Go_NoGo_Report.md` for why.
