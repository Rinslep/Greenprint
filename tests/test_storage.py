"""Tests for the storage layer (models, database, repository functions)."""

import hashlib

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from storage.models import Base, Blueprint, Motif, BlueprintMotif, ReviewQueueItem
import storage


@pytest.fixture()
def session():
    """Create an in-memory SQLite database and yield a session."""
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


class TestBlueprintCRUD:
    def test_save_and_get_blueprint(self, session):
        bp = storage.save_blueprint(
            session,
            raw_string="0abc123",
            raw_string_hash="hash1",
            decoded_json={"blueprint": {"entities": []}},
            source_url="https://example.com/1",
            source_site="factorio_prints",
            author_raw="testuser",
            game_version="1.1.110",
        )
        session.commit()

        fetched = storage.get_blueprint(session, bp.id)
        assert fetched is not None
        assert fetched.raw_string == "0abc123"
        assert fetched.source_site == "factorio_prints"
        assert fetched.game_version == "1.1.110"

    def test_get_blueprint_by_hash(self, session):
        storage.save_blueprint(
            session, raw_string="0abc", raw_string_hash="unique_hash_1"
        )
        session.commit()

        fetched = storage.get_blueprint_by_hash(session, "unique_hash_1")
        assert fetched is not None
        assert fetched.raw_string_hash == "unique_hash_1"

    def test_unique_constraint_on_hash(self, session):
        storage.save_blueprint(
            session, raw_string="0abc", raw_string_hash="dup_hash"
        )
        session.commit()

        with pytest.raises(Exception):
            storage.save_blueprint(
                session, raw_string="0xyz", raw_string_hash="dup_hash"
            )
            session.commit()

    def test_get_nonexistent_returns_none(self, session):
        assert storage.get_blueprint(session, "nonexistent-id") is None

    def test_author_anonymisation(self, session):
        bp = storage.save_blueprint(
            session,
            raw_string="0test",
            raw_string_hash="author_test_hash",
            author_raw="secret_username",
        )
        session.commit()

        expected_hash = hashlib.sha256(b"secret_username").hexdigest()
        assert bp.author_hash == expected_hash
        # Ensure raw username is NOT stored anywhere on the model
        assert not hasattr(bp, "author_raw")

    def test_author_none_when_not_provided(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0x", raw_string_hash="no_author_hash"
        )
        session.commit()
        assert bp.author_hash is None

    def test_json_round_trip(self, session):
        flags = [{"flag": "NO_POWER", "severity": "HIGH", "detail": "No poles"}]
        summary = {"final_products": ["electronic-circuit"], "efficiency": 0.95}
        bp = storage.save_blueprint(
            session,
            raw_string="0json",
            raw_string_hash="json_hash",
            flags=flags,
            summary=summary,
        )
        session.commit()

        fetched = storage.get_blueprint(session, bp.id)
        assert fetched.flags == flags
        assert fetched.summary == summary

    def test_list_blueprints_pagination(self, session):
        for i in range(5):
            storage.save_blueprint(
                session, raw_string=f"0bp{i}", raw_string_hash=f"hash_{i}"
            )
        session.commit()

        results, total = storage.list_blueprints(session, offset=0, limit=3)
        assert total == 5
        assert len(results) == 3

        results2, total2 = storage.list_blueprints(session, offset=3, limit=3)
        assert total2 == 5
        assert len(results2) == 2

    def test_list_blueprints_filter_by_source_site(self, session):
        storage.save_blueprint(
            session, raw_string="0a", raw_string_hash="h1", source_site="reddit"
        )
        storage.save_blueprint(
            session, raw_string="0b", raw_string_hash="h2", source_site="forums"
        )
        storage.save_blueprint(
            session, raw_string="0c", raw_string_hash="h3", source_site="reddit"
        )
        session.commit()

        results, total = storage.list_blueprints(
            session, filters={"source_site": "reddit"}
        )
        assert total == 2
        assert all(bp.source_site == "reddit" for bp in results)


