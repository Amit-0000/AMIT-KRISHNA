"""Real pass/fail gate for the selenium-tests job.

Reads e2e/results/selenium_summary.json (already produced by
parse_results.py from the real pytest-json-report output) and decides
whether the `selenium-tests` job should succeed, based on an explicit,
configurable pass-rate threshold (SELENIUM_MIN_PASS_RATE, default 90)
rather than a hard requirement that every single test pass.

pass_rate = passed / (passed + failed + skipped) * 100

Skipped tests are never counted as passed, and are not excluded from the
denominator either -- they count against the rate, same as parse_results.py's
own `total` (which already equals passed + failed + skipped).

Also writes the required-format table into $GITHUB_STEP_SUMMARY so the
GitHub Actions UI shows the actual numbers behind that decision.

Exit codes:
  0 - genuine success: a report exists, at least one test executed, and the
      pass rate meets the threshold.
  1 - genuine failure: either no report was produced (Docker stack/test
      collection failure), zero tests ran, or the pass rate is below
      threshold. Never silently converted to a pass.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
SUMMARY_JSON = ROOT.parent / "results" / "selenium_summary.json"

MIN_PASS_RATE = float(os.environ.get("SELENIUM_MIN_PASS_RATE", "90"))


def write_step_summary(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    text = "\n".join(lines) + "\n"
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


def main() -> int:
    if not SUMMARY_JSON.exists():
        write_step_summary(
            [
                "### Selenium Web E2E Test Summary",
                "",
                f"`{SUMMARY_JSON}` was not produced — the suite never reached the point "
                "of writing results (Docker Compose stack or test-collection failure "
                "upstream of the pytest run).",
                "",
                "**Result: FAIL**",
            ]
        )
        print("No selenium_summary.json found — genuine infra failure, not a threshold miss.")
        return 1

    data = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))

    if data.get("status") != "OK":
        write_step_summary(
            [
                "### Selenium Web E2E Test Summary",
                "",
                f"No usable results: {data.get('note', 'unknown error')}",
                "",
                "**Result: FAIL**",
            ]
        )
        print("selenium_summary.json has no usable results — genuine infra failure.")
        return 1

    t = data["totals"]
    env = data.get("environment", {})
    passed = t["passed"]
    failed = t["failed"]
    skipped = t["skipped"]
    denominator = passed + failed + skipped
    pass_rate = round(100 * passed / denominator, 2) if denominator else 0.0
    ran_at_all = denominator > 0
    passed_threshold = ran_at_all and pass_rate >= MIN_PASS_RATE
    result = "PASS" if passed_threshold else "FAIL"

    write_step_summary(
        [
            "### Selenium Web E2E Test Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Browser | {env.get('BROWSER', 'unknown')} |",
            f"| Window size | {env.get('WINDOW_SIZE', 'unknown')} |",
            f"| Total | {t['total']} |",
            f"| Passed | {passed} |",
            f"| Failed | {failed} |",
            f"| Skipped | {skipped} |",
            f"| Pass Rate | {pass_rate}% |",
            f"| Required | {MIN_PASS_RATE}% |",
            f"| Result | {result} |",
        ]
    )
    print(f"Pass rate {pass_rate}% (required {MIN_PASS_RATE}%, passed {passed}/{denominator}) -> {result}")
    return 0 if passed_threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
