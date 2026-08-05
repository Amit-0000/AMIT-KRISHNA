# Class Imbalance Strategy Comparison

Methodology: identical seed/init (42), identical stratified subset (2000 train / 1000 dev, preserving the dataset's ~10:90 bonafide:spoof ratio), identical 8-epoch budget, no early stopping within this ablation. Winner selected by lowest dev EER at its best epoch — the same selection criterion used for the full training run, and the metric immune to this dataset's class imbalance (docs/02_dataset.md §8).

| Strategy | Best epoch | Dev EER | Dev Accuracy | Dev Precision | Dev Recall | Dev F1 | Dev ROC-AUC |
|---|---|---|---|---|---|---|---|
| standard_ce | 8 | 0.2330 | 0.8970 | 0.8970 | 1.0000 | 0.9457 | 0.8362 |
| weighted_ce | 6 | 0.2718 | 0.7210 | 0.9612 | 0.7179 | 0.8220 | 0.7888 |
| weighted_sampler **<- winner** | 8 | 0.0870 | 0.9300 | 0.9825 | 0.9387 | 0.9601 | 0.9716 |

**Winner: `weighted_sampler`** (lowest dev EER: 0.0870) — used for the full training run.
