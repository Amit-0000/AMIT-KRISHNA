"""One-time environment bootstrap for the DAST pass.

Registers three real accounts through the live API (no direct DB writes for
account creation), pulls each email-verification token out of the backend
container's console-email log (EMAIL_PROVIDER=console just logs the email
instead of sending it), verifies + logs each one in, then promotes one
account to admin via a direct SQL UPDATE (there is no self-serve admin
signup endpoint in this API, so this is the only way to get an admin
principal for RBAC testing). Writes automated_test/input.json.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
API = BASE_URL + "/api/v1"
ROOT = Path(__file__).resolve().parent
CONTAINER = "voiceguard-backend-1"
PG_CONTAINER = "voiceguard-postgres-1"

USERS = {
    "user_a": {"email": "dast.usera@example.com", "password": "DastTest!2026a", "display_name": "DAST User A"},
    "user_b": {"email": "dast.userb@example.com", "password": "DastTest!2026b", "display_name": "DAST User B"},
    "admin":  {"email": "dast.admin@example.com",  "password": "DastTest!2026c", "display_name": "DAST Admin"},
}


def get_verification_token(email: str) -> str:
    """Greps the backend container's stdout log for the console-provider email
    dispatch and pulls the token out of the verify-email?token=... URL."""
    for _ in range(10):
        logs = subprocess.run(
            ["docker", "logs", "--tail", "500", CONTAINER],
            capture_output=True, text=True, check=True,
        ).stdout + subprocess.run(
            ["docker", "logs", "--tail", "500", CONTAINER],
            capture_output=True, text=True, check=True,
        ).stderr
        # entries look like: "--- TO: <email>\n--- SUBJECT: ...\n--- BODY:\n...verify-email?token=<hex>..."
        blocks = logs.split("email_dispatched (console provider)")
        for block in reversed(blocks):
            if email in block:
                m = re.search(r"verify-email\?token=([0-9a-f]{64})", block)
                if m:
                    return m.group(1)
        time.sleep(1)
    raise RuntimeError(f"Could not find verification token for {email} in backend logs")


def register(email: str, password: str, display_name: str) -> None:
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": password, "display_name": display_name,
    }, timeout=10)
    if r.status_code == 201:
        print(f"  registered {email}")
    elif r.status_code == 409 or (r.status_code == 400 and "already" in r.text.lower()):
        print(f"  {email} already registered, continuing")
    else:
        raise RuntimeError(f"register failed for {email}: {r.status_code} {r.text}")


def verify(email: str) -> None:
    token = get_verification_token(email)
    r = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=10)
    if r.status_code != 200:
        # Might already be verified from a previous run.
        print(f"  verify-email for {email} -> {r.status_code} {r.text[:200]} (continuing)")
    else:
        print(f"  verified {email}")


def login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"login failed for {email}: {r.status_code} {r.text}")
    token = r.cookies.get("access_token")
    if not token:
        raise RuntimeError(f"login for {email} did not set access_token cookie: {dict(r.cookies)}")
    user_id = r.json()["data"]["user"]["id"]
    print(f"  logged in {email} (id={user_id})")
    return token, user_id


def promote_to_admin(email: str) -> None:
    sql = f"UPDATE users SET role = 'admin' WHERE email = '{email}';"
    result = subprocess.run(
        ["docker", "exec", "-i", PG_CONTAINER, "psql", "-U", "voiceguard", "-d", "voiceguard", "-c", sql],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"admin promotion failed: {result.stderr}")
    print(f"  promoted {email} to admin: {result.stdout.strip()}")


def main() -> None:
    print("=== Registering test accounts ===")
    for key, u in USERS.items():
        register(u["email"], u["password"], u["display_name"])

    print("=== Verifying emails ===")
    for key, u in USERS.items():
        verify(u["email"])

    print("=== Promoting admin account ===")
    promote_to_admin(USERS["admin"]["email"])

    print("=== Logging in (JWT role claim is minted fresh here, after promotion) ===")
    tokens = {}
    ids = {}
    for key, u in USERS.items():
        token, uid = login(u["email"], u["password"])
        tokens[key] = token
        ids[key] = uid

    input_json = {
        "baseUrl": BASE_URL,
        "user_a": tokens["user_a"],
        "user_b": tokens["user_b"],
        "admin": tokens["admin"],
        "_meta": {
            "user_a_id": ids["user_a"],
            "user_b_id": ids["user_b"],
            "admin_id": ids["admin"],
            "note": "tokens are raw access_token JWT values, sent as the access_token cookie",
        },
    }
    with open(ROOT / "input.json", "w", encoding="utf-8") as f:
        json.dump(input_json, f, indent=2)
    print(f"\nWrote {ROOT / 'input.json'}")


if __name__ == "__main__":
    main()
