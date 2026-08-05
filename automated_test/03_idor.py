"""Category 3 — IDOR, deeper pass on mutating (non-GET) owner-scoped
endpoints. RBAC matrix (04) already covered GET endpoints; this covers
POST/PATCH/DELETE against user_a's fixture scan using user_b's token, which
04 skips to stay GET-only. Never calls DELETE as the owner (would destroy
the shared fixture) — only as the non-owner, where it's expected to fail
and therefore safe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from http_client import load_input, record, request  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    scan_id = fixtures["user_a_scan_id"]

    records = []

    mutating_checks = [
        ("POST", f"/api/v1/scans/{scan_id}/cancel"),
        ("POST", f"/api/v1/scans/{scan_id}/process"),
        ("POST", f"/api/v1/scans/{scan_id}/share"),
        ("DELETE", f"/api/v1/scans/{scan_id}/share"),
        ("DELETE", f"/api/v1/scans/{scan_id}"),  # last: non-owner delete attempt only
    ]

    for method, path in mutating_checks:
        res = request(method, base, path, cookie=inp["user_b"])
        status = res["status"]
        is_success = status is not None and 200 <= status < 300
        record(
            records,
            endpoint=path, method=method, role="user_b_against_user_a_resource",
            status=status, expected_status="403 or 404",
            finding=is_success, severity="critical" if is_success else "info",
            response_time_ms=res["response_time_ms"], test_category="idor",
            note=(f"IDOR: non-owner mutation succeeded ({status})" if is_success
                  else f"correctly blocked ({status})"),
        )

    # Confirm the fixture scan still exists and is unmodified after the non-owner
    # delete attempt above (proves the blocked DELETE was a no-op, not just a
    # response-code lie).
    verify = request("GET", base, f"/api/v1/scans/{scan_id}", cookie=inp["user_a"])
    still_exists = verify["status"] == 200
    record(
        records,
        endpoint=f"/api/v1/scans/{scan_id}", method="GET", role="user_a_post_verify",
        status=verify["status"], expected_status=200,
        finding=not still_exists, severity="critical" if not still_exists else "info",
        response_time_ms=verify["response_time_ms"], test_category="idor",
        note=("CRITICAL: fixture scan was actually deleted by the blocked non-owner "
              "DELETE call (response code lied)" if not still_exists
              else "fixture scan intact after blocked non-owner DELETE attempt"),
    )

    # Notifications: no code path in this codebase ever creates a notification
    # (grepped api/ — notifications.service is only imported by its own
    # router/repository), so there is no real notification to IDOR-test
    # ownership against. Recorded as a coverage gap, not a finding.
    record(
        records,
        endpoint="/api/v1/notifications/{id}", method="PATCH/DELETE", role="n/a",
        status=None, expected_status="n/a",
        finding=False, severity="info",
        response_time_ms=None, test_category="idor",
        note=("COVERAGE GAP: no code path in the app creates a Notification row, "
              "so ownership on notification endpoints could only be tested against "
              "a nonexistent id (see 04_rbac_matrix.py, which confirms 401/404 there). "
              "Not exploitable now, but if a future feature starts creating "
              "notifications, re-run IDOR testing against a real one."),
    )

    out = ROOT / "results" / "03_idor.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"IDOR (mutating): {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN [{f['severity']}]: {f['method']} {f['endpoint']} -> {f['status']} :: {f['note']}")


if __name__ == "__main__":
    main()
