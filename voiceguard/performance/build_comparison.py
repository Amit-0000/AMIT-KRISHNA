"""Builds performance/performance_before_vs_after.json and .csv by diffing
performance/before/baseline_results.json (pre-fix) against
performance/after/ (post-fix, produced from the same parse_results.py run
against performance/results/raw_metrics.json / resource_usage.csv captured
after the bcrypt/pool fixes). Pure stdlib.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent
BEFORE = json.loads((ROOT / "before" / "baseline_results.json").read_text(encoding="utf-8"))
AFTER = json.loads((ROOT / "baseline_results.json").read_text(encoding="utf-8"))

OUT_JSON = ROOT / "performance_before_vs_after.json"
OUT_CSV = ROOT / "performance_before_vs_after.csv"


def pct_change(before: float, after: float) -> float | None:
    if before == 0:
        return None
    return round(100 * (after - before) / before, 2)


def main() -> None:
    b = BEFORE["overall_performance"]
    a = AFTER["overall_performance"]

    overall_rows = []
    metrics = [
        ("requests_per_second", "Requests/sec", "higher_better"),
        ("avg_response_time_ms", "Avg Response Time (ms)", "lower_better"),
        ("median_response_time_ms", "Median Response Time (ms)", "lower_better"),
        ("p90_response_time_ms", "P90 Response Time (ms)", "lower_better"),
        ("p95_response_time_ms", "P95 Response Time (ms)", "lower_better"),
        ("p99_response_time_ms", "P99 Response Time (ms)", "lower_better"),
        ("max_response_time_ms", "Max Response Time (ms)", "lower_better"),
        ("success_rate_pct", "Success Rate (%)", "higher_better"),
        ("error_rate_pct", "Error Rate (%)", "lower_better"),
        ("total_requests", "Total Requests", "context"),
        ("successful_requests", "Successful Requests", "higher_better"),
        ("failed_requests", "Failed Requests", "lower_better"),
    ]
    for key, label, direction in metrics:
        overall_rows.append(
            {
                "metric": label,
                "before": b.get(key),
                "after": a.get(key),
                "pct_change": pct_change(b.get(key) or 0, a.get(key) or 0),
                "direction": direction,
            }
        )

    endpoint_rows = []
    b_by_ep = {(e["endpoint"], e["method"]): e for e in BEFORE["endpoint_performance"]}
    a_by_ep = {(e["endpoint"], e["method"]): e for e in AFTER["endpoint_performance"]}
    for key in sorted(set(b_by_ep) | set(a_by_ep)):
        be = b_by_ep.get(key, {})
        ae = a_by_ep.get(key, {})
        endpoint_rows.append(
            {
                "endpoint": key[0],
                "method": key[1],
                "before_avg_ms": be.get("avg_response_ms"),
                "after_avg_ms": ae.get("avg_response_ms"),
                "before_p95_ms": be.get("p95_ms"),
                "after_p95_ms": ae.get("p95_ms"),
                "before_p99_ms": be.get("p99_ms"),
                "after_p99_ms": ae.get("p99_ms"),
                "before_success_pct": be.get("success_pct"),
                "after_success_pct": ae.get("success_pct"),
            }
        )

    resource_rows = []
    b_res = BEFORE["resource_usage_summary"]
    a_res = AFTER["resource_usage_summary"]
    for container in sorted(set(b_res) | set(a_res)):
        br = b_res.get(container, {})
        ar = a_res.get(container, {})
        resource_rows.append(
            {
                "container": container,
                "before_avg_cpu_pct": br.get("avg_cpu_pct"),
                "after_avg_cpu_pct": ar.get("avg_cpu_pct"),
                "before_max_cpu_pct": br.get("max_cpu_pct"),
                "after_max_cpu_pct": ar.get("max_cpu_pct"),
                "before_avg_mem_mb": br.get("avg_mem_mb"),
                "after_avg_mem_mb": ar.get("avg_mem_mb"),
                "before_max_mem_mb": br.get("max_mem_mb"),
                "after_max_mem_mb": ar.get("max_mem_mb"),
            }
        )

    status_rows = []
    b_status = {s["status_code"]: s for s in BEFORE["http_status_codes"]}
    a_status = {s["status_code"]: s for s in AFTER["http_status_codes"]}
    for code in sorted(set(b_status) | set(a_status)):
        status_rows.append(
            {
                "status_code": code,
                "before_count": b_status.get(code, {}).get("count", 0),
                "before_pct": b_status.get(code, {}).get("percentage", 0),
                "after_count": a_status.get(code, {}).get("count", 0),
                "after_pct": a_status.get(code, {}).get("percentage", 0),
            }
        )

    result = {
        "test_metadata": {
            "project": "VoiceGuard",
            "test_type": "Before vs After Performance Fix Comparison",
            "root_cause": "bcrypt.checkpw/hashpw executed synchronously inside async auth routes, "
            "blocking the single asyncio event loop for ~150-300ms per call",
            "fix_summary": [
                "api/core/security.py: hash_password/verify_password now run bcrypt via "
                "asyncio.to_thread instead of directly on the event loop",
                "api/core/config.py + api/.env.example: DB_POOL_MIN_SIZE/MAX_SIZE raised "
                "5/20 -> 10/50 (pool exhaustion surfaced once bcrypt stopped serializing "
                "requests and real concurrency hit the database)",
                "api/core/config.py: REDIS_POOL_MAX_SIZE raised 10 -> 50 (same reason, for "
                "the rate-limiter's Redis connections)",
                "performance/k6/baseline_load_test.js: session cookies are now captured "
                "from the login response and attached explicitly as a Cookie header on "
                "every subsequent request — a test-harness fix (this k6 build's implicit "
                "per-VU cookie jar did not reliably persist across iterations under load), "
                "not a change to the traffic mix, VU/stage profile, or thresholds",
            ],
        },
        "overall_comparison": overall_rows,
        "endpoint_comparison": endpoint_rows,
        "resource_comparison": resource_rows,
        "http_status_comparison": status_rows,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["=== OVERALL METRICS ==="])
        writer.writerow(["Metric", "Before", "After", "% Change", "Direction"])
        for r in overall_rows:
            writer.writerow([r["metric"], r["before"], r["after"], r["pct_change"], r["direction"]])

        writer.writerow([])
        writer.writerow(["=== ENDPOINT PERFORMANCE ==="])
        writer.writerow(
            [
                "Endpoint", "Method", "Before Avg (ms)", "After Avg (ms)", "Before P95 (ms)", "After P95 (ms)",
                "Before P99 (ms)", "After P99 (ms)", "Before Success %", "After Success %",
            ]
        )
        for r in endpoint_rows:
            writer.writerow(
                [
                    r["endpoint"], r["method"], r["before_avg_ms"], r["after_avg_ms"], r["before_p95_ms"],
                    r["after_p95_ms"], r["before_p99_ms"], r["after_p99_ms"], r["before_success_pct"],
                    r["after_success_pct"],
                ]
            )

        writer.writerow([])
        writer.writerow(["=== RESOURCE USAGE ==="])
        writer.writerow(
            [
                "Container", "Before Avg CPU %", "After Avg CPU %", "Before Max CPU %", "After Max CPU %",
                "Before Avg Mem (MB)", "After Avg Mem (MB)", "Before Max Mem (MB)", "After Max Mem (MB)",
            ]
        )
        for r in resource_rows:
            writer.writerow(
                [
                    r["container"], r["before_avg_cpu_pct"], r["after_avg_cpu_pct"], r["before_max_cpu_pct"],
                    r["after_max_cpu_pct"], r["before_avg_mem_mb"], r["after_avg_mem_mb"], r["before_max_mem_mb"],
                    r["after_max_mem_mb"],
                ]
            )

        writer.writerow([])
        writer.writerow(["=== HTTP STATUS DISTRIBUTION ==="])
        writer.writerow(["Status Code", "Before Count", "Before %", "After Count", "After %"])
        for r in status_rows:
            writer.writerow([r["status_code"], r["before_count"], r["before_pct"], r["after_count"], r["after_pct"]])

    print("Wrote:", OUT_JSON, OUT_CSV)


if __name__ == "__main__":
    main()
