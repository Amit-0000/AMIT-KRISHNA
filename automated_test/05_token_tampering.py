"""Category 5 — JWT token tampering.
Takes a real, validly-issued user_a token, decodes it WITHOUT verifying
the signature, tampers with claims (flip role -> admin, flip sub -> another
user's id, change email_verified), and re-encodes WITHOUT re-signing
correctly (either keeping the old signature, using alg=none, or signing
with a guessed/empty secret). Server must reject all of these. A 2xx
response is a finding.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from http_client import load_input, record, request  # noqa: E402

import base64
import jwt


def b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def decode_unverified(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def craft_alg_none(payload: dict) -> str:
    header = {"alg": "none", "typ": "JWT"}
    h = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}."


def craft_keep_old_signature(original_token: str, new_payload: dict) -> str:
    """Flip claims but keep the original (now-mismatched) signature — tests
    that the server actually verifies the signature against the new body."""
    header_b64, _, sig_b64 = original_token.split(".")
    p = b64url_encode(json.dumps(new_payload, separators=(",", ":")).encode())
    return f"{header_b64}.{p}.{sig_b64}"


def craft_wrong_secret(payload: dict, header_alg: str = "HS256") -> str:
    return jwt.encode(payload, "attacker-guessed-secret-value-123", algorithm=header_alg)


def craft_hs256_using_no_alg_confusion(payload: dict) -> str:
    """Signs with a trivially-guessable secret — included for completeness
    even though api/core/security.py's ALLOWED_JWT_ALGORITHMS allowlist
    should already block anything except HS256 tokens it itself signed."""
    return jwt.encode(payload, "secret", algorithm="HS256")


def main() -> None:
    inp = load_input()
    base = inp["baseUrl"]
    admin_id = inp["_meta"]["admin_id"]
    real_token = inp["user_a"]
    real_payload = decode_unverified(real_token)

    variants = {}

    p1 = dict(real_payload)
    p1["role"] = "admin"
    variants["role_flip_keep_old_sig"] = craft_keep_old_signature(real_token, p1)

    p2 = dict(real_payload)
    p2["sub"] = admin_id
    variants["sub_flip_to_admin_keep_old_sig"] = craft_keep_old_signature(real_token, p2)

    p3 = dict(real_payload)
    p3["role"] = "admin"
    variants["alg_none_role_admin"] = craft_alg_none(p3)

    p4 = dict(real_payload)
    p4["role"] = "admin"
    variants["wrong_secret_role_admin"] = craft_wrong_secret(p4)

    p5 = dict(real_payload)
    p5["email_verified"] = True
    p5["role"] = "admin"
    variants["empty_secret_role_admin"] = craft_hs256_using_no_alg_confusion(p5)

    records = []
    probe_targets = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/feedback"),  # admin-only — the interesting target for role_flip
    ]

    for variant_name, tampered_token in variants.items():
        for method, path in probe_targets:
            res = request(method, base, path, cookie=tampered_token)
            status = res["status"]
            is_2xx = status is not None and 200 <= status < 300
            record(
                records,
                endpoint=path, method=method, role=f"tampered:{variant_name}",
                status=status, expected_status="401",
                finding=is_2xx, severity="critical" if is_2xx else "info",
                response_time_ms=res["response_time_ms"], test_category="token_tampering",
                note=("VULNERABLE: tampered token accepted" if is_2xx else f"correctly rejected ({status})"),
            )

    out = Path(__file__).resolve().parent / "results" / "05_token_tampering.json"
    out.write_text(json.dumps(records, indent=2))
    findings = [r for r in records if r["finding"]]
    print(f"Token tampering: {len(records)} checks, {len(findings)} findings. Wrote {out}")
    for f in findings:
        print(f"  VULN: {f['method']} {f['endpoint']} ({f['role']}) -> {f['status']}")


if __name__ == "__main__":
    main()
