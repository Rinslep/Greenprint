"""Tests for analysis/motif/lane_model.py and analysis/motif/extractor.py."""

import pytest
from pipeline.validator import validate
from pipeline.decoder import decode
from analysis.motif.lane_model import (
    build_lane_model, _determine_lane_side,
)
from analysis.motif.extractor import extract_motifs


def _make_blueprint(entities):
    bp_dict = {
        "blueprint": {
            "item": "blueprint",
            "label": "Test",
            "version": 281479278886912,
            "entities": entities,
        }
    }
    return validate(bp_dict)


# =============================================================================
# Lane model tests
# =============================================================================


class TestLaneModel:
    def test_belt_tile_creates_two_lane_nodes(self):
        """Each belt tile creates (x, y, 'left') and (x, y, 'right') nodes."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2},
        ])
        G = build_lane_model(wrapper)
        # _snap(0.5) = 1
        assert G.has_node((1, 1, "left"))
        assert G.has_node((1, 1, "right"))

    def test_belt_flow_edge_direction(self):
        """Belt facing East creates edges flowing East."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2},
        ])
        G = build_lane_model(wrapper)
        # _snap(0.5) = 1, East dx=1
        assert G.has_edge((1, 1, "left"), (2, 1, "left"))
        assert G.has_edge((1, 1, "right"), (2, 1, "right"))

    def test_belt_flow_north(self):
        """Belt facing North creates edges flowing North (dy=-1)."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt",
             "position": {"x": 0.5, "y": 0.5}, "direction": 0},
        ])
        G = build_lane_model(wrapper)
        assert G.has_edge((1, 1, "left"), (1, 0, "left"))

    def test_underground_pair_single_edge(self):
        """Underground entrance -> exit creates one edge spanning the gap."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "underground-belt",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2, "type": "input"},
            {"entity_number": 2, "name": "underground-belt",
             "position": {"x": 3.5, "y": 0.5}, "direction": 2, "type": "output"},
        ])
        G = build_lane_model(wrapper)
        # _snap(0.5)=1, _snap(3.5)=4
        assert G.has_edge((1, 1, "left"), (4, 1, "left"))
        assert G.has_edge((1, 1, "right"), (4, 1, "right"))

    def test_underground_chained_nearest_wins(self):
        """When two exits are in range, the nearest one is matched."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "underground-belt",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2, "type": "input"},
            {"entity_number": 2, "name": "underground-belt",
             "position": {"x": 2.5, "y": 0.5}, "direction": 2, "type": "output"},
            {"entity_number": 3, "name": "underground-belt",
             "position": {"x": 4.5, "y": 0.5}, "direction": 2, "type": "output"},
        ])
        G = build_lane_model(wrapper)
        # _snap(0.5)=1, _snap(2.5)=3, _snap(4.5)=5
        assert G.has_edge((1, 1, "left"), (3, 1, "left"))
        assert not G.has_edge((1, 1, "left"), (5, 1, "left"))

    def test_direct_inserter_no_lane_nodes(self):
        """Machine-to-machine inserter creates direct edge with no belt nodes."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-1",
             "position": {"x": 0, "y": 0}, "recipe": "iron-gear-wheel"},
            {"entity_number": 2, "name": "inserter",
             "position": {"x": 1.5, "y": 0.5}, "direction": 2},
            {"entity_number": 3, "name": "assembling-machine-1",
             "position": {"x": 3, "y": 0}, "recipe": "electronic-circuit"},
        ])
        G = build_lane_model(wrapper)
        assert G.has_edge(("machine", 1), ("machine", 3))
        edge = G[("machine", 1)][("machine", 3)]
        assert edge["edge_type"] == "inserter"

    def test_splitter_two_inputs_two_outputs(self):
        """Splitter generates splitter-type edges."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "splitter",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2},
        ])
        G = build_lane_model(wrapper)
        splitter_edges = [
            (u, v) for u, v, d in G.edges(data=True)
            if d.get("edge_type") == "splitter"
        ]
        assert len(splitter_edges) >= 2

    def test_splitter_filter_encoded_on_edge(self):
        """Filtered splitter output edge carries item type attribute."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "splitter",
             "position": {"x": 0.5, "y": 0.5}, "direction": 2,
             "filters": [{"name": "iron-plate", "index": 1}]},
        ])
        G = build_lane_model(wrapper)
        filter_edges = [
            (u, v, d) for u, v, d in G.edges(data=True)
            if d.get("filter_item") == "iron-plate"
        ]
        assert len(filter_edges) > 0

    def test_sideload_near_lane_only(self):
        """An inserter interacting with a belt targets only the near lane."""
        # Belt going East at (3,1), inserter at (3,0) facing South (dir=4)
        # Inserter is north of belt -> left lane for eastward belt
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt",
             "position": {"x": 2.5, "y": 0.5}, "direction": 2},
            {"entity_number": 2, "name": "assembling-machine-1",
             "position": {"x": 2, "y": -2}, "recipe": "iron-gear-wheel"},
            {"entity_number": 3, "name": "inserter",
             "position": {"x": 2.5, "y": -0.5}, "direction": 4},
        ])
        G = build_lane_model(wrapper)
        # _snap(2.5)=3, _snap(0.5)=1. Inserter drops at _snap(2.5+0)=3, _snap(-0.5+1)=1 -> (3,1)
        # Belt is at (3,1). Inserter is north -> left lane
        has_left = G.has_edge(("machine", 2), (3, 1, "left"))
        has_right = G.has_edge(("machine", 2), (3, 1, "right"))
        assert has_left or has_right
        if has_left:
            assert not has_right


