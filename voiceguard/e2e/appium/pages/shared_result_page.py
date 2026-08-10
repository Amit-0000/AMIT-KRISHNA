"""Page object for the public /r/:scanId page
(frontend/src/pages/SharedResult/index.tsx) — no AuthGuard, no AppShell."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import DEFAULT_TIMEOUT, BasePage


class SharedResultPage(BasePage):
    UNAVAILABLE_HEADING = (
        By.XPATH,
        "//h1[contains(text(), \"This shared result isn't available\")]",
    )
    GO_TO_VOICEGUARD_LINK = (By.LINK_TEXT, "Go to VoiceGuard")

    def goto_shared_result(self, scan_id: str) -> None:
        self.goto(f"/r/{scan_id}")

    def is_unavailable(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return self.is_visible(*self.UNAVAILABLE_HEADING, timeout=timeout)
