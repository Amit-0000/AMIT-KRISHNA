"""Category 0/1 — AuthN bypass.
For every endpoint whose access rule is auth / auth_owner / admin, hits it
with: (a) no token, (b) a malformed token, (c) an expired token. A 2xx
response in any of these cases is a finding (auth is not being enforced).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from endpoints import ENDPOINTS, fill_path  # noqa: E402
from http_client import load_input, record, request  # noqa: E402

import jwt

ROOT = Path(__file__).resolve().parent


def make_expired_token(secret_guess_list: list[str]) -> str | None:
    """We don't know JWT_SECRET (it's server-side only, correctly not exposed
    anywhere we could read as an external tester) so we can't mint a validly
    -signed expired token. Instead we sign with a garbage secret — decode_access_token
    will reject it on signature, which is the same bucket of 'invalid token' the
    server must reject. This still exercises the auth-bypass check meaningfully:
    the assertion is that *no* malformed/garbage-signed/no-token request succeeds."""
    payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "role": "admin",
        "email_verified": True,
        "iat": int(time.time()) - 3600,
        "exp": int(time.time()) - 1800,  # expired 30 min ago
        "jti": "dast-expired",
    }
    return jwt.encode(payload, "wrong-secret-not-the-real-one", algorithm="HS256")


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    scan_id = fixtures["user_a_scan_id"]

    malformed_token = "not.a.valid.jwt.token.at.all"
    expired_token = make_expired_token([])

    records = []
    tested = [e for e in ENDPOINTS if e["access"] in ("auth", "auth_owner", "admin")]

    for ep in tested:
        path = fill_path(ep["path"], scan_id=scan_id, notification_id="00000000-0000-0000-0000-000000000000")
        for label, cookie in [("no_token", None), ("malformed_token", malformed_token), ("expired_token", expired_token)]:
            res = request(ep["method"], base, path, cookie=cookie)
            status = res["status"]
            is_2xx = status is not None and 200 <= status < 300
            record(
                records,
                endpoint=path, method=ep["method"], role=label,
                status=status, expected_status="401 (or network N/A)",
                finding=is_2xx, severity="critical" if is_2xx else "info",
                response_time_ms=res["response_time_ms"], test_category="authn_bypass",
                note=("VULNERABLE: endpoint expected to require auth returned 2xx with "
                      f"{label}" if is_2xx else f"correctly rejected ({status})"),
            )

    out = ROOT / "results" / "01_authn_bypass.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"AuthN bypass: {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN: {f['method']} {f['endpoint']} ({f['role']}) -> {f['status']}")


if __name__ == "__main__":
    main()
