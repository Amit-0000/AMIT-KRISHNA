"""Parses the k6 raw JSON stream (performance/results/raw_metrics.json) and the
docker-stats resource sampler CSV into the plain deliverables:
  performance/baseline_results.csv
  performance/baseline_results.json
  performance/baseline_report.md

Pure stdlib (no pandas/numpy) since neither is installed in this environment.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RAW_METRICS = ROOT / "results" / "raw_metrics.json"
RESOURCE_CSV = ROOT / "results" / "resource_usage.csv"
K6_SUMMARY = ROOT / "results" / "summary.json"

OUT_CSV = ROOT / "baseline_results.csv"
OUT_JSON = ROOT / "baseline_results.json"
OUT_MD = ROOT / "baseline_report.md"


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def load_requests() -> list[dict]:
    requests = []
    with RAW_METRICS.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("metric") != "http_req_duration" or d.get("type") != "Point":
                continue
            data = d["data"]
            tags = data.get("tags", {})
            requests.append(
                {
                    "time": data["time"],
                    "duration_ms": data["value"],
                    "endpoint": tags.get("name", "unknown"),
                    "method": tags.get("method", ""),
                    "status": tags.get("status", "0"),
                    "vu": tags.get("vu", ""),
                    "expected_response": tags.get("expected_response", "false") == "true",
                }
            )
    requests.sort(key=lambda r: r["time"])
    return requests


def load_resource_usage() -> list[dict]:
    if not RESOURCE_CSV.exists():
        return []
    with RESOURCE_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_overall(requests: list[dict], test_duration_s: float) -> dict:
    total = len(requests)
    successful = [r for r in requests if r["expected_response"]]
    failed = [r for r in requests if not r["expected_response"]]
    durations = sorted(r["duration_ms"] for r in requests)

    data_sent = None
    data_received = None
    if K6_SUMMARY.exists():
        k6_summary = json.loads(K6_SUMMARY.read_text(encoding="utf-8"))
        data_sent = k6_summary["metrics"].get("data_sent", {}).get("values", {}).get("count")
        data_received = k6_summary["metrics"].get("data_received", {}).get("values", {}).get("count")

    return {
        "virtual_users": 100,
        "duration_s": round(test_duration_s, 1),
        "total_requests": total,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "requests_per_second": round(total / test_duration_s, 2) if test_duration_s else 0,
        "avg_response_time_ms": round(statistics.mean(durations), 2) if durations else 0,
        "median_response_time_ms": round(statistics.median(durations), 2) if durations else 0,
        "min_response_time_ms": round(min(durations), 2) if durations else 0,
        "max_response_time_ms": round(max(durations), 2) if durations else 0,
        "p90_response_time_ms": round(percentile(durations, 90), 2),
        "p95_response_time_ms": round(percentile(durations, 95), 2),
        "p99_response_time_ms": round(percentile(durations, 99), 2),
        "error_rate_pct": round(100 * len(failed) / total, 2) if total else 0,
        "success_rate_pct": round(100 * len(successful) / total, 2) if total else 0,
        "data_sent_bytes": data_sent,
        "data_received_bytes": data_received,
    }


def build_endpoints(requests: list[dict]) -> list[dict]:
    by_endpoint: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in requests:
        by_endpoint[(r["endpoint"], r["method"])].append(r)

    rows = []
    for (endpoint, method), reqs in sorted(by_endpoint.items()):
        durations = sorted(r["duration_ms"] for r in reqs)
        successful = [r for r in reqs if r["expected_response"]]
        n = len(reqs)
        rows.append(
            {
                "endpoint": endpoint,
                "method": method,
                "requests": n,
                "avg_response_ms": round(statistics.mean(durations), 2) if durations else 0,
                "min_ms": round(min(durations), 2) if durations else 0,
                "max_ms": round(max(durations), 2) if durations else 0,
                "p95_ms": round(percentile(durations, 95), 2),
                "p99_ms": round(percentile(durations, 99), 2),
                "success_pct": round(100 * len(successful) / n, 2) if n else 0,
                "failure_pct": round(100 * (n - len(successful)) / n, 2) if n else 0,
            }
        )
    return rows


def build_status_codes(requests: list[dict]) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for r in requests:
        counts[r["status"]] += 1
    total = len(requests)
    rows = [
        {"status_code": code, "count": count, "percentage": round(100 * count / total, 2) if total else 0}
        for code, count in sorted(counts.items())
    ]
    return rows


def build_distribution(requests: list[dict]) -> list[dict]:
    buckets = [
        ("0-50", 0, 50),
        ("51-100", 51, 100),
        ("101-200", 101, 200),
        ("201-500", 201, 500),
        ("501-1000", 501, 1000),
        ("1000+", 1001, math.inf),
    ]
    rows = []
    for label, lo, hi in buckets:
        count = sum(1 for r in requests if lo <= r["duration_ms"] <= hi)
        rows.append({"time_range_ms": label, "request_count": count})
    return rows


def build_resource_summary(resource_rows: list[dict]) -> dict:
    by_container: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"cpu": [], "mem": []})
    for row in resource_rows:
        c = row["container"]
        by_container[c]["cpu"].append(float(row["cpu_pct"]))
        by_container[c]["mem"].append(float(row["mem_usage_mb"]))
    summary = {}
    for c, vals in by_container.items():
        summary[c] = {
            "avg_cpu_pct": round(statistics.mean(vals["cpu"]), 2) if vals["cpu"] else 0,
            "max_cpu_pct": round(max(vals["cpu"]), 2) if vals["cpu"] else 0,
            "avg_mem_mb": round(statistics.mean(vals["mem"]), 2) if vals["mem"] else 0,
            "max_mem_mb": round(max(vals["mem"]), 2) if vals["mem"] else 0,
        }
    return summary


def main():
    requests = load_requests()
    resource_rows = load_resource_usage()

    if requests:
        t0 = datetime.fromisoformat(requests[0]["time"].replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(requests[-1]["time"].replace("Z", "+00:00"))
        test_duration_s = max((t1 - t0).total_seconds(), 1.0)
    else:
        test_duration_s = 60.0

    overall = build_overall(requests, test_duration_s)
    endpoints = build_endpoints(requests)
    status_codes = build_status_codes(requests)
    distribution = build_distribution(requests)
    resource_summary = build_resource_summary(resource_rows)

    result = {
        "test_metadata": {
            "project": "VoiceGuard",
            "test_type": "Baseline Load Test",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_window_start": requests[0]["time"] if requests else None,
            "test_window_end": requests[-1]["time"] if requests else None,
        },
        "overall_performance": overall,
        "endpoint_performance": endpoints,
        "http_status_codes": status_codes,
        "response_time_distribution": distribution,
        "resource_usage_summary": resource_summary,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "virtual_user", "endpoint", "method", "status_code", "response_time_ms", "success"])
        for r in requests:
            writer.writerow(
                [r["time"], r["vu"], r["endpoint"], r["method"], r["status"], round(r["duration_ms"], 3), r["expected_response"]]
            )

    md_lines = [
        "# VoiceGuard Baseline Load Test Report",
        "",
        f"Generated: {result['test_metadata']['generated_at']}",
        "",
        "## Overall Performance",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for k, v in overall.items():
        md_lines.append(f"| {k.replace('_', ' ').title()} | {v} |")

    md_lines += ["", "## Endpoint Performance", "", "| Endpoint | Method | Requests | Avg (ms) | P95 (ms) | P99 (ms) | Success % |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for e in endpoints:
        md_lines.append(
            f"| {e['endpoint']} | {e['method']} | {e['requests']} | {e['avg_response_ms']} | {e['p95_ms']} | {e['p99_ms']} | {e['success_pct']} |"
        )

    md_lines += ["", "## HTTP Status Codes", "", "| Status | Count | % |", "| --- | --- | --- |"]
    for s in status_codes:
        md_lines.append(f"| {s['status_code']} | {s['count']} | {s['percentage']} |")

    md_lines += ["", "## Response Time Distribution", "", "| Range (ms) | Count |", "| --- | --- |"]
    for d in distribution:
        md_lines.append(f"| {d['time_range_ms']} | {d['request_count']} |")

    md_lines += ["", "## Resource Usage Summary", "", "| Container | Avg CPU % | Max CPU % | Avg Mem (MB) | Max Mem (MB) |", "| --- | --- | --- | --- | --- |"]
    for c, s in resource_summary.items():
        md_lines.append(f"| {c} | {s['avg_cpu_pct']} | {s['max_cpu_pct']} | {s['avg_mem_mb']} | {s['max_mem_mb']} |")

    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("Wrote:", OUT_JSON, OUT_CSV, OUT_MD)
    print("Overall:", json.dumps(overall, indent=2))


if __name__ == "__main__":
    main()
