from pathlib import Path

import pytest

from pipeline.decoder import decode
from pipeline.validator import validate
from pipeline.version_filter import check_modded, check_version, unpack_version

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Version unpacking
# ---------------------------------------------------------------------------

def test_unpack_version_1_1_110():
    packed = (1 << 48) | (1 << 32) | (110 << 16) | 0
    assert unpack_version(packed) == (1, 1, 110, 0)


def test_unpack_version_1_1_57():
    packed = (1 << 48) | (1 << 32) | (57 << 16) | 0
    assert unpack_version(packed) == (1, 1, 57, 0)


def test_unpack_version_2_0_1():
    packed = (2 << 48) | (0 << 32) | (1 << 16) | 0
    assert unpack_version(packed) == (2, 0, 1, 0)


# ---------------------------------------------------------------------------
# check_version
# ---------------------------------------------------------------------------

def test_check_version_1_1_110_accepted():
    packed = (1 << 48) | (1 << 32) | (110 << 16) | 0
    accepted, flags, reason = check_version(packed)
    assert accepted is True
    assert reason is None
    assert "EARLY_VERSION" not in flags


def test_check_version_1_1_57_early():
    packed = (1 << 48) | (1 << 32) | (57 << 16) | 0
    accepted, flags, reason = check_version(packed)
    assert accepted is True
    assert "EARLY_VERSION" in flags
    assert reason is None


def test_check_version_2_0_rejected():
    packed = (2 << 48) | (0 << 32) | (1 << 16) | 0
    accepted, flags, reason = check_version(packed)
    assert accepted is False
    assert reason is not None
    assert "UNSUPPORTED_VERSION" in reason


def test_check_version_1_0_rejected():
    packed = (1 << 48) | (0 << 32) | (50 << 16) | 0
    accepted, flags, reason = check_version(packed)
    assert accepted is False
    assert "UNSUPPORTED_VERSION" in reason


def test_check_version_patch_109_early():
    packed = (1 << 48) | (1 << 32) | (109 << 16) | 0
    accepted, flags, reason = check_version(packed)
    assert accepted is True
    assert "EARLY_VERSION" in flags


def test_check_version_patch_110_no_flag():
    packed = (1 << 48) | (1 << 32) | (110 << 16) | 0
    accepted, flags, _ = check_version(packed)
    assert accepted is True
    assert flags == []


# ---------------------------------------------------------------------------
# check_modded — with raw dicts
# ---------------------------------------------------------------------------

def test_check_modded_vanilla_dict():
    data = {
        "blueprint": {
            "entities": [
                {"name": "transport-belt", "position": {"x": 0, "y": 0}},
                {"name": "inserter", "position": {"x": 1, "y": 0}},
            ]
        }
    }
    accepted, reason = check_modded(data)
    assert accepted is True
    assert reason is None


def test_check_modded_unknown_entity_dict():
    data = {
        "blueprint": {
            "entities": [
                {"name": "bobs-inserter-mk5", "position": {"x": 0, "y": 0}},
            ]
        }
    }
    accepted, reason = check_modded(data)
    assert accepted is False
    assert "MODDED_BLUEPRINT" in reason
    assert "bobs-inserter-mk5" in reason


def test_check_modded_unknown_recipe_dict():
    data = {
        "blueprint": {
            "entities": [
                {
                    "name": "assembling-machine-2",
                    "position": {"x": 0, "y": 0},
                    "recipe": "bobs-alien-science-pack",
                },
            ]
        }
    }
    accepted, reason = check_modded(data)
    assert accepted is False
    assert "MODDED_BLUEPRINT" in reason
    assert "bobs-alien-science-pack" in reason


def test_check_modded_vanilla_recipe_accepted():
    data = {
        "blueprint": {
            "entities": [
                {
                    "name": "assembling-machine-2",
                    "position": {"x": 0, "y": 0},
                    "recipe": "electronic-circuit",
                },
            ]
        }
    }
    accepted, reason = check_modded(data)
    assert accepted is True


# ---------------------------------------------------------------------------
# check_modded — with validated Pydantic model
# ---------------------------------------------------------------------------

def test_check_modded_pydantic_model():
    data = {
        "blueprint": {
            "item": "blueprint",
            "entities": [
                {"entity_number": 1, "name": "transport-belt", "position": {"x": 0.5, "y": 0.5}},
            ],
        }
    }
    wrapper = validate(data)
    accepted, reason = check_modded(wrapper)
    assert accepted is True


# ---------------------------------------------------------------------------
# Integration: decode + validate + version/mod check
# ---------------------------------------------------------------------------

def test_modded_fixture_rejected():
    raw = (FIXTURES / "modded.txt").read_text().strip()
    results = decode(raw)
    for r in results:
        accepted, reason = check_modded(r)
        assert accepted is False
        assert "MODDED_BLUEPRINT" in reason


def test_simple_valid_fixture_accepted():
    raw = (FIXTURES / "simple_valid.txt").read_text().strip()
    results = decode(raw)
    for r in results:
        wrapper = validate(r)
        # Check version from the blueprint
        version_int = wrapper.blueprint.version
        accepted, flags, reason = check_version(version_int)
        assert accepted is True

        # Check modded
        mod_accepted, mod_reason = check_modded(wrapper)
        assert mod_accepted is True
