"""Detect non-functional patterns in validated blueprints and attach flags.

Run AFTER successful decode, schema validation, and version filter pass.
Flags do NOT prevent storage — they are informational/warning metadata.
"""

import math

from pipeline import reference_loader


def _snap(v):
    """Snap a coordinate to the nearest integer, avoiding banker's rounding."""
    return math.floor(v + 0.5)


# Entity name sets for classification
_POLE_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "pole_supply_area" in e
)
_INSERTER_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "inserter_reach" in e
)
_BELT_NAMES = frozenset(
    e["name"]
    for e in reference_loader.load_entities()
    if "belt_speed" in e and "underground" not in e["name"]
    and "splitter" not in e["name"] and "loader" not in e["name"]
)
_UNDERGROUND_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "underground_max_distance" in e
)
_MACHINE_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "crafting_speed" in e
)
_CHEST_NAMES = frozenset(
    e["name"]
    for e in reference_loader.load_entities()
    if "chest" in e["name"] or e["name"] in ("wooden-chest", "iron-chest", "steel-chest")
)
_LOADER_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "loader" in e["name"]
)
_SPLITTER_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "splitter" in e["name"]
)

# All belt-like entities (valid adjacent entities for inserters)
_BELT_FAMILY = _BELT_NAMES | _UNDERGROUND_NAMES | _SPLITTER_NAMES | _LOADER_NAMES

# Direction to delta mapping
_DIRECTION_DELTA = {
    0: (0, -1),   # North
    2: (1, 0),    # East
    4: (0, 1),    # South
    6: (-1, 0),   # West
}


