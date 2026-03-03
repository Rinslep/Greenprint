# tests/test_canonicaliser.py
#
# TODO: Tests for analysis/motif/canonicaliser.py.
#
# Test cases to implement (all use programmatically constructed motif subgraphs — no file fixtures):
#
# - test_hash_is_md5_hex: canonical_hash is a 32-character hex string.
# - test_same_motif_same_hash: two identical motif subgraphs produce the same hash.
# - test_rotated_90_same_hash: a motif and its 90° rotation hash identically.
# - test_rotated_180_same_hash: a motif and its 180° rotation hash identically.
# - test_rotated_270_same_hash: a motif and its 270° rotation hash identically.
# - test_mirrored_same_hash: a motif and its horizontal mirror hash identically.
#   This is the CRITICAL invariant — mirrored motifs must hash identically.
# - test_different_motifs_different_hash: two structurally distinct motifs have different hashes.
# - test_anchor_at_origin: after canonicalisation, source machine anchor is at (0, 0).
# - test_direction_rotation_correct: entity direction 0 rotated 90° clockwise → direction 2.
# - test_direction_mirror_correct: direction 2 (E) mirrored → direction 6 (W).
# - test_canonical_entities_returned: canonical_entities list is returned and matches hash input.
# - test_extra_attributes_included: extra_attributes (e.g. filter item) affect the hash.

import pytest
