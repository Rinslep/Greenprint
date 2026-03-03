"""Compute actual throughput (items/sec) and identify bottlenecks per connection.

Three analysis layers: machine output rate, inserter delivery rate, belt lane capacity.
"""

from fractions import Fraction

import networkx as nx

from pipeline import reference_loader
from analysis.ratio_analyser import compute_machine_rate

_ENTITY_DATA = {e["name"]: e for e in reference_loader.load_entities()}
_MACHINE_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "crafting_speed" in e
)
_INSERTER_NAMES = frozenset(
    name for name, e in _ENTITY_DATA.items() if "inserter_reach" in e
)


def _get_inserter_rate(inserter_entity):
    """Compute items/sec for a single inserter."""
    ent_data = _ENTITY_DATA.get(inserter_entity.name, {})
    stack_size = Fraction(ent_data.get("inserter_stack_size", 1))
    swing_speed = Fraction(ent_data.get("inserter_swing_speed", 1)).limit_denominator(10000)
    return stack_size * swing_speed


def analyse_throughput(blueprint, crafting_graph, lane_graph) -> dict:
    """Compute throughput analysis for a blueprint.

    Returns:
        dict with keys: actual_output_rate, bottleneck_entity, bottleneck_type, lane_saturation
    """
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])
    entities_by_num = {e.entity_number: e for e in entities}

    actual_output_rate = {}
    lane_saturation = {}
    bottleneck_entity = None
    bottleneck_type = None
    min_rate = None

    # Find machine nodes in the lane graph
    machine_nodes = [
        n for n in lane_graph.nodes()
        if isinstance(n, tuple) and len(n) == 2 and n[0] == "machine"
    ]

    for machine_node in machine_nodes:
        entity_num = machine_node[1]
        entity = entities_by_num.get(entity_num)
        if not entity or not entity.recipe:
            continue

        try:
            recipe = reference_loader.get_recipe(entity.recipe)
        except KeyError:
            continue

        # Layer 1: Machine output rate
        machine_rates = compute_machine_rate(entity, recipe, entities)

        for item_name, machine_rate in machine_rates.items():
            if machine_rate <= 0:
                continue

            # Check outgoing edges from this machine
            if machine_node not in lane_graph:
                continue

            for _, successor, edge_data in lane_graph.out_edges(machine_node, data=True):
                edge_type = edge_data.get("edge_type", "")

                if edge_type == "inserter":
                    inserter = edge_data.get("inserter")
                    if not inserter:
                        continue

                    # Layer 2: Inserter delivery rate
                    inserter_rate = _get_inserter_rate(inserter)

                    # If filter inserter, only counts for its items
                    filter_items = edge_data.get("filter_items")
                    if filter_items and item_name not in filter_items:
                        continue

                    # Layer 3: Trace belt path for lane capacity
                    path_belt_rate = None
                    current = successor
                    visited = set()
                    while current and current not in visited:
                        visited.add(current)
                        node_data = lane_graph.nodes.get(current, {})
                        if node_data.get("node_type") == "belt_lane":
                            belt_speed = Fraction(
                                node_data.get("belt_speed", Fraction(15, 2))
                            ).limit_denominator(10000)
                            # Track saturation
                            saturation = float(machine_rate / belt_speed) if belt_speed > 0 else float("inf")
                            lane_saturation[current] = max(
                                lane_saturation.get(current, 0), saturation
                            )
                            if path_belt_rate is None or belt_speed < path_belt_rate:
                                path_belt_rate = belt_speed

                        # Follow to next node
                        successors = list(lane_graph.successors(current))
                        next_node = None
                        for s in successors:
                            if s not in visited:
                                s_data = lane_graph.nodes.get(s, {})
                                if s_data.get("node_type") in ("belt_lane", "machine", "chest"):
                                    next_node = s
                                    break
                        if next_node and isinstance(next_node, tuple) and len(next_node) == 2:
                            # Reached a machine or chest — stop
                            break
                        current = next_node

                    # Determine bottleneck
                    rates = [("machine", entity.entity_number, machine_rate)]
                    rates.append(("inserter", inserter.entity_number, inserter_rate))
                    if path_belt_rate is not None:
                        rates.append(("belt_lane", entity.entity_number, path_belt_rate))

                    limiting = min(rates, key=lambda r: r[2])
                    effective_rate = limiting[2]

                    if min_rate is None or effective_rate < min_rate:
                        min_rate = effective_rate
                        bottleneck_type = limiting[0]
                        bottleneck_entity = limiting[1]

                    # Track output rate for final products
                    if item_name in crafting_graph.graph.get("final_products", set()):
                        current_rate = actual_output_rate.get(item_name, Fraction(0))
                        actual_output_rate[item_name] = current_rate + effective_rate

    return {
        "actual_output_rate": actual_output_rate,
        "bottleneck_entity": bottleneck_entity,
        "bottleneck_type": bottleneck_type,
        "lane_saturation": lane_saturation,
    }
