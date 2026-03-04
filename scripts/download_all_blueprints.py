"""Download all blueprints from factorioprints.com to a local JSONL file.

Bypasses the pipeline version filter — saves every blueprint regardless of
game version. Each line is a JSON object with the raw string and metadata.

Resumable: uses the scraper's progress DB to skip already-fetched URLs.
Rate-limited: 1s delay between requests (Firebase is a paid service for the site owner).

Usage:
    python scripts/download_all_blueprints.py
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import FactorioPrintsScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "raw_blueprints.jsonl"


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Count existing lines for resume reporting
    existing = 0
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = sum(1 for _ in f)
        logger.info("Resuming — %d blueprints already saved", existing)

    saved = 0
    out = open(OUTPUT_FILE, "a", encoding="utf-8")

    def save_raw(raw, source_url, source_site, author_raw):
        nonlocal saved
        record = {
            "raw": raw,
            "source_url": source_url,
            "source_site": source_site,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        out.flush()
        saved += 1
        if saved % 100 == 0:
            logger.info("Saved %d new blueprints (%d total)", saved, existing + saved)

    scraper = FactorioPrintsScraper(limit=None)
    scraper._on_new_blueprint = save_raw

    logger.info("Starting full download from factorioprints.com...")
    logger.info("Rate limit: %.1fs between requests", scraper._delay)

    try:
        scraper.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        out.close()
        logger.info(
            "Done. Saved %d new blueprints (%d total on disk)",
            saved, existing + saved,
        )


if __name__ == "__main__":
    main()
