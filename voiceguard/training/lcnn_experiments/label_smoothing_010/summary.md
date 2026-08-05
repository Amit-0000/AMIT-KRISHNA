# Experiment: label_smoothing_010

variable_changed: label_smoothing=0.10

| Metric | Baseline | label_smoothing_010 | Delta |
|---|---|---|---|
| Dev EER | 0.0870 | 0.1126 | +0.0256 |
| Eval-subset EER | 0.3108 | 0.3004 | -0.0104 |
| Balanced Accuracy | 0.7001 | 0.7086 | +0.0085 |
| ROC-AUC | 0.7599 | 0.7676 | +0.0078 |
| F1 | 0.7378 | 0.7807 | +0.0429 |
| Recall | 0.6027 | 0.6646 | +0.0619 |
| PR-AUC | n/a | 0.9581 | n/a |
| Weak-attack mean EER | 0.4500 | 0.4346 | -0.0154 |

## Per-attack EER

| Attack | EER |
|---|---|
| A07 | 0.0650 |
| A08 | 0.0350 |
| A09 | 0.1625 |
| A10 (weak) | 0.4000 |
| A11 | 0.3175 |
| A12 (weak) | 0.5650 |
| A13 (weak) | 0.5900 |
| A14 | 0.2000 |
| A15 (weak) | 0.3550 |
| A16 | 0.1200 |
| A17 (weak) | 0.3625 |
| A18 (weak) | 0.3350 |
| A19 | 0.1200 |
| nan | nan |

Outcome: **no_improvement**
