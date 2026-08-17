"""Parses e2e/results/appium_android_report.json (pytest-json-report output
from the native Android app suite) into the plain deliverable:
  e2e/results/appium_android_summary.json

Sibling to ../appium/parse_results.py, adapted for this suite's own
report/summary filenames and environment (a packaged APK + real device
emulator, not mobile Chrome) rather than sharing one script across both —
matches the existing convention of ../appium and ../selenium each owning
their own copy rather than a shared library.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS_DIR = ROOT.parent / "results"
REPORT_JSON = RESULTS_DIR / "appium_android_report.json"
OUT_JSON = RESULTS_DIR / "appium_android_summary.json"

ENV_DEFAULTS = {
    "ANDROID_API_LEVEL": "33",
    "ANDROID_TARGET": "google_apis",
    "ANDROID_ARCH": "x86_64",
    "ANDROID_PROFILE": "pixel_5",
    "APPIUM_VERSION": "3.6.0",
    "UIAUTOMATOR2_DRIVER_VERSION": "8.2.2",
    "APP_PACKAGE": "com.voiceguard.app",
}


def module_name(nodeid: str) -> str:
    file_part = nodeid.split("::", 1)[0]
    name = Path(file_part).stem
    if name.startswith("test_"):
        name = name[len("test_"):]
    return name


def outcome_of(test: dict) -> str:
    return test.get("outcome", test.get("call", {}).get("outcome", "unknown"))


def failure_reason(test: dict) -> str | None:
    call = test.get("call") or {}
    longrepr = call.get("longrepr")
    if not longrepr:
        setup = test.get("setup") or {}
        longrepr = setup.get("longrepr")
    if not longrepr:
        return None
    text = str(longrepr)
    return text if len(text) <= 2000 else text[:2000] + "… (truncated)"


def build_module_breakdown(tests: list[dict]) -> list[dict]:
    by_module: dict[str, dict[str, int]] = {}
    for t in tests:
        m = module_name(t["nodeid"])
        bucket = by_module.setdefault(m, {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
        bucket["total"] += 1
        outcome = outcome_of(t)
        if outcome == "passed":
            bucket["passed"] += 1
        elif outcome == "skipped":
            bucket["skipped"] += 1
        else:
            bucket["failed"] += 1
    rows = []
    for m, b in sorted(by_module.items()):
        pass_pct = round(100 * b["passed"] / b["total"], 2) if b["total"] else 0
        rows.append({"module": m, **b, "pass_pct": pass_pct})
    return rows


def main() -> None:
    if not REPORT_JSON.exists():
        OUT_JSON.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "NO_REPORT",
                    "note": f"{REPORT_JSON} not found — the suite did not reach the point of writing a "
                    "pytest-json-report, most likely an emulator/Appium-server/APK-build failure upstream "
                    "of test collection.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"No report found at {REPORT_JSON}; wrote NO_REPORT summary to {OUT_JSON}")
        return

    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    tests = data.get("tests", [])
    summary = data.get("summary", {})

    total = summary.get("total", len(tests))
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0) + summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    executed = passed + failed
    pass_pct = round(100 * passed / executed, 2) if executed else 0.0

    failed_tests = [
        {
            "nodeid": t["nodeid"],
            "module": module_name(t["nodeid"]),
            "reason": failure_reason(t),
            "duration_s": round(t.get("call", {}).get("duration", 0), 3),
        }
        for t in tests
        if outcome_of(t) not in ("passed", "skipped")
    ]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "OK",
        "totals": {
            "total": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_pct": pass_pct,
        },
        "duration_s": round(data.get("duration", 0), 2),
        "environment": {k: os.environ.get(k, v) for k, v in ENV_DEFAULTS.items()},
        "module_breakdown": build_module_breakdown(tests),
        "failed_tests": failed_tests,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Wrote", OUT_JSON)
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
