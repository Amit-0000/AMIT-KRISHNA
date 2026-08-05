# RawNet2 Readiness Report

Scope: verify what actually exists for RawNet2 in this repository, empirically where possible, rather than trust comments/docs. No project files were modified to produce this report — every claim below is from reading `src/models/rawnet2.py`, `scripts/train_rawnet2.py`, `scripts/evaluate_rawnet2.py`, `configs/rawnet2.yaml`, and from running small, isolated, read-only diagnostic snippets (forward/backward timing, parameter counts) that do not touch any checkpoint or config file.

## 1. Implementation completeness

| Item | Status | Evidence |
|---|---|---|
| Architecture implemented | Yes | `src/models/rawnet2.py` (123 lines): `SincConv` → `BatchNorm1d`+LeakyReLU → 6× `ResBlock` (70→70→70→128→128→256→256 channels, stride-3 downsampling twice) → single-layer `GRU` (hidden=1024) → `Linear(1024,2)`. |
| Matches original RawNet2 (Tak et al. 2021) | **Partially** | Core shape (SincConv frontend + residual stack + GRU + FC) matches. **Missing: Feature Map Scaling (FMS)** — the original architecture applies a sigmoid-gated channel-attention (SE-block-style) after each residual block; this implementation's `ResBlock` is a plain residual block with no FMS. This is a real, material deviation, not a naming quibble — the original paper's ablations credit FMS with a meaningful share of RawNet2's performance. |
| SincConv correct | Yes, verified | Formula implements bandpass = lowpass(f2) − lowpass(f1), Hamming-windowed, made symmetric via `flip+cat` for zero phase response, mel-scale cutoff initialization — matches the standard SincNet/RawNet2 approach. Frequencies are correctly constrained (`f2 > f1`, `f2 < Nyquist`) before filter construction. |
| Forward pass correct | Yes, verified by running it | `RawNet2()(torch.randn(2,1,64000))` → output shape `(2,2)`, no errors. Confirmed real intermediate shapes (not the code's comments — see below): SincConv output `[batch,70,4001]` (comment in the code says "~2000", **verified wrong by direct measurement** — off by ~2x; harmless since only a comment, but a concrete instance of why this audit verifies rather than reads and trusts), residual-block output `[batch,256,445]`, GRU final hidden state `[1,batch,1024]`. |
| Dropout / explicit regularization | **None** | No `nn.Dropout` anywhere in `RawNet2`, unlike LCNN's `Dropout(0.75)`. Only BatchNorm + L2 weight decay regularize it. Worth flagging given ASVspoof2019 LA's small training set (25,380 files, 2,580 bonafide). |
| Training code exists | Yes | `scripts/train_rawnet2.py` (94 lines), reuses the shared `src.training.trainer.Trainer` (same class LCNN uses). |
| Evaluation code exists | Yes, but materially thinner than LCNN's | `scripts/evaluate_rawnet2.py` (77 lines) computes overall EER and per-attack EER only (reuses `src.evaluation.eer`, verified correct). It has **no** balanced accuracy, ROC-AUC, PR-AUC, F1, precision/recall, confusion matrix, latency benchmarking, or plot/xlsx export — all of which `scripts/evaluate.py` produces for LCNN. Bringing RawNet2 to evaluation parity with LCNN needs this script extended, not rewritten (same shared `src.evaluation.metrics` module LCNN already uses would drop in directly). |
| Checkpoint saving/loading | Yes (save side); loading is naive | `Trainer` saves `best.pt` (bare state_dict) / `last.pt` (full training state) identically to LCNN. **Loading in `train_rawnet2.py` is not real resume support** — see next row. |
| Resume support | **No — a bug-prone shortcut, not resume** | `train_rawnet2.py`: `if checkpoint_path.exists(): model.load_state_dict(...)`. This unconditionally reloads model weights only — no optimizer state, no scheduler state, no epoch counter, no best-EER/patience-counter — and it's not gated behind a flag, so it silently fires on every run if a checkpoint happens to exist. Compare to LCNN's `scripts/train.py --resume`, which calls `load_training_checkpoint()` to restore optimizer/scheduler/epoch/best_eer/patience state, and only does so when explicitly asked. A multi-day RawNet2 run interrupted partway would **not** resume correctly with the current script — it would restart the LR schedule and optimizer state from scratch while keeping only the weights, silently. |
| TensorBoard | Yes | Inherited automatically from `Trainer` (`SummaryWriter(log_dir=cfg["paths"]["log_dir"])` = `runs/rawnet2`). |
| CSV logging | **Capability exists, not activated** | `Trainer` supports `metrics_csv_path`, but `train_rawnet2.py`'s `Trainer(...)` call does not pass it (unlike `scripts/train.py`, which passes `metrics_csv_path=Path("training")/"Training_Log.csv"`). As currently written, a RawNet2 run produces TensorBoard events but no CSV log. |
| Mixed precision | Yes (inherited, currently inert) | `Trainer.use_amp = device.type == "cuda"` — same hook as LCNN. Inert on this CPU-only machine either way. |
| Deterministic seed support | **Capability exists, not activated** | `src.training.trainer.set_seed()` exists and is used by LCNN's `scripts/train.py` (`set_seed(cfg["training"].get("seed", 42))`). `scripts/train_rawnet2.py` **never calls `set_seed`**, and `configs/rawnet2.yaml` has no `seed:` key at all. A RawNet2 run today is not reproducible run-to-run. |
| Early stopping | Yes | Inherited from `Trainer`, `patience=15` from `configs/rawnet2.yaml` (vs LCNN's 10) — correctly wired. |
| Optimizer / scheduler | Yes | Adam (`lr=1e-4`, `weight_decay=1e-4`) + `CosineAnnealingLR(T_max=100, eta_min=1e-6)` — same pattern as LCNN, config-driven. |
| Class-imbalance handling | **Present, but the demonstrably worse strategy** | `train_rawnet2.py` uses `build_loss()` — inverse-frequency-weighted CrossEntropy (`weighted_ce`). This repo's own ablation (`training/imbalance_experiments/class_imbalance_comparison.md`) already measured `weighted_ce` as decisively worse than `weighted_sampler` (dev EER 0.272 vs 0.087) and switched LCNN's production training to `weighted_sampler` as a result. RawNet2's script was never updated to match — it still uses the strategy this repo's own evidence rejected. |
| Training/eval scripts functional | Yes, both run | Both import cleanly and exercise real, tested shared code (`Trainer`, `src.evaluation.eer`). No stub functions. |
| Docker compatibility | Yes, no changes needed | RawNet2 imports only `torch`, `torch.nn`, `torch.nn.functional`, `numpy` — all already in `requirements.txt` / `api/requirements-ml.txt` and installed in both `Dockerfile` and `api/Dockerfile.ml`. No new system packages needed (no librosa/ffmpeg dependency from the model itself; the shared data-loading path already needs those regardless of architecture). |
| VoiceGuard / adapter / registry compatibility | Not yet integrated — see `RawNet2_Compatibility_Report.md` | No `RawNet2Adapter` and no raw-waveform feature extractor exist yet. Full gap analysis in the companion report. |

## 2. A critical evidentiary problem: internal docs vs. verified reality

`docs/03_architecture.md`, `docs/05_training.md`, `docs/06_evaluation.md`, and `docs/09_results_and_conclusions.md` contain a detailed narrative describing a **completed** RawNet2 training run: dev EER trajectory 24.37% (epoch 50) → 2.47% (epoch 100+), eval EER 12.78%, ~12 hours of training, an ensemble/fusion analysis against LCNN with specific logistic-regression weights (10.707 vs 3.065), and per-attack numbers for both models.

**This is not substantiated by anything on disk, and it contradicts this repo's own verified results:**

- No `checkpoints/rawnet2/` directory exists (confirmed by direct filesystem listing — only `checkpoints/best.pt`, `checkpoints/last.pt`, `checkpoints/deepfake_cnn.pth`, `checkpoints/experiments/`).
- No `runs/rawnet2/` TensorBoard logs exist (only `runs/lcnn/`).
- No RawNet2 training log or report exists under `training/`.
- `checkpoints/` and `runs/` are gitignored, so this isn't just "not committed" — it is genuinely absent from this environment's disk right now.
- The docs' cited **LCNN** eval EER (7.07%) does not match this repo's own verified, measured LCNN eval EER (**22.83%**, `training/LCNN_Training_Report.md`, cross-checked against the real per-attack breakdown in `training/Benchmark_Results.xlsx`). These are not close — they describe different runs.
- `docs/05_training.md` states LCNN trained on "Apple Silicon MPS... approximately 2–3 hours." The actual verified run (`training/LCNN_Training_Report.md`) was **CPU-only, ~6.01 hours**, explicitly noting no CUDA/MPS was available. Another direct contradiction.
- `scripts/evaluate_rawnet2.py` hardcodes an "LCNN Eval EER: 7.0724%" print and a hardcoded per-attack `lcnn_eer` dict — these numbers match the docs' narrative exactly, but **not** the real, currently-deployed LCNN checkpoint's measured per-attack EER (e.g. real A10 = 44.24% vs the script's hardcoded 0.5846%; real A17 = 16.94% vs hardcoded 36.8457%; real A18 = 29.15% vs hardcoded 9.7477%).

The docs and the hardcoded script constants are internally consistent with *each other*, but not with this repository's actual, independently-verified training history. The most likely explanation, given the very first commit's message ("Initial commit: Add VoiceGuard project and documentation"), is that this narrative is pre-written illustrative/scaffolding content authored before the real LCNN training run that produced the 22.83% number — not a record of a RawNet2 run that actually happened here. Whichever it is, **none of the specific quantitative claims in those four docs files, or the hardcoded constants in `evaluate_rawnet2.py`, should be treated as evidence for this audit.** They are flagged here so they don't get cited later as if verified. See `RawNet2_Go_NoGo_Report.md` §Phase 5 for how this affects the expected-benefit estimate.

## 3. Empirically measured properties (not from docs — measured directly this session)

| Property | RawNet2 | LCNN (measured, `training/LCNN_Training_Report.md`) |
|---|---|---|
| Parameters | 4,908,026 | 699,938 |
| Serialized checkpoint size (state_dict) | ~19.7 MB | ~2.82 MB |
| Single-sample CPU forward latency (mean of 30 runs) | ~237 ms | ~4.56 ms |
| Batch=32 forward+backward+optimizer.step() (measured) | **121.3 s/batch** | not separately isolated, but full-epoch average (773 s / ~793 batches) implies ~1 s/batch |

The batch-level number above is the load-bearing finding of this audit — see `RawNet2_Go_NoGo_Report.md`.
