# config.py
#
# TODO: Environment configuration, global paths, and constants.
#
# Needs to provide:
# - DB_URL: SQLAlchemy connection string, read from env var (default: local SQLite for dev)
# - REFERENCE_DIR: absolute path to the reference/ directory
# - LOG_LEVEL: from env, default INFO
# - SCRAPER_RATE_LIMIT_DELAY: seconds between requests per scraper (default 1.0)
# - SCRAPER_PROGRESS_DB: path to the SQLite progress tracker used by scrapers
# - REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT: from env, for PRAW
# - API_RATE_LIMIT_PER_MINUTE: per-IP request cap (default 60)
# - TARGET_GAME_VERSION: (1, 1, 110) as a tuple for version filter comparisons
# - Load with python-dotenv so .env works in dev without setting real env vars
# - Expose a single `settings` object imported everywhere (use pydantic-settings BaseSettings)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = BASE_DIR / "reference"
