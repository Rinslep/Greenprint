import base64
import json
import zlib
from pathlib import Path

import pytest

from pipeline.decoder import DecodeError, decode

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text().strip()


def test_decode_simple_valid():
    raw = _load_fixture("simple_valid.txt")
    result = decode(raw, source_url="test://simple")
    assert len(result) == 1
    assert "blueprint" in result[0]
    bp = result[0]["blueprint"]
    assert bp["label"] == "Test Blueprint"
    assert len(bp["entities"]) == 2


def test_decode_blueprint_book():
    raw = _load_fixture("blueprint_book.txt")
    result = decode(raw, source_url="test://book")
    assert len(result) == 2
    # Each child should have source_book_id
    for child in result:
        assert "source_book_id" in child
        assert "blueprint" in child
    labels = {child["blueprint"]["label"] for child in result}
    assert labels == {"Child 1", "Child 2"}


def test_decode_strips_version_char():
    raw = _load_fixture("simple_valid.txt")
    assert raw[0] == "0"
    # The string without '0' prefix should be valid base64
    base64.b64decode(raw[1:])


def test_decode_failure_bad_base64():
    with pytest.raises(DecodeError) as exc_info:
        decode("0!!!not-base64!!!", source_url="test://bad64")
    assert exc_info.value.failure_stage == "DECODE_FAILURE"


def test_decode_failure_bad_json():
    # Valid base64+zlib blob that decompresses to non-JSON
    not_json = b"this is not json"
    compressed = zlib.compress(not_json)
    encoded = "0" + base64.b64encode(compressed).decode()
    with pytest.raises(DecodeError) as exc_info:
        decode(encoded, source_url="test://badjson")
    assert exc_info.value.failure_stage == "JSON_PARSE"


def test_decode_failure_wrong_prefix():
    with pytest.raises(DecodeError) as exc_info:
        decode("1abcdef", source_url="test://wrongprefix")
    assert exc_info.value.failure_stage == "STRING_EXTRACTION"

    with pytest.raises(DecodeError) as exc_info:
        decode("aXYZ", source_url="test://wrongprefix2")
    assert exc_info.value.failure_stage == "STRING_EXTRACTION"


def test_decode_failure_empty_string():
    with pytest.raises(DecodeError) as exc_info:
        decode("", source_url="test://empty")
    assert exc_info.value.failure_stage == "STRING_EXTRACTION"


def test_decode_corrupt_fixture():
    raw = _load_fixture("corrupt.txt")
    with pytest.raises(DecodeError):
        decode(raw, source_url="test://corrupt")


def test_decode_error_includes_hash():
    with pytest.raises(DecodeError) as exc_info:
        decode("1bad", source_url="test://hash_check")
    assert exc_info.value.raw_string_hash  # non-empty
    assert exc_info.value.source_url == "test://hash_check"


def test_no_network_calls(monkeypatch):
    """Verify decoding never makes HTTP requests."""
    import urllib.request

    def deny_urlopen(*args, **kwargs):
        raise AssertionError("Network call attempted during decode")

    monkeypatch.setattr(urllib.request, "urlopen", deny_urlopen)

    raw = _load_fixture("simple_valid.txt")
    decode(raw, source_url="test://no_network")
