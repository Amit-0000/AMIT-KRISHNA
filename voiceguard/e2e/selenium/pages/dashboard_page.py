"""Page object for /dashboard (voiceguard/frontend/src/pages/Dashboard/index.tsx).

DashboardPage renders one of two real states depending on the account's scan
history: EmptyDashboard (zero scans) or the full grid (StatsGrid/QuickActions/
etc., only when there's at least one scan). DashboardHeader (the greeting +
"Analyze Audio" button) renders unconditionally in both states, so it's the
one stable anchor tests should rely on without assuming which state a shared,
long-lived fixture account is in. Same component as the Appium suite covers
(desktop viewport doesn't change this page's structure).
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class DashboardPage(BasePage):
    GREETING_HEADING = (By.TAG_NAME, "h1")
    ANALYZE_AUDIO_HEADER_LINK = (By.XPATH, '//h1/following::a[@href="/scan/new"][1]')
    EMPTY_STATE = (By.XPATH, '//*[@aria-label="No analyses yet"]')
    QUICK_ACTIONS_HEADING = (By.XPATH, '//h2[normalize-space()="Quick Actions"]')
    QUICK_ACTION_VIEW_HISTORY = (By.XPATH, '//a[@href="/history"][.//p[normalize-space()="View History"]]')

    def goto_dashboard(self) -> None:
        # Waiting on the URL alone isn't enough: goto() is a full
        # driver.get() navigation (a hard reload, not a client-side route
        # change), and the URL updates before React finishes mounting/
        # hydrating. A caller that immediately clicks TopBar chrome (search
        # trigger, notification bell) right after this returns can land the
        # click before the real handlers are attached — confirmed live: the
        # notification bell's onClick reliably toggled state when clicked
        # after this page had already rendered, and reliably didn't right
        # after a bare goto("/dashboard"). Wait for GREETING_HEADING (real,
        # unconditional per this class's docstring) so the page is actually
        # interactive before returning.
        self.goto("/dashboard")
        self.wait_url_contains("/dashboard")
        self.find(*self.GREETING_HEADING)

    def greeting_text(self) -> str:
        return self.find(*self.GREETING_HEADING).text

    def is_empty_state(self) -> bool:
        return self.is_present(*self.EMPTY_STATE)

    def is_populated_state(self) -> bool:
        return self.is_present(*self.QUICK_ACTIONS_HEADING)

    def click_analyze_audio(self) -> None:
        self.click(self.find_clickable(*self.ANALYZE_AUDIO_HEADER_LINK))

    def click_view_history_quick_action(self) -> None:
        self.click(self.find_clickable(*self.QUICK_ACTION_VIEW_HISTORY))
