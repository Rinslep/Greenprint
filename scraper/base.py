# scraper/base.py
#
# TODO: Abstract base class that all concrete scrapers extend.
#
# Responsibilities:
# - Resumability:
#     Maintain a local SQLite database (path from config.SCRAPER_PROGRESS_DB).
#     Record each fetched page/URL with status (pending, fetched, failed).
#     On restart, skip already-fetched items and resume from where it stopped.
# - Rate limiting:
#     Enforce configurable delay (config.SCRAPER_RATE_LIMIT_DELAY) between requests.
#     Respect Retry-After headers — if received, sleep for the specified duration before retrying.
#     Exponential backoff on 5xx errors (max 3 retries then mark failed).
# - robots.txt compliance:
#     Before first request to any domain, fetch and parse robots.txt using urllib.robotparser.
#     Cache parsed robots per domain for the session.
#     Skip any URL disallowed for the user agent.
# - Deduplication:
#     SHA256-hash raw blueprint strings before passing to the pipeline.
#     Skip (log, don't error) strings already present in the blueprints table.
# - Metadata capture:
#     Attach source_url, scraped_at (UTC timestamp), source_site, and raw author identifier.
#     Author identifier is stored raw by the scraper; anonymisation happens in the storage layer.
# - String extraction:
#     Provide a shared regex that matches Factorio blueprint strings (starts with '0' + base64 chars).
#     Account for line breaks within strings, code block wrappers (backtick, [code] tags), whitespace.
#     Return a list of candidate strings; let the pipeline decide which are valid.
# - Abstract interface:
#     Define abstract method `run()` that each concrete scraper implements.
#     Concrete scrapers call self._process_string(raw, source_url, author) for each candidate found.


class BaseScraper:
    pass  # TODO: implement
