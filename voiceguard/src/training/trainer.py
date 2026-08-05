import csv
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm


def set_seed(seed: int) -> None:
    """Seeds every RNG the training pipeline touches (python's random, numpy,
    torch CPU/CUDA) and disables cuDNN's non-deterministic autotuner, so a
    given config produces the same result run to run."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_training_checkpoint(
    path: str | Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler=None,
    device: torch.device | str = "cpu",
) -> dict:
    """Restores model/optimizer/scheduler state from a `last.pt`-style
    training checkpoint (see Trainer._save_last_checkpoint) and returns the
    bookkeeping needed to resume `Trainer.fit` mid-run: next epoch to start
    at, the best dev EER seen so far, and the early-stopping counter. Never
    touches `best.pt` — that file stays a plain state_dict for the inference
    adapter (api.inference.adapters.lcnn_adapter), unrelated to resume."""
    state = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(state["model_state_dict"])
    if optimizer is not None and state.get("optimizer_state_dict") is not None:
        optimizer.load_state_dict(state["optimizer_state_dict"])
    if scheduler is not None and state.get("scheduler_state_dict") is not None:
        scheduler.load_state_dict(state["scheduler_state_dict"])
    return {
        "start_epoch": state["epoch"] + 1,
        "best_eer": state.get("best_eer", float("inf")),
        "best_epoch": state.get("best_epoch"),
        "epochs_no_improve": state.get("epochs_no_improve", 0),
    }


class Trainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler,
        criterion: nn.Module,
        device: torch.device,
        checkpoint_dir: str,
        log_dir: str,
        patience: int = 10,
        metrics_csv_path: str | Path | None = None,
    ):
        self.model          = model.to(device)
        self.optimizer      = optimizer
        self.scheduler      = scheduler
        self.criterion      = criterion
        self.device         = device
        self.checkpoint_dir = Path(checkpoint_dir)
        self.patience       = patience
        self.writer         = SummaryWriter(log_dir=log_dir)
        # Mixed precision only on CUDA — CPU/MPS autocast for a model this
        # small doesn't reliably help and this repo's dev machine is CPU-only;
        # the hook is here (rather than skipped outright) so a GPU box picks
        # it up automatically without code changes.
        self.use_amp = device.type == "cuda"
        self.scaler  = torch.amp.GradScaler(device.type, enabled=self.use_amp)

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.best_eer     = float("inf")
        self.best_epoch: int | None = None
        self.epochs_no_improve = 0
        self.last_epoch_metrics: dict | None = None

        self.metrics_csv_path = Path(metrics_csv_path) if metrics_csv_path else None
        if self.metrics_csv_path is not None:
            self.metrics_csv_path.parent.mkdir(parents=True, exist_ok=True)

    def _save_last_checkpoint(self, epoch: int) -> None:
        """Full training-state checkpoint for resuming a run — distinct from
        best.pt (a bare state_dict the inference adapter loads directly).
        Nothing outside Trainer/load_training_checkpoint ever reads this
        file's shape, so it's free to carry optimizer/scheduler/epoch state."""
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "scheduler_state_dict": self.scheduler.state_dict() if self.scheduler is not None else None,
                "best_eer": self.best_eer,
                "best_epoch": self.best_epoch,
                "epochs_no_improve": self.epochs_no_improve,
            },
            self.checkpoint_dir / "last.pt",
        )

    def _log_metrics_csv(self, row: dict) -> None:
        if self.metrics_csv_path is None:
            return
        write_header = not self.metrics_csv_path.exists()
        with open(self.metrics_csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def train_epoch(self, loader: DataLoader, epoch: int) -> float:
        self.model.train()
        total_loss = 0.0

        for x, labels in tqdm(loader, desc=f"Epoch {epoch} [train]", leave=False):
            x, labels = x.to(self.device), labels.to(self.device)

            self.optimizer.zero_grad()
            with torch.amp.autocast(self.device.type, enabled=self.use_amp):
                logits = self.model(x)
                loss   = self.criterion(logits, labels)
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()

            total_loss += loss.item()

        return total_loss / len(loader)

    def eval_epoch(self, loader: DataLoader, epoch: int) -> dict:
        """Runs one full validation pass and returns a dict of avg_loss plus
        the per-epoch metric suite (accuracy/precision/recall/f1/roc_auc/eer).
        EER remains the model-selection criterion (see fit()) — it's the
        metric immune to this task's ~9:1 class imbalance (docs/02_dataset.md
        §8); the rest are reported per epoch so training dynamics are fully
        visible, not just the selection metric."""
        from src.evaluation.eer import compute_eer

        self.model.eval()
        total_loss = 0.0
        all_scores = []
        all_labels = []
        all_preds  = []

        with torch.no_grad():
            for x, labels in tqdm(loader, desc=f"Epoch {epoch} [eval] ", leave=False):
                x, labels = x.to(self.device), labels.to(self.device)
                with torch.amp.autocast(self.device.type, enabled=self.use_amp):
                    logits = self.model(x)
                    loss   = self.criterion(logits, labels)
                total_loss += loss.item()

                # Softmax score for class 1 (spoof) used as detection score
                scores = torch.softmax(logits, dim=1)[:, 1]
                preds  = logits.argmax(dim=1)
                all_scores.extend(scores.cpu().tolist())
                all_labels.extend(labels.cpu().tolist())
                all_preds.extend(preds.cpu().tolist())

        avg_loss = total_loss / len(loader)
        eer      = compute_eer(all_labels, all_scores)

        has_both_classes = len(set(all_labels)) == 2
        metrics = {
            "loss": avg_loss,
            "eer": eer,
            "accuracy": accuracy_score(all_labels, all_preds),
            "precision": precision_score(all_labels, all_preds, zero_division=0),
            "recall": recall_score(all_labels, all_preds, zero_division=0),
            "f1": f1_score(all_labels, all_preds, zero_division=0),
            "roc_auc": roc_auc_score(all_labels, all_scores) if has_both_classes else float("nan"),
        }
        return metrics

    def fit(self, train_loader: DataLoader, dev_loader: DataLoader, epochs: int, start_epoch: int = 1):
        for epoch in range(start_epoch, epochs + 1):
            epoch_started = time.perf_counter()

            train_loss = self.train_epoch(train_loader, epoch)
            dev = self.eval_epoch(dev_loader, epoch)
            dev_loss, dev_eer = dev["loss"], dev["eer"]

            if self.scheduler is not None:
                self.scheduler.step()

            epoch_time_s = time.perf_counter() - epoch_started
            lr = self.optimizer.param_groups[0]["lr"]
            print(
                f"Epoch {epoch:3d} | train_loss {train_loss:.4f} | dev_loss {dev_loss:.4f} | dev_EER {dev_eer:.4f} "
                f"| acc {dev['accuracy']:.4f} | prec {dev['precision']:.4f} | rec {dev['recall']:.4f} | f1 {dev['f1']:.4f} "
                f"| auc {dev['roc_auc']:.4f} | lr {lr:.2e} | {epoch_time_s:.1f}s"
            )

            # TensorBoard logging
            self.writer.add_scalar("loss/train", train_loss, epoch)
            self.writer.add_scalar("loss/dev",   dev_loss,   epoch)
            self.writer.add_scalar("EER/dev",    dev_eer,    epoch)
            self.writer.add_scalar("accuracy/dev",  dev["accuracy"],  epoch)
            self.writer.add_scalar("precision/dev", dev["precision"], epoch)
            self.writer.add_scalar("recall/dev",    dev["recall"],    epoch)
            self.writer.add_scalar("f1/dev",        dev["f1"],        epoch)
            self.writer.add_scalar("roc_auc/dev",   dev["roc_auc"],   epoch)
            self.writer.add_scalar("lr",         lr,         epoch)

            checkpoint_saved = False
            # Save best checkpoint — EER is the model-selection criterion
            # (see eval_epoch docstring); never overwrite a lower-EER best.pt
            # with a higher-EER one.
            if dev_eer == dev_eer:  # nan check — skip if EER couldn't be computed
                if dev_eer < self.best_eer:
                    self.best_eer = dev_eer
                    self.best_epoch = epoch
                    self.epochs_no_improve = 0
                    torch.save(self.model.state_dict(), self.checkpoint_dir / "best.pt")
                    checkpoint_saved = True
                    print(f"           -> new best EER: {dev_eer:.4f} — checkpoint saved")
                else:
                    self.epochs_no_improve += 1
            else:
                print(f"           -> EER is NaN (too few samples) — skipping best-checkpoint update")

            # last.pt always reflects the most recent epoch, regardless of
            # whether it improved — this is the resume checkpoint.
            self._save_last_checkpoint(epoch)

            self.last_epoch_metrics = {
                "epoch": epoch,
                "train_loss": round(train_loss, 6),
                "dev_loss": round(dev_loss, 6),
                "dev_accuracy": round(dev["accuracy"], 6),
                "dev_precision": round(dev["precision"], 6),
                "dev_recall": round(dev["recall"], 6),
                "dev_f1": round(dev["f1"], 6),
                "dev_roc_auc": round(dev["roc_auc"], 6) if dev["roc_auc"] == dev["roc_auc"] else "nan",
                "dev_eer": round(dev_eer, 6) if dev_eer == dev_eer else "nan",
                "learning_rate": lr,
                "epoch_time_seconds": round(epoch_time_s, 2),
                "best_checkpoint_saved": checkpoint_saved,
            }
            self._log_metrics_csv(self.last_epoch_metrics)

            # Early stopping
            if self.epochs_no_improve >= self.patience:
                print(f"Early stopping at epoch {epoch} — no improvement for {self.patience} epochs")
                break

        self.writer.close()
        print(f"\nTraining complete. Best dev EER: {self.best_eer:.4f}" + (f" (epoch {self.best_epoch})" if self.best_epoch else ""))
