"""Page objects for /settings/* (voiceguard/frontend/src/pages/Settings/).

All three pages share SettingsLayout's tab nav (nav[aria-label="Settings
sections"], links "Profile"/"Account"/"Appearance" from SETTINGS_ITEMS in
nav-config.ts). Every field error on these pages comes from the shared
Input component (components/ui/input.tsx), which always renders the error as
a `<p role="alert">` immediately after the `<input>` -- that's the one
reliable, real selector for "this field's validation message" used below.
Same components/structure as the Appium suite covers (desktop viewport
doesn't change these pages).
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage

SETTINGS_TABS_NAV = (By.CSS_SELECTOR, 'nav[aria-label="Settings sections"]')


def field_error_locator(field_id: str):
    return (By.XPATH, f'//input[@id="{field_id}"]/following-sibling::p[@role="alert"]')


class ProfilePage(BasePage):
    DISPLAY_NAME_INPUT = (By.ID, "displayName")
    SAVE_BUTTON = (By.CSS_SELECTOR, 'button[type=submit]')
    EMAIL_TEXT = (By.XPATH, '//h2[normalize-space()="Profile"]/following::*[contains(text(), "@")][1]')

    def goto_profile(self) -> None:
        self.goto("/settings/profile")
        self.find(*self.DISPLAY_NAME_INPUT)

    def display_name_value(self) -> str:
        return self.find(*self.DISPLAY_NAME_INPUT).get_attribute("value")

    def set_display_name(self, value: str) -> None:
        self.fill_id("displayName", value)

    def is_save_disabled(self) -> bool:
        return self.find(*self.SAVE_BUTTON).get_attribute("disabled") is not None

    def display_name_error(self) -> str:
        return self.find(*field_error_locator("displayName")).text


class AccountPage(BasePage):
    EMAIL_ROW_TEXT = (By.XPATH, '//h3[normalize-space()="Email address"]/following::*[contains(text(), "@")][1]')
    CURRENT_PASSWORD_INPUT = (By.ID, "currentPassword")
    NEW_PASSWORD_INPUT = (By.ID, "newPassword")
    CONFIRM_PASSWORD_INPUT = (By.ID, "confirmPassword")
    CHANGE_PASSWORD_HEADING = (By.XPATH, '//h3[normalize-space()="Change password"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'button[type=submit]')

    def goto_account(self) -> None:
        self.goto("/settings/account")
        self.find(*self.CHANGE_PASSWORD_HEADING)

    def email_row_text(self) -> str:
        return self.find(*self.EMAIL_ROW_TEXT).text

    def fill_change_password_form(self, current: str, new: str, confirm: str) -> None:
        self.fill_id("currentPassword", current)
        self.fill_id("newPassword", new)
        self.fill_id("confirmPassword", confirm)

    def submit_password_change(self) -> None:
        # js_click, not click(): confirmed live (ElementClickIntercepted at
        # the button's own coordinates, elementFromPoint finding nothing
        # there) that a native coordinate-based click can race this page's
        # entrance animation right after goto_account() -- same class of
        # issue as BasePage.js_click's documented Link-click quirk, same fix.
        self.js_click(self.find_clickable(*self.SUBMIT_BUTTON))

    def new_password_error(self) -> str:
        return self.find(*field_error_locator("newPassword")).text

    def confirm_password_error(self) -> str:
        return self.find(*field_error_locator("confirmPassword")).text


class AppearancePage(BasePage):
    THEME_RADIOGROUP = (By.CSS_SELECTOR, 'div[role="radiogroup"][aria-label="Theme"]')
    NAV_EXPANDED_BUTTON = (By.XPATH, '//button[contains(., "Expanded")]')
    NAV_COMPACT_BUTTON = (By.XPATH, '//button[contains(., "Compact")]')

    def goto_appearance(self) -> None:
        self.goto("/settings/appearance")
        self.find(*self.THEME_RADIOGROUP)

    def theme_option(self, label: str):
        # label is one of "Light", "Dark", "System" (THEME_OPTIONS in
        # Appearance.tsx).
        return self.find(
            By.XPATH, f'//div[@role="radiogroup"][@aria-label="Theme"]//button[.//p[normalize-space()="{label}"]]'
        )

    def select_theme(self, label: str) -> None:
        self.click(self.theme_option(label))

    def is_theme_active(self, label: str) -> bool:
        return self.theme_option(label).get_attribute("aria-checked") == "true"

    def set_nav_compact(self) -> None:
        self.click(self.find_clickable(*self.NAV_COMPACT_BUTTON))

    def set_nav_expanded(self) -> None:
        self.click(self.find_clickable(*self.NAV_EXPANDED_BUTTON))

    def is_nav_compact(self) -> bool:
        return self.find(*self.NAV_COMPACT_BUTTON).get_attribute("aria-pressed") == "true"
