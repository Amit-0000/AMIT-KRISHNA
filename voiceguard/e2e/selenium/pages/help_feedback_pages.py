"""Page objects for /help, /help/:articleSlug, /feedback
(voiceguard/frontend/src/pages/Help/, Feedback/index.tsx). Same components as
the Appium suite covers (desktop viewport doesn't change these pages)."""
from __future__ import annotations

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

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

    def wait_articles_settled(self, timeout: int = 5) -> int:
        # Each card animates in inside its own <motion.div> with a
        # staggered delay (Help/index.tsx: transition={{delay: i * 0.03}})
        # -- .text can read as empty on a card that hasn't finished its
        # fade-in yet. Poll until article_card_titles()'s count stops
        # changing rather than reading it once right after a
        # navigation/click.
        last = {"count": -1, "stable_since": None}

        def _stable(_driver):
            n = len(self.article_card_titles())
            if n != last["count"]:
                last["count"] = n
                last["stable_since"] = time.monotonic()
                return False
            return time.monotonic() - last["stable_since"] >= 0.3

        WebDriverWait(self.driver, timeout, poll_frequency=0.1).until(_stable)
        return last["count"]

    def open_first_article(self) -> None:
        self.click(self.find_clickable(*self.ARTICLE_CARDS))

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
        # is_visible (waits), not is_present (immediate): confirmed live
        # that an immediate check can race React's first paint for
        # URL-encoded slugs specifically (e.g. "<img src=x onerror=...>"),
        # even though getArticleBySlug's lookup itself is synchronous.
        return self.is_visible(*self.NOT_FOUND_HEADING, timeout=10)

    def article_title(self) -> str:
        return self.find(By.CSS_SELECTOR, "article h1").text


class FeedbackPage(BasePage):
    CATEGORY_RADIOGROUP = (By.CSS_SELECTOR, 'div[role="radiogroup"][aria-label="Feedback category"]')
    MESSAGE_TEXTAREA = (By.ID, "message")
    SCAN_ID_INPUT = (By.ID, "scanId")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'button[type=submit]')
    MESSAGE_ERROR = (By.ID, "message-error")
    # POST /feedback is now implemented server-side (voiceguard security
    # audit F-30 added its rate limit, confirming the route is real and
    # live) -- confirmed by an actual POST /feedback call succeeding
    # against the running backend, not assumed from old comments. A
    # validation-passing submit now reaches the real "success" state below;
    # NOT_WIRED_UP_HEADING is kept only as a defensive fallback locator for
    # whatever real failure Feedback/index.tsx's catch branch still renders
    # (e.g. a genuine network/rate-limit error), not the expected path.
    SUCCESS_HEADING = (By.XPATH, '//h1[normalize-space()="Thanks for the feedback"]')
    NOT_WIRED_UP_HEADING = (By.XPATH, '//h1[normalize-space()="Couldn\'t send that yet"]')
    COPY_MESSAGE_BUTTON = (By.XPATH, '//button[contains(., "Copy message")]')

    def goto_feedback(self) -> None:
        self.goto("/feedback")
        self.find(*self.MESSAGE_TEXTAREA)

    def select_category(self, label: str) -> None:
        option = self.find(
            By.XPATH, f'//div[@role="radiogroup"][@aria-label="Feedback category"]//button[normalize-space()="{label}"]'
        )
        self.click(option)

    def fill_message(self, text: str) -> None:
        self.type_text(self.find(*self.MESSAGE_TEXTAREA), text)

    def submit(self) -> None:
        self.click(self.find_clickable(*self.SUBMIT_BUTTON))

    def message_error_text(self) -> str:
        return self.find(*self.MESSAGE_ERROR).text

    def is_not_wired_up_state_shown(self) -> bool:
        return self.is_visible(*self.NOT_WIRED_UP_HEADING, timeout=10)

    def is_success_state_shown(self) -> bool:
        return self.is_visible(*self.SUCCESS_HEADING, timeout=10)
