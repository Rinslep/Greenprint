"""Calculate ideal and actual machine ratios for each recipe pair in the crafting graph.

All intermediate values are stored as fractions.Fraction to avoid rounding drift.
"""

from fractions import Fraction

import networkx as nx

from pipeline import reference_loader


_MACHINE_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "crafting_speed" in e
)


def _compute_module_effects(entity):
    """Compute combined speed and productivity multipliers from modules in entity.items."""
    speed_bonus = Fraction(0)
    productivity_bonus = Fraction(0)

    items = None
    if hasattr(entity, "items") and entity.items:
        items = entity.items
    elif isinstance(entity, dict) and entity.get("items"):
        items = entity["items"]

    if not items:
        return Fraction(1), Fraction(0)

    for module_name, count in items.items():
        try:
            mod = reference_loader.get_module(module_name)
        except KeyError:
            continue
        effect = mod.get("effect", {})
        speed_bonus += Fraction(effect.get("speed", 0)).limit_denominator(10000) * count
        productivity_bonus += Fraction(effect.get("productivity", 0)).limit_denominator(10000) * count

    speed_multiplier = Fraction(1) + speed_bonus
    return speed_multiplier, productivity_bonus


def _compute_beacon_effects(machine_entity, all_entities):
    """Compute speed and productivity bonuses from nearby beacons."""
    speed_bonus = Fraction(0)
    productivity_bonus = Fraction(0)

    mx = machine_entity.position.x if hasattr(machine_entity, "position") else machine_entity["position"]["x"]
    my = machine_entity.position.y if hasattr(machine_entity, "position") else machine_entity["position"]["y"]

    for e in all_entities:
        name = e.name if hasattr(e, "name") else e["name"]
        if name != "beacon":
            continue
        try:
            beacon_data = reference_loader.get_entity("beacon")
        except KeyError:
            continue

        bx = e.position.x if hasattr(e, "position") else e["position"]["x"]
        by = e.position.y if hasattr(e, "position") else e["position"]["y"]
        beacon_range = beacon_data.get("beacon_range", 3)
        effectivity = Fraction(beacon_data.get("beacon_effectivity", Fraction(1, 2))).limit_denominator(10000)

        if abs(mx - bx) <= beacon_range and abs(my - by) <= beacon_range:
            items = None
            if hasattr(e, "items") and e.items:
                items = e.items
            elif isinstance(e, dict) and e.get("items"):
                items = e["items"]
            if not items:
                continue
            for module_name, count in items.items():
                try:
                    mod = reference_loader.get_module(module_name)
                except KeyError:
                    continue
                effect = mod.get("effect", {})
                speed_bonus += Fraction(effect.get("speed", 0)).limit_denominator(10000) * count * effectivity
                productivity_bonus += Fraction(effect.get("productivity", 0)).limit_denominator(10000) * count * effectivity

    return speed_bonus, productivity_bonus


def compute_machine_rate(entity, recipe, all_entities=None):
    """Compute items/sec output rate for a single machine as a Fraction.

    Returns dict mapping output item name to Fraction rate.
    """
    machine_name = entity.name if hasattr(entity, "name") else entity["name"]
    try:
        machine_data = reference_loader.get_entity(machine_name)
    except KeyError:
        return {}

    crafting_speed = Fraction(machine_data.get("crafting_speed", 1)).limit_denominator(10000)
    crafting_time = Fraction(recipe["crafting_time"]).limit_denominator(10000)

    speed_mult, prod_bonus = _compute_module_effects(entity)

    if all_entities:
        beacon_speed, beacon_prod = _compute_beacon_effects(entity, all_entities)
        speed_mult += beacon_speed
        prod_bonus += beacon_prod

    # Clamp speed_mult to minimum 0.2 (Factorio minimum)
    if speed_mult < Fraction(1, 5):
        speed_mult = Fraction(1, 5)

    rates = {}
    for out in recipe.get("outputs", []):
        output_count = Fraction(out["amount"])
        rate = output_count / crafting_time * crafting_speed * speed_mult * (Fraction(1) + prod_bonus)
        rates[out["name"]] = rate

    return rates


