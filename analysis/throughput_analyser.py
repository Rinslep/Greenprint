# analysis/throughput_analyser.py
#
# TODO: Compute actual throughput (items/sec) and identify bottlenecks per connection.
#
# Four analysis layers per connection path (machine output → machine input):
#
# Layer 1 — Machine output rate:
#   rate = crafting_speed * tier_multiplier * module_effects / crafting_time * machine_count
#   (reuse the Fraction-based calculation from ratio_analyser — do not duplicate, import it)
#
# Layer 2 — Inserter delivery rate:
#   rate = items_per_swing * swings_per_second * inserter_count
#   - items_per_swing: inserter_stack_size from entities.json (before stack size research bonuses;
#     use base values only unless a way to detect research level exists).
#   - Filter inserters: only count swings for the relevant item type.
#   - DIRECT connection (machine-to-machine inserter, no belt): still compute inserter rate;
#     this is a first-class case modelled as a direct edge in the lane model.
#
# Layer 3 — Belt lane capacity:
#   For each lane node in the path (from lane_model), compute:
#     saturation = sum of all item rates on the lane / lane capacity (from belt_speed in entities.json)
#   Flag any lane with saturation > 1.0 as overloaded.
#
# Bottleneck:
#   minimum rate across all three layers = actual_output_rate for that connection.
#   bottleneck_entity: the specific entity that is the constraint.
#   bottleneck_type: 'machine' | 'inserter' | 'belt_lane'.
#
# Output per blueprint:
#   - actual_output_rate: dict mapping final_product item name → items/sec
#   - bottleneck_entity: entity_number of the constraining entity
#   - bottleneck_type: string
#   - lane_saturation: dict mapping (x, y, side) → saturation float


def analyse_throughput(blueprint, crafting_graph, lane_graph) -> dict:
    pass  # TODO: implement
