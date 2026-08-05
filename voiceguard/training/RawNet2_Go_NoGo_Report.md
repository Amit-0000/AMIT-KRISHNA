# RawNet2 Go/No-Go Report

## Phase 5 — Expected benefit on the weak attacks (A10/A12/A13/A15/A17/A18)

This section is explicitly an **estimate**, separated into what's verified, what's published literature, and what's architectural reasoning — none of it is a measured result for this repository's RawNet2 implementation, because it has never been trained here (see `RawNet2_Readiness_Report.md` §2).

**What is not usable as evidence:** `docs/06_evaluation.md` and `docs/09_results_and_conclusions.md` contain specific per-attack RawNet2-vs-LCNN numbers (claiming RawNet2 does *worse* than LCNN almost everywhere, including catastrophic failure on A17 at 40.38% and A18 at 40.82%). These numbers are internally consistent with each other and with `evaluate_rawnet2.py`'s hardcoded constants, but they contradict this repo's own independently-verified LCNN eval EER (22.83% real vs. 7.07% claimed) and training hardware (CPU/6hr real vs. MPS/2-3hr claimed). Because the paired LCNN number in that narrative is demonstrably wrong, the paired RawNet2 numbers cannot be trusted either — they are not used below.

**What is usable — published literature:** The original RawNet2 anti-spoofing paper (Tak et al., 2021, "End-to-End anti-spoofing with RawNet2") is a real, peer-reviewed, GPU-trained baseline reporting EER in the ~4-5% range on ASVspoof2019 LA eval — meaningfully better than this repo's verified LCNN result (22.83%). This establishes that the raw-waveform architecture *family* has a credible track record of strong generalization to unseen attacks when properly trained, under the conditions (full architecture including FMS, GPU training, adequate epoch budget) that produced those published numbers.

**What is usable — architecture reasoning:** A10/A12/A13/A15 (neural-waveform TTS and TTS_VC hybrids) and A17/A18 (VC waveform-filtering/vocoder) are, per this project's own per-attack audit, the attacks where LCNN's fixed mel-spectrogram front end fails hardest. A mel-spectrogram with log compression discards phase and some fine temporal structure by design — exactly the kind of information a high-quality neural vocoder's artifacts might live in. This is the standard, credible motivation for trying a raw-waveform model at all, not something specific to this repo.

**Important caveat specific to this repo's implementation:** `src/models/rawnet2.py` is missing Feature Map Scaling (FMS), a component the original paper's own ablations credit with a meaningful share of its performance. This implementation is a simplified variant of the published architecture, so even the literature's ~4-5% figure should be treated as an optimistic ceiling, not an expectation for this exact code.

**Net estimate:** There is a plausible, literature-grounded, moderate-confidence hypothesis that a properly-trained RawNet2 (ideally with FMS added back) could improve on LCNN's specific weak attacks. This is *not* a prediction of a specific number, and it is explicitly not confirmed by anything measured in this repository.

## Phase 6 — Decision

## NO-GO — for training RawNet2 to completion on this machine's current CPU-only hardware, as currently configured.

**This is a compute-feasibility NO-GO, not an architecture-merit NO-GO.** The reasoning in Phase 5 above is still a reasonable basis to revisit RawNet2 later; the blocker is specifically what this hardware can deliver in a reasonable timeframe.

### Precisely why

Measured, not estimated (see `RawNet2_Readiness_Report.md` §3 for the isolated profiling that produced these numbers):

- One training batch of 32 samples (forward + backward + optimizer step) took **121.3 seconds**, measured directly on this machine.
- Isolating the cause: backward through the SincConv+residual stack alone is fast (0.13s at batch 4); backward through the full model (which adds the GRU) is 17.0s at batch 4 — **the GRU's backpropagation-through-time is responsible for essentially all of the cost.** This is a known, structural property of running recurrent nets on CPU (no fused backward kernel equivalent to cuDNN's GPU RNN kernels), not a bug in this implementation or something a config tweak fixes (already confirmed: `torch.get_num_threads()` = 14, already using all physical cores).
- Extrapolated to the full training set (25,380 files, batch 32, ≈793 batches/epoch): **≈26.7 hours per epoch.**
- `configs/rawnet2.yaml` specifies 100 epochs: **≈111 days of continuous compute** for the configured schedule — not counting dev-set evaluation time each epoch, which adds more.
- No GPU is available in this environment (`torch.cuda.is_available()` = False; no MPS on this Windows machine) — there is no cheaper path to real training here.
- Even the "cheap" subset-scale ablation protocol used throughout this project's LCNN work (2,000 train / 1,000 dev, 8 epochs) is **not cheap for RawNet2 on this hardware**: at the measured per-batch rate, 2,000 files ≈ 62.5 batches/epoch × 121.3s ≈ 2.1 hours/epoch × 8 epochs ≈ **~17 hours** just for a directional smoke signal — three orders of magnitude more expensive than the equivalent LCNN subset ablations (~65s/epoch, ~9 minutes total), which is why none of the LCNN-style rapid ablation methodology can be reused as-is for RawNet2 on this machine.

This is a hard, empirically-measured constraint independent of how promising the architecture is. Even in the best case where RawNet2 would perfectly fix every weak attack, this hardware cannot get there in a timeframe that's actionable.

### What would change this decision

- **GPU access** (even a modest consumer GPU or a cheap cloud instance) — cuDNN's fused RNN kernels specifically target the exact bottleneck identified above (GRU backward), so a 20-50x+ speedup is a reasonable expectation for this workload, which would bring the full 100-epoch schedule from ~111 days to a plausible ~2-5 days, and the subset smoke test from ~17 hours to minutes.
- Given that, the contingent plan in `RawNet2_Training_Plan.md` (fix the identified code gaps → cheap correctness smoke test → subset-scale ablation identical in spirit to the LCNN work → full run only if the subset signal is positive → integrate only if it beats LCNN) is what to execute once GPU compute is confirmed.

### What was NOT done

- No RawNet2 training was started, full-scale or subset-scale.
- No project files were modified — `src/models/rawnet2.py`, `scripts/train_rawnet2.py`, `scripts/evaluate_rawnet2.py`, `configs/rawnet2.yaml` are unchanged. The code gaps identified (seed, CSV logging, resume, imbalance strategy, stale hardcoded comparison numbers) are documented as findings, not fixed, per the instruction not to modify project files during this audit.
- Only the four requested report files were created, all new, under `training/`.
