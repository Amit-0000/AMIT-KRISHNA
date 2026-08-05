"""Creates real, owned resources (a scan, a share, a notification) needed as
IDOR/RBAC test targets. Uses only safe writes (POST of a scan owned by our
own test account) — no destructive ops on data we don't own.
"""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_client import load_input  # noqa: E402


def make_valid_wav_bytes(seconds: float = 1.0) -> bytes:
    """Minimal valid 16-bit PCM mono WAV so upload validation (min 1024 bytes,
    real audio content for downstream preprocessing) passes."""
    sample_rate = 16000
    n_samples = int(sample_rate * seconds)
    data = struct.pack("<" + "h" * n_samples, *([0] * n_samples))
    byte_rate = sample_rate * 2
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


def create_scan(base_url: str, cookie: str) -> dict:
    wav = make_valid_wav_bytes(2.0)
    files = {"file": ("dast_fixture.wav", io.BytesIO(wav), "audio/wav")}
    r = requests.post(f"{base_url}/api/v1/scans", cookies={"access_token": cookie}, files=files, timeout=15)
    r.raise_for_status()
    return r.json()["data"]["scan"]


def create_share(base_url: str, cookie: str, scan_id: str) -> dict:
    r = requests.post(f"{base_url}/api/v1/scans/{scan_id}/share", cookies={"access_token": cookie}, timeout=15)
    r.raise_for_status()
    return r.json()["data"]


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    print("Creating a scan owned by user_a...")
    scan = create_scan(base, inp["user_a"])
    print(f"  scan_id = {scan['id']}, status = {scan.get('status')}")

    import json
    fixtures = {"user_a_scan_id": scan["id"]}

    try:
        share = create_share(base, inp["user_a"], scan["id"])
        fixtures["user_a_share_token"] = share["token"]
        print(f"  share token created")
    except Exception as exc:
        print(f"  share creation skipped/failed: {exc}")

    out_path = Path(__file__).resolve().parent.parent / "fixtures.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
