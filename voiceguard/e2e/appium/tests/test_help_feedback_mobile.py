"""Mobile-web coverage of /help, /help/:articleSlug, /feedback."""
from __future__ import annotations

from pages.help_feedback_pages import FeedbackPage, HelpArticlePage, HelpCenterPage

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


def test_feedback_form_submit_reaches_the_real_not_wired_up_state(authenticated_driver, base_url):
    # Real, current backend behavior (see FeedbackPage.NOT_WIRED_UP_HEADING's
    # docstring) -- a validation-passing submit still can't succeed because
    # the backend endpoint isn't implemented yet, so this is the true
    # end-to-end outcome today, not a simulated failure.
    feedback = FeedbackPage(authenticated_driver, base_url)
    feedback.goto_feedback()
    feedback.select_category("General feedback")
    feedback.fill_message("This is a real feedback message submitted by the Appium mobile-web suite.")
    feedback.submit()
    assert feedback.is_not_wired_up_state_shown()