def analyse_ratios(blueprint, crafting_graph) -> dict:
    """Calculate ideal and actual ratios for each recipe pair.

    Returns dict keyed by (supplier_recipe, consumer_recipe) with:
    - ideal_ratio: Fraction
    - actual_ratio: Fraction
    - efficiency: float
    Also includes 'bottleneck' key with the pair having lowest efficiency.
    """
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])

    # Group machines by recipe
    machines_by_recipe: dict[str, list] = {}
    for e in entities:
        name = e.name if hasattr(e, "name") else e["name"]
        if name not in _MACHINE_NAMES:
            continue
        recipe_name = e.recipe if hasattr(e, "recipe") else e.get("recipe")
        if not recipe_name:
            continue
        machines_by_recipe.setdefault(recipe_name, []).append(e)

    results = {}
    min_efficiency = None
    bottleneck_pair = None

    # For each edge in the crafting graph, find supplier→consumer recipe pairs
    for item_node in crafting_graph.nodes():
        # Find recipes that produce this item (incoming edges)
        for pred in crafting_graph.predecessors(item_node):
            edge_in = crafting_graph[pred][item_node]
            supplier_recipe = edge_in["recipe_name"]

            # Find recipes that consume this item (outgoing edges)
            for succ in crafting_graph.successors(item_node):
                edge_out = crafting_graph[item_node][succ]
                consumer_recipe = edge_out["recipe_name"]

                if supplier_recipe == consumer_recipe:
                    continue  # Skip self-loops

                pair_key = (supplier_recipe, consumer_recipe)
                if pair_key in results:
                    continue

                # Get recipe data
                try:
                    sup_recipe = reference_loader.get_recipe(supplier_recipe)
                    con_recipe = reference_loader.get_recipe(consumer_recipe)
                except KeyError:
                    continue

                sup_machines = machines_by_recipe.get(supplier_recipe, [])
                con_machines = machines_by_recipe.get(consumer_recipe, [])

                if not sup_machines or not con_machines:
                    continue

                # Compute rates for one supplier machine
                sup_rates = compute_machine_rate(sup_machines[0], sup_recipe, entities)
                # Find the item rate that connects these two recipes
                item_rate_sup = sup_rates.get(item_node, Fraction(0))

                # Compute consumption rate for one consumer machine
                con_speed = Fraction(
                    reference_loader.get_entity(con_machines[0].name).get("crafting_speed", 1)
                ).limit_denominator(10000)
                con_time = Fraction(con_recipe["crafting_time"]).limit_denominator(10000)
                con_speed_mult, _ = _compute_module_effects(con_machines[0])
                beacon_speed, _ = _compute_beacon_effects(con_machines[0], entities)
                con_speed_mult += beacon_speed
                if con_speed_mult < Fraction(1, 5):
                    con_speed_mult = Fraction(1, 5)

                # Items consumed per second per consumer machine
                item_amount_needed = Fraction(0)
                for inp in con_recipe.get("inputs", []):
                    if inp["name"] == item_node:
                        item_amount_needed = Fraction(inp["amount"])
                        break
                con_rate = item_amount_needed / con_time * con_speed * con_speed_mult

                if item_rate_sup == 0:
                    continue

                # Ideal ratio: how many suppliers per consumer
                ideal_ratio = con_rate / item_rate_sup
                actual_ratio = Fraction(len(sup_machines), len(con_machines))
                efficiency = min(float(actual_ratio / ideal_ratio), 1.0) if ideal_ratio > 0 else 1.0

                results[pair_key] = {
                    "ideal_ratio": ideal_ratio,
                    "actual_ratio": actual_ratio,
                    "efficiency": efficiency,
                }

                if min_efficiency is None or efficiency < min_efficiency:
                    min_efficiency = efficiency
                    bottleneck_pair = pair_key

    results["bottleneck"] = bottleneck_pair
    return results
