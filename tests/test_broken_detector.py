"""Tests for pipeline/broken_detector.py."""

import pytest
from pipeline.decoder import decode
from pipeline.validator import validate
from pipeline.broken_detector import detect


def _load_fixture(name):
    with open(f"tests/fixtures/{name}") as f:
        raw = f.read().strip()
    decoded = decode(raw)[0]
    return validate(decoded)


def _make_blueprint(entities):
    """Create a BlueprintWrapper from a list of entity dicts."""
    from pipeline.validator import validate
    bp_dict = {
        "blueprint": {
            "item": "blueprint",
            "label": "Test",
            "version": 281479278886912,
            "entities": entities,
        }
    }
    return validate(bp_dict)


class TestNoPower:
    def test_no_power_flag(self):
        wrapper = _load_fixture("no_power.txt")
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "NO_POWER" in flag_names

    def test_power_present_no_flag(self):
        wrapper = _load_fixture("with_power.txt")
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "NO_POWER" not in flag_names


class TestFloatingInserter:
    def test_floating_inserter(self):
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "inserter", "position": {"x": 0.5, "y": 0.5}, "direction": 2},
        ])
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "FLOATING_INSERTER" in flag_names

    def test_connected_inserter_no_flag(self):
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt", "position": {"x": -0.5, "y": 0.5}, "direction": 2},
            {"entity_number": 2, "name": "inserter", "position": {"x": 0.5, "y": 0.5}, "direction": 2},
            {"entity_number": 3, "name": "assembling-machine-2", "position": {"x": 2, "y": 1}, "recipe": "electronic-circuit"},
        ])
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "FLOATING_INSERTER" not in flag_names


class TestBeltDeadEnd:
    def test_belt_dead_end(self):
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "transport-belt", "position": {"x": 0.5, "y": 0.5}, "direction": 2},
        ])
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "BELT_DEAD_END" in flag_names


class TestConditionalBehaviour:
    def test_conditional_behaviour(self):
        wrapper = _make_blueprint([
            {
                "entity_number": 1,
                "name": "inserter",
                "position": {"x": 0.5, "y": 0.5},
                "direction": 2,
                "control_behavior": {"circuit_condition": {"comparator": ">"}},
            },
        ])
        flags = detect(wrapper)
        flag_names = [f["flag"] for f in flags]
        assert "CONDITIONAL_BEHAVIOUR" in flag_names


class TestCleanBlueprint:
    def test_no_high_flags_on_clean_blueprint(self):
        """A simple belt-only blueprint should have no HIGH flags."""
        wrapper = _load_fixture("simple_valid.txt")
        flags = detect(wrapper)
        high_flags = [f for f in flags if f["severity"] == "HIGH"]
        assert high_flags == []

    def test_belt_dead_end_expected_at_chain_end(self):
        """A short belt chain legitimately has a dead end at the last belt."""
        wrapper = _load_fixture("simple_valid.txt")
        flags = detect(wrapper)
        dead_ends = [f for f in flags if f["flag"] == "BELT_DEAD_END"]
        # 2-belt chain: last belt has no receiver — this is expected
        assert len(dead_ends) == 1


class TestFlagStructure:
    def test_flag_dict_structure(self):
        wrapper = _load_fixture("no_power.txt")
        flags = detect(wrapper)
        assert len(flags) > 0
        for flag in flags:
            assert "flag" in flag
            assert "severity" in flag
            assert "detail" in flag
