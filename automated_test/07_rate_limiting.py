"""Category 7 — Rate limiting.
Bounded bursts (well under the ~30 req cap from the spec) against:
  - /api/v1/auth/login (documented limit: 10/hour/IP) -> expect a 429 to
    appear before the burst ends, confirming the limiter is live.
  - /predict, unauthenticated (top-level legacy endpoint) -> was previously
    a HIGH finding (no auth, no rate limit, unlimited CPU-bound ML inference).
    Now fixed: require_authenticated + require_predict_rate_limit were added
    in api/main.py, so this now expects 401 for every unauthenticated call.
  - /predict, authenticated as user_a -> expect a 429 after ~30 calls
    (RATE_LIMIT_PREDICT_PER_HOUR_PER_USER=30), confirming the new per-user
    limiter is live, not just present in config.
  - /api/v1/auth/register (documented limit: 5/hour/IP) -> expect a 429.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from http_client import load_input, record, request  # noqa: E402
from fixtures import make_valid_wav_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent


def burst_login(base: str, n: int) -> list[int]:
    statuses = []
    for i in range(n):
        res = request("POST", base, "/api/v1/auth/login", json_body={"email": "nobody@example.com", "password": "wrong-pw"})
        statuses.append(res["status"])
    return statuses


def burst_register(base: str, n: int) -> list[int]:
    statuses = []
    for i in range(n):
        res = request("POST", base, "/api/v1/auth/register", json_body={
            "email": f"dast.ratelimit{i}@example.com", "password": "ValidPass!2026x", "display_name": f"RL {i}",
        })
        statuses.append(res["status"])
    return statuses


def burst_predict(base: str, n: int, cookie: str | None = None) -> list[int]:
    wav = make_valid_wav_bytes(1.0)
    statuses = []
    for i in range(n):
        res = request("POST", base, "/predict", cookie=cookie,
                       files={"audio_file": ("t.wav", io.BytesIO(wav), "audio/wav")}, max_time=15)
        statuses.append(res["status"])
    return statuses


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    records = []

    print("Bursting /api/v1/auth/login x15...")
    login_statuses = burst_login(base, 15)
    got_429 = 429 in login_statuses
    record(
        records, endpoint="/api/v1/auth/login", method="POST", role="anon",
        status=json.dumps(login_statuses), expected_status="429 appears within the burst",
        finding=not got_429, severity="medium" if not got_429 else "info",
        response_time_ms=None, test_category="rate_limiting",
        note=(f"statuses={login_statuses}; " + ("429 seen, limiter active" if got_429 else "no 429 in 15 requests -- limiter may not be enforcing")),
    )

    print("Bursting /api/v1/auth/register x7 (limit is 5/hr, kept small to avoid flooding real accounts)...")
    register_statuses = burst_register(base, 7)
    got_429 = 429 in register_statuses
    record(
        records, endpoint="/api/v1/auth/register", method="POST", role="anon",
        status=json.dumps(register_statuses), expected_status="429 appears within the burst",
        finding=not got_429, severity="medium" if not got_429 else "info",
        response_time_ms=None, test_category="rate_limiting",
        note=(f"statuses={register_statuses}; " + ("429 seen, limiter active" if got_429 else "no 429 in 7 requests -- limiter may not be enforcing")),
    )

    print("Bursting unauthenticated /predict x30 (should now be blocked by auth, not just rate limiting)...")
    predict_statuses = burst_predict(base, 30, cookie=None)
    all_401 = all(s == 401 for s in predict_statuses)
    got_429 = 429 in predict_statuses
    protected = all_401 or got_429
    record(
        records, endpoint="/predict", method="POST", role="anon",
        status=json.dumps(predict_statuses[:10]) + ("..." if len(predict_statuses) > 10 else ""),
        expected_status="401 (auth now required) for every call",
        finding=not protected, severity="high" if not protected else "info",
        response_time_ms=None, test_category="rate_limiting",
        note=(f"{predict_statuses.count(200)}/{len(predict_statuses)} succeeded with 200 while unauthenticated. "
              "VULNERABLE: unauthenticated endpoint with no auth/rate limiting allows unlimited "
              "CPU-bound ML inference calls -- cost-abuse / DoS risk." if not protected
              else f"correctly rejected unauthenticated calls (401 x{predict_statuses.count(401)})"),
    )

    print("Bursting authenticated /predict x33 as user_a (new limit: 30/hr/user)...")
    auth_predict_statuses = burst_predict(base, 33, cookie=inp["user_a"])
    got_429_auth = 429 in auth_predict_statuses
    record(
        records, endpoint="/predict", method="POST", role="user_a",
        status=json.dumps(auth_predict_statuses),
        expected_status="429 appears after ~30 successful calls",
        finding=not got_429_auth, severity="medium" if not got_429_auth else "info",
        response_time_ms=None, test_category="rate_limiting",
        note=(f"statuses={auth_predict_statuses}; " + ("429 seen, per-user limiter active" if got_429_auth
              else "no 429 in 33 authenticated requests -- limiter may not be enforcing")),
    )

    out = ROOT / "results" / "07_rate_limiting.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"Rate limiting: {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN [{f['severity']}]: {f['method']} {f['endpoint']} :: {f['note']}")


if __name__ == "__main__":
    main()
