"""Decode raw Factorio blueprint strings into Python dicts.

Decode steps:
1. Verify leading version character is '0' (Factorio 1.1)
2. Base64 decode the remainder
3. zlib decompress
4. JSON parse
5. Detect and dissolve blueprint books into individual blueprints

Every failure raises DecodeError with stage and reason for logging.
"""

import base64
import hashlib
import json
import zlib

import structlog

log = structlog.get_logger()


class DecodeError(Exception):
    def __init__(
        self,
        failure_stage: str,
        failure_reason: str,
        raw_string_hash: str,
        source_url: str,
    ):
        self.failure_stage = failure_stage
        self.failure_reason = failure_reason
        self.raw_string_hash = raw_string_hash
        self.source_url = source_url
        super().__init__(f"[{failure_stage}] {failure_reason}")


def _hash_string(raw_string: str) -> str:
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()


def decode(raw_string: str, source_url: str = "") -> list[dict]:
    """Decode a Factorio blueprint string into a list of blueprint dicts.

    Blueprint books are dissolved: each child blueprint is returned separately
    with ``source_book_id`` set to the SHA-256 hash of the raw string.
    Books themselves are never returned.

    Returns a list (single blueprint -> list of one, book -> list of children).
    """
    raw_hash = _hash_string(raw_string)

    # Step 1: Check version prefix
    if not raw_string or raw_string[0] != "0":
        log.warning(
            "decode_failed",
            stage="STRING_EXTRACTION",
            hash=raw_hash,
            source_url=source_url,
        )
        raise DecodeError(
            failure_stage="STRING_EXTRACTION",
            failure_reason=f"Expected leading '0', got '{raw_string[0] if raw_string else '<empty>'}'",
            raw_string_hash=raw_hash,
            source_url=source_url,
        )

    # Step 2: Base64 decode
    try:
        decoded_bytes = base64.b64decode(raw_string[1:])
    except Exception as exc:
        log.warning(
            "decode_failed",
            stage="DECODE_FAILURE",
            reason="base64",
            hash=raw_hash,
            source_url=source_url,
        )
        raise DecodeError(
            failure_stage="DECODE_FAILURE",
            failure_reason=f"Base64 decode failed: {exc}",
            raw_string_hash=raw_hash,
            source_url=source_url,
        ) from exc

    # Step 3: zlib decompress
    try:
        decompressed = zlib.decompress(decoded_bytes)
    except Exception as exc:
        log.warning(
            "decode_failed",
            stage="DECODE_FAILURE",
            reason="zlib",
            hash=raw_hash,
            source_url=source_url,
        )
        raise DecodeError(
            failure_stage="DECODE_FAILURE",
            failure_reason=f"zlib decompress failed: {exc}",
            raw_string_hash=raw_hash,
            source_url=source_url,
        ) from exc

    # Step 4: JSON parse
    try:
        data = json.loads(decompressed)
    except Exception as exc:
        log.warning(
            "decode_failed",
            stage="JSON_PARSE",
            hash=raw_hash,
            source_url=source_url,
        )
        raise DecodeError(
            failure_stage="JSON_PARSE",
            failure_reason=f"JSON parse failed: {exc}",
            raw_string_hash=raw_hash,
            source_url=source_url,
        ) from exc

    # Step 5: Dissolve blueprint books
    if "blueprint_book" in data:
        log.debug("blueprint_book_detected", hash=raw_hash, source_url=source_url)
        return _extract_book_children(data, raw_hash)

    return [data]


def _extract_book_children(data: dict, book_hash: str) -> list[dict]:
    """Recursively extract all blueprints from a blueprint book."""
    results = []
    book = data.get("blueprint_book", {})
    children = book.get("blueprints", [])

    for child in children:
        if "blueprint_book" in child:
            results.extend(_extract_book_children(child, book_hash))
        elif "blueprint" in child:
            child["source_book_id"] = book_hash
            results.append(child)

    log.debug("book_dissolved", child_count=len(results), book_hash=book_hash)
    return results
