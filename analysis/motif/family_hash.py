"""Run-length normalisation and family hash for motif grouping.

A family hash groups motifs that are structurally equivalent but differ only
in belt tier (yellow/red/blue) or inserter type.  Physical positions from the
canonical entity list are preserved, so run lengths are implicitly encoded:
a 3-tile run and a 5-tile run hash differently, while a 3-tile yellow run and
a 3-tile blue run hash identically.

Sub-motif derivation works by replacing complex entities (underground belts,
splitters) with their simple equivalents to find the "base" family that this
motif is an elaboration of.
"""

import hashlib

# ── Entity normalisation sets ────────────────────────────────────────────────

_BELT_TIERS = frozenset({
    "transport-belt",
    "fast-transport-belt",
    "express-transport-belt",
})

_UNDERGROUND_BELT_TIERS = frozenset({
    "underground-belt",
    "fast-underground-belt",
    "express-underground-belt",
})

_SPLITTER_TIERS = frozenset({
    "splitter",
    "fast-splitter",
    "express-splitter",
})

_INSERTER_TYPES = frozenset({
    "burner-inserter",
    "inserter",
    "long-handed-inserter",
    "fast-inserter",
    "filter-inserter",
    "stack-inserter",
    "stack-filter-inserter",
})


# ── Internal helpers ─────────────────────────────────────────────────────────

def _abstract_entity_type(name: str) -> str:
    """Return the normalised abstract entity type.

    Belt tiers collapse to ``"belt"``.
    Underground belt tiers collapse to ``"underground-belt"``.
    Splitter tiers collapse to ``"splitter"``.
    All inserter variants collapse to ``"inserter"``.
    Any other name is returned unchanged.
    """
    if name in _BELT_TIERS:
        return "belt"
    if name in _UNDERGROUND_BELT_TIERS:
        return "underground-belt"
    if name in _SPLITTER_TIERS:
        return "splitter"
    if name in _INSERTER_TYPES:
        return "inserter"
    return name


def _hash_entity_list(entity_tuples: list[tuple]) -> str:
    """Sort entity tuples and MD5-hash them."""
    entity_tuples.sort()
    return hashlib.md5(str(entity_tuples).encode("utf-8")).hexdigest()


def _to_abstract_tuples(canonical_entities: list[dict]) -> list[tuple]:
    """Convert canonical entity dicts to abstract (type, x, y, dir, extra) tuples."""
    return [
        (
            _abstract_entity_type(e.get("entity_type", "")),
            e.get("x", 0),
            e.get("y", 0),
            e.get("direction", 0),
            e.get("extra", ""),
        )
        for e in canonical_entities
    ]


# ── Public API ───────────────────────────────────────────────────────────────

def compute_family_hash(canonical_entities: list[dict]) -> str:
    """Compute a family hash from canonical entities.

    Takes the canonical entity list produced by ``canonicalise()`` and
    returns an MD5 hex string that groups motifs which are structurally
    identical but differ only in belt tier or inserter type.

    Physical positions are preserved so run lengths remain encoded:
    - 3-tile yellow run == 3-tile blue run  (same family)
    - 3-tile yellow run != 5-tile yellow run (different run length → different family)
    """
    if not canonical_entities:
        return hashlib.md5(b"empty").hexdigest()

    abstract_tuples = _to_abstract_tuples(canonical_entities)
    return _hash_entity_list(abstract_tuples)


def compute_simplified_family_hash(canonical_entities: list[dict]) -> str:
    """Compute the family hash of the maximally simplified form of a motif.

    Replaces underground belts with plain belts and splitters with plain
    belts, then re-hashes.  The result is the family hash of the "base"
    SIMPLE/DIRECT motif that this one is an elaboration of.

    Used to populate ``sub_motif_of_family`` on the ``Motif`` row.
    """
    if not canonical_entities:
        return hashlib.md5(b"empty").hexdigest()

    simplified: list[tuple] = []
    for e in canonical_entities:
        abstract = _abstract_entity_type(e.get("entity_type", ""))
        # Flatten underground belts and splitters to plain belt
        if abstract in ("underground-belt", "splitter"):
            abstract = "belt"
        simplified.append((
            abstract,
            e.get("x", 0),
            e.get("y", 0),
            e.get("direction", 0),
            e.get("extra", ""),
        ))

    return _hash_entity_list(simplified)
