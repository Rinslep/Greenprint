"""Tests for analysis/motif/canonicaliser.py."""

import pytest
import networkx as nx

from analysis.motif.canonicaliser import (
    canonicalise, _rotate_direction, _mirror_direction,
)


def _make_mock_entity(name, x, y, direction=0, filters=None):
    """Create a mock entity object for testing."""
    class MockPos:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockEntity:
        def __init__(self, name, x, y, direction, filters):
            self.name = name
            self.position = MockPos(x, y)
            self.direction = direction
            self.filters = filters
            self.entity_number = id(self)

    return MockEntity(name, x, y, direction, filters)


def _make_motif(entities_data, source_idx=0):
    """Build a motif subgraph from entity tuples: [(name, x, y, direction, filters), ...]"""
    G = nx.DiGraph()
    mock_entities = []
    for i, (name, x, y, direction, *rest) in enumerate(entities_data):
        filters = rest[0] if rest else None
        ent = _make_mock_entity(name, x, y, direction, filters)
        mock_entities.append(ent)
        node_id = ("machine", ent.entity_number) if "machine" in name else (round(x), round(y), "left")
        G.add_node(node_id, entity=ent, node_type="machine" if "machine" in name else "belt_lane")

    nodes = list(G.nodes())
    if len(nodes) >= 2:
        G.add_edge(nodes[0], nodes[1], edge_type="inserter")
    G.graph["source_machine"] = nodes[source_idx] if nodes else None
    return G


class TestCanonicaliser:
    def test_hash_is_md5_hex(self):
        motif = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        hash_val, _ = canonicalise(motif)
        assert len(hash_val) == 32
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_same_motif_same_hash(self):
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 == h2

    def test_rotated_90_same_hash(self):
        """A motif and its 90 degree rotation hash identically."""
        # Original: machine at (0,0), belt at (2,0) facing East
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        # 90 CW: (x,y) -> (y,-x), dir +2. So (2,0) -> (0,-2), dir 2->4
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 2),
            ("transport-belt", 0, -2, 4),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 == h2

    def test_rotated_180_same_hash(self):
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        # 180: (x,y) -> (-x,-y), dir +4. So (2,0) -> (-2,0), dir 2->6
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 4),
            ("transport-belt", -2, 0, 6),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 == h2

    def test_rotated_270_same_hash(self):
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        # 270 CW (= 90 CCW): (x,y) -> (-y,x), dir +6. So (2,0) -> (0,2), dir 2->0
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 6),
            ("transport-belt", 0, 2, 0),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 == h2

    def test_mirrored_same_hash(self):
        """CRITICAL: mirrored motifs must hash identically."""
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),  # East
        ])
        # Mirror: (x,y) -> (-x,y), dir E->W. So (2,0) -> (-2,0), dir 2->6
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", -2, 0, 6),  # West
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 == h2

    def test_different_motifs_different_hash(self):
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("fast-transport-belt", 3, 1, 4),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 != h2

    def test_anchor_at_origin(self):
        """After canonicalisation, positions are relative to source machine at (0,0)."""
        motif = _make_motif([
            ("assembling-machine-1", 5, 3, 0),
            ("transport-belt", 7, 3, 2),
        ])
        _, entities = canonicalise(motif)
        # All entities should have positions relative to anchor
        assert len(entities) == 2

    def test_direction_rotation_correct(self):
        """Direction 0 (N) rotated 90 CW -> direction 2 (E)."""
        assert _rotate_direction(0, 1) == 2

    def test_direction_mirror_correct(self):
        """Direction 2 (E) mirrored -> direction 6 (W)."""
        assert _mirror_direction(2) == 6

    def test_canonical_entities_returned(self):
        motif = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("transport-belt", 2, 0, 2),
        ])
        _, entities = canonicalise(motif)
        assert isinstance(entities, list)
        assert len(entities) > 0
        for e in entities:
            assert "entity_type" in e
            assert "x" in e
            assert "y" in e
            assert "direction" in e

    def test_extra_attributes_included(self):
        """Extra attributes (e.g. filter item) affect the hash."""
        motif1 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("filter-inserter", 2, 0, 2, [{"name": "iron-plate", "index": 1}]),
        ])
        motif2 = _make_motif([
            ("assembling-machine-1", 0, 0, 0),
            ("filter-inserter", 2, 0, 2, [{"name": "copper-plate", "index": 1}]),
        ])
        h1, _ = canonicalise(motif1)
        h2, _ = canonicalise(motif2)
        assert h1 != h2
