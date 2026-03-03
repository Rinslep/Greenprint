"""Build a directed crafting graph from a validated blueprint.

Nodes are item names. Edges connect input items to output items via recipes.
"""

import networkx as nx

from pipeline import reference_loader

_MACHINE_NAMES = frozenset(
    e["name"] for e in reference_loader.load_entities() if "crafting_speed" in e
)


def build_crafting_graph(blueprint) -> nx.DiGraph:
    """Build a crafting graph from a validated blueprint.

    Returns a DiGraph with graph-level attributes:
    final_products, raw_inputs, intermediates, is_self_contained,
    has_cycle, byproduct_candidates.
    """
    bp = blueprint.blueprint if hasattr(blueprint, "blueprint") else blueprint
    entities = bp.entities if hasattr(bp, "entities") else bp.get("entities", [])

    G = nx.DiGraph()

    # Count machines per (recipe, machine_type)
    recipe_machines: dict[tuple[str, str], int] = {}
    for e in entities:
        if e.name not in _MACHINE_NAMES:
            continue
        recipe_name = e.recipe if hasattr(e, "recipe") else None
        if not recipe_name:
            continue
        key = (recipe_name, e.name)
        recipe_machines[key] = recipe_machines.get(key, 0) + 1

    # Build graph edges
    for (recipe_name, machine_type), count in recipe_machines.items():
        try:
            recipe = reference_loader.get_recipe(recipe_name)
        except KeyError:
            continue

        inputs = [inp["name"] for inp in recipe.get("inputs", [])]
        outputs = [out["name"] for out in recipe.get("outputs", [])]

        for inp in inputs:
            if not G.has_node(inp):
                G.add_node(inp)
        for out in outputs:
            if not G.has_node(out):
                G.add_node(out)

        for inp in inputs:
            for out in outputs:
                if G.has_edge(inp, out):
                    edge = G[inp][out]
                    edge["machine_count"] += count
                else:
                    G.add_edge(
                        inp, out,
                        recipe_name=recipe_name,
                        machine_count=count,
                        machine_type=machine_type,
                    )

    # Classify nodes
    produced = set()
    consumed = set()
    for u, v, data in G.edges(data=True):
        consumed.add(u)
        produced.add(v)

    for node in G.nodes():
        G.nodes[node]["produced_internally"] = node in produced
        G.nodes[node]["consumed_internally"] = node in consumed

    final_products = produced - consumed
    raw_inputs = consumed - produced
    intermediates = produced & consumed

    # Byproduct candidates: outputs of multi-output recipes that are in final_products
    byproduct_candidates = set()
    multi_output_recipes = set()
    for (recipe_name, _), _ in recipe_machines.items():
        try:
            recipe = reference_loader.get_recipe(recipe_name)
        except KeyError:
            continue
        outputs = [out["name"] for out in recipe.get("outputs", [])]
        if len(outputs) > 1:
            multi_output_recipes.add(recipe_name)
            for out_name in outputs:
                if out_name in final_products:
                    byproduct_candidates.add(out_name)

    # Cycle detection
    has_cycle = False
    try:
        nx.find_cycle(G)
        has_cycle = True
    except nx.NetworkXNoCycle:
        pass

    G.graph["final_products"] = final_products
    G.graph["raw_inputs"] = raw_inputs
    G.graph["intermediates"] = intermediates
    G.graph["is_self_contained"] = not (intermediates & raw_inputs)
    G.graph["has_cycle"] = has_cycle
    G.graph["byproduct_candidates"] = byproduct_candidates

    return G