def _build_position_index(entities):
    """Build a dict mapping grid position to list of entities.

    Multi-tile entities are indexed at all tiles in their footprint.
    """
    idx = {}
    for e in entities:
        size = _get_entity_size(e.name)
        w, h = size[0], size[1]
        cx, cy = e.position.x, e.position.y
        if w <= 1 and h <= 1:
            key = (_snap(cx), _snap(cy))
            idx.setdefault(key, []).append(e)
        else:
            for ddx in range(-(w // 2), w // 2 + 1):
                for ddy in range(-(h // 2), h // 2 + 1):
                    key = (_snap(cx + ddx), _snap(cy + ddy))
                    idx.setdefault(key, []).append(e)
    return idx


def _get_entity_size(name):
    """Get entity size from reference data, default [1,1]."""
    try:
        ent = reference_loader.get_entity(name)
        return ent.get("size", [1, 1])
    except KeyError:
        return [1, 1]


def _check_no_power(entities):
    """NO_POWER: No electric poles present."""
    for e in entities:
        if e.name in _POLE_NAMES:
            return None
    # Only flag if there are machines that need power
    has_machines = any(e.name in _MACHINE_NAMES for e in entities)
    if not has_machines:
        return None
    return {
        "flag": "NO_POWER",
        "severity": "HIGH",
        "detail": "No electric poles present in blueprint",
    }


def _check_power_gap(entities):
    """POWER_GAP: Poles present but don't cover all machines."""
    poles = [e for e in entities if e.name in _POLE_NAMES]
    if not poles:
        return None  # NO_POWER handles this case

    machines = [e for e in entities if e.name in _MACHINE_NAMES]
    if not machines:
        return None

    # Build set of powered tiles from all poles
    powered_tiles = set()
    for pole in poles:
        pole_data = reference_loader.get_entity(pole.name)
        supply = pole_data.get("pole_supply_area", 0)
        half = supply / 2
        px, py = pole.position.x, pole.position.y
        for dx in range(int(-half), int(half) + 1):
            for dy in range(int(-half), int(half) + 1):
                powered_tiles.add((_snap(px + dx), _snap(py + dy)))

    # Check each machine
    uncovered = []
    for machine in machines:
        size = _get_entity_size(machine.name)
        w, h = size[0], size[1]
        mx, my = machine.position.x, machine.position.y
        covered = False
        for dx in range(-(w // 2), w // 2 + 1):
            for dy in range(-(h // 2), h // 2 + 1):
                if (_snap(mx + dx), _snap(my + dy)) in powered_tiles:
                    covered = True
                    break
            if covered:
                break
        if not covered:
            uncovered.append(machine.entity_number)

    if uncovered:
        return {
            "flag": "POWER_GAP",
            "severity": "MEDIUM",
            "detail": f"Machines not covered by pole supply area: {uncovered}",
        }
    return None


def _check_floating_inserter(entities, pos_index):
    """FLOATING_INSERTER: Inserter with no adjacent source or destination."""
    flags = []
    for e in entities:
        if e.name not in _INSERTER_NAMES:
            continue
        ent_data = reference_loader.get_entity(e.name)
        reach = ent_data.get("inserter_reach", 1)
        direction = e.direction or 0

        # Inserter picks up from behind, drops in front
        dx, dy = _DIRECTION_DELTA.get(direction, (0, -1))
        pickup_pos = (_snap(e.position.x - dx * reach), _snap(e.position.y - dy * reach))
        drop_pos = (_snap(e.position.x + dx * reach), _snap(e.position.y + dy * reach))

        has_pickup = bool(pos_index.get(pickup_pos))
        has_drop = bool(pos_index.get(drop_pos))

        if not has_pickup or not has_drop:
            flags.append({
                "flag": "FLOATING_INSERTER",
                "severity": "LOW",
                "detail": f"Inserter entity {e.entity_number} has no "
                          f"{'source' if not has_pickup else 'destination'} at "
                          f"{'pickup' if not has_pickup else 'drop'} position",
            })
    return flags


def _check_belt_dead_end(entities, pos_index):
    """BELT_DEAD_END: Belt whose output tile has nothing to receive items."""
    flags = []
    for e in entities:
        if e.name not in _BELT_NAMES:
            continue
        direction = e.direction or 0
        dx, dy = _DIRECTION_DELTA.get(direction, (0, -1))
        output_pos = (_snap(e.position.x + dx), _snap(e.position.y + dy))

        entities_at_output = pos_index.get(output_pos, [])
        has_receiver = False
        for recv in entities_at_output:
            if recv.name in (_BELT_FAMILY | _MACHINE_NAMES | _CHEST_NAMES):
                has_receiver = True
                break
        if not has_receiver:
            flags.append({
                "flag": "BELT_DEAD_END",
                "severity": "MEDIUM",
                "detail": f"Belt entity {e.entity_number} output has no receiver at {output_pos}",
            })
    return flags


def _check_unsupplied_recipe(entities, pos_index):
    """UNSUPPLIED_RECIPE: Machine with recipe but no inserter feeding an input."""
    flags = []
    for e in entities:
        if e.name not in _MACHINE_NAMES or not e.recipe:
            continue
        try:
            recipe = reference_loader.get_recipe(e.recipe)
        except KeyError:
            continue

        if not recipe.get("inputs"):
            continue

        # Check if any inserter points into this machine
        size = _get_entity_size(e.name)
        w, h = size[0], size[1]
        mx, my = e.position.x, e.position.y

        machine_tiles = set()
        for ddx in range(-(w // 2), w // 2 + 1):
            for ddy in range(-(h // 2), h // 2 + 1):
                machine_tiles.add((_snap(mx + ddx), _snap(my + ddy)))

        has_input_inserter = False
        for ins in entities:
            if ins.name not in _INSERTER_NAMES:
                continue
            ins_data = reference_loader.get_entity(ins.name)
            reach = ins_data.get("inserter_reach", 1)
            direction = ins.direction or 0
            dx, dy = _DIRECTION_DELTA.get(direction, (0, -1))
            drop_pos = (_snap(ins.position.x + dx * reach), _snap(ins.position.y + dy * reach))
            if drop_pos in machine_tiles:
                has_input_inserter = True
                break

        if not has_input_inserter:
            flags.append({
                "flag": "UNSUPPLIED_RECIPE",
                "severity": "HIGH",
                "detail": f"Machine entity {e.entity_number} ({e.recipe}) has no input inserter",
            })
    return flags


def _check_conditional_behaviour(entities):
    """CONDITIONAL_BEHAVIOUR: Entity has non-None control_behavior."""
    for e in entities:
        if e.control_behavior:
            return {
                "flag": "CONDITIONAL_BEHAVIOUR",
                "severity": "INFO",
                "detail": "Blueprint contains entities with circuit network control behavior",
            }
    return None


def detect(blueprint) -> list[dict]:
    """Scan a validated blueprint and return a list of flag dicts.

    Each flag dict has keys: flag, severity, detail.
    """
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])

    if not entities:
        return []

    pos_index = _build_position_index(entities)
    flags = []

    # Single-result checks
    for check in (_check_no_power, _check_conditional_behaviour):
        result = check(entities)
        if result:
            flags.append(result)

    result = _check_power_gap(entities)
    if result:
        flags.append(result)

    # Multi-result checks
    flags.extend(_check_floating_inserter(entities, pos_index))
    flags.extend(_check_belt_dead_end(entities, pos_index))
    flags.extend(_check_unsupplied_recipe(entities, pos_index))

    return flags
