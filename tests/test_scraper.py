"""Tests for scraper base class and utilities."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.base import BaseScraper, extract_blueprint_strings


# ---------------------------------------------------------------------------
# String extraction tests
# ---------------------------------------------------------------------------

class TestExtractBlueprintStrings:
    def test_bare_string(self):
        text = "Here is a blueprint: 0eNpjYBBiYGBgZmBg... and more text"
        # Need 40+ chars after the 0
        raw = "0" + "A" * 50
        text = f"Check this out: {raw} cool right?"
        result = extract_blueprint_strings(text)
        assert len(result) == 1
        assert result[0] == raw

    def test_code_block_backticks(self):
        raw = "0" + "B" * 60
        text = f"```\n{raw}\n```"
        result = extract_blueprint_strings(text)
        assert len(result) == 1
        assert result[0] == raw

    def test_code_tags(self):
        raw = "0" + "C" * 50
        text = f"[code]{raw}[/code]"
        result = extract_blueprint_strings(text)
        assert len(result) == 1
        assert result[0] == raw

    def test_linebreaks_in_code_block(self):
        part1 = "0" + "D" * 30
        part2 = "E" * 30
        text = f"```\n{part1}\n{part2}\n```"
        result = extract_blueprint_strings(text)
        assert len(result) >= 1
        # Linebreaks should be stripped from code block matches
        assert "\n" not in result[0]

    def test_rejects_short_strings(self):
        text = "Not a blueprint: 0ABC123"
        result = extract_blueprint_strings(text)
        assert len(result) == 0

    def test_multiple_strings(self):
        raw1 = "0" + "F" * 50
        raw2 = "0" + "G" * 50
        text = f"{raw1} some text {raw2}"
        result = extract_blueprint_strings(text)
        assert len(result) == 2

    def test_no_duplicates(self):
        raw = "0" + "H" * 50
        text = f"{raw} repeated {raw}"
        result = extract_blueprint_strings(text)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# BaseScraper tests
# ---------------------------------------------------------------------------

class ConcreteScraper(BaseScraper):
    """Minimal concrete scraper for testing."""
    source_site = "test"

    def __init__(self, **kwargs):
        # Use a temp file for the progress DB
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        with patch.object(
            type(self), '__init__', lambda self, **kw: None
        ):
            pass
        self.limit = kwargs.get("limit")
        self._delay = 0  # No delay in tests
        self._progress_db = self._tmp.name
        self._robots_cache = {}
        self._processed_count = 0
        self._on_new_blueprint = kwargs.get("on_new_blueprint")
        self._init_progress_db()

    def run(self):
        pass


class TestBaseScraper:
    def test_resumability_tracks_urls(self):
        scraper = ConcreteScraper()
        assert not scraper._is_fetched("https://example.com/1")
        scraper._mark_fetched("https://example.com/1")
        assert scraper._is_fetched("https://example.com/1")

    def test_resumability_persists(self):
        scraper = ConcreteScraper()
        scraper._mark_fetched("https://example.com/persist")

        # Create new scraper with same DB
        scraper2 = ConcreteScraper()
        scraper2._progress_db = scraper._progress_db
        assert scraper2._is_fetched("https://example.com/persist")

    def test_process_string_calls_hook(self):
        callback = MagicMock()
        scraper = ConcreteScraper(on_new_blueprint=callback)

        scraper._process_string("0abc123", "https://example.com", "author1")

        callback.assert_called_once()
        call_kwargs = callback.call_args
        assert call_kwargs.kwargs["raw"] == "0abc123"
        assert call_kwargs.kwargs["source_site"] == "test"

    def test_limit_stops_processing(self):
        scraper = ConcreteScraper(limit=2, on_new_blueprint=MagicMock())
        assert scraper._should_continue()
        scraper._process_string("0a" + "X" * 50, "url1", None)
        assert scraper._should_continue()
        scraper._process_string("0b" + "X" * 50, "url2", None)
        assert not scraper._should_continue()

    def test_dedup_via_progress_tracker(self):
        callback = MagicMock()
        scraper = ConcreteScraper(on_new_blueprint=callback)

        # Mark URL as already fetched
        scraper._mark_fetched("https://example.com/old")
        assert scraper._is_fetched("https://example.com/old")
        assert not scraper._is_fetched("https://example.com/new")
