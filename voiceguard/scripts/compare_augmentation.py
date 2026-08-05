"""Waveform-domain augmentation ablation for LCNN cross-attack generalization.

Motivation (see training/LCNN_Training_Report.md and the per-attack EER
breakdown in training/Benchmark_Results.xlsx): the deployed LCNN checkpoint
gets dev EER 0.0135% (attacks A01-A06, seen at train time) but eval EER
22.83% (attacks A07-A19, entirely unseen). The failure is concentrated on
6 of 13 unseen attacks (A10, A12, A13, A15, A17, A18 — 17-54% EER) while
attacks from the same synthesis family as a training attack (A16, waveform
concat like A04; A19, spectral-filtering VC like A06) are near-perfect
(<1%). That pattern — good on familiar synthesis families, bad on novel
ones — is the classic signature of a model keying on training-attack-
specific artifacts rather than general spoofing cues, and is exactly what
waveform-domain augmentation (RawBoost-style noise/channel perturbation) is
reported to address in the anti-spoofing literature (ASVspoof2021 baselines).

This script tests that hypothesis cheaply, before committing to a full
6-hour run: 4 variants, one train-time waveform-augmentation change each,
identical everything else (seed, stratified subset, epoch budget, the
already-validated weighted_sampler imbalance strategy — see
training/imbalance_experiments/class_imbalance_comparison.md, not re-litigated
here). Each variant's best-dev-EER checkpoint is then evaluated on a FIXED
stratified subset of the real eval split (A07-A19, disjoint from train/dev)
to measure the thing that actually matters: unseen-attack generalization,
with per-attack EER broken out for the known-weak attacks.

Variants:
  baseline       - SpecAugment only (matches current production training)
  noise          - + additive Gaussian noise (random SNR)
  channel        - + random FIR channel-response perturbation
  noise_channel  - both combined

Decision rule (per the task instruction): only proceed to a full 28-epoch
run on the complete training set if a variant shows a measurable
improvement, particularly on A10/A12/A13/A15/A17/A18.
"""
import json
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from src.data.augmentation import WaveformAugmentation
from src.data.dataset import load_waveform, serving_equivalent_preprocess
from src.data.protocol import parse_protocol
from src.data.transforms import MelSpectrogramTransform
from src.evaluation.eer import compute_eer_per_attack
from src.evaluation.metrics import compute_full_metrics
from src.models.lcnn import LCNN
from src.training.losses import compute_class_weights
from src.training.trainer import Trainer, set_seed

DATA_ROOT = Path("data")
PROTOCOLS = DATA_ROOT / "ASVspoof2019_LA_cm_protocols"
OUT_DIR = Path("training") / "augmentation_experiments"
SEED = 42
EPOCHS = 8
TRAIN_SUBSET_N = 2000
DEV_SUBSET_N = 1000
EVAL_BONAFIDE_N = 400
EVAL_PER_ATTACK_N = 200
BATCH_SIZE = 32
LR = 1e-4
WEIGHT_DECAY = 1e-4
WEAK_ATTACKS = {"A10", "A12", "A13", "A15", "A17", "A18"}  # from the existing per-attack audit

VARIANTS = {
    "baseline": dict(use_noise=False, use_channel=False),
    "noise": dict(use_noise=True, use_channel=False),
    "channel": dict(use_noise=False, use_channel=True),
    "noise_channel": dict(use_noise=True, use_channel=True),
}


