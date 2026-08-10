"""Appends this CI run's build number to the GitHub Pages history manifest
(reports/history/index.json) that trends.html reads client-side.

Called from .github/workflows/qa-suite.yml's deploy-appium-report job —
kept as a real script rather than an inline YAML heredoc so it can be read/
tested like the rest of this repo's report tooling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MAX_BUILDS = 50


def main() -> None:
    if len(sys.argv) != 4:
        print("usage: update_history_manifest.py <build_number> <prev_manifest_path> <out_manifest_path>")
        sys.exit(1)

    build_number = int(sys.argv[1])
    prev_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    builds: list[int] = []
    if prev_path.exists():
        try:
            builds = json.loads(prev_path.read_text(encoding="utf-8")).get("builds", [])
        except json.JSONDecodeError:
            builds = []

    if build_number not in builds:
        builds.append(build_number)
    builds = builds[-MAX_BUILDS:]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"builds": builds}, indent=2), encoding="utf-8")
    print("history/index.json builds:", builds)


if __name__ == "__main__":
    main()
