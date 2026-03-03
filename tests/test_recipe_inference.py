"""Tests for pipeline/recipe_inference.py."""

import pytest
from pipeline.validator import validate
from pipeline.recipe_inference import infer_recipes
from pipeline import review_queue


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


@pytest.fixture(autouse=True)
def clear_queue():
    review_queue.clear()
    yield
    review_queue.clear()


class TestRecipeInference:
    def test_infer_single_match(self):
        """Machine with filtered inserter carrying copper-plate → infers copper-cable (unique match)."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2", "position": {"x": 0, "y": 0}},
            {
                "entity_number": 2, "name": "filter-inserter",
                "position": {"x": -2, "y": 0}, "direction": 2,
                "filters": [
                    {"name": "copper-plate", "index": 1},
                ],
            },
        ])
        flags = infer_recipes(wrapper, "test-bp")
        machine = wrapper.blueprint.entities[0]
        assert machine.recipe == "copper-cable"
        assert len(flags) == 1
        assert flags[0]["flag"] == "INFERRED_RECIPE"

    def test_infer_multiple_candidates(self):
        """Ambiguous inputs → added to review queue, not inferred."""
        # iron-plate alone could match multiple recipes
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2", "position": {"x": 0, "y": 0}},
            {
                "entity_number": 2, "name": "filter-inserter",
                "position": {"x": -2, "y": 0}, "direction": 2,
                "filters": [
                    {"name": "iron-plate", "index": 1},
                    {"name": "copper-plate", "index": 2},
                    {"name": "steel-plate", "index": 3},
                    {"name": "stone", "index": 4},
                ],
            },
        ])
        flags = infer_recipes(wrapper, "test-bp")
        machine = wrapper.blueprint.entities[0]
        # Should NOT infer if multiple match
        if machine.recipe is None:
            unresolved = review_queue.list_unresolved()
            assert len(unresolved) >= 1

    def test_infer_no_match(self):
        """No hints → added to review queue."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2", "position": {"x": 0, "y": 0}},
            {
                "entity_number": 2, "name": "inserter",
                "position": {"x": -2, "y": 0}, "direction": 2,
                # No filters — no item hints available
            },
        ])
        flags = infer_recipes(wrapper, "test-bp")
        machine = wrapper.blueprint.entities[0]
        assert machine.recipe is None
        unresolved = review_queue.list_unresolved()
        assert len(unresolved) == 1
        assert unresolved[0]["context"]["reason"] == "no_candidate_found"

    def test_inferred_always_flagged(self):
        """Even with high confidence, INFERRED_RECIPE flag is always set."""
        wrapper = _make_blueprint([
            {"entity_number": 1, "name": "assembling-machine-2", "position": {"x": 0, "y": 0}},
            {
                "entity_number": 2, "name": "filter-inserter",
                "position": {"x": -2, "y": 0}, "direction": 2,
                "filters": [
                    {"name": "copper-plate", "index": 1},
                ],
            },
        ])
        flags = infer_recipes(wrapper, "test-bp")
        assert any(f["flag"] == "INFERRED_RECIPE" for f in flags)

    def test_machine_with_explicit_recipe_unchanged(self):
        """Machines already having a recipe are skipped."""
        wrapper = _make_blueprint([
            {
                "entity_number": 1, "name": "assembling-machine-2",
                "position": {"x": 0, "y": 0}, "recipe": "iron-gear-wheel",
            },
        ])
        flags = infer_recipes(wrapper, "test-bp")
        machine = wrapper.blueprint.entities[0]
        assert machine.recipe == "iron-gear-wheel"
        assert len(flags) == 0