class TestMotifCRUD:
    def test_save_new_motif(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0m", raw_string_hash="motif_bp_hash"
        )
        session.commit()

        motif = storage.save_motif(
            session,
            canonical_hash="canon1",
            canonical_entities=[("belt", 0, 0, 2)],
            category="SIMPLE",
            source_recipes={"iron-gear-wheel": 1},
            example_blueprint_id=bp.id,
            blueprint_id=bp.id,
        )
        session.commit()

        assert motif.occurrence_count == 1
        assert motif.category == "SIMPLE"

    def test_upsert_increments_count(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0u", raw_string_hash="upsert_hash"
        )
        session.commit()

        storage.save_motif(
            session,
            canonical_hash="upsert_canon",
            category="DIRECT",
            source_recipes={"copper-cable": 2},
            blueprint_id=bp.id,
        )
        session.commit()

        storage.save_motif(
            session,
            canonical_hash="upsert_canon",
            category="DIRECT",
            source_recipes={"copper-cable": 3},
            blueprint_id=bp.id,
        )
        session.commit()

        fetched = storage.get_motif_by_hash(session, "upsert_canon")
        assert fetched.occurrence_count == 2
        assert fetched.source_recipes["copper-cable"] == 5

    def test_list_motifs_filter_by_category(self, session):
        storage.save_motif(session, canonical_hash="lm1", category="SIMPLE")
        storage.save_motif(session, canonical_hash="lm2", category="DIRECT")
        storage.save_motif(session, canonical_hash="lm3", category="SIMPLE")
        session.commit()

        results, total = storage.list_motifs(
            session, filters={"category": "SIMPLE"}
        )
        assert total == 2
        assert all(m.category == "SIMPLE" for m in results)

    def test_get_blueprints_for_motif(self, session):
        bp1 = storage.save_blueprint(
            session, raw_string="0g1", raw_string_hash="gbp1"
        )
        bp2 = storage.save_blueprint(
            session, raw_string="0g2", raw_string_hash="gbp2"
        )
        session.commit()

        motif = storage.save_motif(
            session, canonical_hash="shared_motif", category="SIMPLE",
            blueprint_id=bp1.id,
        )
        session.commit()
        storage.save_motif(
            session, canonical_hash="shared_motif", category="SIMPLE",
            blueprint_id=bp2.id,
        )
        session.commit()

        bps = storage.get_blueprints_for_motif(session, motif.id)
        bp_ids = {bp.id for bp in bps}
        assert bp_ids == {bp1.id, bp2.id}


class TestReviewQueue:
    def test_add_and_list_review_items(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0rq", raw_string_hash="rq_hash"
        )
        session.commit()

        storage.add_review_item(
            session,
            blueprint_id=bp.id,
            entity_number=5,
            context={"candidates": ["iron-gear-wheel", "copper-cable"]},
        )
        session.commit()

        items, total = storage.list_review_queue(session)
        assert total == 1
        assert items[0].entity_number == 5
        assert items[0].resolved is False

    def test_resolve_review_item(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0rv", raw_string_hash="rv_hash"
        )
        session.commit()

        item = storage.add_review_item(
            session, blueprint_id=bp.id, entity_number=3, context={}
        )
        session.commit()

        resolved = storage.resolve_review_item(session, item.id, "iron-gear-wheel")
        session.commit()

        assert resolved.resolved is True
        assert resolved.resolution == "iron-gear-wheel"
        assert resolved.resolved_at is not None

    def test_resolve_nonexistent_raises(self, session):
        with pytest.raises(KeyError):
            storage.resolve_review_item(session, "no-such-id", "REJECTED")

    def test_resolved_items_excluded_by_default(self, session):
        bp = storage.save_blueprint(
            session, raw_string="0ex", raw_string_hash="ex_hash"
        )
        session.commit()

        item = storage.add_review_item(
            session, blueprint_id=bp.id, entity_number=1, context={}
        )
        storage.add_review_item(
            session, blueprint_id=bp.id, entity_number=2, context={}
        )
        session.commit()

        storage.resolve_review_item(session, item.id, "REJECTED")
        session.commit()

        unresolved, total = storage.list_review_queue(session)
        assert total == 1
        assert unresolved[0].entity_number == 2
