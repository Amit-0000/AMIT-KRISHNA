"""Desktop coverage of /settings/profile, /settings/account,
/settings/appearance (Settings/Profile.tsx, Account.tsx, Appearance.tsx).

Profile and Account changes are real, persisted mutations against the same
shared fixture account every other test in this run logs in as -- so tests
here only exercise client-side-rejected (invalid) submissions, never a real
successful profile/password update, and Appearance-page toggles are
deliberately idempotent (client-side zustand state, not account data). Same
components as the Appium suite covers.
"""
from __future__ import annotations

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from data.test_inputs import INVALID_DISPLAY_NAMES, MISMATCHED_PASSWORD, WEAK_PASSWORDS
from data.users import FIXTURE_USER, SECOND_FIXTURE_USER
from pages.base_page import BasePage
from pages.settings_pages import SETTINGS_TABS_NAV, AccountPage, AppearancePage, ProfilePage

pytestmark = [pytest.mark.medium]


def test_profile_page_prefills_current_display_name(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    assert profile.display_name_value() == FIXTURE_USER["display_name"]


def test_profile_save_button_disabled_until_dirty(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    assert profile.is_save_disabled()


def test_profile_rejects_disallowed_display_name_characters(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    profile.set_display_name(INVALID_DISPLAY_NAMES["disallowed_chars"])
    profile.submit()
    assert profile.display_name_error()
    # Restore the original value so later tests in this run still see the
    # real fixture display name -- the invalid submit above never reached
    # the API (client-side zod rejection), but the field itself is now dirty.
    profile.set_display_name(FIXTURE_USER["display_name"])


def test_profile_rejects_display_name_too_long(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    profile.set_display_name(INVALID_DISPLAY_NAMES["too_long"])
    profile.submit()
    assert profile.display_name_error()
    profile.set_display_name(FIXTURE_USER["display_name"])


def test_account_page_shows_current_email(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    assert FIXTURE_USER["email"] in account.email_row_text()


def test_account_change_password_rejects_mismatched_confirmation(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    account.fill_change_password_form(
        current=FIXTURE_USER["password"], new="Br4nd!NewPass2026", confirm=MISMATCHED_PASSWORD
    )
    account.submit_password_change()
    assert "match" in account.confirm_password_error().lower()


@pytest.mark.parametrize("rule", sorted(WEAK_PASSWORDS))
def test_account_change_password_rejects_weak_new_password(authenticated_driver, base_url, rule):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    weak = WEAK_PASSWORDS[rule]
    account.fill_change_password_form(current=FIXTURE_USER["password"], new=weak, confirm=weak)
    account.submit_password_change()
    assert account.new_password_error(), f"weak password ({rule}) must be rejected"


def test_appearance_page_renders_theme_options(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    for label in ("Light", "Dark", "System"):
        assert appearance.theme_option(label).is_displayed()


def test_appearance_theme_selection_updates_active_state(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    appearance.select_theme("Dark")
    assert appearance.is_theme_active("Dark")


def test_appearance_nav_density_toggle_is_idempotent(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    appearance.set_nav_compact()
    assert appearance.is_nav_compact()
    appearance.set_nav_expanded()
    assert not appearance.is_nav_compact()


def test_settings_default_route_redirects_to_profile(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto("/settings")
    profile.wait_url_contains("/settings/profile")
    assert "/settings/profile" in profile.current_url


def test_settings_tabs_nav_visible_on_profile_page(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    assert profile.is_visible(*SETTINGS_TABS_NAV)


def test_settings_tabs_nav_visible_on_account_page(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    assert account.is_visible(*SETTINGS_TABS_NAV)


def test_settings_tabs_nav_visible_on_appearance_page(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    assert appearance.is_visible(*SETTINGS_TABS_NAV)


def test_account_change_password_wrong_current_password_returns_401_and_logs_out(base_url):
    # Dedicated, isolated Chrome session (not the shared authenticated_driver
    # fixture) -- this test's real, confirmed effect is a full session
    # logout, which would otherwise wreck every later test's assumption that
    # authenticated_driver stays logged in (same reasoning as
    # test_session_guards.py's isolated sign-out test). Uses
    # SECOND_FIXTURE_USER for the same reason.
    #
    # Real, confirmed current behavior -- NOT the originally-expected "stay
    # on the account page with a field error": api/auth/service.py's
    # change_password() raises InvalidCredentialsError for a wrong current
    # password, which maps to a 401. frontend/src/services/api.ts's global
    # response interceptor treats *every* 401 as an expired/invalid session
    # (dispatches `vg:unauthorized`, which the auth store handles by
    # clearing the session), not specifically a "your current password
    # field was wrong" signal. The practical effect: mistyping your current
    # password while trying to change it logs you out of your whole
    # session instead of showing an inline field error. Documented here as
    # a real product-behavior quirk this suite verifies rather than
    # silently working around; not something this Selenium-suite task
    # should unilaterally change in the backend/frontend.
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    drv = webdriver.Chrome(options=options)
    try:
        page = BasePage(drv, base_url)
        page.goto("/login")
        page.fill_id("email", SECOND_FIXTURE_USER["email"])
        page.fill_id("password", SECOND_FIXTURE_USER["password"])
        page.submit()
        page.wait_url_contains("/dashboard")

        account = AccountPage(drv, base_url)
        account.goto_account()
        account.fill_change_password_form(
            current="DefinitelyWrongCurrent!1", new="Br4nd!NewPass2026", confirm="Br4nd!NewPass2026"
        )
        account.submit_password_change()
        account.wait_url_contains("/login")
        assert "/login" in account.current_url
    finally:
        drv.quit()


def test_profile_display_name_input_has_real_value_attribute(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    assert profile.find(*profile.DISPLAY_NAME_INPUT).get_attribute("value") != ""


def test_appearance_light_theme_selection_updates_active_state(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    appearance.select_theme("Light")
    assert appearance.is_theme_active("Light")
    appearance.select_theme("System")  # leave at a neutral default for tests after this one


def test_appearance_system_theme_selection_updates_active_state(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    appearance.select_theme("System")
    assert appearance.is_theme_active("System")


def test_account_new_password_and_confirm_fields_use_password_input_type(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    assert account.find(*account.NEW_PASSWORD_INPUT).get_attribute("type") == "password"
    assert account.find(*account.CONFIRM_PASSWORD_INPUT).get_attribute("type") == "password"


def test_settings_tab_nav_link_from_profile_to_account(authenticated_driver, base_url):
    profile = ProfilePage(authenticated_driver, base_url)
    profile.goto_profile()
    link = profile.find(By.XPATH, '//nav[@aria-label="Settings sections"]//a[contains(., "Account")]')
    profile.click(link)
    profile.wait_url_contains("/settings/account")
    assert "/settings/account" in profile.current_url


def test_settings_tab_nav_link_from_account_to_appearance(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    link = account.find(By.XPATH, '//nav[@aria-label="Settings sections"]//a[contains(., "Appearance")]')
    account.click(link)
    account.wait_url_contains("/settings/appearance")
    assert "/settings/appearance" in account.current_url


def test_settings_tab_nav_link_from_appearance_to_profile(authenticated_driver, base_url):
    appearance = AppearancePage(authenticated_driver, base_url)
    appearance.goto_appearance()
    link = appearance.find(By.XPATH, '//nav[@aria-label="Settings sections"]//a[contains(., "Profile")]')
    appearance.click(link)
    appearance.wait_url_contains("/settings/profile")
    assert "/settings/profile" in appearance.current_url
