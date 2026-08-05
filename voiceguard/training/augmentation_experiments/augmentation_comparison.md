# Waveform-Domain Augmentation Ablation (subset-scale)

Methodology: identical seed/init (42), identical stratified train/dev subset (2000/1000), identical 8-epoch budget, weighted_sampler imbalance handling held constant (already validated separately). Each variant changes only the train-time waveform augmentation. All 4 checkpoints evaluated on the SAME fixed stratified subset of the real eval split (3000 files: 400 bonafide + 200/attack across A07-A19), never seen during training.

## Overall (eval subset, unseen attacks A07-A19)

| Variant | Dev EER | Eval-subset EER | Balanced Acc | ROC-AUC | F1 | Recall | Weak-attack mean EER (A10/A12/A13/A15/A17/A18) | Weak EER change vs baseline |
|---|---|---|---|---|---|---|---|---|
| baseline | 0.0870 | 0.3108 | 0.7001 | 0.7599 | 0.7378 | 0.6027 | 0.4500 |  |
| noise | 0.4735 | 0.5109 | 0.5000 | 0.4474 | 0.9286 | 1.0000 | 0.5161 | +0.0661 |
| channel | 0.1748 | 0.3123 | 0.6896 | 0.7622 | 0.7778 | 0.6642 | 0.3988 | -0.0512 |
| noise_channel | 0.4272 | 0.4475 | 0.5000 | 0.5833 | 0.9286 | 1.0000 | 0.4662 | +0.0163 |

## Per-attack EER (eval subset)

| Attack | baseline | noise | channel | noise_channel |
|---|---|---|---|---|
| A07 | 0.0475 | 0.4692 | 0.2000 | 0.4225 |
| A08 | 0.0200 | 0.5956 | 0.0500 | 0.4100 |
| A09 | 0.1800 | 0.5441 | 0.1200 | 0.4200 |
| A10 **(weak)** | 0.4150 | 0.5570 | 0.4200 | 0.4950 |
| A11 | 0.3500 | 0.5017 | 0.3350 | 0.5000 |
| A12 **(weak)** | 0.5950 | 0.5388 | 0.4700 | 0.4725 |
| A13 **(weak)** | 0.6275 | 0.5050 | 0.5150 | 0.4100 |
| A14 | 0.1975 | 0.4590 | 0.1700 | 0.3350 |
| A15 **(weak)** | 0.3850 | 0.5225 | 0.2150 | 0.4250 |
| A16 | 0.0950 | 0.5692 | 0.2300 | 0.4500 |
| A17 **(weak)** | 0.3750 | 0.4883 | 0.3825 | 0.4750 |
| A18 **(weak)** | 0.3025 | 0.4850 | 0.3900 | 0.5200 |
| A19 | 0.1050 | 0.4489 | 0.3250 | 0.4550 |
| nan | nan | nan | nan | nan |

**Best variant by eval-subset EER: `baseline`** (0.3108 vs baseline 0.3108, no improvement of +0.0000).
