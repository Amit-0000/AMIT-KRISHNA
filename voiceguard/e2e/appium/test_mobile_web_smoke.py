"""Mobile-web smoke coverage via Appium (Android emulator + Chrome).

Mirrors the highest-value flows from e2e/selenium/test_public_pages.py and
test_authenticated_flows.py, scoped down to what's worth re-verifying on a
real mobile viewport/touch input path rather than duplicating the full
desktop suite.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_landing_page_loads_on_mobile_chrome(driver, base_url):
    driver.get(base_url)
    assert driver.title


def test_signup_form_is_usable_via_touch(driver, base_url):
    driver.get(f"{base_url}/signup")
    field = driver.find_element(By.ID, "displayName")
    field.click()
    field.send_keys("Appium QA")
    assert field.get_attribute("value") == "Appium QA"


def test_login_page_renders_on_mobile_viewport(driver, base_url):
    driver.get(f"{base_url}/login")
    assert driver.find_element(By.ID, "email").is_displayed()
    assert driver.find_element(By.ID, "password").is_displayed()


def test_login_with_valid_credentials_reaches_dashboard(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/dashboard"))
    assert "/dashboard" in authenticated_driver.current_url


def test_mobile_nav_reaches_history_page(authenticated_driver, base_url):
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/dashboard"))
    authenticated_driver.get(f"{base_url}/history")
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/history"))
    assert "/history" in authenticated_driver.current_url
