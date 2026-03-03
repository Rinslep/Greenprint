"""Tests for analysis/ratio_analyser.py."""

import pytest
from fractions import Fraction

from pipeline.validator import validate
from analysis.crafting_graph import build_crafting_graph
from analysis.ratio_analyser import analyse_ratios, compute_machine_rate
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


def _copper_cable_ec_blueprint(cable_count=3, ec_count=2):
    """Blueprint with copper-cable -> electronic-circuit chain."""
    entities = []
    num = 1
    for i in range(cable_count):
        entities.append({
            "entity_number": num, "name": "assembling-machine-2",
            "position": {"x": i * 5, "y": 0}, "recipe": "copper-cable",
        })
        num += 1
    for i in range(ec_count):
        entities.append({
            "entity_number": num, "name": "assembling-machine-2",
            "position": {"x": i * 5, "y": 5}, "recipe": "electronic-circuit",
        })
        num += 1
    return _make_blueprint(entities)


class TestRatioAnalyser:
    def test_ideal_ratio_is_fraction(self):
        wrapper = _copper_cable_ec_blueprint()
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        for key, val in result.items():
            if key == "bottleneck":
                continue
            assert isinstance(val["ideal_ratio"], Fraction)

    def test_actual_ratio_is_fraction(self):
        wrapper = _copper_cable_ec_blueprint()
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        for key, val in result.items():
            if key == "bottleneck":
                continue
            assert isinstance(val["actual_ratio"], Fraction)

    def test_efficiency_is_float(self):
        wrapper = _copper_cable_ec_blueprint()
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        for key, val in result.items():
            if key == "bottleneck":
                continue
            assert isinstance(val["efficiency"], float)

    def test_efficiency_perfect(self):
        """3 cable machines : 2 EC machines = perfect 3:2 ratio."""
        wrapper = _copper_cable_ec_blueprint(cable_count=3, ec_count=2)
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        pair = ("copper-cable", "electronic-circuit")
        assert pair in result
        assert result[pair]["efficiency"] == 1.0

    def test_efficiency_undersupply(self):
        """1 cable : 2 EC = undersupply."""
        wrapper = _copper_cable_ec_blueprint(cable_count=1, ec_count=2)
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        pair = ("copper-cable", "electronic-circuit")
        assert pair in result
        assert result[pair]["efficiency"] < 1.0

    def test_efficiency_oversupply(self):
        """6 cable : 2 EC = oversupply, capped at 1.0."""
        wrapper = _copper_cable_ec_blueprint(cable_count=6, ec_count=2)
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        pair = ("copper-cable", "electronic-circuit")
        assert pair in result
        assert result[pair]["efficiency"] == 1.0

    def test_bottleneck_identified(self):
        wrapper = _copper_cable_ec_blueprint(cable_count=1, ec_count=2)
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        assert result["bottleneck"] is not None

    def test_speed_module_increases_rate(self):
        """Adding a speed module increases items/sec."""
        recipe = reference_loader.get_recipe("copper-cable")

        ent_no_mod = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
        ]).blueprint.entities[0]
        rate_no_mod = compute_machine_rate(ent_no_mod, recipe)

        ent_with_mod = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable",
             "items": {"speed-module": 1}},
        ]).blueprint.entities[0]
        rate_with_mod = compute_machine_rate(ent_with_mod, recipe)

        assert rate_with_mod["copper-cable"] > rate_no_mod["copper-cable"]

    def test_productivity_module_affects_ratio(self):
        """Productivity module changes output rate."""
        recipe = reference_loader.get_recipe("copper-cable")

        ent_no_mod = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
        ]).blueprint.entities[0]
        rate_no_mod = compute_machine_rate(ent_no_mod, recipe)

        ent_with_mod = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable",
             "items": {"productivity-module": 1}},
        ]).blueprint.entities[0]
        rate_with_mod = compute_machine_rate(ent_with_mod, recipe)

        assert rate_with_mod["copper-cable"] != rate_no_mod["copper-cable"]

    def test_beacon_applies_to_in_range_machines(self):
        """Beacon modules apply to machines within supply area."""
        recipe = reference_loader.get_recipe("copper-cable")
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
            {"entity_number": 2, "name": "beacon",
             "position": {"x": 3, "y": 0},
             "items": {"speed-module-2": 2}},
        ])
        ents = wrapper.blueprint.entities
        rate_with_beacon = compute_machine_rate(ents[0], recipe, ents)
        rate_without = compute_machine_rate(ents[0], recipe, [])
        assert rate_with_beacon["copper-cable"] > rate_without["copper-cable"]

    def test_beacon_does_not_apply_to_out_of_range(self):
        """Machines outside beacon supply area unaffected."""
        recipe = reference_loader.get_recipe("copper-cable")
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2",
             "position": {"x": 0, "y": 0}, "recipe": "copper-cable"},
            {"entity_number": 2, "name": "beacon",
             "position": {"x": 50, "y": 50},
             "items": {"speed-module-2": 2}},
        ])
        ents = wrapper.blueprint.entities
        rate_with_far_beacon = compute_machine_rate(ents[0], recipe, ents)
        rate_without = compute_machine_rate(ents[0], recipe, [])
        assert rate_with_far_beacon["copper-cable"] == rate_without["copper-cable"]

    def test_no_rounding_drift(self):
        """Known 3:2 copper-cable:electronic-circuit ratio is exact."""
        wrapper = _copper_cable_ec_blueprint(cable_count=3, ec_count=2)
        G = build_crafting_graph(wrapper)
        result = analyse_ratios(wrapper, G)
        pair = ("copper-cable", "electronic-circuit")
        assert isinstance(result[pair]["ideal_ratio"], Fraction)
