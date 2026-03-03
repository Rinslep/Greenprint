# scraper/forums.py
#
# TODO: Scraper for the Factorio forums (forums.factorio.com).
#
# Source characteristics:
# - Static HTML for most pages, but some threads may require JS rendering.
# - Use BeautifulSoup for static pages; fall back to Playwright for JS-rendered ones.
# - Blueprint strings often embedded in [code] tags or bare text in posts.
#
# Implementation notes:
# - Extend BaseScraper.
# - Identify relevant subforums (e.g., "Show your Creations", "Blueprints/Maps").
# - Paginate through thread listings; visit each thread; iterate all posts in the thread.
# - Apply the base class string extraction regex to each post's text content.
# - Use Playwright only when requests + BeautifulSoup yields empty/incomplete content.
# - Author identifier: forum username (stored raw; anonymised in storage layer).
# - Record progress by thread ID and page number in the resumability DB.
# - Honour robots.txt; apply configured rate limit delay between page fetches.
# - Note: Playwright requires a browser install step (playwright install chromium).


from scraper.base import BaseScraper


class ForumsScraper(BaseScraper):
    pass  # TODO: implement
