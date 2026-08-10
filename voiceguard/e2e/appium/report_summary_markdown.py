"""Prints a Markdown table of this run's real Appium execution numbers,
read from appium_summary.json (parse_results.py's output), for
.github/workflows/qa-suite.yml's `summary` job to redirect into
$GITHUB_STEP_SUMMARY.

Kept as a real script rather than an inline YAML heredoc so it can be read/
tested like the rest of this repo's report tooling.
"""
from __future__ import annotations

import json
import sys


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: report_summary_markdown.py <appium_summary.json path>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    print("### Appium (Mobile Web)")
    if data.get("status") != "OK":
        print(f"- {data.get('note', 'No data available for this run.')}")
        return

    t = data["totals"]
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Total | {t['total']} |")
    print(f"| Executed | {t['executed']} |")
    print(f"| Passed | {t['passed']} |")
    print(f"| Failed | {t['failed']} |")
    print(f"| Skipped | {t['skipped']} |")
    print(f"| Pass % | {t['pass_pct']}% |")
    print(f"| Duration | {data['duration_s']}s |")
    if t["pass_pct"] < 95 and t["executed"] > 0:
        print(
            f"\n**WARN:** pass rate {t['pass_pct']}% is below the 95% bar "
            "(non-blocking — see appium-tests job comment)."
        )


if __name__ == "__main__":
    main()
