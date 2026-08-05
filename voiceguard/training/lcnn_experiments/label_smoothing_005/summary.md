# Experiment: label_smoothing_005

variable_changed: label_smoothing=0.05

| Metric | Baseline | label_smoothing_005 | Delta |
|---|---|---|---|
| Dev EER | 0.0870 | 0.1068 | +0.0198 |
| Eval-subset EER | 0.3108 | 0.3081 | -0.0027 |
| Balanced Accuracy | 0.7001 | 0.7084 | +0.0083 |
| ROC-AUC | 0.7599 | 0.7646 | +0.0048 |
| F1 | 0.7378 | 0.7640 | +0.0262 |
| Recall | 0.6027 | 0.6392 | +0.0365 |
| PR-AUC | n/a | 0.9576 | n/a |
| Weak-attack mean EER | 0.4500 | 0.4475 | -0.0025 |

## Per-attack EER

| Attack | EER |
|---|---|
| A07 | 0.0650 |
| A08 | 0.0275 |
| A09 | 0.1675 |
| A10 (weak) | 0.4050 |
| A11 | 0.3200 |
| A12 (weak) | 0.5800 |
| A13 (weak) | 0.6000 |
| A14 | 0.1900 |
| A15 (weak) | 0.3800 |
| A16 | 0.1050 |
| A17 (weak) | 0.3750 |
| A18 (weak) | 0.3450 |
| A19 | 0.1150 |
| nan | nan |

Outcome: **no_improvement**
