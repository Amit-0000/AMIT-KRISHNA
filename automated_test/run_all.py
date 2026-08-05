"""Runs the full VoiceGuard DAST pass end to end, in order. Idempotent-ish:
setup_env.py and lib/fixtures.py are safe to re-run (they reuse existing
accounts/skip already-registered emails; fixtures.py creates a fresh scan
each time, which is harmless).

Requires: backend reachable at the baseUrl in input.json (see README note in
setup_env.py for spinning up postgres+redis+backend via docker compose).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    "setup_env.py",
    "lib/fixtures.py",
    "01_authn_bypass.py",
    "04_rbac_matrix.py",
    "03_idor.py",
    "05_token_tampering.py",
    "06_injection_probe.py",
    "07_rate_limiting.py",
    "08_hardcoded_creds.py",
    "09_generate_report.py",
]


def main() -> None:
    savepoint_path = ROOT / "savepoint.json"
    import json
    savepoint = json.loads(savepoint_path.read_text()) if savepoint_path.exists() else {"completed_steps": []}

    for step in STEPS:
        print(f"\n{'=' * 70}\n>>> {step}\n{'=' * 70}")
        result = subprocess.run([sys.executable, step], cwd=ROOT)
        if result.returncode != 0:
            print(f"STEP FAILED: {step} (exit {result.returncode}) — stopping.")
            savepoint["last_failed_step"] = step
            savepoint_path.write_text(json.dumps(savepoint, indent=2))
            sys.exit(1)
        if step not in savepoint["completed_steps"]:
            savepoint["completed_steps"].append(step)
        savepoint_path.write_text(json.dumps(savepoint, indent=2))

    print("\nAll steps completed. See report.json for the full findings list.")


if __name__ == "__main__":
    main()
