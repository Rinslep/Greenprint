# pipeline/decoder.py
#
# TODO: Decode raw Factorio blueprint strings into Python dicts.
#
# Decode steps (in order):
# 1. Strip the leading version character — must be '0' for Factorio 1.1. Any other prefix is
#    a STRING_EXTRACTION failure.
# 2. Base64 decode the remainder. Failure → DECODE_FAILURE.
# 3. zlib decompress. Failure → DECODE_FAILURE (distinguish from base64 failure in the reason).
# 4. JSON parse. Failure → JSON_PARSE.
# 5. Detect blueprint books: if decoded['blueprint_book'] exists, recursively extract all child
#    blueprints. Return a list; each child carries source_book_id = SHA256(raw_string).
#    Books themselves are never returned as a result — only their children.
#
# Failure handling:
# - Every failure must be logged with: source_url, raw_string_hash (SHA256), failure_stage,
#   failure_reason (human-readable detail).
# - Raise a typed DecodeError exception that the orchestrator catches and logs to DB.
# - Do NOT silently swallow errors.
#
# Return type: list[dict] — always a list (book = multiple items, single blueprint = list of one).
#
# Failure categories (use these exact string names):
#   STRING_EXTRACTION, DECODE_FAILURE, JSON_PARSE, SCHEMA_VALIDATION, SEMANTIC_VALIDATION


def decode(raw_string: str, source_url: str) -> list[dict]:
    pass  # TODO: implement
