"""Empirical comparison of class-imbalance handling strategies for LCNN on
ASVspoof2019 LA (bonafide:spoof ~ 1:9). Per the task's explicit instruction
not to assume weighting is beneficial, this runs all three strategies —
standard (unweighted) CrossEntropyLoss, inverse-frequency-weighted
CrossEntropyLoss, and a WeightedRandomSampler with standard CrossEntropyLoss —
under identical conditions (same seed/init, same subset, same epoch budget)
and picks whichever gets the lowest dev EER, the model-selection metric
already used everywhere else in this codebase because it's immune to this
exact class imbalance (docs/02_dataset.md §8).

Runs on a stratified subset (not the full 121k-file dataset) to keep this
ablation fast; the winning strategy is then used for the full training run.
"""
import json
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

from src.data.protocol import parse_protocol
from src.data.dataset import ASVspoofDataset
from src.data.transforms import MelSpectrogramTransform
from src.models.lcnn import LCNN
from src.training.losses import build_loss, compute_class_weights
from src.training.trainer import Trainer, set_seed

DATA_ROOT = Path("data")
PROTOCOLS = DATA_ROOT / "ASVspoof2019_LA_cm_protocols"
OUT_DIR = Path("training") / "imbalance_experiments"
SEED = 42
EPOCHS = 8
TRAIN_SUBSET_N = 2000
DEV_SUBSET_N = 1000
BATCH_SIZE = 32
LR = 1e-4
WEIGHT_DECAY = 1e-4


def stratified_subset(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    frac_bonafide = (df["label"] == "bonafide").mean()
    n_bonafide = max(1, int(round(n * frac_bonafide)))
    n_spoof = n - n_bonafide
    bonafide = df[df["label"] == "bonafide"].sample(n=min(n_bonafide, (df["label"] == "bonafide").sum()), random_state=seed)
    spoof = df[df["label"] == "spoof"].sample(n=min(n_spoof, (df["label"] == "spoof").sum()), random_state=seed)
    return pd.concat([bonafide, spoof], ignore_index=True)


def build_run(strategy: str, df_train: pd.DataFrame, device: torch.device):
    set_seed(SEED)  # identical init across strategies for a fair comparison
    model = LCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    train_ds = ASVspoofDataset(df_train, transform=MelSpectrogramTransform(augment=True))

    if strategy == "standard_ce":
        criterion = torch.nn.CrossEntropyLoss()
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True)
    elif strategy == "weighted_ce":
        criterion = build_loss(df_train, device)
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True)
    elif strategy == "weighted_sampler":
        criterion = torch.nn.CrossEntropyLoss()
        class_weights = compute_class_weights(df_train)  # [w_bonafide, w_spoof]
        label_to_idx = {"bonafide": 0, "spoof": 1}
        sample_weights = df_train["label"].map(lambda l: class_weights[label_to_idx[l]]).tolist()
        sampler = WeightedRandomSampler(sample_weights, num_samples=len(df_train), replacement=True)
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=4, pin_memory=True)
    else:
        raise ValueError(strategy)

    return model, optimizer, scheduler, criterion, train_loader


