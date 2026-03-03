"""Scraper for factorioprints.com / factorio.school via Firebase REST API.

Both sites share a single Firebase Realtime Database backend
(project: facorio-blueprints — note the typo, one 't').
"""

import logging

import httpx

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)

_FIREBASE_BASE = "https://facorio-blueprints.firebaseio.com"
_BY_TAG_URL = f"{_FIREBASE_BASE}/byTag/version/1,1.json"
_BLUEPRINT_URL = f"{_FIREBASE_BASE}/blueprints/{{id}}.json"


class FactorioPrintsScraper(BaseScraper):
    """Firebase REST client for factorioprints.com / factorio.school."""

    source_site = "factorio_prints"

    def run(self):
        """Fetch blueprint keys tagged as version 1.1, then retrieve each one."""
        with httpx.Client(timeout=30) as client:
            # Get all blueprint keys tagged as version 1.1
            resp = self._fetch_with_retry(client, _BY_TAG_URL)
            if resp is None:
                logger.error("Failed to fetch 1.1 blueprint index")
                return

            tag_data = resp.json()
            if not tag_data or not isinstance(tag_data, dict):
                logger.warning("No blueprints found under version/1,1 tag")
                return

            keys = list(tag_data.keys())
            logger.info("Found %d blueprints tagged as version 1.1", len(keys))

            for key in keys:
                if not self._should_continue():
                    break

                detail_url = _BLUEPRINT_URL.format(id=key)
                if self._is_fetched(detail_url):
                    continue

                self._rate_limit()

                detail_resp = self._fetch_with_retry(client, detail_url)
                if detail_resp is None:
                    continue

                data = detail_resp.json()
                if not data or not isinstance(data, dict):
                    self._mark_fetched(detail_url)
                    continue

                bp_string = data.get("blueprintString")
                if not bp_string:
                    self._mark_fetched(detail_url)
                    continue

                author = None
                if "author" in data and isinstance(data["author"], dict):
                    author = data["author"].get("displayName")

                source_url = f"https://factorioprints.com/view/{key}"
                self._process_string(bp_string, source_url, author)
                self._mark_fetched(detail_url)
