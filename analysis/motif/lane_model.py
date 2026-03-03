"""Build a lane-level graph from a blueprint's belt/inserter/machine topology.

Each belt tile contributes two graph nodes: (x, y, 'left') and (x, y, 'right').
Machine nodes are keyed as ('machine', entity_number).
Chest/loader nodes are keyed as ('chest', entity_number).
"""

import math

import networkx as nx

from pipeline import reference_loader


def _snap(v):
    """Snap a coordinate to the nearest integer, avoiding banker's rounding."""
    return math.floor(v + 0.5)

_ENTITY_DATA = {e["name"]: e for e in reference_loader.load_entities()}

_BELT_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items()
    if "belt_speed" in e and "underground" not in name
    and "splitter" not in name and "loader" not in name
)
_UNDERGROUND_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "underground_max_distance" in e
)
_SPLITTER_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "splitter" in name
)
_INSERTER_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "inserter_reach" in e
)
_MACHINE_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "crafting_speed" in e
)
_CHEST_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items()
    if "chest" in name
)
_LOADER_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "loader" in name
)

_DIRECTION_DELTA = {
    0: (0, -1),   # North
    2: (1, 0),    # East
    4: (0, 1),    # South
    6: (-1, 0),   # West
}


def _direction_to_delta(direction):
    return _DIRECTION_DELTA.get(direction, (0, -1))


def _get_entity_size(name):
    return _ENTITY_DATA.get(name, {}).get("size", [1, 1])


def _determine_lane_side(inserter_pos, belt_tile_pos, belt_direction):
    """Determine which lane (left or right) an inserter interacts with.

    Left/right are relative to the belt's direction of travel.
    The inserter targets the near lane (the lane on the same side as the inserter).
    """
    dx = inserter_pos[0] - belt_tile_pos[0]
    dy = inserter_pos[1] - belt_tile_pos[1]

    if belt_direction == 0:  # North: left=West(-X), right=East(+X)
        return "left" if dx < 0 else "right"
    elif belt_direction == 4:  # South: left=East(+X), right=West(-X)
        return "left" if dx > 0 else "right"
    elif belt_direction == 2:  # East: left=North(-Y), right=South(+Y)
        return "left" if dy < 0 else "right"
    elif belt_direction == 6:  # West: left=South(+Y), right=North(-Y)
        return "left" if dy > 0 else "right"
    return "left"


def _compute_inserter_positions(entity):
    """Compute (pickup_pos, drop_pos) for an inserter entity."""
    ent_data = _ENTITY_DATA.get(entity.name, {})
    reach = ent_data.get("inserter_reach", 1)
    direction = entity.direction or 0
    dx, dy = _direction_to_delta(direction)
    ix = entity.position.x
    iy = entity.position.y
    pickup = (_snap(ix - dx * reach), _snap(iy - dy * reach))
    drop = (_snap(ix + dx * reach), _snap(iy + dy * reach))
    return pickup, drop


def _build_entity_position_index(entities):
    """Map grid position -> list of entities, including multi-tile footprints."""
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


def _find_entity_at(position, entities_by_pos, name_filter=None):
    """Find entity at position, optionally filtering by name set."""
    entities = entities_by_pos.get(position, [])
    for e in entities:
        if name_filter is None or e.name in name_filter:
            return e
    return None


def _get_belt_at(position, entities_by_pos):
    """Find a belt-family entity at position."""
    return _find_entity_at(
        position, entities_by_pos,
        _BELT_NAMES | _UNDERGROUND_NAMES | _SPLITTER_NAMES
    )


