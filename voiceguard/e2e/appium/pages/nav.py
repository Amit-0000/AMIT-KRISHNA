"""Page objects for the app's shared chrome (voiceguard/frontend/src/components/layout/).

Mobile viewport (Appium mobile Chrome) renders the *mobile* variants of this
chrome: Sidebar is `hidden lg:flex` (never visible), TopBar's hamburger opens
MobileDrawer instead, and Breadcrumb is `hidden sm:flex` (never visible either)
-- see AppShell.tsx/TopBar.tsx. Selectors below are read directly from those
components, not guessed.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class AppChrome(BasePage):
    """Everything reachable from the TopBar on any authenticated page."""

    HAMBURGER = (By.CSS_SELECTOR, 'button[aria-label="Open navigation"]')
    MOBILE_SEARCH_TRIGGER = (By.CSS_SELECTOR, 'button[aria-label="Search"]')
    NOTIFICATION_BELL = (By.CSS_SELECTOR, 'button[aria-label^="Notifications"]')
    THEME_TOGGLE_ICON = (By.CSS_SELECTOR, 'button[aria-label^="Current theme"]')
    BREADCRUMB_NAV = (By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"]')

    def open_mobile_drawer(self) -> "MobileDrawer":
        self.tap(self.find_clickable(*self.HAMBURGER))
        return MobileDrawer(self.driver, self.base_url)

    def open_search(self) -> "GlobalSearch":
        self.tap(self.find_clickable(*self.MOBILE_SEARCH_TRIGGER))
        return GlobalSearch(self.driver, self.base_url)

    def open_notifications(self) -> "NotificationCenter":
        self.tap(self.find_clickable(*self.NOTIFICATION_BELL))
        return NotificationCenter(self.driver, self.base_url)

    def cycle_theme(self) -> None:
        self.tap(self.find_clickable(*self.THEME_TOGGLE_ICON))

    def current_theme_label(self) -> str:
        return self.find(*self.THEME_TOGGLE_ICON).get_attribute("aria-label")


class MobileDrawer(BasePage):
    # Attribute-only, no "div" tag qualifier: the real component
    # (MobileDrawer.tsx) renders this as <motion.aside>, an <aside>
    # element, not a <div> -- a "div[role=...]" selector never matches it.
    # Confirmed via a real CI run's failure screenshot showing the drawer
    # genuinely open while this locator still couldn't find it.
    PANEL = (By.CSS_SELECTOR, '[role="dialog"][aria-label="Navigation menu"]')
    CLOSE_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Close navigation"]')
    NAV_LANDMARK = (By.CSS_SELECTOR, 'nav[aria-label="Mobile navigation"]')

    def is_open(self) -> bool:
        # 10s, not the previous 5s: a real CI failure's captured screenshot
        # showed the drawer genuinely open at report time, just past the
        # 5s window is_open() itself had already given up within — the
        # open transition itself was fine, the wait was just too tight
        # under CI's shared emulator load.
        return self.is_visible(*self.PANEL, timeout=10)

    def close(self) -> None:
        self.tap(self.find_clickable(*self.CLOSE_BUTTON))
        self.wait_gone(*self.PANEL)

    def nav_link(self, label: str):
        # SIDEBAR_SECTIONS/SETTINGS_NAV item labels, e.g. "Dashboard", "New
        # Scan", "History", "Notifications", "Help Center", "Give Feedback",
        # "Settings" (nav-config.ts) -- exact visible link text.
        return self.find(By.XPATH, f'//nav[@aria-label="Mobile navigation"]//a[normalize-space()="{label}"]')

    def go_to(self, label: str) -> None:
        self.tap(self.nav_link(label))

    def open_user_menu(self, display_name: str) -> "UserMenu":
        button = self.find(By.XPATH, f'//button[.//p[normalize-space()="{display_name}"]]')
        self.tap(button)
        return UserMenu(self.driver, self.base_url)


class GlobalSearch(BasePage):
    DIALOG = (By.CSS_SELECTOR, 'div[role="dialog"][aria-label="Search"]')
    INPUT = (By.CSS_SELECTOR, 'input[aria-label="Search VoiceGuard"]')
    CLEAR_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Clear search"]')
    CLOSE_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Close search (Escape)"]')
    RESULTS = (By.CSS_SELECTOR, "#search-results")
    OPTIONS = (By.CSS_SELECTOR, '#search-results [role="option"]')
    NO_RESULTS = (By.XPATH, '//div[@id="search-results"]//div[contains(text(), "No results for")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.DIALOG, timeout=10)

    def type_query(self, text: str) -> None:
        self.type_text(self.find(*self.INPUT), text)

    def result_labels(self) -> list[str]:
        # Just the label <p>, not el.text: each option renders a label <p>
        # plus an optional description <p> below it
        # (GlobalSearch.tsx), and el.text was returning both lines joined,
        # never equal to the bare label text callers actually compare
        # against.
        return [el.find_element(By.CSS_SELECTOR, "p").text for el in self.find_all(*self.OPTIONS)]

    def select_result(self, label: str) -> None:
        option = self.find(By.XPATH, f'//div[@id="search-results"]//div[@role="option"][.//p[normalize-space()="{label}"]]')
        self.tap(option)

    def close(self) -> None:
        self.tap(self.find_clickable(*self.CLOSE_BUTTON))
        self.wait_gone(*self.DIALOG)


class NotificationCenter(BasePage):
    # Attribute-only, no "div" tag qualifier: the real component
    # (NotificationCenter.tsx) renders this as <motion.aside>, an <aside>
    # element, not a <div> -- a "div[role=...]" selector never matches it.
    PANEL = (By.CSS_SELECTOR, '[role="dialog"][aria-label="Notifications"]')
    CLOSE_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Close notifications"]')
    MARK_ALL_READ = (By.CSS_SELECTOR, 'button[aria-label="Mark all notifications as read"]')
    VIEW_ALL_LINK = (By.XPATH, '//a[normalize-space()="View all notifications"]')
    EMPTY_STATE_TEXT = (By.XPATH, '//p[contains(text(), "No notifications yet")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.PANEL, timeout=10)

    def is_empty(self) -> bool:
        return self.is_present(*self.EMPTY_STATE_TEXT)

    def go_to_all_notifications(self) -> None:
        self.tap(self.find_clickable(*self.VIEW_ALL_LINK))

    def close(self) -> None:
        self.tap(self.find_clickable(*self.CLOSE_BUTTON))
        self.wait_gone(*self.PANEL)


class UserMenu(BasePage):
    # DropdownMenuContent items -- plain text content, no distinguishing ids
    # (components/ui/dropdown-menu.tsx wraps Radix, which renders
    # role="menuitem" for each DropdownMenuItem).
    MENU = (By.CSS_SELECTOR, '[role="menu"]')
    PROFILE_ITEM = (By.XPATH, '//div[@role="menuitem"][normalize-space()="Profile"]')
    ACCOUNT_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Account settings")]')
    APPEARANCE_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Appearance")]')
    SIGN_OUT_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Sign out")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.MENU, timeout=10)

    def go_to_profile(self) -> None:
        self.tap(self.find_clickable(*self.PROFILE_ITEM))

    def sign_out(self) -> None:
        self.tap(self.find_clickable(*self.SIGN_OUT_ITEM))
