# LCNN Improvement Project — Research Summary & Recommendation

Covers three completed experiment phases, all logged in `training/Experiment_Log.csv` / `.xlsx`:
1. Class-imbalance ablation (pre-existing, subset scale) — `weighted_sampler` won, already in production.
2. Waveform-augmentation ablation (subset scale) — noise/channel/noise+channel, all failed or were neutral.
3. Post-augmentation reassessment (subset scale) — label smoothing (ε=0.05, ε=0.10), EMA.

No checkpoint under `checkpoints/best.pt` or `checkpoints/last.pt` was touched. All new experiment checkpoints are under `checkpoints/experiments/<name>/`. No full 28-epoch run was triggered — none of phase 3's experiments cleared the improvement bar.

## 1. Ranked experiments by effectiveness (eval-subset EER, lower is better; n=3000, 400 bonafide + 200/attack A07–A19)

| Rank | Experiment | Eval-subset EER | Weak-attack mean EER | Balanced Acc | Outcome |
|---|---|---|---|---|---|
| 1 | label_smoothing_010 | 0.3004 | 0.4346 | 0.7086 | no_improvement (best overall EER, but below the improvement bar) |
| 2 | ema | 0.3046 | 0.4421 | 0.7129 | no_improvement |
| 3 | label_smoothing_005 | 0.3081 | 0.4475 | 0.7084 | no_improvement |
| 4 | augmentation_baseline | 0.3108 | 0.4500 | 0.7001 | baseline (reference point) |
| 5 | augmentation_channel | 0.3123 | **0.3988 (best weak-attack score)** | 0.6896 | no_improvement (best on weak attacks, but worse dev convergence and balanced accuracy) |
| 6 | augmentation_noise_channel | 0.4475 | 0.4663 | 0.5000 | collapsed |
| 7 | augmentation_noise | 0.5109 | 0.5161 | 0.5000 | collapsed |

No single experiment cleared this project's improvement bar (a deliberately conservative threshold: eval-subset EER improvement > 0.02 absolute). All are within a band plausibly explained by subset-sampling noise (n=200/attack) — no bootstrap confidence intervals were computed, so none of these deltas should be read as statistically confirmed.

## 2. What improved

Nothing crossed the bar for "meaningful." That said, label smoothing showed a **consistent, monotonic dose-response** across essentially every metric (ε=0 → 0.05 → 0.10: eval-subset EER 0.3108 → 0.3081 → 0.3004; weak-attack EER 0.4500 → 0.4475 → 0.4346; F1 0.738 → 0.764 → 0.781; recall 0.603 → 0.639 → 0.665). A monotonic trend across five largely-independent metrics as one parameter increases is a genuine (if modest) signal, not just noise — it's the one candidate worth carrying forward as a low-risk addition to a future run, not as a standalone justification for one.

## 3. What regressed