def stratified_subset(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    frac_bonafide = (df["label"] == "bonafide").mean()
    n_bonafide = max(1, int(round(n * frac_bonafide)))
    n_spoof = n - n_bonafide
    bonafide = df[df["label"] == "bonafide"].sample(n=min(n_bonafide, (df["label"] == "bonafide").sum()), random_state=seed)
    spoof = df[df["label"] == "spoof"].sample(n=min(n_spoof, (df["label"] == "spoof").sum()), random_state=seed)
    return pd.concat([bonafide, spoof], ignore_index=True)


def attack_stratified_eval_subset(df_eval: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Fixed subset used identically for every variant: EVAL_BONAFIDE_N
    bonafide + EVAL_PER_ATTACK_N per attack type (A07-A19), so per-attack
    EER is comparable across variants and reasonably stable (n=200/attack
    rather than n=1-2 from a naive random sample)."""
    bonafide = df_eval[df_eval["label"] == "bonafide"].sample(n=EVAL_BONAFIDE_N, random_state=seed)
    parts = [bonafide]
    for attack in sorted(df_eval["attack_type"].dropna().unique()):
        pool = df_eval[df_eval["attack_type"] == attack]
        parts.append(pool.sample(n=min(EVAL_PER_ATTACK_N, len(pool)), random_state=seed))
    return pd.concat(parts, ignore_index=True)


class AugmentedASVspoofDataset(Dataset):
    """Mirrors src.data.dataset.ASVspoofDataset (same loading + serving-
    equivalent preprocessing) but inserts an optional waveform augmentation
    stage between preprocessing and the mel transform. Ablation-only — does
    not touch the production dataset class."""

    def __init__(self, df: pd.DataFrame, mel_transform, waveform_aug=None):
        self.df = df.reset_index(drop=True)
        self.mel_transform = mel_transform
        self.waveform_aug = waveform_aug

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        waveform = load_waveform(row["file_path"])
        waveform = serving_equivalent_preprocess(waveform)
        if self.waveform_aug is not None:
            waveform = self.waveform_aug(waveform)
        features = self.mel_transform(waveform)
        label = {"bonafide": 0, "spoof": 1}[row["label"]]
        return features, label


def build_train_loader(df_train: pd.DataFrame, use_noise: bool, use_channel: bool) -> DataLoader:
    aug = WaveformAugmentation(use_noise=use_noise, use_channel=use_channel)
    train_ds = AugmentedASVspoofDataset(df_train, MelSpectrogramTransform(augment=True), waveform_aug=aug)

    # weighted_sampler held constant across all 4 variants — already the
    # empirically-validated imbalance strategy, not the variable under test here.
    class_weights = compute_class_weights(df_train)
    label_to_idx = {"bonafide": 0, "spoof": 1}
    sample_weights = df_train["label"].map(lambda l: class_weights[label_to_idx[l]]).tolist()
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(df_train), replacement=True)
    return DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=4, pin_memory=True)


def evaluate_on_eval_subset(model: LCNN, df_eval_subset: pd.DataFrame, device: torch.device) -> dict:
    eval_ds = AugmentedASVspoofDataset(df_eval_subset, MelSpectrogramTransform(augment=False), waveform_aug=None)
    loader = DataLoader(eval_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model.eval()
    all_scores, all_labels, all_preds = [], [], []
    with torch.no_grad():
        for x, labels in loader:
            x = x.to(device)
            logits = model(x)
            scores = torch.softmax(logits, dim=1)[:, 1]
            preds = logits.argmax(dim=1)
            all_scores.extend(scores.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_preds.extend(preds.cpu().tolist())

    metrics = compute_full_metrics(all_labels, all_preds, all_scores)
    per_attack = compute_eer_per_attack(all_labels, all_scores, df_eval_subset["attack_type"].tolist())
    metrics["per_attack_eer"] = {k: v for k, v in per_attack.items() if k != "overall"}
    return metrics


def main():
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    print(f"Using device: {device}")

    df_train_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.train.trn.txt", DATA_ROOT / "ASVspoof2019_LA_train" / "flac")
    df_dev_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.dev.trl.txt", DATA_ROOT / "ASVspoof2019_LA_dev" / "flac")
    df_eval_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.eval.trl.txt", DATA_ROOT / "ASVspoof2019_LA_eval" / "flac")

    df_train = stratified_subset(df_train_full, TRAIN_SUBSET_N, SEED)
    df_dev = stratified_subset(df_dev_full, DEV_SUBSET_N, SEED)
    df_eval_subset = attack_stratified_eval_subset(df_eval_full, SEED)
    print(f"Train subset: {len(df_train)} | Dev subset: {len(df_dev)} | Eval subset: {len(df_eval_subset)} "
          f"({EVAL_BONAFIDE_N} bonafide + {EVAL_PER_ATTACK_N}/attack x 13 attacks)")

    dev_ds = AugmentedASVspoofDataset(df_dev, MelSpectrogramTransform(augment=False), waveform_aug=None)
    dev_loader = DataLoader(dev_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    results = {}
    for variant, flags in VARIANTS.items():
        print(f"\n{'='*70}\nVariant: {variant}  ({flags})\n{'='*70}")
        set_seed(SEED)  # identical init across variants for a fair comparison
        model = LCNN()
        optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
        train_loader = build_train_loader(df_train, **flags)

        variant_dir = OUT_DIR / variant
        trainer = Trainer(
            model=model, optimizer=optimizer, scheduler=scheduler,
            criterion=torch.nn.CrossEntropyLoss(), device=device,
            checkpoint_dir=str(variant_dir / "checkpoints"), log_dir=str(variant_dir / "runs"),
            patience=EPOCHS + 1,  # no early stopping within this short ablation
            metrics_csv_path=variant_dir / "training_log.csv",
        )
        trainer.fit(train_loader, dev_loader, epochs=EPOCHS)

        log_df = pd.read_csv(variant_dir / "training_log.csv")
        best_row = log_df.loc[log_df["dev_eer"].astype(float).idxmin()]

        # Reload the best checkpoint (not necessarily the last epoch) before eval-subset scoring.
        best_model = LCNN()
        best_model.load_state_dict(torch.load(variant_dir / "checkpoints" / "best.pt", map_location=device, weights_only=True))
        best_model = best_model.to(device)
        eval_metrics = evaluate_on_eval_subset(best_model, df_eval_subset, device)

        results[variant] = {
            "dev_best_epoch": int(best_row["epoch"]),
            "dev_eer": float(best_row["dev_eer"]),
            "dev_accuracy": float(best_row["dev_accuracy"]),
            "dev_f1": float(best_row["dev_f1"]),
            "dev_roc_auc": float(best_row["dev_roc_auc"]) if best_row["dev_roc_auc"] != "nan" else None,
            "eval_subset_eer": eval_metrics["eer"],
            "eval_subset_balanced_accuracy": eval_metrics["balanced_accuracy"],
            "eval_subset_roc_auc": eval_metrics["roc_auc"],
            "eval_subset_f1": eval_metrics["f1"],
            "eval_subset_recall": eval_metrics["recall"],
            "eval_subset_per_attack_eer": eval_metrics["per_attack_eer"],
        }
        weak_mean = sum(eval_metrics["per_attack_eer"].get(a, float("nan")) for a in WEAK_ATTACKS) / len(WEAK_ATTACKS)
        results[variant]["eval_subset_weak_attack_mean_eer"] = weak_mean
        print(f"{variant}: dev_eer={results[variant]['dev_eer']:.4f} | eval_subset_eer={eval_metrics['eer']:.4f} "
              f"| weak-attack mean EER={weak_mean:.4f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump({
            "results": results,
            "config": {
                "seed": SEED, "epochs": EPOCHS, "train_subset_n": len(df_train), "dev_subset_n": len(df_dev),
                "eval_subset_n": len(df_eval_subset), "eval_bonafide_n": EVAL_BONAFIDE_N,
                "eval_per_attack_n": EVAL_PER_ATTACK_N, "batch_size": BATCH_SIZE, "lr": LR,
                "weight_decay": WEIGHT_DECAY, "class_imbalance_strategy": "weighted_sampler",
            },
        }, f, indent=2)

    baseline_eval_eer = results["baseline"]["eval_subset_eer"]
    baseline_weak_eer = results["baseline"]["eval_subset_weak_attack_mean_eer"]

    lines = ["# Waveform-Domain Augmentation Ablation (subset-scale)\n"]
    lines.append(f"Methodology: identical seed/init ({SEED}), identical stratified train/dev subset "
                 f"({len(df_train)}/{len(df_dev)}), identical {EPOCHS}-epoch budget, weighted_sampler "
                 f"imbalance handling held constant (already validated separately). Each variant changes "
                 f"only the train-time waveform augmentation. All 4 checkpoints evaluated on the SAME "
                 f"fixed stratified subset of the real eval split ({len(df_eval_subset)} files: "
                 f"{EVAL_BONAFIDE_N} bonafide + {EVAL_PER_ATTACK_N}/attack across A07-A19), never seen "
                 f"during training.\n")
    lines.append("## Overall (eval subset, unseen attacks A07-A19)\n")
    lines.append("| Variant | Dev EER | Eval-subset EER | Balanced Acc | ROC-AUC | F1 | Recall | Weak-attack mean EER (A10/A12/A13/A15/A17/A18) | Weak EER change vs baseline |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for variant, r in results.items():
        delta = r["eval_subset_weak_attack_mean_eer"] - baseline_weak_eer
        marker = "" if variant == "baseline" else f"{delta:+.4f}"
        lines.append(
            f"| {variant} | {r['dev_eer']:.4f} | {r['eval_subset_eer']:.4f} | {r['eval_subset_balanced_accuracy']:.4f} | "
            f"{r['eval_subset_roc_auc']:.4f} | {r['eval_subset_f1']:.4f} | {r['eval_subset_recall']:.4f} | "
            f"{r['eval_subset_weak_attack_mean_eer']:.4f} | {marker} |"
        )

    lines.append("\n## Per-attack EER (eval subset)\n")
    all_attacks = sorted(a for a in next(iter(results.values()))["eval_subset_per_attack_eer"].keys() if isinstance(a, str))
    lines.append("| Attack | " + " | ".join(results.keys()) + " |")
    lines.append("|---|" + "---|" * len(results))
    for attack in all_attacks:
        flag = " **(weak)**" if attack in WEAK_ATTACKS else ""
        row = [f"{results[v]['eval_subset_per_attack_eer'].get(attack, float('nan')):.4f}" for v in results]
        lines.append(f"| {attack}{flag} | " + " | ".join(row) + " |")

    best_variant = min(results, key=lambda v: results[v]["eval_subset_eer"])
    improvement = baseline_eval_eer - results[best_variant]["eval_subset_eer"]
    lines.append(f"\n**Best variant by eval-subset EER: `{best_variant}`** "
                 f"({results[best_variant]['eval_subset_eer']:.4f} vs baseline {baseline_eval_eer:.4f}, "
                 f"{'improvement' if improvement > 0 else 'no improvement'} of {improvement:+.4f}).\n")
    (OUT_DIR / "augmentation_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "\n".join(lines))
    print(f"\nWROTE: {OUT_DIR/'augmentation_comparison.md'}, {OUT_DIR/'results.json'}")


if __name__ == "__main__":
    main()
