# analysis/motif/canonicaliser.py
#
# TODO: Normalise a motif subgraph and produce a stable canonical hash.
#
# Algorithm:
# 1. Translate all entity positions so the source machine anchor is at (0, 0).
# 2. Generate all 8 geometric transformations:
#    - 4 rotations: 0°, 90°, 180°, 270° clockwise.
#    - 2 mirror states: original and horizontally mirrored.
#    - Combined: 4 rotations × 2 mirrors = 8 candidates.
# 3. For each transformation:
#    - Apply the transformation to all entity positions and directions.
#    - Direction rotation: Factorio uses 0=N, 2=E, 4=S, 6=W.
#      Rotating 90° clockwise: add 2 mod 8.
#    - Mirror (negate x): direction mapping must be updated (E↔W, i.e. direction 2↔6).
#    - Serialise as a sorted tuple of (entity_type, x, y, direction, extra_attributes)
#      sorted lexicographically by (entity_type, x, y, direction).
# 4. Select the lexicographically smallest serialisation across all 8 candidates.
#    This ensures mirrored motifs hash identically to their unmirrored counterparts.
# 5. MD5-hash the canonical serialisation string.
#
# Return: (canonical_hash: str, canonical_entities: list[dict])
# The canonical_entities list is stored in the motifs table as one example in canonical form.
#
# CRITICAL: Mirrored motifs MUST hash to the same value as their unmirrored versions.
# The 8-transformation approach achieves this — do not reduce to 4 rotations only.


import hashlib


def canonicalise(motif_subgraph) -> tuple[str, list[dict]]:
    pass  # TODO: implement