def main():
    device = torch.device("cpu")
    if torch.cuda.is_available():
        device = torch.device("cuda")

    df_train_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.train.trn.txt", DATA_ROOT / "ASVspoof2019_LA_train" / "flac")
    df_dev_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.dev.trl.txt", DATA_ROOT / "ASVspoof2019_LA_dev" / "flac")

    df_train = stratified_subset(df_train_full, TRAIN_SUBSET_N, SEED)
    df_dev = stratified_subset(df_dev_full, DEV_SUBSET_N, SEED)
    print(f"Train subset: {len(df_train)} ({(df_train['label']=='bonafide').sum()} bonafide / {(df_train['label']=='spoof').sum()} spoof)")
    print(f"Dev subset:   {len(df_dev)} ({(df_dev['label']=='bonafide').sum()} bonafide / {(df_dev['label']=='spoof').sum()} spoof)")

    dev_ds = ASVspoofDataset(df_dev, transform=MelSpectrogramTransform(augment=False))
    dev_loader = DataLoader(dev_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    results = {}
    for strategy in ["standard_ce", "weighted_ce", "weighted_sampler"]:
        print(f"\n{'='*60}\nStrategy: {strategy}\n{'='*60}")
        model, optimizer, scheduler, criterion, train_loader = build_run(strategy, df_train, device)
        strategy_dir = OUT_DIR / strategy
        trainer = Trainer(
            model=model, optimizer=optimizer, scheduler=scheduler, criterion=criterion, device=device,
            checkpoint_dir=str(strategy_dir / "checkpoints"), log_dir=str(strategy_dir / "runs"),
            patience=EPOCHS + 1,  # no early stopping within this short ablation — run the full budget
            metrics_csv_path=strategy_dir / "training_log.csv",
        )
        trainer.fit(train_loader, dev_loader, epochs=EPOCHS)

        # Balanced accuracy at the best epoch = (recall_bonafide + recall_spoof) / 2.
        # last_epoch_metrics only has the *last* epoch's precision/recall; re-derive
        # balanced accuracy at the best epoch from the CSV we just wrote.
        log_df = pd.read_csv(strategy_dir / "training_log.csv")
        best_row = log_df.loc[log_df["dev_eer"].astype(float).idxmin()]
        # recall (sensitivity, spoof) is dev_recall; specificity (bonafide) isn't
        # logged per-epoch, so approximate balanced accuracy from accuracy+recall
        # is not exact — report accuracy/recall/f1/eer directly instead, which are
        # both logged and sufficient to rank strategies unambiguously here.
        results[strategy] = {
            "best_epoch": int(best_row["epoch"]),
            "best_dev_eer": float(best_row["dev_eer"]),
            "dev_accuracy_at_best": float(best_row["dev_accuracy"]),
            "dev_precision_at_best": float(best_row["dev_precision"]),
            "dev_recall_at_best": float(best_row["dev_recall"]),
            "dev_f1_at_best": float(best_row["dev_f1"]),
            "dev_roc_auc_at_best": float(best_row["dev_roc_auc"]) if best_row["dev_roc_auc"] != "nan" else None,
        }
        print(f"{strategy}: best dev EER={results[strategy]['best_dev_eer']:.4f} at epoch {results[strategy]['best_epoch']}")

    winner = min(results, key=lambda s: results[s]["best_dev_eer"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump({"results": results, "winner": winner, "config": {
            "seed": SEED, "epochs": EPOCHS, "train_subset_n": len(df_train), "dev_subset_n": len(df_dev),
            "batch_size": BATCH_SIZE, "lr": LR, "weight_decay": WEIGHT_DECAY,
        }}, f, indent=2)

    # Human-readable report
    lines = ["# Class Imbalance Strategy Comparison\n"]
    lines.append(f"Methodology: identical seed/init ({SEED}), identical stratified subset "
                 f"({len(df_train)} train / {len(df_dev)} dev, preserving the dataset's ~10:90 "
                 f"bonafide:spoof ratio), identical {EPOCHS}-epoch budget, no early stopping within "
                 f"this ablation. Winner selected by lowest dev EER at its best epoch — the same "
                 f"selection criterion used for the full training run, and the metric immune to this "
                 f"dataset's class imbalance (docs/02_dataset.md §8).\n")
    lines.append("| Strategy | Best epoch | Dev EER | Dev Accuracy | Dev Precision | Dev Recall | Dev F1 | Dev ROC-AUC |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for strategy, r in results.items():
        marker = " **<- winner**" if strategy == winner else ""
        lines.append(f"| {strategy}{marker} | {r['best_epoch']} | {r['best_dev_eer']:.4f} | {r['dev_accuracy_at_best']:.4f} | "
                     f"{r['dev_precision_at_best']:.4f} | {r['dev_recall_at_best']:.4f} | {r['dev_f1_at_best']:.4f} | "
                     f"{r['dev_roc_auc_at_best']:.4f} |")
    lines.append(f"\n**Winner: `{winner}`** (lowest dev EER: {results[winner]['best_dev_eer']:.4f}) — "
                 f"used for the full training run.\n")
    (OUT_DIR / "class_imbalance_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "\n".join(lines))
    print(f"\nWROTE: {OUT_DIR/'class_imbalance_comparison.md'}, {OUT_DIR/'results.json'}")
    print(f"WINNER: {winner}")


if __name__ == "__main__":
    main()
