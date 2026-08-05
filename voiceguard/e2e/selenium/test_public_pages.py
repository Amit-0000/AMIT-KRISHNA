"""Validation-focused Selenium coverage of VoiceGuard's public (unauthenticated) pages."""
from __future__ import annotations

from selenium.webdriver.common.by import By


def test_landing_page_loads(driver, base_url):
    driver.get(base_url)
    assert driver.title, "landing page should set a document title"
    assert driver.current_url.rstrip("/") == base_url.rstrip("/")


def test_signup_page_renders_required_fields(driver, base_url):
    driver.get(f"{base_url}/signup")
    assert driver.find_element(By.ID, "displayName").is_displayed()
    assert driver.find_element(By.ID, "email").is_displayed()
    assert driver.find_element(By.ID, "password").is_displayed()
    assert driver.find_element(By.ID, "confirmPassword").is_displayed()


def test_signup_client_side_validation_blocks_empty_submit(driver, base_url):
    driver.get(f"{base_url}/signup")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    assert "/signup" in driver.current_url, "empty submit must not navigate away from the form"


def test_signup_rejects_mismatched_passwords(driver, base_url):
    driver.get(f"{base_url}/signup")
    driver.find_element(By.ID, "displayName").send_keys("Selenium QA")
    driver.find_element(By.ID, "email").send_keys("selenium.mismatch@example.com")
    driver.find_element(By.ID, "password").send_keys("Sup3rSecure!2026")
    driver.find_element(By.ID, "confirmPassword").send_keys("DoesNotMatch!1")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    body_text = driver.find_element(By.TAG_NAME, "body").text
    assert "match" in body_text.lower(), "mismatched-password validation message should be visible"


def test_login_page_renders(driver, base_url):
    driver.get(f"{base_url}/login")
    assert driver.find_element(By.ID, "email").is_displayed()
    assert driver.find_element(By.ID, "password").is_displayed()


def test_login_rejects_bad_credentials(driver, base_url):
    driver.get(f"{base_url}/login")
    driver.find_element(By.ID, "email").send_keys("nobody-selenium@example.com")
    driver.find_element(By.ID, "password").send_keys("WrongPassword!1")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    alert = driver.find_element(By.CSS_SELECTOR, "[role=alert]")
    assert "incorrect" in alert.text.lower() or "credentials" in alert.text.lower()


def test_unknown_route_shows_404(driver, base_url):
    driver.get(f"{base_url}/this-route-does-not-exist")
    body_text = driver.find_element(By.TAG_NAME, "body").text
    assert "404" in body_text
