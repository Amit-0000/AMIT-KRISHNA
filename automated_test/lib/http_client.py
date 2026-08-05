"""Shared HTTP helper for the VoiceGuard DAST pass.

Cookie-based auth: the API issues httponly `access_token` / `refresh_token`
JWT cookies (see voiceguard/api/auth/service.py), not Authorization bearer
headers. All test scripts route requests through here so behavior (timeouts,
retries, logging) stays consistent.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "input.json"


def load_input() -> dict:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def make_session(cookie_value: str | None) -> requests.Session:
    """cookie_value is the raw access_token JWT string (or None for anonymous)."""
    s = requests.Session()
    if cookie_value:
        s.cookies.set("access_token", cookie_value, path="/")
    return s


def request(method: str, base_url: str, path: str, *, cookie: str | None = None,
            headers: dict | None = None, json_body: dict | None = None,
            files=None, data=None, max_time: float = 10.0, retries: int = 2) -> dict:
    """Fires one real HTTP request, returns a normalized result dict.
    Retries only on network errors / 5xx, never on a clean 4xx (per DAST spec)."""
    url = base_url.rstrip("/") + path
    cookies = {"access_token": cookie} if cookie else {}
    attempt = 0
    last_exc = None
    while attempt <= retries:
        start = time.time()
        try:
            resp = requests.request(
                method, url, cookies=cookies, headers=headers or {},
                json=json_body, files=files, data=data, timeout=max_time,
            )
            elapsed_ms = round((time.time() - start) * 1000, 1)
            if resp.status_code >= 500 and attempt < retries:
                attempt += 1
                time.sleep(0.5 * attempt)
                continue
            try:
                body = resp.json()
            except ValueError:
                body = resp.text[:500]
            return {
                "status": resp.status_code,
                "body": body,
                "response_time_ms": elapsed_ms,
                "url": url,
                "method": method,
            }
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            attempt += 1
            time.sleep(0.5 * attempt)
    return {
        "status": None,
        "body": f"NETWORK_ERROR: {last_exc}",
        "response_time_ms": None,
        "url": url,
        "method": method,
    }


def record(records: list, *, endpoint: str, method: str, role: str, status,
           expected_status, finding: bool, severity: str, response_time_ms,
           test_category: str, note: str = "") -> None:
    from datetime import datetime, timezone
    records.append({
        "endpoint": endpoint,
        "method": method,
        "role": role,
        "status": status,
        "expected_status": expected_status,
        "finding": finding,
        "severity": severity,
        "response_time_ms": response_time_ms,
        "test_category": test_category,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
