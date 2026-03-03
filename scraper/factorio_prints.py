# scraper/factorio_prints.py
#
# TODO: Scraper for factorio.school (formerly known as Factorio Prints).
#
# Source characteristics:
# - Paginated API-style endpoints (largest source by volume).
# - Use plain HTTP requests (no JS rendering needed).
# - Blueprint strings are available directly in API responses or linked pages.
#
# Implementation notes:
# - Extend BaseScraper.
# - Discover the pagination scheme (endpoint URL pattern, page/cursor parameter).
# - Iterate all pages; for each page extract blueprint entries with their URL and author.
# - Follow each blueprint detail URL to retrieve the raw string if not in the listing.
# - Pass each candidate string to self._process_string(raw, source_url, author).
# - Record progress (page number or cursor) in the resumability DB so scraping can resume.
# - Be respectful: honour robots.txt; use the configured rate limit delay.


from scraper.base import BaseScraper


class FactorioPrintsScraper(BaseScraper):
    pass  # TODO: implement
