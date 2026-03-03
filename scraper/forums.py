"""Scraper for the Factorio forums (forums.factorio.com).

phpBB is fully server-rendered HTML — no Playwright needed.
Uses httpx + BeautifulSoup.
"""

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.base import BaseScraper, extract_blueprint_strings

logger = logging.getLogger(__name__)

_BASE_URL = "https://forums.factorio.com"
_SUBFORUMS = [
    {"f": 8, "name": "Show your Creations"},
    {"f": 194, "name": "Mechanical Throughput Magic"},
    {"f": 193, "name": "Combinator Creations"},
]


class ForumsScraper(BaseScraper):
    """Scrapes blueprint strings from Factorio forum posts."""

    source_site = "forums"

    def run(self):
        """Iterate target subforums, paginate threads, extract blueprints."""
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for subforum in _SUBFORUMS:
                if not self._should_continue():
                    break
                self._scrape_subforum(client, subforum["f"])

    def _scrape_subforum(self, client: httpx.Client, forum_id: int):
        """Paginate through a subforum's thread listings."""
        start = 0
        while self._should_continue():
            url = f"{_BASE_URL}/viewforum.php?f={forum_id}&start={start}"

            if not self._check_robots(url):
                logger.info("Disallowed by robots.txt: %s", url)
                break

            resp = self._fetch_with_retry(client, url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            topic_links = soup.select("a.topictitle")

            if not topic_links:
                break

            for link in topic_links:
                if not self._should_continue():
                    break
                href = link.get("href", "")
                if href:
                    topic_url = urljoin(_BASE_URL + "/", href)
                    self._scrape_topic(client, topic_url)

            start += 25

    def _scrape_topic(self, client: httpx.Client, topic_url: str):
        """Scrape all pages of a single topic thread."""
        page_start = 0
        while self._should_continue():
            url = topic_url if page_start == 0 else f"{topic_url}&start={page_start}"

            if self._is_fetched(url):
                page_start += 15
                continue

            resp = self._fetch_with_retry(client, url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            posts = soup.select("div.postbody div.content")

            if not posts:
                break

            for post in posts:
                if not self._should_continue():
                    break

                text = post.get_text()
                author_el = post.find_parent("div", class_="postbody")
                author = None
                if author_el:
                    author_link = author_el.select_one("a.username, a.username-coloured")
                    if author_link:
                        author = author_link.get_text(strip=True)

                candidates = extract_blueprint_strings(text)
                for raw in candidates:
                    if not self._should_continue():
                        break
                    self._process_string(raw, url, author)

            self._mark_fetched(url)

            # Check for next page
            next_link = soup.select_one("li.arrow.next a")
            if not next_link:
                break
            page_start += 15
