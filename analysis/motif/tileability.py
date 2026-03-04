"""Tileability detection for motif patterns.

Detects whether a motif tiles regularly across a blueprint by analysing the
spatial offset vectors between multiple occurrences of the same canonical
motif within and across blueprints.

A motif is considered tileable when the same spatial offset (dx, dy) appears
between two or more occurrence pairs consistently.
"""

from collections import Counter


# Minimum number of times an offset vector must appear within a single
# blueprint's occurrences of the same motif to declare it tileable.
_TILE_COUNT_THRESHOLD = 2


def detect_tileability(
    positions: list[tuple[float, float]],
) -> dict | None:
    """Detect tileability from a list of (x, y) positions for a single motif.

    ``positions`` is the source-machine anchor position of each occurrence of
    one canonical motif within a single blueprint.

    Returns a dict with keys ``tile_vector``, ``tile_count`` if the motif is
    tileable, or ``None`` if not enough evidence.

    ``tile_vector`` is ``{"dx": float, "dy": float}``.
    ``tile_count`` is how many pairs share the dominant offset.
    """
    if len(positions) < _TILE_COUNT_THRESHOLD:
        return None

    # Compute all pairwise offset vectors
    offset_counts: Counter = Counter()
    for i, (x1, y1) in enumerate(positions):
        for j, (x2, y2) in enumerate(positions):
            if i >= j:
                continue
            dx = round(x2 - x1, 4)
            dy = round(y2 - y1, 4)
            # Store canonical form: prefer positive dx, then positive dy
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            offset_counts[(dx, dy)] += 1

    if not offset_counts:
        return None

    (best_dx, best_dy), best_count = offset_counts.most_common(1)[0]
    if best_count < _TILE_COUNT_THRESHOLD:
        return None

    return {
        "tile_vector": {"dx": best_dx, "dy": best_dy},
        "tile_count": best_count,
    }


def compute_blueprint_tileability(
    motif_positions: dict[str, list[tuple[float, float]]],
) -> dict[str, dict | None]:
    """Compute tileability for each canonical hash appearing in one blueprint.

    ``motif_positions`` maps canonical_hash → list of (x, y) anchor positions.

    Returns a dict mapping canonical_hash → tileability result (or None).
    """
    return {
        canon_hash: detect_tileability(positions)
        for canon_hash, positions in motif_positions.items()
    }
