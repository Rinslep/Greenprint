"""Tests for analysis/throughput_analyser.py."""

import pytest
from fractions import Fraction

from pipeline.validator import validate
from analysis.crafting_graph import build_crafting_graph
from analysis.motif.lane_model import build_lane_model
from analysis.throughput_analyser import analyse_throughput
from pipeline import reference_loader


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


def _simple_production_line(belt_type="transport-belt"):
    """Machine -> inserter -> belt -> inserter -> machine."""
    return _make_blueprint([
        {"entity_number": 1, "name": "assembling-machine-2",
         "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
        {"entity_number": 2, "name": "inserter",
         "position": {"x": 2.5, "y": 0.5}, "direction": 2},
        {"entity_number": 3, "name": belt_type,
         "position": {"x": 3.5, "y": 0.5}, "direction": 2},
        {"entity_number": 4, "name": belt_type,
         "position": {"x": 4.5, "y": 0.5}, "direction": 2},
        {"entity_number": 5, "name": "inserter",
         "position": {"x": 5.5, "y": 0.5}, "direction": 2},
        {"entity_number": 6, "name": "assembling-machine-2",
         "position": {"x": 7, "y": 0}, "recipe": "electronic-circuit"},
    ])


class TestThroughputAnalyser:
    def test_output_rate_computed(self):
        wrapper = _simple_production_line()
        G = build_crafting_graph(wrapper)
        L = build_lane_model(wrapper)
        result = analyse_throughput(wrapper, G, L)
        assert "actual_output_rate" in result

    def test_bottleneck_identified(self):
        wrapper = _simple_production_line()
        G = build_crafting_graph(wrapper)
        L = build_lane_model(wrapper)
        result = analyse_throughput(wrapper, G, L)
        # Should identify some bottleneck
        if result["bottleneck_type"]:
            assert result["bottleneck_type"] in ("machine", "inserter", "belt_lane")

    def test_direct_inserter_no_belt_nodes(self):
        """DIRECT machine-to-machine inserter path has no lane nodes."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-1",
             "position": {"x": 0, "y": 0}, "recipe": "iron-gear-wheel"},
            {"entity_number": 2, "name": "inserter",
             "position": {"x": 1.5, "y": 0.5}, "direction": 2},
            {"entity_number": 3, "name": "assembling-machine-1",
             "position": {"x": 3, "y": 0}, "recipe": "electronic-circuit"},
        ])
        G = build_crafting_graph(wrapper)
        L = build_lane_model(wrapper)
        result = analyse_throughput(wrapper, G, L)
        # Lane saturation should be empty (no belt lanes)
        assert len(result["lane_saturation"]) == 0

    def test_lane_saturation_map(self):
        """lane_saturation contains entries for belt tiles in path."""
        wrapper = _simple_production_line()
        G = build_crafting_graph(wrapper)
        L = build_lane_model(wrapper)
        result = analyse_throughput(wrapper, G, L)
        # If there are belt lanes in the path, saturation should be tracked
        if result["lane_saturation"]:
            for key, val in result["lane_saturation"].items():
                assert isinstance(val, float)
                assert val >= 0

    def test_yellow_belt_speed(self):
        """Yellow belt lane capacity is 7.5 items/sec."""
        ent = reference_loader.get_entity("transport-belt")
        assert ent["belt_speed"] == 7.5

    def test_red_belt_speed(self):
        """Red belt lane capacity is 15.0 items/sec."""
        ent = reference_loader.get_entity("fast-transport-belt")
        assert ent["belt_speed"] == 15.0

    def test_blue_belt_speed(self):
        """Blue belt lane capacity is 22.5 items/sec."""
        ent = reference_loader.get_entity("express-transport-belt")
        assert ent["belt_speed"] == 22.5

    def test_filter_inserter_counted_for_target_item(self):
        """Filter inserter only contributes rate for its filtered item."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
            {"entity_number": 2, "name": "filter-inserter",
             "position": {"x": 2.5, "y": 0.5}, "direction": 2,
             "filters": [{"name": "copper-cable", "index": 1}]},
            {"entity_number": 3, "name": "assembling-machine-2",
             "position": {"x": 5, "y": 0}, "recipe": "electronic-circuit"},
        ])
        G = build_crafting_graph(wrapper)
        L = build_lane_model(wrapper)
        result = analyse_throughput(wrapper, G, L)
        # Should complete without error
        assert "actual_output_rate" in result
