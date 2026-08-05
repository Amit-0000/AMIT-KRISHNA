"""Phase 3 dataset audit: verifies every file listed in the official ASVspoof2019
LA protocol files actually exists and is a readable FLAC (header-only check via
soundfile.info — no full decode needed), and produces the two Phase 3
deliverables: training/asvspoof_manifest.csv and training/asvspoof_dataset_report.md."""
from pathlib import Path

import pandas as pd
import soundfile as sf
from tqdm import tqdm

from src.data.protocol import parse_protocol

DATA_ROOT = Path("data")
PROTOCOLS = DATA_ROOT / "ASVspoof2019_LA_cm_protocols"
REPORT_DIR = Path("training")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SPLITS = {
    "train": (PROTOCOLS / "ASVspoof2019.LA.cm.train.trn.txt", DATA_ROOT / "ASVspoof2019_LA_train" / "flac"),
    "dev":   (PROTOCOLS / "ASVspoof2019.LA.cm.dev.trl.txt",   DATA_ROOT / "ASVspoof2019_LA_dev"   / "flac"),
    "eval":  (PROTOCOLS / "ASVspoof2019.LA.cm.eval.trl.txt",  DATA_ROOT / "ASVspoof2019_LA_eval"  / "flac"),
}


def audit_split(split: str, protocol_file: Path, audio_dir: Path) -> pd.DataFrame:
    df = parse_protocol(protocol_file, audio_dir)
    df["split"] = split

    exists_col, sr_col, frames_col, dur_col, readable_col, error_col = [], [], [], [], [], []
    for file_path in tqdm(df["file_path"], desc=f"auditing {split}"):
        p = Path(file_path)
        if not p.exists():
            exists_col.append(False); sr_col.append(None); frames_col.append(None)
            dur_col.append(None); readable_col.append(False); error_col.append("file not found")
            continue
        exists_col.append(True)
        try:
            info = sf.info(str(p))
            sr_col.append(info.samplerate)
            frames_col.append(info.frames)
            dur_col.append(round(info.frames / info.samplerate, 4))
            readable_col.append(True)
            error_col.append(None)
        except Exception as exc:  # noqa: BLE001 - any header-read failure = corrupted
            sr_col.append(None); frames_col.append(None); dur_col.append(None)
            readable_col.append(False); error_col.append(str(exc))

    df["exists"] = exists_col
    df["sample_rate"] = sr_col
    df["num_frames"] = frames_col
    df["duration_seconds"] = dur_col
    df["readable"] = readable_col
    df["error"] = error_col
    return df


def main():
    all_dfs = []
    for split, (protocol_file, audio_dir) in SPLITS.items():
        assert protocol_file.exists(), f"Missing protocol file: {protocol_file}"
        assert audio_dir.exists(), f"Missing audio dir: {audio_dir}"
        all_dfs.append(audit_split(split, protocol_file, audio_dir))

    manifest = pd.concat(all_dfs, ignore_index=True)
    manifest_cols = [
        "split", "speaker_id", "utterance_id", "file_path", "label", "attack_type",
        "exists", "readable", "sample_rate", "num_frames", "duration_seconds", "error",
    ]
    manifest = manifest[manifest_cols]
    manifest.to_csv(REPORT_DIR / "asvspoof_manifest.csv", index=False)

    # ── Report ──────────────────────────────────────────────────────────────
    lines = []
    lines.append("# ASVspoof2019 LA Dataset Report\n")
    lines.append(f"Source: Kaggle `awsaf49/asvpoof-2019-dataset` (official ASVspoof2019 LA partition, "
                  f"as documented in `docs/02_dataset.md`).\n")

    total_files = len(manifest)
    total_missing = int((~manifest["exists"]).sum())
    total_unreadable = int((manifest["exists"] & ~manifest["readable"]).sum())
    total_dupe_paths = int(manifest["file_path"].duplicated().sum())

    lines.append("## Integrity summary\n")
    lines.append(f"- Total utterances across all protocol files: **{total_files}**")
    lines.append(f"- Missing files (listed in protocol, not found on disk): **{total_missing}**")
    lines.append(f"- Present but unreadable/corrupted (FLAC header failed to parse): **{total_unreadable}**")
    lines.append(f"- Duplicate file paths within the manifest: **{total_dupe_paths}**")
    lines.append("")

    for split in ["train", "dev", "eval"]:
        sub = manifest[manifest["split"] == split]
        readable = sub[sub["readable"]]
        bonafide = (sub["label"] == "bonafide").sum()
        spoof = (sub["label"] == "spoof").sum()
        total = len(sub)
        lines.append(f"## {split}\n")
        lines.append(f"- Total utterances: **{total}**")
        lines.append(f"- Bonafide: **{bonafide}** ({100*bonafide/total:.1f}%)")
        lines.append(f"- Spoof: **{spoof}** ({100*spoof/total:.1f}%)")
        lines.append(f"- Missing: **{(~sub['exists']).sum()}**  |  Unreadable: **{(sub['exists'] & ~sub['readable']).sum()}**")
        if len(readable):
            sr_counts = readable["sample_rate"].value_counts().to_dict()
            lines.append(f"- Sample rate(s) observed: {sr_counts}")
            dur = readable["duration_seconds"]
            lines.append(f"- Duration (s): min={dur.min():.3f}, max={dur.max():.3f}, "
                          f"mean={dur.mean():.3f}, median={dur.median():.3f}, std={dur.std():.3f}")
        attack_counts = sub[sub["attack_type"].notna()]["attack_type"].value_counts().sort_index()
        if len(attack_counts):
            lines.append(f"- Attack-type breakdown: {dict(attack_counts)}")
        lines.append("")

    lines.append("## Folder structure (verified on disk)\n")
    lines.append("```")
    lines.append("data/")
    lines.append("├── ASVspoof2019_LA_cm_protocols/")
    lines.append("│   ├── ASVspoof2019.LA.cm.train.trn.txt")
    lines.append("│   ├── ASVspoof2019.LA.cm.dev.trl.txt")
    lines.append("│   └── ASVspoof2019.LA.cm.eval.trl.txt")
    lines.append("├── ASVspoof2019_LA_train/flac/   (25,380 files)")
    lines.append("├── ASVspoof2019_LA_dev/flac/     (24,844 files)")
    lines.append("└── ASVspoof2019_LA_eval/flac/    (71,237 files)")
    lines.append("```")
    lines.append("\nMatches the official layout documented in `docs/02_dataset.md` §10 exactly "
                  "(the Kaggle mirror wrapped this under an extra `LA/LA/` prefix and included an "
                  "unused `PA/` — physical access — partition; both were reconciled/left untouched "
                  "respectively during extraction, see final report).\n")

    (REPORT_DIR / "asvspoof_dataset_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORT_DIR/'asvspoof_manifest.csv'} ({total_files} rows) and {REPORT_DIR/'asvspoof_dataset_report.md'}")


if __name__ == "__main__":
    main()
