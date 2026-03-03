"""Scraper for r/factorio using PRAW."""

import logging

import praw

from config import settings
from scraper.base import BaseScraper, extract_blueprint_strings

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """Scrapes blueprint strings from r/factorio posts and comments."""

    source_site = "reddit"

    def run(self):
        """Search r/factorio for posts containing blueprint strings."""
        if not settings.reddit_client_id:
            logger.error("Reddit credentials not configured, skipping")
            return

        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent or "greenprint-scraper/0.1",
        )

        subreddit = reddit.subreddit("factorio")

        for submission in subreddit.search("blueprint", sort="new", limit=self.limit):
            if not self._should_continue():
                break

            post_url = f"https://reddit.com{submission.permalink}"
            if self._is_fetched(post_url):
                continue

            # Search post body
            if submission.selftext:
                candidates = extract_blueprint_strings(submission.selftext)
                for raw in candidates:
                    if not self._should_continue():
                        break
                    author = str(submission.author) if submission.author else None
                    self._process_string(raw, post_url, author)

            # Search comments
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                if not self._should_continue():
                    break
                if comment.body:
                    candidates = extract_blueprint_strings(comment.body)
                    for raw in candidates:
                        if not self._should_continue():
                            break
                        comment_url = f"https://reddit.com{comment.permalink}"
                        author = str(comment.author) if comment.author else None
                        self._process_string(raw, comment_url, author)

            self._mark_fetched(post_url)
