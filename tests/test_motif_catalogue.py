"""Tests for analysis/motif/catalogue.py."""

import pytest
from analysis.motif.catalogue import upsert, get, list_motifs, get_blueprints_for_motif, clear


@pytest.fixture(autouse=True)
def _clean_catalogue():
    """Ensure catalogue is empty before and after each test."""
    clear()
    yield
    clear()


_SAMPLE_ENTITIES = [("transport-belt", 0, 0, 2)]
_SAMPLE_METADATA = {
    "belt_type": "transport-belt",
    "uses_underground": False,
    "uses_splitter": False,
    "entity_count": 3,
    "source_recipes": {"iron-gear-wheel": 1},
    "dest_recipes": {"electronic-circuit": 1},
}


class TestMotifCatalogue:
    def test_upsert_new_motif(self):
        """First insert creates entry with count 1."""
        upsert("abc123", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-001")
        entry = get("abc123")
        assert entry is not None
        assert entry["occurrence_count"] == 1
        assert entry["category"] == "SIMPLE"

    def test_upsert_existing_increments(self):
        """Second insert for same hash increments count to 2."""
        upsert("abc123", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-001")
        upsert("abc123", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-002")
        entry = get("abc123")
        assert entry["occurrence_count"] == 2

    def test_get_by_hash(self):
        """Retrieve a stored motif by its canonical hash."""
        upsert("hash1", _SAMPLE_ENTITIES, "DIRECT", _SAMPLE_METADATA, "bp-001")
        entry = get("hash1")
        assert entry["canonical_hash"] == "hash1"
        assert entry["belt_type"] == "transport-belt"

    def test_get_missing_returns_none(self):
        assert get("nonexistent") is None

    def test_list_all(self):
        """list_motifs with no filter returns all motifs."""
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-001")
        upsert("h2", _SAMPLE_ENTITIES, "DIRECT", _SAMPLE_METADATA, "bp-002")
        results = list_motifs()
        assert len(results) == 2

    def test_list_filtered_by_category(self):
        """Filter by category returns only matching motifs."""
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-001")
        upsert("h2", _SAMPLE_ENTITIES, "DIRECT", _SAMPLE_METADATA, "bp-002")
        upsert("h3", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-003")
        results = list_motifs({"category": "SIMPLE"})
        assert len(results) == 2
        assert all(m["category"] == "SIMPLE" for m in results)

    def test_recipe_counts_merged(self):
        """source_recipes counts accumulate across upserts."""
        meta1 = {**_SAMPLE_METADATA, "source_recipes": {"copper-cable": 2}}
        meta2 = {**_SAMPLE_METADATA, "source_recipes": {"copper-cable": 3}}
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", meta1, "bp-001")
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", meta2, "bp-002")
        entry = get("h1")
        assert entry["source_recipes"]["copper-cable"] == 5

    def test_get_blueprints_for_motif(self):
        """Returns all blueprint IDs that contain the given motif."""
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-001")
        upsert("h1", _SAMPLE_ENTITIES, "SIMPLE", _SAMPLE_METADATA, "bp-002")
        upsert("h2", _SAMPLE_ENTITIES, "DIRECT", _SAMPLE_METADATA, "bp-003")
        bps = get_blueprints_for_motif("h1")
        assert set(bps) == {"bp-001", "bp-002"}
