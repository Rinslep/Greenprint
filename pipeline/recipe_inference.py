"""Infer missing recipes for machines where no recipe is explicitly set.

For each machine with no recipe:
1. Find inserters whose drop position is within reach of the machine
2. Collect item hints from inserter filters and control_behavior
3. Cross-reference with recipes valid for this machine type
4. Resolution: 1 match → assign + flag, multiple → review queue, 0 → review queue
"""

import math

import structlog

from pipeline import reference_loader, review_queue


def _snap(v):
    """Snap a coordinate to the nearest integer, avoiding banker's rounding."""
    return math.floor(v + 0.5)

log = structlog.get_logger()

_DIRECTION_DELTA = {
    0: (0, -1),
    2: (1, 0),
    4: (0, 1),
    6: (-1, 0),
}

_INSERTER_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "inserter_reach" in e
)
_MACHINE_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "crafting_speed" in e
)


def _get_entity_size(name):
    try:
        ent = reference_loader.get_entity(name)
        return ent.get("size", [1, 1])
    except KeyError:
        return [1, 1]


def _get_machine_tiles(entity):
    """Get all tile positions occupied by a machine."""
    size = _get_entity_size(entity.name)
    w, h = size[0], size[1]
    cx, cy = entity.position.x, entity.position.y
    tiles = set()
    for dx in range(-(w // 2), w // 2 + 1):
        for dy in range(-(h // 2), h // 2 + 1):
            tiles.add((_snap(cx + dx), _snap(cy + dy)))
    return tiles


def _find_input_inserters(machine, entities):
    """Find all inserters whose drop position is within the machine's footprint."""
    machine_tiles = _get_machine_tiles(machine)
    result = []
    for e in entities:
        if e.name not in _INSERTER_NAMES:
            continue
        ent_data = reference_loader.get_entity(e.name)
        reach = ent_data.get("inserter_reach", 1)
        direction = e.direction or 0
        dx, dy = _DIRECTION_DELTA.get(direction, (0, -1))
        drop_pos = (_snap(e.position.x + dx * reach), _snap(e.position.y + dy * reach))
        if drop_pos in machine_tiles:
            result.append(e)
    return result


def _collect_item_hints(inserters):
    """Collect item names from inserter filters and control_behavior."""
    items = set()
    for ins in inserters:
        # Check explicit filters
        if ins.filters:
            for f in ins.filters:
                if isinstance(f, dict) and "name" in f:
                    items.add(f["name"])
        # Check control_behavior for circuit-conditioned filters
        if ins.control_behavior and isinstance(ins.control_behavior, dict):
            cb = ins.control_behavior
            # circuit_condition may reference item signals
            for key in ("circuit_condition", "circuit_read_hand_contents"):
                if key in cb and isinstance(cb[key], dict):
                    cond = cb[key]
                    if "first_signal" in cond and isinstance(cond["first_signal"], dict):
                        sig = cond["first_signal"]
                        if sig.get("type") == "item" and "name" in sig:
                            items.add(sig["name"])
    return items


def _find_candidate_recipes(machine_name, item_hints):
    """Find recipes valid for this machine type whose inputs match hints."""
    recipes = reference_loader.load_recipes()
    candidates = []
    for recipe in recipes:
        if machine_name not in recipe.get("valid_machines", []):
            continue
        if not item_hints:
            # No hints available — can't narrow down
            continue
        recipe_inputs = {inp["name"] for inp in recipe.get("inputs", [])}
        if recipe_inputs.issubset(item_hints):
            candidates.append(recipe)
    return candidates


def infer_recipes(blueprint, blueprint_id="unknown") -> list[dict]:
    """Mutate blueprint in place: set inferred recipes and populate review queue.

    Returns list of INFERRED_RECIPE flag dicts.
    """
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])

    flags = []
    for entity in entities:
        if entity.name not in _MACHINE_NAMES:
            continue
        if entity.recipe is not None:
            continue  # Already has a recipe

        input_inserters = _find_input_inserters(entity, entities)
        item_hints = _collect_item_hints(input_inserters)

        log.info(
            "recipe_inference",
            entity_number=entity.entity_number,
            machine=entity.name,
            hints=sorted(item_hints) if item_hints else [],
        )

        candidates = _find_candidate_recipes(entity.name, item_hints)

        if len(candidates) == 1:
            entity.recipe = candidates[0]["name"]
            flags.append({
                "flag": "INFERRED_RECIPE",
                "severity": "INFO",
                "detail": f"Inferred recipe '{candidates[0]['name']}' for "
                          f"machine entity {entity.entity_number}",
            })
        elif len(candidates) > 1:
            review_queue.add(
                blueprint_id,
                entity.entity_number,
                {
                    "candidates": [c["name"] for c in candidates],
                    "item_hints": sorted(item_hints),
                    "reason": "multiple_candidates",
                },
            )
        else:
            review_queue.add(
                blueprint_id,
                entity.entity_number,
                {
                    "candidates": [],
                    "item_hints": sorted(item_hints) if item_hints else [],
                    "reason": "no_candidate_found",
                },
            )

    return flags
