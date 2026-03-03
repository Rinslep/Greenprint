"""Tests for the REST API."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from storage.models import Base
import storage


@pytest.fixture()
def session():
    """In-memory SQLite session for API tests."""
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


@pytest.fixture()
def client(session):
    """FastAPI test client with DB dependency override."""
    def _override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_blueprint(session, **kwargs):
    """Helper to seed a blueprint into the test DB."""
    defaults = {
        "raw_string": "0testraw",
        "raw_string_hash": "abc123",
        "decoded_json": {"blueprint": {"entities": []}},
        "source_site": "test",
        "flags": [{"flag": "NO_POWER", "severity": "HIGH", "detail": ""}],
        "summary": {
            "crafting_graph": {
                "final_products": ["iron-plate"],
                "raw_inputs": ["iron-ore"],
                "intermediates": [],
                "is_self_contained": False,
                "has_cycle": False,
            }
        },
    }
    defaults.update(kwargs)
    return storage.save_blueprint(session, **defaults)


# ---------------------------------------------------------------------------
# Response envelope tests
# ---------------------------------------------------------------------------

class TestEnvelope:
    def test_list_endpoint_has_envelope(self, client, session):
        resp = client.get("/v1/blueprints")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "warnings" in body
        assert "error" in body

    def test_detail_endpoint_has_envelope(self, client, session):
        bp = _seed_blueprint(session)
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "warnings" in body


# ---------------------------------------------------------------------------
# Blueprint endpoint tests
# ---------------------------------------------------------------------------

class TestBlueprintEndpoints:
    def test_list_empty(self, client, session):
        resp = client.get("/v1/blueprints")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_list_with_blueprints(self, client, session):
        _seed_blueprint(session, raw_string_hash="hash1")
        _seed_blueprint(session, raw_string_hash="hash2")
        session.commit()

        resp = client.get("/v1/blueprints")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 2

    def test_get_blueprint_found(self, client, session):
        bp = _seed_blueprint(session)
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == bp.id

    def test_get_blueprint_not_found(self, client, session):
        resp = client.get("/v1/blueprints/nonexistent-id")
        assert resp.status_code == 404

    def test_flags_always_in_response(self, client, session):
        bp = _seed_blueprint(session)
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}")
        body = resp.json()
        assert body["data"]["flags"] is not None
        assert "NO_POWER" in body["warnings"]

    def test_author_never_in_api_response(self, client, session):
        bp = _seed_blueprint(session, author_raw="secret_user")
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}")
        body = resp.json()
        data_str = json.dumps(body)
        assert "author_hash" not in data_str
        assert "author_raw" not in data_str
        assert "secret_user" not in data_str

    def test_get_graph(self, client, session):
        bp = _seed_blueprint(session)
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}/graph")
        assert resp.status_code == 200
        body = resp.json()
        assert "final_products" in body["data"]

    def test_get_ratios(self, client, session):
        bp = _seed_blueprint(session, summary={"ratios": {"efficiency": 0.95}})
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}/ratios")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["efficiency"] == 0.95

    def test_get_throughput(self, client, session):
        bp = _seed_blueprint(session, summary={"throughput": {"bottleneck_type": "belt_lane"}})
        session.commit()
        resp = client.get(f"/v1/blueprints/{bp.id}/throughput")
        assert resp.status_code == 200

    def test_pagination(self, client, session):
        for i in range(5):
            _seed_blueprint(session, raw_string_hash=f"hash_{i}")
        session.commit()
        resp = client.get("/v1/blueprints?per_page=2&page=1")
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5
        assert body["meta"]["page"] == 1
        assert body["meta"]["per_page"] == 2


# ---------------------------------------------------------------------------
# Motif endpoint tests
# ---------------------------------------------------------------------------

class TestMotifEndpoints:
    def test_list_empty(self, client, session):
        resp = client.get("/v1/motifs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []

    def test_get_motif_not_found(self, client, session):
        resp = client.get("/v1/motifs/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Recipe endpoint tests
# ---------------------------------------------------------------------------

class TestRecipeEndpoints:
    def test_list_recipes(self, client):
        resp = client.get("/v1/recipes?per_page=5")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) <= 5
        assert body["meta"]["total"] > 0

    def test_get_recipe_found(self, client):
        resp = client.get("/v1/recipes/electronic-circuit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["name"] == "electronic-circuit"

    def test_get_recipe_not_found(self, client):
        resp = client.get("/v1/recipes/nonexistent-recipe")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analysis endpoint tests
# ---------------------------------------------------------------------------

class TestAnalysisEndpoints:
    def test_stats(self, client, session):
        _seed_blueprint(session, raw_string_hash="stats_hash")
        session.commit()
        resp = client.get("/v1/analysis/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["total_blueprints"] >= 1

    def test_compare_not_found(self, client, session):
        resp = client.post(
            "/v1/analysis/compare",
            json={"blueprint_ids": ["nonexistent"]},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Review queue endpoint tests
# ---------------------------------------------------------------------------

class TestReviewQueueEndpoints:
    def test_list_empty(self, client, session):
        resp = client.get("/v1/review-queue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_resolve_not_found(self, client, session):
        resp = client.post(
            "/v1/review-queue/nonexistent",
            json={"resolution": "iron-plate"},
        )
        assert resp.status_code == 404

    def test_review_queue_round_trip(self, client, session):
        bp = _seed_blueprint(session, raw_string_hash="review_hash")
        session.flush()
        item = storage.add_review_item(
            session, blueprint_id=bp.id, entity_number=1,
            context={"candidates": ["iron-plate"]},
        )
        session.commit()

        # List should have 1 item
        resp = client.get("/v1/review-queue")
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["entity_number"] == 1

        # Resolve it
        resp = client.post(
            f"/v1/review-queue/{item.id}",
            json={"resolution": "iron-plate"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["resolved"] is True

        # List should now be empty (unresolved only)
        resp = client.get("/v1/review-queue")
        body = resp.json()
        assert body["meta"]["total"] == 0
