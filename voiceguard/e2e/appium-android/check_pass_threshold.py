"""Real pass/fail gate for the appium-android-tests job.

Reads e2e/results/appium_android_summary.json (already produced by
parse_results.py from the real pytest-json-report output) and decides
whether the job should succeed, based on an explicit, configurable pass-rate
threshold (APPIUM_ANDROID_MIN_PASS_RATE, default 90) — same pattern as
../appium/check_pass_threshold.py, own env var/filenames so this job's gate
is independent of the mobile-web job's.

Exit codes:
  0 - genuine success: a report exists, at least one test executed, and the
      pass rate among executed tests meets the threshold.
  1 - genuine failure: either no report was produced (emulator/Appium/APK-
      build never got far enough to run tests), zero tests executed, or the
      pass rate is below threshold. Never silently converted to a pass.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
SUMMARY_JSON = ROOT.parent / "results" / "appium_android_summary.json"

MIN_PASS_RATE = float(os.environ.get("APPIUM_ANDROID_MIN_PASS_RATE", "90"))


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
                "### Appium Android Native App Test Summary",
                "",
                f"`{SUMMARY_JSON}` was not produced — the suite never reached the point "
                "of writing results (emulator, Appium server, or APK build failure "
                "upstream of test collection).",
                "",
                "**Result: FAIL**",
            ]
        )
        print("No appium_android_summary.json found — genuine infra failure, not a threshold miss.")
        return 1

    data = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))

    if data.get("status") != "OK":
        write_step_summary(
            [
                "### Appium Android Native App Test Summary",
                "",
                f"No usable results: {data.get('note', 'unknown error')}",
                "",
                "**Result: FAIL**",
            ]
        )
        print("appium_android_summary.json has no usable results — genuine infra failure.")
        return 1

    t = data["totals"]
    env = data.get("environment", {})
    executed = t["executed"]
    pass_pct = t["pass_pct"]
    passed_threshold = executed > 0 and pass_pct >= MIN_PASS_RATE
    result = "PASS" if passed_threshold else "FAIL"

    device = f"Android Emulator ({env.get('ANDROID_PROFILE', 'unknown')}, API {env.get('ANDROID_API_LEVEL', '?')})"

    write_step_summary(
        [
            "### Appium Android Native App Test Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Device | {device} |",
            f"| Android | {env.get('ANDROID_API_LEVEL', 'unknown')} ({env.get('ANDROID_TARGET', '')}/{env.get('ANDROID_ARCH', '')}) |",
            f"| App | {env.get('APP_PACKAGE', 'com.voiceguard.app')} (debug APK) |",
            f"| Total | {t['total']} |",
            f"| Passed | {t['passed']} |",
            f"| Failed | {t['failed']} |",
            f"| Skipped | {t['skipped']} |",
            f"| Pass Rate | {pass_pct}% |",
            f"| Required | {MIN_PASS_RATE}% |",
            f"| Result | {result} |",
        ]
    )
    print(f"Pass rate {pass_pct}% (required {MIN_PASS_RATE}%, executed {executed}) -> {result}")
    return 0 if passed_threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
