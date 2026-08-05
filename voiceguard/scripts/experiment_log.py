"""Shared append-only experiment log — training/Experiment_Log.csv (source of
truth) + training/Experiment_Log.xlsx (regenerated from the CSV on every
append). One row per experiment, across the whole LCNN improvement project
(class-imbalance ablation, augmentation ablation, and everything after),
so there is a single place that answers "what has already been tried."
Never overwrites a previous row — always appends.
"""
from pathlib import Path

import pandas as pd

LOG_CSV = Path("training") / "Experiment_Log.csv"
LOG_XLSX = Path("training") / "Experiment_Log.xlsx"

COLUMNS = [
    "experiment_id", "phase", "dataset_scale", "train_n", "dev_n", "eval_n",
    "epochs", "seed", "variable_changed", "dev_eer", "eval_eer",
    "balanced_accuracy", "roc_auc", "precision", "recall", "f1", "pr_auc",
    "weak_attack_mean_eer", "avg_epoch_time_seconds", "outcome", "notes",
]


def append_experiment_log(row: dict) -> None:
    """row may omit columns (e.g. metrics that predate a given protocol
    version) — missing ones are written as blank, not fabricated."""
    full_row = {col: row.get(col, "") for col in COLUMNS}

    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_CSV.exists()
    df_row = pd.DataFrame([full_row], columns=COLUMNS)
    df_row.to_csv(LOG_CSV, mode="a", header=write_header, index=False)

    full_df = pd.read_csv(LOG_CSV)
    full_df.to_excel(LOG_XLSX, sheet_name="experiments", index=False)
