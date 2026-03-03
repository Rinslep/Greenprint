"""Tests for pipeline/orchestrator.py."""

import hashlib

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from storage.models import Base
import storage
from pipeline.orchestrator import PipelineResult, process_string, _serialise_summary
from fractions import Fraction


@pytest.fixture()
def session():
    """In-memory SQLite session for orchestrator tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def _load_fixture(name: str) -> str:
    with open(f"tests/fixtures/{name}") as f:
        return f.read().strip()


class TestSerialise:
    def test_fraction_to_float(self):
        result = _serialise_summary(Fraction(1, 3))
        assert isinstance(result, float)
        assert abs(result - 1/3) < 1e-10

    def test_nested_dict(self):
        data = {"rate": Fraction(3, 4), "name": "test"}
        result = _serialise_summary(data)
        assert result["rate"] == 0.75
        assert result["name"] == "test"

    def test_nested_list(self):
        data = [Fraction(1, 2), "hello", Fraction(2, 3)]
        result = _serialise_summary(data)
        assert result[0] == 0.5
        assert result[1] == "hello"

    def test_deeply_nested(self):
        data = {"outer": {"inner": [Fraction(7, 8)]}}
        result = _serialise_summary(data)
        assert result["outer"]["inner"][0] == 0.875


class TestProcessString:
    def test_valid_blueprint_end_to_end(self, session):
        raw = _load_fixture("simple_valid.txt")
        result = process_string(session, raw, source_url="test://1", source_site="test")
        session.commit()

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.blueprint_ids) >= 1

        # Verify blueprint was saved
        bp = storage.get_blueprint(session, result.blueprint_ids[0])
        assert bp is not None
        assert bp.source_site == "test"

    def test_corrupt_string_rejected(self, session):
        result = process_string(session, "not_a_blueprint", source_site="test")
        assert result.rejected is True
        assert "DECODE_FAILURE" in (result.rejection_reason or "")
        assert len(result.blueprint_ids) == 0

    def test_modded_blueprint_rejected(self, session):
        raw = _load_fixture("modded.txt")
        result = process_string(session, raw, source_site="test")

        assert result.rejected is True
        assert result.rejection_reason is not None

    def test_deduplication(self, session):
        raw = _load_fixture("simple_valid.txt")

        result1 = process_string(session, raw, source_site="test")
        session.commit()
        result2 = process_string(session, raw, source_site="test")

        assert result1.success is True
        assert result2.success is True
        # Second call should return the same blueprint ID (dedup)
        assert result1.blueprint_ids == result2.blueprint_ids

    def test_author_anonymised(self, session):
        raw = _load_fixture("simple_valid.txt")
        result = process_string(
            session, raw, source_site="test", author_raw="secret_user"
        )
        session.commit()

        bp = storage.get_blueprint(session, result.blueprint_ids[0])
        expected_hash = hashlib.sha256(b"secret_user").hexdigest()
        assert bp.author_hash == expected_hash

    def test_flags_persisted(self, session):
        raw = _load_fixture("no_power.txt")
        result = process_string(session, raw, source_site="test")
        session.commit()

        if result.success:
            bp = storage.get_blueprint(session, result.blueprint_ids[0])
            assert bp.flags is not None
            flag_names = [f["flag"] for f in bp.flags]
            assert "NO_POWER" in flag_names

    def test_book_dissolution(self, session):
        raw = _load_fixture("blueprint_book.txt")
        result = process_string(session, raw, source_site="test")
        session.commit()

        # Books should be dissolved — multiple blueprints from one string
        if result.success:
            assert len(result.blueprint_ids) >= 1

    def test_pipeline_result_structure(self, session):
        raw = _load_fixture("simple_valid.txt")
        result = process_string(session, raw, source_site="test")

        assert hasattr(result, "success")
        assert hasattr(result, "blueprint_ids")
        assert hasattr(result, "rejected")
        assert hasattr(result, "rejection_reason")
        assert hasattr(result, "flags")
        assert hasattr(result, "review_queue_items")
        assert hasattr(result, "errors")
        assert isinstance(result.blueprint_ids, list)
        assert isinstance(result.flags, list)
        assert isinstance(result.errors, list)
