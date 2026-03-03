# scraper/factorio_school.py
#
# TODO: Scraper for factorio.school.
#
# Source characteristics:
# - Clean, consistent HTML structure — no JS rendering required.
# - Use plain HTTP requests + BeautifulSoup.
#
# Implementation notes:
# - Extend BaseScraper.
# - Identify the site's blueprint listing and pagination structure.
# - Extract blueprint detail page URLs from listings, then visit each for the raw string.
# - Capture author username (to be anonymised later) and source URL.
# - Pass each candidate string to self._process_string(raw, source_url, author).
# - Record progress in the resumability DB.
# - Honour robots.txt and the configured rate limit delay.


from scraper.base import BaseScraper


class FactorioSchoolScraper(BaseScraper):
    pass  # TODO: implement
