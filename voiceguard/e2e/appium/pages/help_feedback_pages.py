"""Page objects for /help, /help/:articleSlug, /feedback
(voiceguard/frontend/src/pages/Help/, Feedback/index.tsx)."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class HelpCenterPage(BasePage):
    SEARCH_INPUT = (By.CSS_SELECTOR, 'input[aria-label="Search help articles"]')
    ALL_TOPICS_BUTTON = (By.XPATH, '//button[normalize-space()="All topics"]')
    NO_RESULTS_HEADING = (By.XPATH, '//h2[normalize-space()="No articles found"]')
    ARTICLE_CARDS = (By.CSS_SELECTOR, 'a[href^="/help/"]')
    GIVE_FEEDBACK_LINK = (By.XPATH, '//a[@href="/feedback"]')

    def goto_help(self) -> None:
        self.goto("/help")
        self.find(*self.SEARCH_INPUT)

    def search(self, query: str) -> None:
        self.type_text(self.find(*self.SEARCH_INPUT), query)

    def article_card_titles(self) -> list[str]:
        return [el.text for el in self.find_all(*self.ARTICLE_CARDS) if el.text]

    def open_first_article(self) -> None:
        self.tap(self.find_clickable(*self.ARTICLE_CARDS))

    def is_no_results_shown(self) -> bool:
        return self.is_present(*self.NO_RESULTS_HEADING)


class HelpArticlePage(BasePage):
    ARTICLE = (By.TAG_NAME, "article")
    NOT_FOUND_HEADING = (By.XPATH, '//h2[normalize-space()="Article not found"]')
    BACK_TO_HELP_LINK = (By.XPATH, '//a[@href="/help"]')

    def goto_article(self, slug: str) -> None:
        self.goto(f"/help/{slug}")

    def is_article_shown(self) -> bool:
        return self.is_present(*self.ARTICLE)

    def is_not_found_shown(self) -> bool:
        return self.is_present(*self.NOT_FOUND_HEADING)

    def article_title(self) -> str:
        return self.find(By.CSS_SELECTOR, "article h1").text


class FeedbackPage(BasePage):
    CATEGORY_RADIOGROUP = (By.CSS_SELECTOR, 'div[role="radiogroup"][aria-label="Feedback category"]')
    MESSAGE_TEXTAREA = (By.ID, "message")
    SCAN_ID_INPUT = (By.ID, "scanId")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'button[type=submit]')
    MESSAGE_ERROR = (By.ID, "message-error")
    # Real, current backend state: feedbackApi.submit() isn't implemented
    # server-side yet, so a validation-passing submit lands on the "failed"
    # UI state below, not "success" -- see Feedback/index.tsx's own comment.
    NOT_WIRED_UP_HEADING = (By.XPATH, '//h1[normalize-space()="Couldn\'t send that yet"]')
    COPY_MESSAGE_BUTTON = (By.XPATH, '//button[contains(., "Copy message")]')

    def goto_feedback(self) -> None:
        self.goto("/feedback")
        self.find(*self.MESSAGE_TEXTAREA)

    def select_category(self, label: str) -> None:
        option = self.find(By.XPATH, f'//div[@role="radiogroup"][@aria-label="Feedback category"]//button[normalize-space()="{label}"]')
        self.tap(option)

    def fill_message(self, text: str) -> None:
        self.type_text(self.find(*self.MESSAGE_TEXTAREA), text)

    def submit(self) -> None:
        self.tap(self.find_clickable(*self.SUBMIT_BUTTON))

    def message_error_text(self) -> str:
        return self.find(*self.MESSAGE_ERROR).text

    def is_not_wired_up_state_shown(self) -> bool:
        return self.is_visible(*self.NOT_WIRED_UP_HEADING, timeout=10)
