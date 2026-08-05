"""Category 2 + 4 — AuthZ/privesc and full RBAC matrix.
Every role token (anon, user_a, user_b, admin) x every endpoint. Compares
actual status to the expected access rule:
  public      -> any role should get a real response (not 401/403)
  auth        -> anon should get 401; user_a/user_b/admin should NOT get 401/403
  auth_owner  -> anon 401; non-owner (user_b against user_a's resource) should
                 get 404 (never the owner's data — a 200 here is IDOR, handled
                 in more depth by 03_idor.py, but caught here too)
  admin       -> anon 401; user_a/user_b (non-admin) should get 403; admin should not
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from endpoints import ENDPOINTS, fill_path  # noqa: E402
from http_client import load_input, record, request  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    scan_id = fixtures["user_a_scan_id"]
    share_token = fixtures.get("user_a_share_token", "nonexistent-token")

    roles = {
        "anon": None,
        "user_a": inp["user_a"],
        "user_b": inp["user_b"],
        "admin": inp["admin"],
    }

    # GET-only + safe-POST endpoints only, to keep this a detection pass (no
    # destructive writes). Mutating endpoints (cancel/delete/process/share
    # create-or-revoke, change-password, mark-all-read) are exercised for
    # ownership in 03_idor.py against a role_matrix-safe subset, not blasted
    # here across all 4 roles.
    safe_methods = {"GET"}

    records = []
    for ep in ENDPOINTS:
        if ep["method"] not in safe_methods:
            continue
        path = fill_path(
            ep["path"], scan_id=scan_id,
            notification_id="00000000-0000-0000-0000-000000000000",
            share_token=share_token,
        )
        for role_name, cookie in roles.items():
            res = request(ep["method"], base, path, cookie=cookie)
            status = res["status"]

            access = ep["access"]
            finding = False
            severity = "info"
            note = "as expected"

            if access == "public":
                if status == 401:
                    finding, severity, note = True, "medium", "public endpoint unexpectedly requires auth"
            elif access == "auth":
                if role_name == "anon":
                    if status != 401:
                        finding, severity, note = True, "high", f"expected 401 for anon, got {status}"
                else:
                    if status in (401, 403):
                        finding, severity, note = True, "high", f"authenticated {role_name} got {status} on an any-auth endpoint"
            elif access == "auth_owner":
                if role_name == "anon":
                    if status != 401:
                        finding, severity, note = True, "high", f"expected 401 for anon, got {status}"
                elif role_name == "user_a":
                    if status not in (200,):
                        note = f"owner got non-200 ({status}) — may be a legitimate business-state error, see notes"
                elif role_name in ("user_b", "admin"):
                    if status == 200:
                        finding, severity, note = True, "critical", f"IDOR: {role_name} (non-owner) got 200 on user_a's resource"
            elif access == "admin":
                if role_name == "anon":
                    if status != 401:
                        finding, severity, note = True, "high", f"expected 401 for anon, got {status}"
                elif role_name in ("user_a", "user_b"):
                    if status != 403:
                        finding, severity, note = True, "critical", f"privesc: non-admin {role_name} got {status} (expected 403) on admin-only endpoint"
                elif role_name == "admin":
                    if status not in (200,):
                        note = f"admin got non-200 ({status})"

            record(
                records,
                endpoint=path, method=ep["method"], role=role_name,
                status=status, expected_status=access,
                finding=finding, severity=severity,
                response_time_ms=res["response_time_ms"], test_category="rbac_matrix",
                note=note,
            )

    out = ROOT / "results" / "04_rbac_matrix.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"RBAC matrix: {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN [{f['severity']}]: {f['method']} {f['endpoint']} ({f['role']}) -> {f['status']} :: {f['note']}")


if __name__ == "__main__":
    main()
