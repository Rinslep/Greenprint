"""Normalise a motif subgraph and produce a stable canonical hash.

Uses 8 geometric transformations (4 rotations x 2 mirror states) to
ensure mirrored and rotated motifs hash identically.
"""

import hashlib


_DIRECTION_MIRROR = {0: 0, 2: 6, 4: 4, 6: 2}


def _rotate_pos_90cw(x, y):
    """Rotate position 90 degrees clockwise: (x, y) -> (y, -x)."""
    return (y, -x)


def _mirror_pos(x, y):
    """Mirror position horizontally: (x, y) -> (-x, y)."""
    return (-x, y)


def _rotate_direction(direction, times=1):
    """Rotate Factorio direction 90 degrees CW, N times."""
    return (direction + 2 * times) % 8


def _mirror_direction(direction):
    """Mirror direction (swap E and W)."""
    return _DIRECTION_MIRROR.get(direction, direction)


def _extract_entities_from_motif(motif_subgraph):
    """Extract entity data from motif nodes."""
    entities = []
    source_machine = motif_subgraph.graph.get("source_machine")
    anchor_x, anchor_y = 0, 0

    # Find anchor position (source machine)
    if source_machine and source_machine in motif_subgraph:
        node_data = motif_subgraph.nodes[source_machine]
        entity = node_data.get("entity")
        if entity:
            anchor_x = entity.position.x if hasattr(entity, "position") else 0
            anchor_y = entity.position.y if hasattr(entity, "position") else 0

    for node, data in motif_subgraph.nodes(data=True):
        entity = data.get("entity")
        if not entity:
            continue

        # Get position relative to anchor
        if hasattr(entity, "position"):
            x = entity.position.x - anchor_x
            y = entity.position.y - anchor_y
        else:
            continue

        name = entity.name if hasattr(entity, "name") else str(entity)
        direction = entity.direction if hasattr(entity, "direction") else 0
        if direction is None:
            direction = 0

        # Extra attributes that affect the hash
        extra = ""
        if hasattr(entity, "filters") and entity.filters:
            filter_names = []
            for f in entity.filters:
                if isinstance(f, dict) and "name" in f:
                    filter_names.append(f["name"])
            if filter_names:
                extra = ",".join(sorted(filter_names))

        entities.append({
            "entity_type": name,
            "x": x,
            "y": y,
            "direction": direction,
            "extra": extra,
        })

    return entities


def _apply_transformation(entities, rotation, mirror):
    """Apply rotation and mirror transformation to entity list."""
    result = []
    for e in entities:
        x, y = e["x"], e["y"]
        direction = e["direction"]

        # Apply rotation
        for _ in range(rotation):
            x, y = _rotate_pos_90cw(x, y)
        direction = _rotate_direction(direction, rotation)

        # Apply mirror
        if mirror:
            x, y = _mirror_pos(x, y)
            direction = _mirror_direction(direction)

        result.append({
            "entity_type": e["entity_type"],
            "x": x,
            "y": y,
            "direction": direction,
            "extra": e["extra"],
        })

    return result


def _serialize(entities):
    """Serialize entities to a canonical string for hashing."""
    tuples = []
    for e in entities:
        tuples.append((e["entity_type"], e["x"], e["y"], e["direction"], e["extra"]))
    tuples.sort()
    return str(tuples)


def canonicalise(motif_subgraph) -> tuple[str, list[dict]]:
    """Produce a canonical hash and entity list for a motif.

    Returns (canonical_hash, canonical_entities).
    """
    entities = _extract_entities_from_motif(motif_subgraph)

    if not entities:
        return (hashlib.md5(b"empty").hexdigest(), [])

    # Generate all 8 transformations and find lexicographic minimum
    best_serialization = None
    best_entities = None

    for rotation in range(4):       # 0, 1, 2, 3 (90° increments)
        for mirror in (False, True):
            transformed = _apply_transformation(entities, rotation, mirror)
            serialization = _serialize(transformed)
            if best_serialization is None or serialization < best_serialization:
                best_serialization = serialization
                best_entities = transformed

    canonical_hash = hashlib.md5(best_serialization.encode("utf-8")).hexdigest()
    return (canonical_hash, best_entities)
