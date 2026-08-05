"""Category 6 — Injection probe (detection only, no exploitation).
Sends classic SQLi/NoSQLi payloads into login credentials, register fields,
scan-list query params, and the scan_id path segment. Flags anomalies:
500s, DB error text leaking into responses, or response-time outliers that
would suggest a time-based blind injection.

Static note: grepped api/ for raw SQL string interpolation — every query in
this codebase goes through SQLAlchemy's select()/execute() with bound
parameters (no f-string/```.format()``` building SQL), so this is a
confirmation pass, not a blind probe.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from http_client import load_input, record, request  # noqa: E402

ROOT = Path(__file__).resolve().parent

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1--",
    "'; DROP TABLE users;--",
    "' UNION SELECT NULL--",
    "admin'--",
]
NOSQLI_PAYLOADS = [
    {"$ne": None},
    {"$gt": ""},
]
TIME_BASED_PAYLOADS = [
    "' OR SLEEP(5)--",
    "'; SELECT pg_sleep(5);--",
]

DB_ERROR_SIGNATURES = [
    "psycopg", "asyncpg", "sqlalchemy", "syntax error", "sqlite3",
    "IntegrityError", "OperationalError", "postgresql", "traceback",
]


def looks_like_db_error(body) -> bool:
    text = json.dumps(body) if not isinstance(body, str) else body
    low = text.lower()
    return any(sig.lower() in low for sig in DB_ERROR_SIGNATURES)


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    scan_id = fixtures["user_a_scan_id"]

    records = []

    # 1. Login email/password fields
    for payload in SQLI_PAYLOADS:
        res = request("POST", base, "/api/v1/auth/login", json_body={"email": payload, "password": payload})
        anomaly = looks_like_db_error(res["body"]) or res["status"] == 500
        record(
            records, endpoint="/api/v1/auth/login", method="POST", role="anon",
            status=res["status"], expected_status="401/422 (never 500 or DB error text)",
            finding=anomaly, severity="high" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"payload={payload!r} -> anomalous response" if anomaly else f"payload={payload!r} handled safely"),
        )

    # 2. Register email field
    for payload in SQLI_PAYLOADS:
        res = request("POST", base, "/api/v1/auth/register", json_body={
            "email": f"probe{abs(hash(payload))}@example.com",
            "password": "ValidPass!2026x",
            "display_name": payload,
        })
        anomaly = looks_like_db_error(res["body"]) or res["status"] == 500
        record(
            records, endpoint="/api/v1/auth/register", method="POST", role="anon",
            status=res["status"], expected_status="201/422 (never 500 or DB error text)",
            finding=anomaly, severity="high" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"display_name payload={payload!r} -> anomalous response" if anomaly else "handled safely"),
        )

    # 3. scan_id path segment (FastAPI types this as uuid.UUID, so a non-UUID
    # payload should be a clean 422, not reach the DB layer at all)
    for payload in SQLI_PAYLOADS:
        res = request("GET", base, f"/api/v1/scans/{payload}", cookie=inp["user_a"])
        anomaly = looks_like_db_error(res["body"]) or res["status"] == 500
        record(
            records, endpoint="/api/v1/scans/{scan_id}", method="GET", role="user_a",
            status=res["status"], expected_status="422 (UUID type validation)",
            finding=anomaly, severity="high" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"scan_id payload={payload!r} -> anomalous response" if anomaly else "handled safely"),
        )

    # 4. list_scans query params (status filter, sort) — status_filter is a
    # typed enum, sort is a Literal, so injection should be rejected by
    # FastAPI/Pydantic before ever reaching the query builder.
    for payload in SQLI_PAYLOADS:
        res = request("GET", base, f"/api/v1/scans?status={payload}", cookie=inp["user_a"])
        anomaly = looks_like_db_error(res["body"]) or res["status"] == 500
        record(
            records, endpoint="/api/v1/scans?status=", method="GET", role="user_a",
            status=res["status"], expected_status="422 (enum validation)",
            finding=anomaly, severity="high" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"status payload={payload!r} -> anomalous response" if anomaly else "handled safely"),
        )

    # 5. Time-based blind SQLi on login — compare response time against a
    # baseline of normal failed logins. A >3s delta would indicate the
    # payload actually reached and executed against the DB.
    baseline_times = []
    for _ in range(3):
        r = request("POST", base, "/api/v1/auth/login", json_body={"email": "nobody@example.com", "password": "x"})
        if r["response_time_ms"]:
            baseline_times.append(r["response_time_ms"])
    baseline = statistics.median(baseline_times) if baseline_times else 200

    for payload in TIME_BASED_PAYLOADS:
        res = request("POST", base, "/api/v1/auth/login", json_body={"email": payload, "password": payload}, max_time=15)
        delta = (res["response_time_ms"] or 0) - baseline
        anomaly = delta > 3000
        record(
            records, endpoint="/api/v1/auth/login", method="POST", role="anon",
            status=res["status"], expected_status=f"~{baseline:.0f}ms (baseline), no multi-second delay",
            finding=anomaly, severity="critical" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"time-based payload={payload!r} delta={delta:.0f}ms vs baseline {baseline:.0f}ms"
                  + (" -- POSSIBLE BLIND SQLI" if anomaly else " -- no delay, safe")),
        )

    # 6. NoSQLi-style operator injection (this app has no NoSQL store, but a
    # dict payload where a string is expected exercises Pydantic's type
    # rejection — confirms it doesn't silently coerce/ignore unexpected types)
    for payload in NOSQLI_PAYLOADS:
        res = request("POST", base, "/api/v1/auth/login", json_body={"email": payload, "password": "x"})
        anomaly = res["status"] == 500 or (res["status"] == 200)
        record(
            records, endpoint="/api/v1/auth/login", method="POST", role="anon",
            status=res["status"], expected_status="422 (type validation)",
            finding=anomaly, severity="high" if anomaly else "info",
            response_time_ms=res["response_time_ms"], test_category="injection_probe",
            note=(f"NoSQLi-style operator payload {payload} -> {res['status']}"),
        )

    out = ROOT / "results" / "06_injection_probe.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"Injection probe: {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN [{f['severity']}]: {f['method']} {f['endpoint']} -> {f['status']} :: {f['note']}")


if __name__ == "__main__":
    main()
