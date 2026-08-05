"""Benchmarks the deployed AudioCNN checkpoint (checkpoints/deepfake_cnn.pth)
on the official ASVspoof2019 LA eval split, using the exact same evaluation
methodology (src.evaluation.metrics) as scripts/evaluate.py uses for LCNN, so
the two models' numbers are directly comparable per the Phase 5 benchmark
requirement.

Feature extraction reuses api.inference.feature_extraction's registered
"logmel64db" extractor verbatim (the same code path production inference
uses for AudioCNN) rather than reimplementing it, so these numbers reflect
real deployment behavior. Waveform preprocessing reuses
src.data.dataset.serving_equivalent_preprocess for the same reason LCNN's
training/eval does.
"""
import time

import pandas as pd
import torch
import yaml
from pathlib import Path
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.data.protocol import parse_protocol
from src.data.dataset import ASVspoofDataset
from src.models.audio_cnn import AudioCNN
from src.evaluation.eer import compute_eer_per_attack
from src.evaluation.metrics import (
    compute_full_metrics,
    compute_latency_stats,
    save_confusion_matrix_plot,
    save_pr_curve_plot,
    save_roc_curve_plot,
)

REPORT_DIR = Path("training")


def logmel64db_transform(waveform: torch.Tensor) -> torch.Tensor:
    """Wraps the production "logmel64db" extractor as an
    ASVspoofDataset-compatible transform (waveform -> feature tensor),
    exactly like MelSpectrogramTransform does for LCNN."""
    from api.inference.feature_extraction import extract_features

    feature = extract_features(waveform, extractor_name="logmel64db", extractor_version="v1")
    return feature.tensor


def measure_inference_latency(model: AudioCNN, dataset: ASVspoofDataset, device: torch.device, n_samples: int = 200) -> list[float]:
    """Per-sample forward-pass latency in ms — mirrors production
    (api.inference.adapters.audio_cnn_adapter.AudioCNNAdapter.predict runs
    one file at a time), not batched throughput."""
    n = min(n_samples, len(dataset))
    timings = []
    with torch.no_grad():
        for i in range(n):
            x, _ = dataset[i]
            x = x.unsqueeze(0).to(device)
            started = time.perf_counter()
            model(x)
            timings.append((time.perf_counter() - started) * 1000)
    return timings


