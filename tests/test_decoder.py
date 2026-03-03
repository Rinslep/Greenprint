# tests/test_decoder.py
#
# TODO: Tests for pipeline/decoder.py.
#
# Test cases to implement:
# - test_decode_simple_valid: decode simple_valid.txt → expect a list of one dict with 'blueprint' key.
# - test_decode_blueprint_book: decode blueprint_book.txt → expect a list of multiple dicts,
#   each with source_book_id set to the book's hash.
# - test_decode_strips_version_char: confirm the leading '0' is stripped before base64 decoding.
# - test_decode_failure_bad_base64: pass a corrupted string → expect DecodeError with
#   failure_stage='DECODE_FAILURE'.
# - test_decode_failure_bad_json: craft a valid base64+zlib blob that decompresses to non-JSON
#   → expect DecodeError with failure_stage='JSON_PARSE'.
# - test_decode_failure_wrong_prefix: pass a string starting with '1' or 'a'
#   → expect DecodeError with failure_stage='STRING_EXTRACTION'.
# - test_decode_corrupt_fixture: decode corrupt.txt → expect DecodeError.
# - test_no_network_calls: verify no HTTP requests are made during decoding (mock requests if needed).
#
# All tests must be deterministic — load strings from tests/fixtures/ files.
# No network calls permitted in any test.

import pytest
