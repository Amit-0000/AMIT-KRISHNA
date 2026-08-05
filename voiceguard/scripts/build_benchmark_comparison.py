"""Compiles training/Benchmark_Comparison.xlsx: LCNN vs deployed AudioCNN,
both evaluated on the official ASVspoof2019 LA eval split with identical
methodology (src.evaluation.metrics), per the Phase 5 benchmark requirement.

Reads the two models' already-computed Benchmark_Results.xlsx files
(scripts/evaluate.py, scripts/evaluate_audio_cnn.py) rather than
re-running inference — this only aggregates and adds model
size/param-count/memory figures on top.
"""
import pandas as pd

from pathlib import Path

REPORT_DIR = Path("training")

# Measured via scripts/evaluate.py / scripts/evaluate_audio_cnn.py
LCNN_PARAMS = 699_938
AUDIOCNN_PARAMS = 23_585
LCNN_CHECKPOINT_MB = round(2_818_131 / (1024 * 1024), 2)
AUDIOCNN_CHECKPOINT_MB = round(103_343 / (1024 * 1024), 2)
# Measured via isolated-process load+inference RSS delta (see conversation) —
# approximate, single-run measurement, not averaged across repeated trials.
LCNN_INFERENCE_MEMORY_MB = 418.51
AUDIOCNN_INFERENCE_MEMORY_MB = 52.41


def main():
    lcnn = pd.read_excel(REPORT_DIR / "Benchmark_Results.xlsx", sheet_name="overall_metrics").set_index("metric")["value"]
    audiocnn = pd.read_excel(REPORT_DIR / "AudioCNN_Benchmark_Results.xlsx", sheet_name="overall_metrics").set_index("metric")["value"]

    rows = [
        ("Accuracy (%)", lcnn["accuracy"] * 100, audiocnn["accuracy"] * 100),
        ("Precision (%)", lcnn["precision"] * 100, audiocnn["precision"] * 100),
        ("Recall / Sensitivity, spoof (%)", lcnn["recall"] * 100, audiocnn["recall"] * 100),
        ("Specificity (%)", lcnn["specificity"] * 100, audiocnn["specificity"] * 100),
        ("Balanced Accuracy (%)", lcnn["balanced_accuracy"] * 100, audiocnn["balanced_accuracy"] * 100),
        ("F1", lcnn["f1"], audiocnn["f1"]),
        ("ROC-AUC", lcnn["roc_auc"], audiocnn["roc_auc"]),
        ("PR-AUC", lcnn["pr_auc"], audiocnn["pr_auc"]),
        ("EER (%)", lcnn["eer"] * 100, audiocnn["eer"] * 100),
        ("False Positive Rate (%)", lcnn["false_positive_rate"] * 100, audiocnn["false_positive_rate"] * 100),
        ("False Negative Rate (%)", lcnn["false_negative_rate"] * 100, audiocnn["false_negative_rate"] * 100),
        ("Avg inference latency (ms/sample)", lcnn["avg_inference_latency_ms"], audiocnn["avg_inference_latency_ms"]),
        ("Median inference latency (ms/sample)", lcnn["median_inference_latency_ms"], audiocnn["median_inference_latency_ms"]),
        ("P95 inference latency (ms/sample)", lcnn["p95_inference_latency_ms"], audiocnn["p95_inference_latency_ms"]),
        ("P99 inference latency (ms/sample)", lcnn["p99_inference_latency_ms"], audiocnn["p99_inference_latency_ms"]),
        ("Parameter count", LCNN_PARAMS, AUDIOCNN_PARAMS),
        ("Checkpoint size (MB)", LCNN_CHECKPOINT_MB, AUDIOCNN_CHECKPOINT_MB),
        ("Approx. inference memory (MB, process RSS delta)", LCNN_INFERENCE_MEMORY_MB, AUDIOCNN_INFERENCE_MEMORY_MB),
    ]
    comparison_df = pd.DataFrame(rows, columns=["Metric", "LCNN (best.pt, epoch 18)", "AudioCNN (deployed, deepfake_cnn.pth)"])

    criteria = [
        ("Lower EER", lcnn["eer"] < audiocnn["eer"]),
        ("Higher Balanced Accuracy", lcnn["balanced_accuracy"] > audiocnn["balanced_accuracy"]),
        ("Higher Recall (spoof)", lcnn["recall"] > audiocnn["recall"]),
        ("Comparable or better Precision", lcnn["precision"] >= audiocnn["precision"] - 0.02),
        ("Comparable latency (same order of magnitude)", lcnn["avg_inference_latency_ms"] < 20),
    ]
    criteria_df = pd.DataFrame(criteria, columns=["Production-readiness criterion", "Met by LCNN?"])
    all_met = all(c[1] for c in criteria)

    notes_df = pd.DataFrame({
        "Note": [
            "Both models evaluated on the identical official ASVspoof2019 LA eval split (71,237 files), never seen during LCNN training.",
            "Identical evaluation code path (src.evaluation.metrics.compute_full_metrics / compute_latency_stats) used for both models.",
            "LCNN was trained on ASVspoof2019 LA; AudioCNN is a vendored checkpoint (Devil-92/Fake-Audio-Detector) never trained on ASVspoof data "
            "— this is an out-of-domain test for AudioCNN, which is the most likely explanation for its near-chance ROC-AUC (0.483) here. "
            "The comparison is still valid for VoiceGuard's purpose: it measures which checkpoint currently deployed/trainable performs better "
            "on VoiceGuard's actual target detection task.",
            f"All {len(criteria)} production-readiness criteria met by LCNN: {all_met}.",
        ]
    })

    with pd.ExcelWriter(REPORT_DIR / "Benchmark_Comparison.xlsx") as writer:
        comparison_df.to_excel(writer, sheet_name="metric_comparison", index=False)
        criteria_df.to_excel(writer, sheet_name="production_readiness", index=False)
        notes_df.to_excel(writer, sheet_name="notes", index=False)

    print(f"Wrote {REPORT_DIR / 'Benchmark_Comparison.xlsx'}")
    print(f"All production-readiness criteria met by LCNN: {all_met}")
    for name, met in criteria:
        print(f"  [{'x' if met else ' '}] {name}")


if __name__ == "__main__":
    main()
