# tests/test_crafting_graph.py
#
# TODO: Tests for analysis/crafting_graph.py.
#
# Test cases to implement:
# - test_graph_nodes_are_items: nodes in the graph are item name strings.
# - test_graph_edges_are_recipes: edges carry recipe_name, machine_count, machine_type.
# - test_final_products: a blueprint producing electronic-circuit but not consuming it internally
#   → electronic-circuit is in final_products.
# - test_raw_inputs: iron-plate consumed but not produced → in raw_inputs.
# - test_intermediates: copper-cable produced and consumed internally → in intermediates.
# - test_is_self_contained_true: blueprint where all intermediates are produced internally.
# - test_is_self_contained_false: blueprint that requires an intermediate to be supplied externally.
# - test_has_cycle_detected: build from cycle.txt fixture → has_cycle == True.
# - test_has_cycle_no_error: has_cycle being True does not raise an exception.
# - test_machines_without_recipes_excluded: machines with no recipe do not appear in the graph.
# - test_multiple_machines_same_recipe_summed: two assemblers with the same recipe → one edge
#   with machine_count == 2.

import pytest
