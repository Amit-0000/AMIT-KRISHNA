"""Mobile-web coverage of /settings/profile, /settings/account,
/settings/appearance (Settings/Profile.tsx, Account.tsx, Appearance.tsx).

Profile and Account changes are real, persisted mutations against the same
shared fixture account every other test in this run logs in as -- so tests
here only exercise client-side-rejected (invalid) submissions, never a real
successful profile/password update, and Appearance-page toggles are
deliberately idempotent (client-side zustand state, not account data).
"""
from __future__ import annotations

from data.test_inputs import INVALID_DISPLAY_NAMES, MISMATCHED_PASSWORD, WEAK_PASSWORDS
from data.users import FIXTURE_USER
from pages.settings_pages import AccountPage, AppearancePage, ProfilePage


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


def test_account_change_password_rejects_weak_new_password(authenticated_driver, base_url):
    account = AccountPage(authenticated_driver, base_url)
    account.goto_account()
    weak = WEAK_PASSWORDS["no_special"]
    account.fill_change_password_form(current=FIXTURE_USER["password"], new=weak, confirm=weak)
    account.submit_password_change()
    assert account.new_password_error()


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
