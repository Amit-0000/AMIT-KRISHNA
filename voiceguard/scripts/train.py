import argparse

import torch
import yaml
from pathlib import Path
from torch.utils.data import DataLoader, WeightedRandomSampler

from src.data.protocol import parse_protocol, print_stats
from src.data.dataset import ASVspoofDataset
from src.data.transforms import MelSpectrogramTransform
from src.models.lcnn import LCNN
from src.training.losses import compute_class_weights
from src.training.trainer import Trainer, load_training_checkpoint, set_seed
from init_experiment import create_experiment_record

# Winner of the empirical class-imbalance ablation (training/imbalance_experiments/
# class_imbalance_comparison.md): WeightedRandomSampler, dev EER 0.0870 vs 0.2330
# (standard CE) and 0.2718 (weighted CE) — decisively better, not assumed.
CLASS_IMBALANCE_STRATEGY = "weighted_sampler"


def parse_args():
    parser = argparse.ArgumentParser(description="Train LCNN on ASVspoof2019 LA")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoints/last.pt (model + optimizer + scheduler + epoch state) instead of starting fresh.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load config
    with open("configs/lcnn.yaml") as f:
        cfg = yaml.safe_load(f)

    set_seed(cfg["training"].get("seed", 42))

    # Device
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Using device: {device}")

    # Dataset
    data_root = Path(cfg["paths"]["data_root"])
    protocols = data_root / "ASVspoof2019_LA_cm_protocols"

    df_train = parse_protocol(
        protocols / "ASVspoof2019.LA.cm.train.trn.txt",
        data_root / "ASVspoof2019_LA_train" / "flac",
    )
    df_dev = parse_protocol(
        protocols / "ASVspoof2019.LA.cm.dev.trl.txt",
        data_root / "ASVspoof2019_LA_dev" / "flac",
    )

    print_stats(df_train, "train")
    print_stats(df_dev,   "dev")

    experiment_record = create_experiment_record(
        "configs/lcnn.yaml",
        device=device,
        class_imbalance_strategy=CLASS_IMBALANCE_STRATEGY,
        data_root=data_root,
    )
    print(f"Experiment ID: {experiment_record['experiment_id']}")

    train_dataset = ASVspoofDataset(df_train, transform=MelSpectrogramTransform(augment=True))
    dev_dataset   = ASVspoofDataset(df_dev,   transform=MelSpectrogramTransform(augment=False))

    # WeightedRandomSampler — empirically the best class-imbalance strategy
    # (see CLASS_IMBALANCE_STRATEGY note above), so the loss stays standard
    # unweighted CrossEntropyLoss and the sampler does the balancing.
    class_weights = compute_class_weights(df_train)
    label_to_idx = {"bonafide": 0, "spoof": 1}
    sample_weights = df_train["label"].map(lambda l: class_weights[label_to_idx[l]]).tolist()
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(df_train), replacement=True)

    train_loader = DataLoader(
        train_dataset,
        batch_size=cfg["data"]["batch_size"],
        sampler=sampler,
        num_workers=cfg["data"]["num_workers"],
        pin_memory=True,
    )
    dev_loader = DataLoader(
        dev_dataset,
        batch_size=cfg["data"]["batch_size"],
        shuffle=False,
        num_workers=cfg["data"]["num_workers"],
        pin_memory=True,
    )

    # Model, loss, optimizer, scheduler
    model     = LCNN()
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=cfg["training"]["learning_rate"],
        weight_decay=cfg["training"]["weight_decay"],
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=cfg["scheduler"]["T_max"],
        eta_min=cfg["scheduler"]["eta_min"],
    )

    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        criterion=criterion,
        device=device,
        checkpoint_dir=cfg["paths"]["checkpoint_dir"],
        log_dir=cfg["paths"]["log_dir"],
        patience=cfg["training"]["patience"],
        metrics_csv_path=Path("training") / "Training_Log.csv",
    )

    start_epoch = 1
    if args.resume:
        last_ckpt = Path(cfg["paths"]["checkpoint_dir"]) / "last.pt"
        if not last_ckpt.exists():
            raise FileNotFoundError(f"--resume given but no checkpoint at {last_ckpt}")
        state = load_training_checkpoint(last_ckpt, model, optimizer, scheduler, device=device)
        trainer.best_eer = state["best_eer"]
        trainer.best_epoch = state["best_epoch"]
        trainer.epochs_no_improve = state["epochs_no_improve"]
        start_epoch = state["start_epoch"]
        print(f"Resumed from {last_ckpt}: starting at epoch {start_epoch}, best_eer so far {trainer.best_eer:.4f}")

    trainer.fit(train_loader, dev_loader, epochs=cfg["training"]["epochs"], start_epoch=start_epoch)


if __name__ == "__main__":
    main()
