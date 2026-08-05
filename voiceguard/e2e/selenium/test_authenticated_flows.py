"""Authenticated Selenium coverage: login success, dashboard, and core nav
using the DAST fixture account (see conftest.py)."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_login_with_valid_credentials_reaches_dashboard(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/dashboard"))
    assert "/dashboard" in authenticated_driver.current_url


def test_dashboard_renders_app_shell(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/dashboard"))
    nav_text = authenticated_driver.find_element(By.TAG_NAME, "body").text.lower()
    assert "dashboard" in nav_text or "scan" in nav_text


def test_navigate_to_history_page(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/dashboard"))
    authenticated_driver.get(f"{base_url}/history")
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/history"))
    assert "/history" in authenticated_driver.current_url


def test_navigate_to_new_scan_page(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/dashboard"))
    authenticated_driver.get(f"{base_url}/scan/new")
    WebDriverWait(authenticated_driver, 10).until(EC.url_contains("/scan/new"))
    assert "/scan/new" in authenticated_driver.current_url


def test_unauthenticated_user_redirected_from_dashboard(driver, base_url):
    driver.get(f"{base_url}/dashboard")
    WebDriverWait(driver, 10).until(EC.url_contains("/login"))
    assert "/login" in driver.current_url, "AuthGuard should bounce anonymous users to /login"