Both variants including additive Gaussian noise (`noise`, `noise_channel`) collapsed to a majority-class shortcut (dev recall pinned at exactly 1.0, dev accuracy pinned at exactly 0.897 = the subset's spoof fraction, for all 8 epochs). This confirms the earlier waveform-augmentation ablation's finding rather than being a new result — logged, not retried, per your instruction not to rerun waveform augmentation.

## 4. What had no measurable effect

- Channel-only augmentation: statistically neutral overall (this repeats/confirms the earlier finding — logged from the existing run, not rerun).
- EMA: essentially a wash — small gains in balanced accuracy/ROC-AUC/EER, small losses in F1/recall. Plausible explanation: 8 epochs × ~63 steps/epoch (~500 total steps) is a short enough run that the EMA shadow (decay 0.999, even with warmup) never fully "catches up" to the raw weights — this is a training-budget artifact of the fast subset protocol, not necessarily evidence against EMA at full training length (28 epochs, ~800 steps/epoch → ~22,000 steps gives EMA far more room to converge). This is a genuine open question a full-scale run would answer differently than this subset test — flagged, not resolved.

## 5. Updated comparison vs. current LCNN

No change — no experiment here was promoted to a full run, so `checkpoints/best.pt` remains the best available LCNN checkpoint:

| Metric | Deployed LCNN (full eval, 71,237 files) |
|---|---|
| Dev EER | 0.0135% |
| Eval EER | 22.83% |
| Balanced Accuracy | 78.62% |
| ROC-AUC | 0.8547 |

(The subset-scale numbers above, ~0.30–0.31 eval-subset EER, are **not directly comparable** to this 22.83% full-eval number — the subset ablations use 8 epochs on 2,000 training files specifically to get a fast, cheap directional read, not a production-scale estimate. Scale, not just the experimental variable, differs.)

## 6. Updated comparison vs. AudioCNN

Unchanged from `training/LCNN_Training_Report.md` (no new AudioCNN evaluation was run this session):

| Metric | LCNN (deployed) | AudioCNN (deployed) |
|---|---|---|
| Eval EER | 22.83% | 51.02% |
| Balanced Accuracy | 78.62% | 52.22% |
| ROC-AUC | 0.8547 | 0.4827 (≈chance) |

LCNN remains decisively better than AudioCNN; nothing in this session changes that recommendation.

## 7. Is another full 28-epoch LCNN run justified right now?

**No, not on the current evidence.** Three consecutive subset experiments (label smoothing ×2, EMA) failed to clear the improvement bar — the stop condition you specified. A full run costs ~6 hours of CPU time; committing that on a "no_improvement" subset signal isn't justified. The one exception worth flagging: label smoothing's monotonic trend is real enough that if/when a full run *does* happen (e.g. after a stronger candidate is found, or paired with an architecture change), adding `label_smoothing=0.10` to that run is a low-risk, essentially-free addition worth including — not a reason to run LCNN again on its own.

## 8. Is the architecture becoming the limiting factor?

**Moderate evidence yes, though not conclusive from subset-scale testing alone.** Across 7 subset-scale variants spanning three orthogonal regularization mechanisms — input-level (noise/channel augmentation), loss-level (label smoothing), and weight-level (EMA) — the weak-attack mean EER never left a narrow 0.40–0.52 band, and overall eval-subset EER never left 0.30–0.31 (excluding the two collapsed noise runs). When structurally different regularizers all plateau in the same range on the same six attacks (A10/A12/A13/A15/A17/A18 — all neural-waveform-vocoder or hybrid TTS_VC systems with no close relative among A01–A06), the more likely explanation shifts from "under-regularized" to "the fixed 128-band mel-spectrogram front end + ~700K-parameter 4-block CNN may lack the representational capacity or inductive bias to separate these specific synthesis artifacts from bonafide speech" — a capacity/representation ceiling, not a training-recipe gap.

This isn't proven — only 3 of the 6 remaining ranked candidates (stronger SpecAugment, weight decay tuning, mixup) were tested, and none was pushed to full scale. But the consistent, narrow plateau across mechanistically different regularizers is a real signal worth acting on rather than continuing to iterate on LCNN's training recipe alone.

## 9. RawNet2 vs. continuing to tune LCNN

**Recommend evaluating RawNet2 next, in preference to further LCNN regularization tuning — but this is a recommendation only; no RawNet2 training was started.**

Verified before recommending (not assumed): `src/models/rawnet2.py` (122 lines) implements a real SincConv-based learnable bandpass-filterbank front end operating directly on the raw waveform — not a stub. `configs/rawnet2.yaml`, `scripts/train_rawnet2.py`, and `scripts/evaluate_rawnet2.py` all exist and are wired to this repo's data/protocol/evaluation code. **It has never been trained** — there is no `checkpoints/rawnet2/` and no `runs/rawnet2/` on disk. This is a genuinely untested code path, not a repeat of earlier work.

Why this is the better next move: RawNet2's raw-waveform sinc-filter front end is a fundamentally different feature-extraction mechanism than LCNN's fixed log-mel spectrogram — it can learn task-specific frequency-selective filters rather than being constrained to a general-purpose mel filterbank. Published ASVspoof2019 LA results consistently show raw-waveform architectures generalizing better to unseen attacks than mel-spectrogram CNNs specifically — the same failure mode this project's per-attack analysis identified as LCNN's central weakness. If the bottleneck really is representational (finding #8), a different front end is the mechanism that targets it; another loss/regularization tweak on LCNN does not.

Practical caveat: `configs/rawnet2.yaml` specifies 100 epochs (vs. LCNN's 28) and RawNet2's architecture (SincConv + presumably residual blocks/GRU) is heavier per-sample than LCNN's small CNN — a full run will cost more than LCNN's ~6 hours on this CPU-only machine. **If you want to pursue this, the same subset-scale protocol used throughout this project (2,000/1,000 train/dev, ~8 epochs, the fixed 3,000-file eval subset) should be run first** to sanity-check RawNet2 trains correctly here and get a fast, cheap directional read — mirroring exactly how the LCNN experiments in this report were de-risked before any full run — rather than committing to a full 100-epoch run blind.
