# Experiment: ema

variable_changed: EMA(decay=0.999, warmup)

| Metric | Baseline | ema | Delta |
|---|---|---|---|
| Dev EER | 0.0870 | 0.1059 | +0.0190 |
| Eval-subset EER | 0.3108 | 0.3046 | -0.0062 |
| Balanced Accuracy | 0.7001 | 0.7129 | +0.0128 |
| ROC-AUC | 0.7599 | 0.7680 | +0.0082 |
| F1 | 0.7378 | 0.7275 | -0.0103 |
| Recall | 0.6027 | 0.5858 | -0.0170 |
| PR-AUC | n/a | 0.9587 | n/a |
| Weak-attack mean EER | 0.4500 | 0.4421 | -0.0079 |

## Per-attack EER

| Attack | EER |
|---|---|
| A07 | 0.0550 |
| A08 | 0.0150 |
| A09 | 0.1650 |
| A10 (weak) | 0.4000 |
| A11 | 0.3400 |
| A12 (weak) | 0.5500 |
| A13 (weak) | 0.5850 |
| A14 | 0.1775 |
| A15 (weak) | 0.3850 |
| A16 | 0.0975 |
| A17 (weak) | 0.3875 |
| A18 (weak) | 0.3450 |
| A19 | 0.1050 |
| nan | nan |

Outcome: **no_improvement**
