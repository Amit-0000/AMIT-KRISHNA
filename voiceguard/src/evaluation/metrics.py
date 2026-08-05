"""Shared evaluation metric computation and plotting — used identically by
LCNN's and AudioCNN's evaluation scripts so the two models' benchmark numbers
are directly comparable (same code computes both), not just similarly
computed."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from src.evaluation.eer import compute_eer


def compute_full_metrics(labels: list[int], preds: list[int], scores: list[float]) -> dict:
    """labels/preds: 0=bonafide, 1=spoof. scores: model's spoof probability.
    Decision rule (preds) must be argmax(softmax) / >=0.5 on scores — the
    same rule src.inference.predict and the production adapters use, so
    these numbers reflect real deployment behavior, not an arbitrary cutoff."""
    y_true = np.array(labels)
    y_pred = np.array(preds)
    y_score = np.array(scores)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    has_both_classes = len(np.unique(y_true)) == 2

    recall = recall_score(y_true, y_pred, zero_division=0)  # sensitivity, spoof
    specificity = tn / (tn + fp) if (tn + fp) > 0 else float("nan")

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_score) if has_both_classes else float("nan"),
        "pr_auc": average_precision_score(y_true, y_score) if has_both_classes else float("nan"),
        "eer": compute_eer(labels, scores),
        "false_positive_rate": fp / (fp + tn) if (fp + tn) > 0 else float("nan"),
        "false_negative_rate": fn / (fn + tp) if (fn + tp) > 0 else float("nan"),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def compute_latency_stats(timings_ms: list[float]) -> dict:
    arr = np.array(timings_ms)
    return {
        "avg_inference_latency_ms": float(np.mean(arr)),
        "median_inference_latency_ms": float(np.median(arr)),
        "p95_inference_latency_ms": float(np.percentile(arr, 95)),
        "p99_inference_latency_ms": float(np.percentile(arr, 99)),
    }


def save_confusion_matrix_plot(metrics: dict, title: str, out_path: str | Path) -> None:
    tn, fp, fn, tp = metrics["true_negative"], metrics["false_positive"], metrics["false_negative"], metrics["true_positive"]
    cm = np.array([[tn, fp], [fn, tp]])
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["bonafide", "spoof"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["bonafide", "spoof"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_roc_curve_plot(labels: list[int], scores: list[float], roc_auc: float, title: str, out_path: str | Path) -> None:
    fpr_curve, tpr_curve, _ = roc_curve(labels, scores)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr_curve, tpr_curve, label=f"AUC={roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="chance")
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_pr_curve_plot(labels: list[int], scores: list[float], pr_auc: float, title: str, out_path: str | Path) -> None:
    precision_curve, recall_curve, _ = precision_recall_curve(labels, scores)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(recall_curve, precision_curve, label=f"PR-AUC={pr_auc:.4f}")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
