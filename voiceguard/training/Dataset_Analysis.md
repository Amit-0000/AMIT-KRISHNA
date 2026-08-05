# ASVspoof2019 LA — Dataset Analysis (LCNN Training Run)

## Split sizes and class balance

| Split | Total files | Bonafide | Spoof | Bonafide % | Spoof % | Spoof:Bonafide ratio |
|---|---|---|---|---|---|---|
| train | 25,380 | 2,580 | 22,800 | 10.17% | 89.83% | 8.84:1 |
| dev | 24,844 | 2,548 | 22,296 | 10.26% | 89.74% | 8.75:1 |
| eval | 71,237 | 7,355 | 63,882 | 10.32% | 89.68% | 8.69:1 |

All three splits carry essentially the same ~9:1 spoof:bonafide imbalance — this is what motivated the empirical class-imbalance ablation (`training/imbalance_experiments/`) before the full training run. See [class_imbalance_comparison.md](imbalance_experiments/class_imbalance_comparison.md): `WeightedRandomSampler` won decisively (dev EER 0.087 vs 0.233 standard CE vs 0.272 weighted CE on the ablation subset) and was used for the full run.

## Attack-type composition — the critical structural fact

| Split | Attack types present |
|---|---|
| train | A01, A02, A03, A04, A05, A06 |
| dev | A01, A02, A03, A04, A05, A06 |
| eval | A07, A08, A09, A10, A11, A12, A13, A14, A15, A16, A17, A18, A19 |

**Train and dev share exactly the same 6 attack algorithms (A01–A06). The eval split's 13 attack algorithms (A07–A19) are entirely disjoint from train/dev — zero overlap.** This is ASVspoof2019 LA's designed generalization challenge, not a data-preparation artifact.

Practical consequence for this training run: dev-set metrics (used for checkpoint selection and early stopping) measure how well the model fits the *training-time attack family* (A01–A06), not how well it generalizes to unseen spoofing methods. The near-zero dev EER achieved by epoch 18 (0.0135%) reflects this — it is a legitimate measurement of in-distribution fit, not a generalization estimate. The eval-split EER (22.83%) is the only number in this run that measures true generalization to novel attacks, and is the one that should be trusted for production-readiness judgments.

Per-attack eval EER (see `Benchmark_Results.xlsx`) shows this isn't uniform: near-perfect on A07–A09/A14/A16/A19 (0.02–0.5%), but 23–54% EER on A10/A12/A13/A15/A17/A18. Per the ASVspoof2019 challenge documentation, A10–A13 and A16–A19 include voice-conversion-based spoofing (as opposed to the TTS-based attacks the model handles well) — the model's weakness clusters specifically around the VC attack family, consistent with it not having seen any VC-style spoofing during training (A01–A06 are TTS-only).

## Preprocessing applied

Every file in every split was processed identically at both training and evaluation time via `src.data.dataset.serving_equivalent_preprocess` (peak-amplitude normalization → RMS-based silence trim → fixed-length pad/truncate to 64,000 samples / 4s @ 16kHz) — the same steps the live inference pipeline (`api.inference.preprocessing.run_preprocessing`) applies, closing the train/serve mismatch identified in this session's Phase 4 audit.

## Integrity

Full-dataset audit (`asvspoof_dataset_report.md`, `asvspoof_manifest.csv`, 121,461 files): 0 missing, 0 corrupted, 0 duplicates, all 16kHz mono, split counts matching the official protocol files exactly.
