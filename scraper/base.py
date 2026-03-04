"""Abstract base class for all scrapers.

Provides resumability, rate limiting, robots.txt compliance, deduplication,
and blueprint string extraction shared across all concrete scrapers.
"""

import logging
import re
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Blueprint strings: start with '0', followed by 40+ base64 chars
# Handles line breaks within strings and code block wrappers
_CODE_BLOCK_RE = re.compile(
    r"(?:```[^\n]*\n|`|\[code\])"
    r"(0[A-Za-z0-9+/=\s]{40,})"
    r"(?:```|`|\[/code\])",
    re.DOTALL,
)
_BARE_RE = re.compile(r"(0[A-Za-z0-9+/=]{40,})")


def extract_blueprint_strings(text: str) -> list[str]:
    """Extract candidate blueprint strings from text content."""
    candidates = []

    # First try code blocks
    for match in _CODE_BLOCK_RE.finditer(text):
        raw = re.sub(r"\s+", "", match.group(1))
        if raw not in candidates:
            candidates.append(raw)

    # Then bare strings not already captured
    for match in _BARE_RE.finditer(text):
        raw = match.group(1)
        if raw not in candidates:
            candidates.append(raw)

    return candidates


class BaseScraper(ABC):
    """Abstract base class for all concrete scrapers."""

    source_site: str = ""

    def __init__(self, *, limit: int | None = None):
        self.limit = limit
        self._delay = settings.scraper_rate_limit_delay
        self._progress_db = str(settings.scraper_progress_db)
        self._robots_cache: dict[str, RobotFileParser] = {}
        self._processed_count = 0
        self._on_new_blueprint = None
        self._init_progress_db()

    def _init_progress_db(self):
        """Create the progress tracker SQLite database if needed."""
        conn = sqlite3.connect(self._progress_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress ("
            "  url TEXT PRIMARY KEY,"
            "  status TEXT NOT NULL,"
            "  scraped_at TEXT NOT NULL"
            ")"
        )
        conn.commit()
        conn.close()

    def _is_fetched(self, url: str) -> bool:
        """Check if a URL has already been fetched."""
        conn = sqlite3.connect(self._progress_db)
        row = conn.execute(
            "SELECT status FROM progress WHERE url = ?", (url,)
        ).fetchone()
        conn.close()
        return row is not None and row[0] == "fetched"

    def _mark_fetched(self, url: str, status: str = "fetched"):
        """Record a URL as fetched in the progress tracker."""
        conn = sqlite3.connect(self._progress_db)
        conn.execute(
            "INSERT OR REPLACE INTO progress (url, status, scraped_at) VALUES (?, ?, ?)",
            (url, status, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

    def _check_robots(self, url: str) -> bool:
        """Check if the URL is allowed by robots.txt."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._robots_cache:
            rp = RobotFileParser()
            rp.set_url(f"{domain}/robots.txt")
            try:
                rp.read()
            except Exception:
                logger.warning("Could not fetch robots.txt for %s, allowing", domain)
                rp.allow_all = True
            self._robots_cache[domain] = rp

        rp = self._robots_cache[domain]
        return rp.can_fetch("*", url)

    def _rate_limit(self):
        """Sleep for the configured delay between requests."""
        time.sleep(self._delay)

    def _fetch_with_retry(
        self, client: httpx.Client, url: str, max_retries: int = 3,
        params: dict | None = None,
    ) -> httpx.Response | None:
        """Fetch a URL with retry logic and exponential backoff."""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = client.get(url, params=params)

                if response.status_code == 200:
                    return response

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limited, sleeping %ds", retry_after)
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    backoff = 2 ** attempt
                    logger.warning(
                        "Server error %d on %s, retry in %ds",
                        response.status_code, url, backoff,
                    )
                    time.sleep(backoff)
                    continue

                logger.warning("HTTP %d for %s, skipping", response.status_code, url)
                return None

            except httpx.HTTPError as exc:
                backoff = 2 ** attempt
                logger.warning("HTTP error on %s: %s, retry in %ds", url, exc, backoff)
                time.sleep(backoff)

        logger.error("Failed after %d retries: %s", max_retries, url)
        self._mark_fetched(url, status="failed")
        return None

    def _process_string(self, raw: str, source_url: str, author: str | None = None):
        """Process a candidate blueprint string: dedup and dispatch."""
        if self._on_new_blueprint:
            self._on_new_blueprint(
                raw=raw,
                source_url=source_url,
                source_site=self.source_site,
                author_raw=author,
            )
            self._processed_count += 1

    def _should_continue(self) -> bool:
        """Check if we should continue scraping (limit not reached)."""
        if self.limit is None:
            return True
        return self._processed_count < self.limit

    @abstractmethod
    def run(self):
        """Execute the scraping process. Implemented by each concrete scraper."""