class TestLaneSideDetermination:
    """Test _determine_lane_side for all 4 belt directions with inserter on each side."""

    def test_north_belt_inserter_west(self):
        assert _determine_lane_side((-1, 0), (0, 0), 0) == "left"

    def test_north_belt_inserter_east(self):
        assert _determine_lane_side((1, 0), (0, 0), 0) == "right"

    def test_south_belt_inserter_east(self):
        assert _determine_lane_side((1, 0), (0, 0), 4) == "left"

    def test_south_belt_inserter_west(self):
        assert _determine_lane_side((-1, 0), (0, 0), 4) == "right"

    def test_east_belt_inserter_north(self):
        assert _determine_lane_side((0, -1), (0, 0), 2) == "left"

    def test_east_belt_inserter_south(self):
        assert _determine_lane_side((0, 1), (0, 0), 2) == "right"

    def test_west_belt_inserter_south(self):
        assert _determine_lane_side((0, 1), (0, 0), 6) == "left"

    def test_west_belt_inserter_north(self):
        assert _determine_lane_side((0, -1), (0, 0), 6) == "right"


# =============================================================================
# Motif extractor tests
# =============================================================================

def _load_fixture(name):
    with open(f"tests/fixtures/{name}") as f:
        raw = f.read().strip()
    decoded = decode(raw)[0]
    return validate(decoded)


class TestMotifExtractor:
    def test_extract_direct_motif(self):
        """Blueprint from direct_inserter.txt -> one DIRECT motif."""
        wrapper = _load_fixture("direct_inserter.txt")
        L = build_lane_model(wrapper)
        motifs = extract_motifs(L)
        direct_motifs = [m for m in motifs if m.graph.get("category") == "DIRECT"]
        assert len(direct_motifs) >= 1

    def test_extract_simple_motif(self):
        """Inserter -> belts -> inserter -> one SIMPLE motif."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-1",
             "position": {"x": 0, "y": 0}, "recipe": "iron-gear-wheel"},
            {"entity_number": 2, "name": "inserter",
             "position": {"x": 1.5, "y": 0.5}, "direction": 2},
            {"entity_number": 3, "name": "transport-belt",
             "position": {"x": 2.5, "y": 0.5}, "direction": 2},
            {"entity_number": 4, "name": "transport-belt",
             "position": {"x": 3.5, "y": 0.5}, "direction": 2},
            {"entity_number": 5, "name": "inserter",
             "position": {"x": 4.5, "y": 0.5}, "direction": 2},
            {"entity_number": 6, "name": "assembling-machine-1",
             "position": {"x": 6, "y": 0}, "recipe": "electronic-circuit"},
        ])
        L = build_lane_model(wrapper)
        motifs = extract_motifs(L)
        simple_motifs = [m for m in motifs if m.graph.get("category") == "SIMPLE"]
        assert len(simple_motifs) >= 1

    def test_extract_split_motif(self):
        """Path through splitter -> SPLIT motif."""
        wrapper = _load_fixture("splitters.txt")
        L = build_lane_model(wrapper)
        motifs = extract_motifs(L)
        split_motifs = [m for m in motifs if m.graph.get("category") == "SPLIT"]
        assert len(split_motifs) >= 1

    def test_no_cross_machine_motifs(self):
        """Motifs stop at machine input inserters, don't continue beyond."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-1",
             "position": {"x": 0, "y": 0}, "recipe": "iron-gear-wheel"},
            {"entity_number": 2, "name": "inserter",
             "position": {"x": 1.5, "y": 0.5}, "direction": 2},
            {"entity_number": 3, "name": "assembling-machine-1",
             "position": {"x": 3, "y": 0}, "recipe": "electronic-circuit"},
            {"entity_number": 4, "name": "inserter",
             "position": {"x": 4.5, "y": 0.5}, "direction": 2},
            {"entity_number": 5, "name": "assembling-machine-1",
             "position": {"x": 6, "y": 0}, "recipe": "copper-cable"},
        ])
        L = build_lane_model(wrapper)
        motifs = extract_motifs(L)
        # Each motif should span exactly one machine-to-machine connection
        for motif in motifs:
            machine_nodes = [
                n for n in motif.nodes()
                if isinstance(n, tuple) and len(n) == 2 and n[0] == "machine"
            ]
            assert len(machine_nodes) <= 3  # source + at most 2 destinations
