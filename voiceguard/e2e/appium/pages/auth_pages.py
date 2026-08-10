"""Page objects for the public/guest-guarded auth pages.

Selectors are taken directly from the real component source (read at
implementation time, not guessed):
  frontend/src/pages/LandingPage/index.tsx
  frontend/src/pages/Login/index.tsx
  frontend/src/pages/Signup/index.tsx
  frontend/src/pages/ForgotPassword/index.tsx
  frontend/src/pages/ResetPassword/index.tsx
  frontend/src/pages/VerifyEmail/index.tsx
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


class LandingPage(BasePage):
    MAIN_CONTENT = (By.ID, "main-content")

    def open(self) -> None:
        self.goto("/")

    def main_content_visible(self) -> bool:
        return self.is_visible(*self.MAIN_CONTENT)


class NotFoundPage(BasePage):
    RETURN_HOME_LINK = (By.LINK_TEXT, "Return home")

    def open_unknown_route(self) -> None:
        self.goto("/this-route-does-not-exist-appium-qa")

    def shows_404(self) -> bool:
        return "404" in self.body_text()


class LoginPage(BasePage):
    EMAIL = (By.ID, "email")
    PASSWORD = (By.ID, "password")
    FORGOT_PASSWORD_LINK = (By.LINK_TEXT, "Forgot password?")

    def open(self) -> None:
        self.goto("/login")

    def login(self, email: str, password: str) -> None:
        self.fill_id("email", email)
        self.fill_id("password", password)
        self.submit()

    def error_message(self) -> str:
        return self.alert_text()


class SignupPage(BasePage):
    DISPLAY_NAME = (By.ID, "displayName")
    EMAIL = (By.ID, "email")
    PASSWORD = (By.ID, "password")
    CONFIRM_PASSWORD = (By.ID, "confirmPassword")

    def open(self) -> None:
        self.goto("/signup")

    def fill_form(self, display_name: str, email: str, password: str, confirm_password: str) -> None:
        self.fill_id("displayName", display_name)
        self.fill_id("email", email)
        self.fill_id("password", password)
        self.fill_id("confirmPassword", confirm_password)

    def submit_signup(self) -> None:
        self.submit()

    def check_email_message_shown(self) -> bool:
        return "sent a verification link" in self.body_text()


class ForgotPasswordPage(BasePage):
    EMAIL = (By.ID, "email")

    def open(self) -> None:
        self.goto("/forgot-password")

    def submit_email(self, email: str) -> None:
        self.fill_id("email", email)
        self.submit()

    def check_email_message_shown(self) -> bool:
        return "sent a link to reset your password" in self.body_text()


class ResetPasswordPage(BasePage):
    PASSWORD = (By.ID, "password")
    CONFIRM_PASSWORD = (By.ID, "confirmPassword")

    def open(self, token: str | None = None) -> None:
        path = "/reset-password"
        if token:
            path += f"?token={token}"
        self.goto(path)

    def fill_and_submit(self, password: str, confirm_password: str) -> None:
        self.fill_id("password", password)
        self.fill_id("confirmPassword", confirm_password)
        self.submit()

    def shows_invalid_link(self) -> bool:
        return "invalid or has expired" in self.body_text() or "Reset link invalid" in self.body_text()

    def shows_form(self) -> bool:
        return self.is_visible(*self.PASSWORD)


class VerifyEmailPage(BasePage):
    RESEND_EMAIL = (By.ID, "resend-email")

    def open(self, token: str | None = None) -> None:
        path = "/verify-email"
        if token:
            path += f"?token={token}"
        self.goto(path)

    def shows_missing_token_message(self) -> bool:
        return "missing a verification token" in self.body_text()

    def shows_invalid_or_expired_message(self, timeout: int = 15) -> bool:
        # The real component fires an async authApi.verifyEmail(token) call
        # in a useEffect before landing on the error state ("Just a
        # moment…" while verifying) — wait for that state transition
        # instead of asserting immediately.
        WebDriverWait(self.driver, timeout).until(
            lambda d: "Just a moment" not in d.find_element(By.TAG_NAME, "body").text
        )
        return "invalid or has expired" in self.body_text()

    def resend_to(self, email: str) -> None:
        self.fill_id("resend-email", email)
        self.submit()

    def resend_confirmation_shown(self) -> bool:
        return "A new verification link has been sent" in self.body_text()
