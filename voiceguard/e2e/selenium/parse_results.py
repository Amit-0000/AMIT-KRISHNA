"""Parses e2e/results/selenium_report.json (pytest-json-report output from
the desktop Selenium suite) into the plain deliverable:
  e2e/results/selenium_summary.json

Pure stdlib, no pandas/numpy — same convention as
voiceguard/e2e/appium/parse_results.py (this script is adapted from it: same
shape, browser/viewport metadata instead of Android/emulator metadata, plus
a `priority` field per test read from the real pytest markers registered in
pytest.ini). reports/build_master_test_report.py already reads
selenium_report.json directly for the master workbook's "Selenium (Web
E2E)" sheet — this script produces the sibling artifact used for the HTML/
Excel reports and the GitHub Actions summary, from the same real
pytest-json-report data.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
# e2e/results/, not e2e/selenium/results/ — the same directory
# .github/workflows/qa-suite.yml's selenium-tests job already writes
# selenium_report.json to, shared with the Appium suite's identical output.
RESULTS_DIR = ROOT.parent / "results"
REPORT_JSON = RESULTS_DIR / "selenium_report.json"
OUT_JSON = RESULTS_DIR / "selenium_summary.json"

# Real, fixed values for this suite's CI environment (.github/workflows/
# qa-suite.yml's selenium-tests job runs headless Chrome via the selenium
# pip package's bundled driver management) — not placeholders. Overridable
# via env for local/manual runs against a different Chrome build.
ENV_DEFAULTS = {
    "BROWSER": "Chrome (headless)",
    "WINDOW_SIZE": "1440x900",
    "SELENIUM_BASE_URL": os.environ.get("SELENIUM_BASE_URL", "http://localhost:5173"),
}

PRIORITY_MARKERS = ("critical", "high", "medium", "low")


def module_name(nodeid: str) -> str:
    file_part = nodeid.split("::", 1)[0]
    name = Path(file_part).stem
    if name.startswith("test_"):
        name = name[len("test_"):]
    return name


def outcome_of(test: dict) -> str:
    # pytest-json-report marks reruns' final state on the top-level
    # "outcome" field even when --reruns is active; "call" may be absent
    # for setup-phase errors/skips.
    return test.get("outcome", test.get("call", {}).get("outcome", "unknown"))


def priority_of(test: dict) -> str:
    keywords = test.get("keywords", [])
    for p in PRIORITY_MARKERS:
        if p in keywords:
            return p
    return "unspecified"


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


def build_test_rows(tests: list[dict]) -> list[dict]:
    rows = []
    for i, t in enumerate(tests, start=1):
        call = t.get("call") or {}
        rows.append(
            {
                "test_id": f"SEL-{i:04d}",
                "nodeid": t["nodeid"],
                "module": module_name(t["nodeid"]),
                "test_name": t["nodeid"].split("::")[-1],
                "status": outcome_of(t),
                "priority": priority_of(t),
                "duration_s": round(call.get("duration", 0), 3),
            }
        )
    return rows


def main() -> None:
    if not REPORT_JSON.exists():
        OUT_JSON.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "NO_REPORT",
                    "note": f"{REPORT_JSON} not found — the Selenium suite did not produce a "
                    "pytest-json-report, most likely a Docker Compose stack health-check failure "
                    "upstream of test collection.",
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

    test_rows = build_test_rows(tests)
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
        "environment": dict(ENV_DEFAULTS),
        "module_breakdown": build_module_breakdown(tests),
        "test_rows": test_rows,
        "failed_tests": failed_tests,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Wrote", OUT_JSON)
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
