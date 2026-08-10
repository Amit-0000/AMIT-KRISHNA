"""Fixture accounts and signup-input generation for the mobile-web suite.

FIXTURE_USER/SECOND_FIXTURE_USER are the same pre-provisioned, pre-verified
DAST accounts automated_test/setup_env.py creates (see that script's
docstring) and that conftest.py's `authenticated_driver` already logs in
with — reused here rather than standing up parallel accounts.

unique_signup_email() follows the same "make every run's content distinct"
approach as performance/k6/baseline_load_test.js's uniqueWavBytes() and
performance/seed_users.py, so repeated CI runs never collide on a
already-registered address.
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
VALID_SIGNUP_PASSWORD = "MobileQA!2026x"


def unique_signup_email() -> str:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    return f"appium.qa.{run_id}.{int(time.time() * 1000)}@example.com"
