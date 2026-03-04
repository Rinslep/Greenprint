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
_ALL_BLUEPRINTS_URL = f"{_FIREBASE_BASE}/blueprints.json"

_PAGE_SIZE = 200


class FactorioPrintsScraper(BaseScraper):
    """Firebase REST client for factorioprints.com / factorio.school."""

    source_site = "factorio_prints"

    def run(self):
        """Phase 1: tagged 1.1 blueprints, Phase 2: paginate full collection."""
        with httpx.Client(timeout=30) as client:
            self._fetch_tagged(client)
            self._fetch_all_paginated(client)

    def _fetch_tagged(self, client: httpx.Client):
        """Fetch blueprint keys tagged as version 1.1, then retrieve each one."""
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
            self._fetch_single(client, key)

    def _fetch_all_paginated(self, client: httpx.Client):
        """Paginate through ALL blueprints using Firebase REST orderBy/limitToFirst.

        The pipeline's version filter rejects non-1.1 blueprints, so we fetch
        everything and let downstream filtering handle version selection.
        """
        last_key = None
        page = 0

        while self._should_continue():
            params = {
                'orderBy': '"$key"',
                'limitToFirst': str(_PAGE_SIZE),
            }
            if last_key:
                params['startAfter'] = f'"{last_key}"'

            url = _ALL_BLUEPRINTS_URL
            self._rate_limit()

            resp = self._fetch_with_retry(client, url, params=params)
            if resp is None:
                logger.error("Failed to fetch blueprint page %d", page)
                break

            data = resp.json()
            if not data or not isinstance(data, dict):
                logger.info("No more blueprints to paginate (page %d)", page)
                break

            keys = sorted(data.keys())
            page += 1
            logger.info("Page %d: %d blueprints", page, len(keys))

            for key in keys:
                if not self._should_continue():
                    break

                bp_data = data[key]
                if not isinstance(bp_data, dict):
                    continue

                detail_url = _BLUEPRINT_URL.format(id=key)
                if self._is_fetched(detail_url):
                    continue

                bp_string = bp_data.get("blueprintString")
                if not bp_string:
                    self._mark_fetched(detail_url)
                    continue

                author = None
                if "author" in bp_data and isinstance(bp_data["author"], dict):
                    author = bp_data["author"].get("displayName")

                source_url = f"https://factorioprints.com/view/{key}"
                self._process_string(bp_string, source_url, author)
                self._mark_fetched(detail_url)

            # If we got fewer than PAGE_SIZE results, we've reached the end
            if len(keys) < _PAGE_SIZE:
                logger.info("Pagination complete after %d pages", page)
                break

            last_key = keys[-1]

    def _fetch_single(self, client: httpx.Client, key: str):
        """Fetch and process a single blueprint by key."""
        detail_url = _BLUEPRINT_URL.format(id=key)
        if self._is_fetched(detail_url):
            return

        self._rate_limit()

        detail_resp = self._fetch_with_retry(client, detail_url)
        if detail_resp is None:
            return

        data = detail_resp.json()
        if not data or not isinstance(data, dict):
            self._mark_fetched(detail_url)
            return

        bp_string = data.get("blueprintString")
        if not bp_string:
            self._mark_fetched(detail_url)
            return

        author = None
        if "author" in data and isinstance(data["author"], dict):
            author = data["author"].get("displayName")

        source_url = f"https://factorioprints.com/view/{key}"
        self._process_string(bp_string, source_url, author)
        self._mark_fetched(detail_url)
