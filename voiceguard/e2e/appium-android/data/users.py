"""Fixture account for the native Android app suite — same pre-provisioned,
pre-verified DAST account the mobile-web (../appium) and desktop
(../selenium) suites already use (see automated_test/setup_env.py), reused
here rather than standing up a parallel account. Duplicated in each suite's
own data/ directory rather than shared, matching the convention already
established between ../appium and ../selenium.
"""
from __future__ import annotations

FIXTURE_USER = {
    "email": "dast.usera@example.com",
    "password": "DastTest!2026a",
    "display_name": "DAST User A",
}
