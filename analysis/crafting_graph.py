# analysis/crafting_graph.py
#
# TODO: Build a directed crafting graph from a validated blueprint.
#
# Graph structure (use networkx.DiGraph):
# - Nodes: item name strings (e.g. 'iron-plate', 'electronic-circuit').
#   Node attributes: produced_internally (bool), consumed_internally (bool).
# - Edges: one edge per recipe, from each input item to each output item.
#   Edge attributes: recipe_name (str), machine_count (int), machine_type (str).
#   If multiple machines run the same recipe, sum their counts into one edge.
#
# Derived properties to compute and attach to the graph object:
# - final_products: set of items produced internally but not consumed internally.
# - raw_inputs: set of items consumed internally but not produced internally.
# - intermediates: set of items both produced and consumed internally.
# - is_self_contained: bool — True if all intermediates are produced within the blueprint
#   (i.e. no intermediate appears in raw_inputs).
# - has_cycle: bool — detected via networkx.find_cycle; flag, do not raise an error.
#
# Machines with no recipe (including those excluded due to unresolved inference) must be
# omitted from the graph entirely.
#
# Input: validated blueprint model.
# Output: networkx.DiGraph with the properties above attached as graph-level attributes.


import networkx as nx


def build_crafting_graph(blueprint) -> nx.DiGraph:
    pass  # TODO: implement
