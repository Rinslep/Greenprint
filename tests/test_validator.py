import math

import pytest

from pipeline.validator import BlueprintWrapper, SchemaError, SemanticError, validate


def _make_bp(**overrides):
    """Build a minimal valid decoded blueprint dict, with overrides."""
    bp = {
        "blueprint": {
            "item": "blueprint",
            "label": "Test",
            "version": 281479278886912,
            "entities": [
                {
                    "entity_number": 1,
                    "name": "transport-belt",
                    "position": {"x": 0.5, "y": 0.5},
                    "direction": 2,
                }
            ],
        }
    }
    bp["blueprint"].update(overrides)
    return bp


def test_validate_simple_valid():
    result = validate(_make_bp())
    assert isinstance(result, BlueprintWrapper)
    assert result.blueprint.label == "Test"
    assert len(result.blueprint.entities) == 1


def test_validate_missing_entities_key():
    data = {"blueprint": {"item": "blueprint", "version": 1}}
    # entities defaults to empty list, so this should still validate
    result = validate(data)
    assert result.blueprint.entities == []


def test_validate_entity_missing_name():
    data = {
        "blueprint": {
            "item": "blueprint",
            "entities": [
                {"entity_number": 1, "position": {"x": 0, "y": 0}}
            ],
        }
    }
    with pytest.raises(SchemaError):
        validate(data)


def test_validate_entity_missing_position():
    data = {
        "blueprint": {
            "item": "blueprint",
            "entities": [
                {"entity_number": 1, "name": "transport-belt"}
            ],
        }
    }
    with pytest.raises(SchemaError):
        validate(data)


def test_validate_duplicate_entity_numbers():
    data = _make_bp(entities=[
        {"entity_number": 1, "name": "transport-belt", "position": {"x": 0, "y": 0}},
        {"entity_number": 1, "name": "inserter", "position": {"x": 1, "y": 0}},
    ])
    with pytest.raises(SemanticError, match="Duplicate entity_number"):
        validate(data)


def test_validate_invalid_connection_reference():
    data = _make_bp(entities=[
        {
            "entity_number": 1,
            "name": "constant-combinator",
            "position": {"x": 0, "y": 0},
            "connections": {
                "1": {
                    "red": [{"entity_id": 999}]
                }
            },
        }
    ])
    with pytest.raises(SemanticError, match="non-existent entity_id"):
        validate(data)


def test_validate_nan_position():
    data = _make_bp(entities=[
        {
            "entity_number": 1,
            "name": "transport-belt",
            "position": {"x": float("nan"), "y": 0.5},
        }
    ])
    with pytest.raises(SemanticError, match="non-finite position"):
        validate(data)


def test_validate_inf_position():
    data = _make_bp(entities=[
        {
            "entity_number": 1,
            "name": "transport-belt",
            "position": {"x": 0.5, "y": float("inf")},
        }
    ])
    with pytest.raises(SemanticError, match="non-finite position"):
        validate(data)


def test_validate_item_not_blueprint():
    data = {"blueprint": {"item": "not-a-blueprint", "entities": []}}
    with pytest.raises(SchemaError):
        validate(data)


def test_validate_no_blueprint_key():
    with pytest.raises(SchemaError):
        validate({"something_else": {}})


def test_validate_valid_connections():
    """Valid connections should pass without error."""
    data = _make_bp(entities=[
        {
            "entity_number": 1,
            "name": "constant-combinator",
            "position": {"x": 0, "y": 0},
            "connections": {
                "1": {"red": [{"entity_id": 2}]}
            },
        },
        {
            "entity_number": 2,
            "name": "arithmetic-combinator",
            "position": {"x": 1, "y": 0},
            "connections": {
                "1": {"red": [{"entity_id": 1}]}
            },
        },
    ])
    result = validate(data)
    assert len(result.blueprint.entities) == 2
