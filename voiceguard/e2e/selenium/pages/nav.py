"""Page objects for the app's shared chrome (voiceguard/frontend/src/components/layout/).

Desktop viewport (headless Chrome, 1440x900 — see conftest.py) renders the
*desktop* variants of this chrome: Sidebar is `hidden lg:flex` (visible at
>=1024px, unlike the Appium mobile suite's MobileDrawer), TopBar's hamburger
is `lg:hidden` (never visible here), and Breadcrumb is `hidden sm:flex`
(visible at >=640px — the opposite of Appium's mobile-emulator viewport,
where it's hidden). Selectors read directly from AppShell.tsx/Sidebar.tsx/
TopBar.tsx/Breadcrumb.tsx/UserMenu.tsx/nav-config.ts, not guessed or copied
blindly from the mobile suite.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


class AppChrome(BasePage):
    """Everything reachable from the TopBar on any authenticated page."""

    HAMBURGER = (By.CSS_SELECTOR, 'button[aria-label="Open navigation"]')
    # Desktop-only trigger (`hidden sm:flex`) — NOT the same element as the
    # mobile suite's `button[aria-label="Search"]` (`sm:hidden`), which
    # doesn't render at this viewport width.
    DESKTOP_SEARCH_TRIGGER = (By.CSS_SELECTOR, 'button[aria-label="Search (Command K)"]')
    NOTIFICATION_BELL = (By.CSS_SELECTOR, 'button[aria-label^="Notifications"]')
    THEME_TOGGLE_ICON = (By.CSS_SELECTOR, 'button[aria-label^="Current theme"]')
    BREADCRUMB_NAV = (By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"]')

    def open_search(self) -> "GlobalSearch":
        self.click(self.find_clickable(*self.DESKTOP_SEARCH_TRIGGER))
        return GlobalSearch(self.driver, self.base_url)

    def open_notifications(self) -> "NotificationCenter":
        self.click(self.find_clickable(*self.NOTIFICATION_BELL))
        return NotificationCenter(self.driver, self.base_url)

    def cycle_theme(self) -> None:
        self.click(self.find_clickable(*self.THEME_TOGGLE_ICON))

    def current_theme_label(self) -> str:
        return self.find(*self.THEME_TOGGLE_ICON).get_attribute("aria-label")

    def breadcrumb_labels(self) -> list[str]:
        crumbs = self.find_all(By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"] li')
        return [c.text for c in crumbs if c.text]


class Sidebar(BasePage):
    ASIDE = (By.CSS_SELECTOR, 'aside[aria-label="Main navigation"]')
    NAV_LANDMARK = (By.CSS_SELECTOR, 'nav[aria-label="Sidebar navigation"]')
    COLLAPSE_TOGGLE = (By.XPATH, '//button[@aria-label="Collapse sidebar" or @aria-label="Expand sidebar"]')
    SETTINGS_LINK = (By.XPATH, '//aside[@aria-label="Main navigation"]//a[contains(., "Settings")]')

    # SIDEBAR_SECTIONS labels -> href, from nav-config.ts. Locating by href
    # rather than visible text: the collapsed layout (Sidebar.tsx) renders
    # icon-only with the label visually hidden, so a text-based XPath only
    # ever matched in the sidebar's default expanded state -- href is
    # present in the DOM either way, since collapse is a pure CSS/layout
    # change, not a different link.
    _LABEL_HREFS = {
        "Dashboard": "/dashboard",
        "New Scan": "/scan/new",
        "History": "/history",
        "Notifications": "/notifications",
        "Help Center": "/help",
        "Give Feedback": "/feedback",
    }

    def nav_link(self, label: str):
        href = self._LABEL_HREFS[label]
        return self.find(By.XPATH, f'//nav[@aria-label="Sidebar navigation"]//a[@href="{href}"]')

    def go_to(self, label: str) -> None:
        self.click(self.nav_link(label))

    def is_link_active(self, label: str) -> bool:
        return self.nav_link(label).get_attribute("aria-current") == "page"

    def go_to_settings(self) -> None:
        self.click(self.find_clickable(*self.SETTINGS_LINK))

    def toggle_collapse(self) -> None:
        before = self.find(*self.COLLAPSE_TOGGLE).get_attribute("aria-label")
        self.click(self.find_clickable(*self.COLLAPSE_TOGGLE))
        # aria-label flips synchronously with the Zustand store update (see
        # this class's docstring reasoning elsewhere in this file), but the
        # click itself can occasionally land during the sidebar's own width
        # transition -- wait for the real state change instead of asserting
        # immediately, same defensive pattern as other animated-chrome
        # interactions in this suite.
        WebDriverWait(self.driver, 5).until(
            lambda d: self.find(*self.COLLAPSE_TOGGLE).get_attribute("aria-label") != before
        )

    def is_collapsed(self) -> bool:
        return self.find(*self.COLLAPSE_TOGGLE).get_attribute("aria-label") == "Expand sidebar"

    def open_user_menu(self, display_name: str) -> "UserMenu":
        # UserMenu.tsx: trigger has no aria-label when the sidebar isn't
        # collapsed, but the account's display name is real visible text
        # inside it — same pattern the Appium suite used for the drawer-
        # embedded UserMenu (same component, different placement only).
        button = self.find(By.XPATH, f'//button[.//p[normalize-space()="{display_name}"]]')
        self.click(button)
        return UserMenu(self.driver, self.base_url)


class GlobalSearch(BasePage):
    DIALOG = (By.CSS_SELECTOR, 'div[role="dialog"][aria-label="Search"]')
    INPUT = (By.CSS_SELECTOR, 'input[aria-label="Search VoiceGuard"]')
    CLOSE_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Close search (Escape)"]')
    OPTIONS = (By.CSS_SELECTOR, '#search-results [role="option"]')
    NO_RESULTS = (By.XPATH, '//div[@id="search-results"]//div[contains(text(), "No results for")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.DIALOG, timeout=5)

    def type_query(self, text: str) -> None:
        self.type_text(self.find(*self.INPUT), text)

    def result_labels(self) -> list[str]:
        # Each option renders a title <p> (result.label) and, when present,
        # a second description <p> (result.description) right after it
        # (GlobalSearch.tsx) -- .text on the option itself concatenates
        # both ("Dashboard\nOverview and recent activity"), so pull just
        # the title paragraph's own text instead.
        return [
            el.find_element(By.CSS_SELECTOR, "p").text
            for el in self.find_all(*self.OPTIONS)
        ]

    def select_result(self, label: str) -> None:
        option = self.find(
            By.XPATH, f'//div[@id="search-results"]//div[@role="option"][.//p[normalize-space()="{label}"]]'
        )
        self.click(option)

    def close(self) -> None:
        self.click(self.find_clickable(*self.CLOSE_BUTTON))
        self.wait_gone(*self.DIALOG)


class NotificationCenter(BasePage):
    # <aside role="dialog">, not <div> (NotificationCenter.tsx renders
    # `<motion.aside ... role="dialog">`) -- confirmed live: the CSS type
    # selector `div[role="dialog"]` silently matches nothing against an
    # <aside>, even though the panel was rendering and the bell's click
    # handler was firing correctly the whole time.
    PANEL = (By.CSS_SELECTOR, 'aside[role="dialog"][aria-label="Notifications"]')
    CLOSE_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Close notifications"]')
    VIEW_ALL_LINK = (By.XPATH, '//a[normalize-space()="View all notifications"]')
    EMPTY_STATE_TEXT = (By.XPATH, '//p[contains(text(), "No notifications yet")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.PANEL, timeout=5)

    def is_empty(self) -> bool:
        return self.is_present(*self.EMPTY_STATE_TEXT)

    def go_to_all_notifications(self) -> None:
        self.click(self.find_clickable(*self.VIEW_ALL_LINK))

    def close(self) -> None:
        self.click(self.find_clickable(*self.CLOSE_BUTTON))
        self.wait_gone(*self.PANEL)


class UserMenu(BasePage):
    MENU = (By.CSS_SELECTOR, '[role="menu"]')
    PROFILE_ITEM = (By.XPATH, '//div[@role="menuitem"][normalize-space()="Profile"]')
    ACCOUNT_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Account settings")]')
    APPEARANCE_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Appearance")]')
    SIGN_OUT_ITEM = (By.XPATH, '//div[@role="menuitem"][contains(., "Sign out")]')

    def is_open(self) -> bool:
        return self.is_visible(*self.MENU, timeout=5)

    def go_to_profile(self) -> None:
        self.click(self.find_clickable(*self.PROFILE_ITEM))

    def sign_out(self) -> None:
        self.click(self.find_clickable(*self.SIGN_OUT_ITEM))
