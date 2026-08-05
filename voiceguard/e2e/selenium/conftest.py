"""Shared fixtures for the Selenium web E2E suite.

Runs headless Chrome against the frontend dev server (docker-compose's
`frontend` service, http://localhost:5173 by default) and reuses the DAST
fixture accounts (automated_test/setup_env.py) for the authenticated flows,
so this suite doesn't need its own signup/verify bootstrapping.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = os.environ.get("SELENIUM_BASE_URL", "http://localhost:5173")
REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_JSON = REPO_ROOT / "automated_test" / "input.json"

# Reuses the same fixture accounts automated_test/setup_env.py provisions
# for the DAST pass — real, verified, already-seeded accounts instead of
# standing up a parallel signup flow just for UI login tests.
FIXTURE_USER = {
    "email": "dast.usera@example.com",
    "password": "DastTest!2026a",
}


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(2)
    yield drv
    drv.quit()


@pytest.fixture
def authenticated_driver(driver, base_url):
    driver.get(f"{base_url}/login")
    driver.find_element("id", "email").send_keys(FIXTURE_USER["email"])
    driver.find_element("id", "password").send_keys(FIXTURE_USER["password"])
    driver.find_element("css selector", "button[type=submit]").click()
    return driver
