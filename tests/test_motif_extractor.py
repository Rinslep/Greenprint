# tests/test_motif_extractor.py
#
# TODO: Tests for analysis/motif/extractor.py and analysis/motif/lane_model.py.
#
# Lane model tests:
# - test_belt_tile_creates_two_lane_nodes: each belt tile → (x, y, 'left') and (x, y, 'right') nodes.
# - test_belt_flow_edge_direction: edges follow belt direction of travel.
# - test_underground_pair_single_edge: entrance → exit is one edge spanning the gap.
# - test_sideload_near_lane_only: sideloading only places onto the near lane.
# - test_direct_inserter_no_lane_nodes: machine→machine inserter has no intermediate lane nodes.
# - test_splitter_two_inputs_two_outputs: splitter generates correct in/out lane edges.
# - test_splitter_filter_encoded_on_edge: filtered splitter output edge carries item type attribute.
#
# Motif extractor tests:
# - test_extract_direct_motif: blueprint from direct_inserter.txt → one DIRECT motif.
# - test_extract_simple_motif: inserter→belts→inserter → one SIMPLE motif.
# - test_extract_underground_motif: path through underground belt → UNDERGROUND motif.
# - test_extract_split_motif: path through splitter → SPLIT motif.
# - test_fork_is_one_motif: a forked path (splitter or sideload) is a single motif, not multiple.
# - test_no_cross_machine_motifs: motifs stop at machine input inserters, don't continue beyond.

import pytest