def build_lane_model(blueprint) -> nx.DiGraph:
    """Build a lane-level directed graph from a validated blueprint."""
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])

    G = nx.DiGraph()
    pos_index = _build_entity_position_index(entities)

    # Classify entities
    belts = [e for e in entities if e.name in _BELT_NAMES]
    undergrounds = [e for e in entities if e.name in _UNDERGROUND_NAMES]
    splitters = [e for e in entities if e.name in _SPLITTER_NAMES]
    inserters = [e for e in entities if e.name in _INSERTER_NAMES]
    machines = [e for e in entities if e.name in _MACHINE_NAMES]
    chests = [e for e in entities if e.name in _CHEST_NAMES]
    loaders = [e for e in entities if e.name in _LOADER_NAMES]

    # 1. Belt lane nodes and flow edges
    for belt in belts:
        x, y = _snap(belt.position.x), _snap(belt.position.y)
        direction = belt.direction or 0
        belt_data = _ENTITY_DATA.get(belt.name, {})
        belt_speed = belt_data.get("belt_speed", 7.5)

        for side in ("left", "right"):
            G.add_node(
                (x, y, side),
                entity=belt, node_type="belt_lane", belt_speed=belt_speed,
            )

        dx, dy = _direction_to_delta(direction)
        for side in ("left", "right"):
            G.add_edge(
                (x, y, side), (x + dx, y + dy, side),
                edge_type="belt_flow",
            )

    # 2. Underground belt edges — nearest exit wins
    ug_inputs = {}  # (tier, direction) -> [entities]
    ug_outputs = {}
    for ug in undergrounds:
        direction = ug.direction or 0
        tier = ug.name
        ug_type = ug.type or "input"
        if ug_type == "input":
            ug_inputs.setdefault((tier, direction), []).append(ug)
        else:
            ug_outputs.setdefault((tier, direction), []).append(ug)

    claimed_exits = set()
    for (tier, direction), entrances in ug_inputs.items():
        exits = ug_outputs.get((tier, direction), [])
        dx, dy = _direction_to_delta(direction)
        ug_data = _ENTITY_DATA.get(tier, {})
        max_dist = ug_data.get("underground_max_distance", 5)
        belt_speed = ug_data.get("belt_speed", 7.5)

        for entrance in entrances:
            ex, ey = _snap(entrance.position.x), _snap(entrance.position.y)
            candidates = []
            for exit_ug in exits:
                ox, oy = _snap(exit_ug.position.x), _snap(exit_ug.position.y)
                diff_x, diff_y = ox - ex, oy - ey
                dist = abs(diff_x) + abs(diff_y)
                # Must be in correct direction and within range
                valid = False
                if dx != 0 and diff_x * dx > 0 and diff_y == 0 and dist <= max_dist:
                    valid = True
                elif dy != 0 and diff_y * dy > 0 and diff_x == 0 and dist <= max_dist:
                    valid = True
                if valid:
                    candidates.append((dist, exit_ug))

            candidates.sort(key=lambda c: c[0])
            for _, exit_ug in candidates:
                eid = exit_ug.entity_number
                if eid not in claimed_exits:
                    claimed_exits.add(eid)
                    ox, oy = _snap(exit_ug.position.x), _snap(exit_ug.position.y)
                    for side in ("left", "right"):
                        if not G.has_node((ex, ey, side)):
                            G.add_node(
                                (ex, ey, side),
                                entity=entrance, node_type="belt_lane",
                                belt_speed=belt_speed,
                            )
                        if not G.has_node((ox, oy, side)):
                            G.add_node(
                                (ox, oy, side),
                                entity=exit_ug, node_type="belt_lane",
                                belt_speed=belt_speed,
                            )
                        G.add_edge(
                            (ex, ey, side), (ox, oy, side),
                            edge_type="underground",
                        )
                    # Flow edge from exit
                    for side in ("left", "right"):
                        G.add_edge(
                            (ox, oy, side), (ox + dx, oy + dy, side),
                            edge_type="belt_flow",
                        )
                    break

    # 3. Splitter edges
    for splitter in splitters:
        direction = splitter.direction or 0
        dx, dy = _direction_to_delta(direction)
        sx, sy = _snap(splitter.position.x), _snap(splitter.position.y)
        spl_data = _ENTITY_DATA.get(splitter.name, {})
        belt_speed = spl_data.get("belt_speed", 7.5)

        # Splitter occupies 2 tiles perpendicular to direction
        if direction in (0, 4):  # N/S — 2 tiles wide on X
            tile_a = (sx, sy)
            tile_b = (sx - 1, sy)
            out_a = (sx, sy + dy)
            out_b = (sx - 1, sy + dy)
        else:  # E/W — 2 tiles wide on Y
            tile_a = (sx, sy)
            tile_b = (sx, sy - 1)
            out_a = (sx + dx, sy)
            out_b = (sx + dx, sy - 1)

        # Build edges from input lanes to output lanes
        spl_filter_item = None
        if splitter.filters:
            if isinstance(splitter.filters, list) and splitter.filters:
                f = splitter.filters[0]
                spl_filter_item = f.get("name") if isinstance(f, dict) else None

        for tile_in, tile_out in [(tile_a, out_a), (tile_b, out_b)]:
            for side in ("left", "right"):
                in_node = (tile_in[0], tile_in[1], side)
                out_node = (tile_out[0], tile_out[1], side)
                if not G.has_node(in_node):
                    G.add_node(in_node, entity=splitter, node_type="belt_lane", belt_speed=belt_speed)
                edge_attrs = {"edge_type": "splitter"}
                if spl_filter_item:
                    edge_attrs["filter_item"] = spl_filter_item
                G.add_edge(in_node, out_node, **edge_attrs)

    # 4. Machine, chest, and loader nodes
    for machine in machines:
        G.add_node(("machine", machine.entity_number), entity=machine, node_type="machine")

    for chest in chests:
        G.add_node(("chest", chest.entity_number), entity=chest, node_type="chest")

    for loader in loaders:
        G.add_node(("chest", loader.entity_number), entity=loader, node_type="loader")

    # 5. Inserter edges
    for inserter in inserters:
        pickup_pos, drop_pos = _compute_inserter_positions(inserter)

        pickup_node = _resolve_node(pickup_pos, pos_index, inserter, G)
        drop_node = _resolve_node(drop_pos, pos_index, inserter, G)

        if pickup_node and drop_node:
            edge_attrs = {"edge_type": "inserter", "inserter": inserter}
            if inserter.filters:
                filter_items = []
                for f in inserter.filters:
                    if isinstance(f, dict) and "name" in f:
                        filter_items.append(f["name"])
                if filter_items:
                    edge_attrs["filter_items"] = filter_items
            G.add_edge(pickup_node, drop_node, **edge_attrs)

    return G


def _resolve_node(position, pos_index, inserter, G):
    """Resolve a position to a graph node (machine, chest, or belt lane)."""
    # Machine?
    machine = _find_entity_at(position, pos_index, _MACHINE_NAMES)
    if machine:
        return ("machine", machine.entity_number)

    # Chest/loader?
    chest = _find_entity_at(position, pos_index, _CHEST_NAMES | _LOADER_NAMES)
    if chest:
        return ("chest", chest.entity_number)

    # Belt?
    belt = _get_belt_at(position, pos_index)
    if belt:
        belt_dir = belt.direction or 0
        ins_pos = (_snap(inserter.position.x), _snap(inserter.position.y))
        side = _determine_lane_side(ins_pos, position, belt_dir)
        return (position[0], position[1], side)

    return None
