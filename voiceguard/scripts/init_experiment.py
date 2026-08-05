"""Creates a reproducible experiment record before training starts: a unique
experiment ID plus every environment/config detail needed to reproduce or
audit the run later. Called from scripts/train.py; also runnable standalone
for inspection.

Saves training/experiments/experiment_<ID>.json.
"""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml

EXPERIMENTS_DIR = Path("training") / "experiments"


def _git_commit_hash() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parent.parent
        ).stdout.strip()
    except Exception:
        return None


def _git_is_dirty() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parent.parent
        )
        return bool(result.stdout.strip())
    except Exception:
        return None


def _protocol_files_checksum(data_root: Path) -> str | None:
    """A single sha256 over the three ASVspoof protocol files — these fully
    define the dataset split assignment. Hashing all 121k audio files would
    be prohibitively slow to do at experiment-init time; Phase 3's
    training/asvspoof_manifest.csv already carries per-file integrity data."""
    protocols_dir = data_root / "ASVspoof2019_LA_cm_protocols"
    files = sorted(protocols_dir.glob("*.txt")) if protocols_dir.exists() else []
    if not files:
        return None
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.read_bytes())
    return digest.hexdigest()


def _hardware_info() -> dict:
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count_logical": None,
        "cpu_count_physical": None,
        "ram_total_gb": None,
        "cuda_available": torch.cuda.is_available(),
        "mps_available": torch.backends.mps.is_available(),
        "gpu_name": None,
    }
    try:
        import psutil

        info["cpu_count_logical"] = psutil.cpu_count(logical=True)
        info["cpu_count_physical"] = psutil.cpu_count(logical=False)
        info["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        pass
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
    return info


def create_experiment_record(
    config_path: str | Path,
    *,
    device: torch.device,
    class_imbalance_strategy: str,
    data_root: str | Path = "data",
    experiment_id: str | None = None,
) -> dict:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    if experiment_id is None:
        experiment_id = f"LCNN_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    data_root = Path(data_root)

    record = {
        "experiment_id": experiment_id,
        "datetime_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": _git_commit_hash(),
        "git_working_tree_dirty": _git_is_dirty(),
        "dataset": {
            "name": "ASVspoof2019 LA",
            "source": "Kaggle awsaf49/asvpoof-2019-dataset",
            "path": str(data_root.resolve()),
            "protocol_files_sha256": _protocol_files_checksum(data_root),
        },
        "config_file": str(Path(config_path).resolve()),
        "config": cfg,
        "class_imbalance_strategy": class_imbalance_strategy,
        "random_seed": cfg["training"].get("seed", 42),
        "learning_rate": cfg["training"]["learning_rate"],
        "optimizer": "Adam",
        "weight_decay": cfg["training"]["weight_decay"],
        "scheduler": "CosineAnnealingLR",
        "scheduler_config": cfg["scheduler"],
        "batch_size": cfg["data"]["batch_size"],
        "epoch_count_configured": cfg["training"]["epochs"],
        "early_stopping_patience": cfg["training"]["patience"],
        "mixed_precision_enabled": device.type == "cuda",
        "serving_equivalent_preprocessing_enabled": True,
        "num_workers": cfg["data"]["num_workers"],
        "device": str(device),
        "hardware": _hardware_info(),
        "python_version": sys.version,
        "torch_version": torch.__version__,
    }

    try:
        import torchaudio

        record["torchaudio_version"] = torchaudio.__version__
    except ImportError:
        record["torchaudio_version"] = None

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPERIMENTS_DIR / f"experiment_{experiment_id}.json"
    with open(out_path, "w") as f:
        json.dump(record, f, indent=2, default=str)

    print(f"Experiment record written: {out_path}")
    return record


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    create_experiment_record("configs/lcnn.yaml", device=device, class_imbalance_strategy="TBD")