def main():
    with open("configs/lcnn.yaml") as f:
        cfg = yaml.safe_load(f)

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    # Load eval set — the OFFICIAL ASVspoof eval split only, identical to
    # scripts/evaluate.py's LCNN evaluation (same files, same labels).
    data_root = Path(cfg["paths"]["data_root"])
    protocols = data_root / "ASVspoof2019_LA_cm_protocols"

    df_eval = parse_protocol(
        protocols / "ASVspoof2019.LA.cm.eval.trl.txt",
        data_root / "ASVspoof2019_LA_eval" / "flac",
    )

    dataset = ASVspoofDataset(df_eval, transform=logmel64db_transform)
    loader  = DataLoader(dataset, batch_size=cfg["data"]["batch_size"],
                         shuffle=False, num_workers=0)

    # Load the deployed AudioCNN checkpoint — same load path as
    # AudioCNNAdapter.load_model (weights_only=True, bare state_dict).
    model = AudioCNN()
    model.load_state_dict(torch.load("checkpoints/deepfake_cnn.pth", map_location=device, weights_only=True))
    model = model.to(device)
    model.eval()

    all_scores  = []
    all_labels  = []
    all_preds   = []

    with torch.no_grad():
        for x, labels in tqdm(loader, desc="Evaluating AudioCNN"):
            x = x.to(device)
            logits = model(x)  # [B] raw logit — AudioCNN.forward, unlike LCNN, returns a single logit per example
            scores = torch.sigmoid(logits)
            preds  = (scores >= 0.5).long()
            all_scores.extend(scores.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_preds.extend(preds.cpu().tolist())

    attack_types = df_eval["attack_type"].tolist()
    per_attack   = compute_eer_per_attack(all_labels, all_scores, attack_types)

    print(f"\nPer-attack EER:")
    print(f"  {'Attack':<10} {'EER':>8}")
    print(f"  {'-'*20}")
    for attack, attack_eer in sorted(per_attack.items()):
        if attack == "overall":
            continue
        print(f"  {attack:<10} {attack_eer*100:>7.4f}%")

    metrics = compute_full_metrics(all_labels, all_preds, all_scores)
    latencies = measure_inference_latency(model, dataset, device)
    metrics.update(compute_latency_stats(latencies))

    print(f"\n{'='*45}")
    print(f"  Accuracy          : {metrics['accuracy']*100:.2f}%")
    print(f"  Precision         : {metrics['precision']*100:.2f}%")
    print(f"  Recall (spoof)    : {metrics['recall']*100:.2f}%")
    print(f"  Specificity       : {metrics['specificity']*100:.2f}%")
    print(f"  Balanced Accuracy : {metrics['balanced_accuracy']*100:.2f}%")
    print(f"  F1                : {metrics['f1']:.4f}")
    print(f"  ROC-AUC           : {metrics['roc_auc']:.4f}")
    print(f"  PR-AUC            : {metrics['pr_auc']:.4f}")
    print(f"  EER               : {metrics['eer']*100:.4f}%  (baseline LFCC-GMM: 8.0900%)")
    print(f"  FPR               : {metrics['false_positive_rate']*100:.2f}%")
    print(f"  FNR               : {metrics['false_negative_rate']*100:.2f}%")
    print(f"  Avg latency       : {metrics['avg_inference_latency_ms']:.2f} ms/sample")
    print(f"  Median latency    : {metrics['median_inference_latency_ms']:.2f} ms/sample")
    print(f"  P95 latency       : {metrics['p95_inference_latency_ms']:.2f} ms/sample")
    print(f"  P99 latency       : {metrics['p99_inference_latency_ms']:.2f} ms/sample")
    print(f"  Confusion matrix (rows=true, cols=pred, [bonafide, spoof]):")
    print(f"    [[{metrics['true_negative']:6d} {metrics['false_positive']:6d}]")
    print(f"     [{metrics['false_negative']:6d} {metrics['true_positive']:6d}]]")
    print(f"{'='*45}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    save_confusion_matrix_plot(metrics, "AudioCNN Confusion Matrix (ASVspoof eval)", REPORT_DIR / "AudioCNN_Confusion_Matrix.png")
    save_roc_curve_plot(all_labels, all_scores, metrics["roc_auc"], "AudioCNN ROC Curve (ASVspoof eval)", REPORT_DIR / "AudioCNN_ROC_Curve.png")
    save_pr_curve_plot(all_labels, all_scores, metrics["pr_auc"], "AudioCNN Precision-Recall Curve (ASVspoof eval)", REPORT_DIR / "AudioCNN_Precision_Recall_Curve.png")

    metrics_df = pd.DataFrame([{"metric": k, "value": v} for k, v in metrics.items()])
    per_attack_df = pd.DataFrame(
        [{"attack_type": k, "eer": v} for k, v in sorted(per_attack.items()) if k != "overall"]
    )
    with pd.ExcelWriter(REPORT_DIR / "AudioCNN_Benchmark_Results.xlsx") as writer:
        metrics_df.to_excel(writer, sheet_name="overall_metrics", index=False)
        per_attack_df.to_excel(writer, sheet_name="per_attack_eer", index=False)

    print(f"\nSaved: {REPORT_DIR/'AudioCNN_Confusion_Matrix.png'}, {REPORT_DIR/'AudioCNN_ROC_Curve.png'}, "
          f"{REPORT_DIR/'AudioCNN_Precision_Recall_Curve.png'}, {REPORT_DIR/'AudioCNN_Benchmark_Results.xlsx'}")


if __name__ == "__main__":
    main()
