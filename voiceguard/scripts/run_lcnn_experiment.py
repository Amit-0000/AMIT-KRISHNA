"""General single-variant LCNN experiment runner — Phase 2 of the post-
augmentation-ablation reassessment (see training/lcnn_experiments/*).

Reuses, byte-for-byte, the subset methodology already established in
compare_augmentation.py: same seed (42), same stratified train/dev subset
(2000/1000), same weighted_sampler imbalance handling, same optimizer/
scheduler/LR/batch size, same fixed eval subset (3000 files, 400 bonafide +
200/attack across A07-A19) so every variant here is directly comparable to
the existing `augmentation_baseline` row in training/Experiment_Log.csv
without retraining that baseline.

One variable changes per run, selected via --variant:
  label_smoothing_005 - CrossEntropyLoss(label_smoothing=0.05)
  label_smoothing_010 - CrossEntropyLoss(label_smoothing=0.10)
  ema                 - Exponential Moving Average of weights (decay 0.999,
                         with a warmup schedule since 8 epochs / ~63 steps
                         each is short: decay_t = min(0.999, (1+t)/(10+t)))

Checkpoints: checkpoints/experiments/<variant>/{best.pt,last.pt} (never
touches checkpoints/best.pt or checkpoints/last.pt — the production files).
Logs: training/lcnn_experiments/<variant>/training_log.csv (+ runs/ for the
Trainer-based variants). Every run appends one row to
training/Experiment_Log.csv + .xlsx.
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import torch

from compare_augmentation import (
    BATCH_SIZE, DATA_ROOT, DEV_SUBSET_N, EPOCHS, EVAL_BONAFIDE_N, EVAL_PER_ATTACK_N,
    LR, PROTOCOLS, SEED, TRAIN_SUBSET_N, WEAK_ATTACKS, WEIGHT_DECAY,
    AugmentedASVspoofDataset, attack_stratified_eval_subset, build_train_loader,
    evaluate_on_eval_subset, stratified_subset,
)
from experiment_log import append_experiment_log
from src.data.protocol import parse_protocol
from src.data.transforms import MelSpectrogramTransform
from src.evaluation.metrics import compute_full_metrics
from src.models.lcnn import LCNN
from src.training.trainer import Trainer, set_seed
from torch.utils.data import DataLoader

CHECKPOINT_ROOT = Path("checkpoints") / "experiments"
LOG_ROOT = Path("training") / "lcnn_experiments"

BASELINE_ROW = {  # from training/augmentation_experiments/results.json — NOT recomputed
    "dev_eer": 0.086957,
    "eval_subset_eer": 0.310769,
    "eval_subset_balanced_accuracy": 0.700096,
    "eval_subset_roc_auc": 0.759861,
    "eval_subset_f1": 0.737762,
    "eval_subset_recall": 0.602740,
    "eval_subset_weak_attack_mean_eer": 0.450000,
}

VARIANTS = ["label_smoothing_005", "label_smoothing_010", "ema"]


def evaluate_dev(model: LCNN, dev_loader: DataLoader, device: torch.device) -> dict:
    model.eval()
    all_scores, all_labels, all_preds = [], [], []
    with torch.no_grad():
        for x, labels in dev_loader:
            x = x.to(device)
            logits = model(x)
            scores = torch.softmax(logits, dim=1)[:, 1]
            preds = logits.argmax(dim=1)
            all_scores.extend(scores.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_preds.extend(preds.cpu().tolist())
    return compute_full_metrics(all_labels, all_preds, all_scores)


class EMA:
    """Shadow-weight exponential moving average over the full state_dict
    (matches timm's ModelEmaV2 approach: float tensors are averaged,
    non-float buffers like BatchNorm's num_batches_tracked are copied)."""

    def __init__(self, model: torch.nn.Module, base_decay: float = 0.999):
        self.base_decay = base_decay
        self.shadow = {k: v.detach().clone() for k, v in model.state_dict().items()}
        self.n_steps = 0

    def update(self, model: torch.nn.Module) -> None:
        self.n_steps += 1
        decay = min(self.base_decay, (1 + self.n_steps) / (10 + self.n_steps))
        msd = model.state_dict()
        for k, shadow_v in self.shadow.items():
            new_v = msd[k].detach()
            if shadow_v.dtype.is_floating_point:
                shadow_v.mul_(decay).add_(new_v, alpha=1 - decay)
            else:
                self.shadow[k] = new_v.clone()

    def state_dict(self) -> dict:
        return self.shadow


def run_label_smoothing(epsilon: float, train_loader, dev_loader, device, out_dir: Path, ckpt_dir: Path):
    set_seed(SEED)
    model = LCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
    criterion = torch.nn.CrossEntropyLoss(label_smoothing=epsilon)

    trainer = Trainer(
        model=model, optimizer=optimizer, scheduler=scheduler, criterion=criterion, device=device,
        checkpoint_dir=str(ckpt_dir), log_dir=str(out_dir / "runs"),
        patience=EPOCHS + 1, metrics_csv_path=out_dir / "training_log.csv",
    )
    trainer.fit(train_loader, dev_loader, epochs=EPOCHS)
    return trainer.best_eer, trainer.best_epoch


def run_ema(train_loader, dev_loader, device, out_dir: Path, ckpt_dir: Path):
    set_seed(SEED)
    model = LCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
    criterion = torch.nn.CrossEntropyLoss()
    ema = EMA(model, base_decay=0.999)
    eval_model = LCNN().to(device)  # scratch model scored against the EMA shadow weights each epoch

    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_rows = []
    best_eer, best_epoch = float("inf"), None

    for epoch in range(1, EPOCHS + 1):
        started = time.perf_counter()
        model.train()
        total_loss = 0.0
        for x, labels in train_loader:
            x, labels = x.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            ema.update(model)
            total_loss += loss.item()
        train_loss = total_loss / len(train_loader)
        scheduler.step()

        eval_model.load_state_dict(ema.state_dict())
        dev_metrics = evaluate_dev(eval_model, dev_loader, device)
        epoch_time = time.perf_counter() - started
        lr = optimizer.param_groups[0]["lr"]

        print(f"Epoch {epoch:3d} | train_loss {train_loss:.4f} | dev_EER(EMA) {dev_metrics['eer']:.4f} "
              f"| acc {dev_metrics['accuracy']:.4f} | f1 {dev_metrics['f1']:.4f} | auc {dev_metrics['roc_auc']:.4f} "
              f"| lr {lr:.2e} | {epoch_time:.1f}s")

        checkpoint_saved = False
        if dev_metrics["eer"] == dev_metrics["eer"] and dev_metrics["eer"] < best_eer:
            best_eer, best_epoch = dev_metrics["eer"], epoch
            torch.save(ema.state_dict(), ckpt_dir / "best.pt")
            checkpoint_saved = True
            print(f"           -> new best EER (EMA): {dev_metrics['eer']:.4f} — checkpoint saved")

        torch.save(
            {"epoch": epoch, "model_state_dict": model.state_dict(), "ema_state_dict": ema.state_dict()},
            ckpt_dir / "last.pt",
        )

        log_rows.append({
            "epoch": epoch, "train_loss": round(train_loss, 6),
            "dev_accuracy": round(dev_metrics["accuracy"], 6), "dev_precision": round(dev_metrics["precision"], 6),
            "dev_recall": round(dev_metrics["recall"], 6), "dev_f1": round(dev_metrics["f1"], 6),
            "dev_roc_auc": round(dev_metrics["roc_auc"], 6) if dev_metrics["roc_auc"] == dev_metrics["roc_auc"] else "nan",
            "dev_eer": round(dev_metrics["eer"], 6) if dev_metrics["eer"] == dev_metrics["eer"] else "nan",
            "learning_rate": lr, "epoch_time_seconds": round(epoch_time, 2),
            "best_checkpoint_saved": checkpoint_saved,
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(log_rows).to_csv(out_dir / "training_log.csv", index=False)
    return best_eer, best_epoch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    args = parser.parse_args()
    variant = args.variant

    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    print(f"Using device: {device} | variant: {variant}")

    df_train_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.train.trn.txt", DATA_ROOT / "ASVspoof2019_LA_train" / "flac")
    df_dev_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.dev.trl.txt", DATA_ROOT / "ASVspoof2019_LA_dev" / "flac")
    df_eval_full = parse_protocol(PROTOCOLS / "ASVspoof2019.LA.cm.eval.trl.txt", DATA_ROOT / "ASVspoof2019_LA_eval" / "flac")

    df_train = stratified_subset(df_train_full, TRAIN_SUBSET_N, SEED)
    df_dev = stratified_subset(df_dev_full, DEV_SUBSET_N, SEED)
    df_eval_subset = attack_stratified_eval_subset(df_eval_full, SEED)
    print(f"Train subset: {len(df_train)} | Dev subset: {len(df_dev)} | Eval subset: {len(df_eval_subset)}")

    dev_ds = AugmentedASVspoofDataset(df_dev, MelSpectrogramTransform(augment=False), waveform_aug=None)
    dev_loader = DataLoader(dev_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)
    train_loader = build_train_loader(df_train, use_noise=False, use_channel=False)  # no waveform aug — already ruled out

    out_dir = LOG_ROOT / variant
    ckpt_dir = CHECKPOINT_ROOT / variant
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    if variant == "label_smoothing_005":
        best_eer, best_epoch = run_label_smoothing(0.05, train_loader, dev_loader, device, out_dir, ckpt_dir)
        variable_changed = "label_smoothing=0.05"
    elif variant == "label_smoothing_010":
        best_eer, best_epoch = run_label_smoothing(0.10, train_loader, dev_loader, device, out_dir, ckpt_dir)
        variable_changed = "label_smoothing=0.10"
    elif variant == "ema":
        best_eer, best_epoch = run_ema(train_loader, dev_loader, device, out_dir, ckpt_dir)
        variable_changed = "EMA(decay=0.999, warmup)"
    else:
        raise ValueError(variant)
    elapsed = time.perf_counter() - started

    log_df = pd.read_csv(out_dir / "training_log.csv")
    avg_epoch_time = log_df["epoch_time_seconds"].mean()

    best_model = LCNN()
    best_model.load_state_dict(torch.load(ckpt_dir / "best.pt", map_location=device, weights_only=True))
    best_model = best_model.to(device)
    eval_metrics = evaluate_on_eval_subset(best_model, df_eval_subset, device)

    print(f"\n{'='*70}\nResult ({variant}): dev_eer={best_eer:.4f} (epoch {best_epoch}) | "
          f"eval_subset_eer={eval_metrics['eer']:.4f} | balanced_acc={eval_metrics['balanced_accuracy']:.4f} | "
          f"weak_attack_mean_eer={sum(eval_metrics['per_attack_eer'].get(a, float('nan')) for a in WEAK_ATTACKS) / len(WEAK_ATTACKS):.4f}\n"
          f"Total wall time: {elapsed:.1f}s\n{'='*70}")

    weak_mean = sum(eval_metrics["per_attack_eer"].get(a, float("nan")) for a in WEAK_ATTACKS) / len(WEAK_ATTACKS)

    eval_eer_delta = eval_metrics["eer"] - BASELINE_ROW["eval_subset_eer"]
    if eval_eer_delta < -0.02:
        outcome = "improved"
    elif eval_eer_delta > 0.05:
        outcome = "regressed"
    else:
        outcome = "no_improvement"

    append_experiment_log({
        "experiment_id": f"lcnn_exp_{variant}",
        "phase": "post_augmentation_reassessment",
        "dataset_scale": "subset",
        "train_n": len(df_train), "dev_n": len(df_dev), "eval_n": len(df_eval_subset),
        "epochs": EPOCHS, "seed": SEED,
        "variable_changed": variable_changed,
        "dev_eer": round(best_eer, 6), "eval_eer": round(eval_metrics["eer"], 6),
        "balanced_accuracy": round(eval_metrics["balanced_accuracy"], 6),
        "roc_auc": round(eval_metrics["roc_auc"], 6),
        "precision": round(eval_metrics["precision"], 6), "recall": round(eval_metrics["recall"], 6),
        "f1": round(eval_metrics["f1"], 6), "pr_auc": round(eval_metrics["pr_auc"], 6),
        "weak_attack_mean_eer": round(weak_mean, 6),
        "avg_epoch_time_seconds": round(avg_epoch_time, 2),
        "outcome": outcome,
        "notes": f"vs augmentation_baseline: eval_subset_eer {BASELINE_ROW['eval_subset_eer']:.4f} -> {eval_metrics['eer']:.4f} "
                 f"({eval_eer_delta:+.4f}); weak_attack_mean_eer {BASELINE_ROW['eval_subset_weak_attack_mean_eer']:.4f} -> {weak_mean:.4f}",
    })

    # Per-attack + summary artifact for this variant
    per_attack_lines = ["# Experiment: " + variant, "",
                        f"variable_changed: {variable_changed}", "",
                        f"| Metric | Baseline | {variant} | Delta |",
                        "|---|---|---|---|",
                        f"| Dev EER | {BASELINE_ROW['dev_eer']:.4f} | {best_eer:.4f} | {best_eer - BASELINE_ROW['dev_eer']:+.4f} |",
                        f"| Eval-subset EER | {BASELINE_ROW['eval_subset_eer']:.4f} | {eval_metrics['eer']:.4f} | {eval_eer_delta:+.4f} |",
                        f"| Balanced Accuracy | {BASELINE_ROW['eval_subset_balanced_accuracy']:.4f} | {eval_metrics['balanced_accuracy']:.4f} | {eval_metrics['balanced_accuracy'] - BASELINE_ROW['eval_subset_balanced_accuracy']:+.4f} |",
                        f"| ROC-AUC | {BASELINE_ROW['eval_subset_roc_auc']:.4f} | {eval_metrics['roc_auc']:.4f} | {eval_metrics['roc_auc'] - BASELINE_ROW['eval_subset_roc_auc']:+.4f} |",
                        f"| F1 | {BASELINE_ROW['eval_subset_f1']:.4f} | {eval_metrics['f1']:.4f} | {eval_metrics['f1'] - BASELINE_ROW['eval_subset_f1']:+.4f} |",
                        f"| Recall | {BASELINE_ROW['eval_subset_recall']:.4f} | {eval_metrics['recall']:.4f} | {eval_metrics['recall'] - BASELINE_ROW['eval_subset_recall']:+.4f} |",
                        f"| PR-AUC | n/a | {eval_metrics['pr_auc']:.4f} | n/a |",
                        f"| Weak-attack mean EER | {BASELINE_ROW['eval_subset_weak_attack_mean_eer']:.4f} | {weak_mean:.4f} | {weak_mean - BASELINE_ROW['eval_subset_weak_attack_mean_eer']:+.4f} |",
                        "", "## Per-attack EER", "",
                        "| Attack | EER |", "|---|---|"]
    for attack in sorted(a for a in eval_metrics["per_attack_eer"].keys() if isinstance(a, str)):
        flag = " (weak)" if attack in WEAK_ATTACKS else ""
        per_attack_lines.append(f"| {attack}{flag} | {eval_metrics['per_attack_eer'][attack]:.4f} |")
    per_attack_lines.append(f"\nOutcome: **{outcome}**\n")
    (out_dir / "summary.md").write_text("\n".join(per_attack_lines), encoding="utf-8")

    print(f"\nWROTE: {out_dir/'summary.md'}, {ckpt_dir/'best.pt'}, training/Experiment_Log.csv")


if __name__ == "__main__":
    main()
