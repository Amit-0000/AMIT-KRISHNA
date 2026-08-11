"""Fixture accounts and signup-input generation for the desktop Selenium suite.

Same real accounts/rules as voiceguard/e2e/appium/data/users.py (same app,
same backend) — copied rather than re-derived. unique_signup_email() uses a
"selenium.qa." prefix (Appium's is "appium.qa.") so the two suites' real
signup calls can never collide even if both jobs happen to run in the same
GITHUB_RUN_ID window.

FIXTURE_USER/SECOND_FIXTURE_USER are the same pre-provisioned, pre-verified
DAST accounts automated_test/setup_env.py creates, reused here rather than
standing up parallel accounts.
"""
from __future__ import annotations

import os
import time

FIXTURE_USER = {
    "email": "dast.usera@example.com",
    "password": "DastTest!2026a",
    "display_name": "DAST User A",
}

SECOND_FIXTURE_USER = {
    "email": "dast.userb@example.com",
    "password": "DastTest!2026b",
    "display_name": "DAST User B",
}

# Meets every rule in frontend/src/lib/validation.ts's PASSWORD_REQUIREMENTS.
VALID_SIGNUP_PASSWORD = "SeleniumQA!2026x"


def unique_signup_email() -> str:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    return f"selenium.qa.{run_id}.{int(time.time() * 1000)}@example.com"
