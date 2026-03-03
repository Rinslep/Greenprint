# tests/test_throughput_analyser.py
#
# TODO: Tests for analysis/throughput_analyser.py.
#
# Test cases to implement:
# - test_output_rate_computed: actual_output_rate is returned for each final product.
# - test_bottleneck_machine: construct a blueprint where the machine is the slowest layer
#   → bottleneck_type == 'machine'.
# - test_bottleneck_inserter: inserter swing speed is the limiting factor
#   → bottleneck_type == 'inserter'.
# - test_bottleneck_belt_lane: belt capacity exceeded → bottleneck_type == 'belt_lane'.
# - test_direct_inserter_no_belt_nodes: DIRECT (machine-to-machine) inserter path has no lane nodes.
# - test_filter_inserter_counted_for_target_item: filter inserter only contributes rate for its item.
# - test_lane_saturation_map: lane_saturation contains entries for all belt tiles in the path.
# - test_overloaded_lane_saturation_above_1: a lane carrying more than its capacity has sat > 1.0.
# - test_yellow_belt_speed: yellow belt lane capacity is 7.5 items/sec.
# - test_red_belt_speed: red belt lane capacity is 15.0 items/sec.
# - test_blue_belt_speed: blue belt lane capacity is 22.5 items/sec.

import pytest
