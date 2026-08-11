"""Desktop coverage of /help, /help/:articleSlug, /feedback. Same components
as the Appium suite covers."""
from __future__ import annotations

import pytest

from pages.help_feedback_pages import FeedbackPage, HelpArticlePage, HelpCenterPage

pytestmark = [pytest.mark.low]

REAL_ARTICLE_SLUG = "how-voiceguard-detects-ai-audio"  # Help/content.ts


def test_help_center_renders_article_cards(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    assert len(help_center.article_card_titles()) > 0


def test_help_center_search_filters_articles(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    help_center.search("audio formats")
    titles = help_center.article_card_titles()
    assert any("format" in t.lower() for t in titles)


def test_help_center_search_with_no_matches_shows_empty_state(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    help_center.search("zzzxxxqqq_no_such_article")
    assert help_center.is_no_results_shown()


def test_help_article_page_renders_real_article(authenticated_driver, base_url):
    article = HelpArticlePage(authenticated_driver, base_url)
    article.goto_article(REAL_ARTICLE_SLUG)
    assert article.is_article_shown()
    assert "VoiceGuard" in article.article_title()


def test_help_article_page_shows_not_found_for_unknown_slug(authenticated_driver, base_url):
    article = HelpArticlePage(authenticated_driver, base_url)
    article.goto_article("this-slug-does-not-exist")
    assert article.is_not_found_shown()


def test_feedback_form_rejects_message_below_minimum_length(authenticated_driver, base_url):
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.fill_message("short")
    feedback.submit()
    assert "10 char" in feedback.message_error_text().lower()


def test_feedback_form_rejects_message_one_char_below_minimum(authenticated_driver, base_url):
    # feedbackSchema: message.min(10) -- 9 chars is the exact boundary
    # violation, distinct from the "short" (5 chars) case above.
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.fill_message("A" * 9)
    feedback.submit()
    assert "10 char" in feedback.message_error_text().lower()


def test_feedback_form_rejects_message_over_maximum_length(authenticated_driver, base_url):
    # feedbackSchema: message.max(2000).
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.fill_message("A" * 2001)
    feedback.submit()
    assert "2000 char" in feedback.message_error_text().lower()


def test_feedback_form_accepts_message_at_exact_minimum_length(authenticated_driver, base_url):
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.select_category("General feedback")
    feedback.fill_message("A" * 10)
    feedback.submit()
    assert feedback.is_success_state_shown()


def test_feedback_scanid_query_param_preselects_incorrect_result_category(authenticated_driver, base_url):
    # Feedback/index.tsx: defaultValues.category is 'incorrect_result' when
    # a ?scanId= query param is present, 'general' otherwise -- real,
    # read behavior, not assumed.
    import uuid

    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto(f"/feedback?scanId={uuid.uuid4()}")
    feedback.find(*feedback.MESSAGE_TEXTAREA)
    option = feedback.find(
        "xpath",
        '//div[@role="radiogroup"][@aria-label="Feedback category"]//button[normalize-space()="Incorrect result"]',
    )
    assert option.get_attribute("aria-checked") == "true"


def test_feedback_without_scanid_query_param_defaults_to_general_category(authenticated_driver, base_url):
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    option = feedback.find(
        "xpath",
        '//div[@role="radiogroup"][@aria-label="Feedback category"]//button[normalize-space()="General feedback"]',
    )
    assert option.get_attribute("aria-checked") == "true"


def test_feedback_form_submit_reaches_the_real_success_state(authenticated_driver, base_url):
    # Real, current backend behavior, confirmed live against the running
    # API (POST /feedback), not assumed from older documentation: a
    # validation-passing submit now succeeds end-to-end and reaches the
    # real "Thanks for the feedback" state, not a failure state.
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.select_category("General feedback")
    feedback.fill_message("This is a real feedback message submitted by the Selenium desktop suite.")
    feedback.submit()
    assert feedback.is_success_state_shown()


def test_feedback_category_radiogroup_shows_all_categories(authenticated_driver, base_url):
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    for label in ("Incorrect result", "Bug report", "Feature request", "General feedback"):
        assert feedback.find(
            "xpath",
            f'//div[@role="radiogroup"][@aria-label="Feedback category"]//button[normalize-space()="{label}"]',
        ).is_displayed()


def test_feedback_message_textarea_reachable_directly_via_url(authenticated_driver, base_url):
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    assert feedback.is_visible(*feedback.MESSAGE_TEXTAREA)
    assert "/login" not in feedback.current_url


def test_help_center_search_is_case_insensitive(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    help_center.search("AUDIO FORMATS")
    titles = help_center.article_card_titles()
    assert any("format" in t.lower() for t in titles)


def test_help_center_category_filter_narrows_results(authenticated_driver, base_url):
    # Help/index.tsx: category is independent state from the search query
    # (both filters AND together) -- selecting "Troubleshooting" narrows
    # results without touching the search box, avoiding the unreliable
    # Selenium .clear()-on-a-React-controlled-input interaction a
    # search-then-clear flow would need.
    #
    # Each card renders inside its own <motion.div> with a staggered
    # entrance animation (transition={{delay: i * 0.03}}) -- reading
    # .text immediately after a navigation/click can catch later cards
    # mid-fade, so wait_articles_settled polls until the count is stable
    # rather than reading it once.
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    before = help_center.wait_articles_settled()
    category_btn = help_center.find_clickable("xpath", "//button[normalize-space()='Troubleshooting']")
    help_center.click(category_btn)
    filtered = help_center.wait_articles_settled()
    assert 0 < filtered <= before


def test_help_center_all_topics_button_resets_category_filter(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    before = help_center.wait_articles_settled()
    category_btn = help_center.find_clickable("xpath", "//button[normalize-space()='Troubleshooting']")
    help_center.click(category_btn)
    all_topics = help_center.find_clickable(*help_center.ALL_TOPICS_BUTTON)
    help_center.click(all_topics)
    restored = help_center.wait_articles_settled()
    assert restored == before


def test_help_article_page_has_back_to_help_link(authenticated_driver, base_url):
    article = HelpArticlePage(authenticated_driver, base_url)
    article.goto_article(REAL_ARTICLE_SLUG)
    assert article.is_visible(*article.BACK_TO_HELP_LINK)


def test_help_article_not_found_has_back_to_help_link(authenticated_driver, base_url):
    article = HelpArticlePage(authenticated_driver, base_url)
    article.goto_article("this-slug-does-not-exist")
    assert article.is_visible(*article.BACK_TO_HELP_LINK)


def test_help_center_give_feedback_link_navigates_to_feedback(authenticated_driver, base_url):
    help_center = HelpCenterPage(authenticated_driver, base_url)
    help_center.goto_help()
    help_center.click(help_center.find_clickable(*help_center.GIVE_FEEDBACK_LINK))
    help_center.wait_url_contains("/feedback")
    assert "/feedback" in help_center.current_url
