"""Page object for /onboarding (AuthGuard-protected, 3-step: welcome ->
use-case -> privacy). Selectors taken from frontend/src/pages/Onboarding/index.tsx
— no ids on this page, so real visible button/label text is used instead."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage

GET_STARTED_XPATH = "//button[contains(., 'Get started')]"
CONTINUE_XPATH = "//button[contains(., 'Continue')]"
FINISH_XPATH = "//button[contains(., 'Go to dashboard')]"
USE_CASE_RADIOGROUP = (By.CSS_SELECTOR, "[role=radiogroup]")
# Real label from Onboarding/index.tsx's USE_CASES list.
CURIOSITY_OPTION_XPATH = "//button[@role='radio' and contains(., 'Personal curiosity')]"
PRIVACY_LIST = (By.CSS_SELECTOR, "ul[role=list]")


class OnboardingPage(BasePage):
    def open(self) -> None:
        self.goto("/onboarding")

    def welcome_step_shown(self) -> bool:
        return self.is_visible(By.XPATH, GET_STARTED_XPATH)

    def click_get_started(self) -> None:
        self.click(self.find_clickable(By.XPATH, GET_STARTED_XPATH))

    def use_case_step_shown(self) -> bool:
        return self.is_visible(*USE_CASE_RADIOGROUP)

    def select_curiosity_use_case(self) -> None:
        self.click(self.find_clickable(By.XPATH, CURIOSITY_OPTION_XPATH))

    def click_continue(self) -> None:
        self.click(self.find_clickable(By.XPATH, CONTINUE_XPATH))

    def privacy_step_shown(self) -> bool:
        return self.is_visible(*PRIVACY_LIST)

    def finish(self) -> None:
        self.click(self.find_clickable(By.XPATH, FINISH_XPATH))
