"""In-memory motif catalogue — manages the motif library pre-database.

Provides upsert, get, list, and query operations on extracted motifs.
Will be replaced by database-backed storage in Step 13.
"""

from datetime import datetime, timezone


_catalogue: dict[str, dict] = {}
_blueprint_motifs: list[dict] = []


def upsert(canonical_hash: str, canonical_entities: list, category: str,
           motif_metadata: dict, blueprint_id: str) -> None:
    """Insert or update a motif in the catalogue.

    If the hash already exists: increment occurrence_count and merge
    source_recipes / dest_recipes counts.
    If new: create entry with occurrence_count=1.
    Also records a blueprint_motifs link.
    """
    if canonical_hash in _catalogue:
        entry = _catalogue[canonical_hash]
        entry["occurrence_count"] += 1
        # Merge source_recipes counts
        for recipe, count in motif_metadata.get("source_recipes", {}).items():
            entry["source_recipes"][recipe] = entry["source_recipes"].get(recipe, 0) + count
        # Merge dest_recipes counts
        for recipe, count in motif_metadata.get("dest_recipes", {}).items():
            entry["dest_recipes"][recipe] = entry["dest_recipes"].get(recipe, 0) + count
    else:
        _catalogue[canonical_hash] = {
            "canonical_hash": canonical_hash,
            "canonical_entities": canonical_entities,
            "category": category,
            "occurrence_count": 1,
            "belt_type": motif_metadata.get("belt_type"),
            "uses_underground": motif_metadata.get("uses_underground", False),
            "uses_splitter": motif_metadata.get("uses_splitter", False),
            "entity_count": motif_metadata.get("entity_count", 0),
            "source_recipes": dict(motif_metadata.get("source_recipes", {})),
            "dest_recipes": dict(motif_metadata.get("dest_recipes", {})),
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "example_blueprint_id": blueprint_id,
        }

    _blueprint_motifs.append({
        "blueprint_id": blueprint_id,
        "canonical_hash": canonical_hash,
    })


def get(canonical_hash: str) -> dict | None:
    """Fetch a single motif by canonical hash."""
    return _catalogue.get(canonical_hash)


def list_motifs(filters: dict | None = None) -> list[dict]:
    """List motifs with optional filtering.

    Supported filter keys: category, belt_type, uses_underground, uses_splitter.
    """
    results = list(_catalogue.values())
    if filters:
        for key, value in filters.items():
            results = [m for m in results if m.get(key) == value]
    return results


def get_blueprints_for_motif(canonical_hash: str) -> list[str]:
    """Return blueprint IDs that contain the given motif."""
    return [
        link["blueprint_id"]
        for link in _blueprint_motifs
        if link["canonical_hash"] == canonical_hash
    ]


def clear() -> None:
    """Clear all catalogue data. Used in tests."""
    _catalogue.clear()
    _blueprint_motifs.clear()
