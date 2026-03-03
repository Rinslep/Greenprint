# analysis/motif/lane_model.py
#
# TODO: Build a lane-level graph from a blueprint's belt/inserter/machine topology.
#
# Each belt tile contributes TWO graph nodes:
#   (x, y, 'left') and (x, y, 'right')
# where 'left'/'right' are relative to the belt's direction of travel.
#
# Edge types (directed):
# - Belt flow: (x, y, side) → (x+dx, y+dy, side) in the belt's direction.
# - Sideloading: items enter the near lane only — do not cross to the far lane.
# - Underground belt pair: entrance lane node → exit lane node (single logical edge spanning the gap).
#   Respect underground_max_distance from entities.json; validate pairs are within range.
# - Splitter: up to 2 input lane nodes → up to 2 output lane nodes.
#   If a filter is set, one output carries only the filtered item type (encode on the edge).
#   If priority is set, prefer the priority output when both outputs are available.
# - Inserter pickup: lane node → machine entity node (the inserter targets the closest lane).
# - Inserter drop: machine entity node → lane node.
# - DIRECT inserter (machine-to-machine): machine_entity_node → machine_entity_node,
#   with the inserter as an edge attribute (no belt nodes in this path — first-class case).
#
# Machine entity nodes: keyed by entity_number.
# Chest/loader nodes: keyed by entity_number.
#
# Use networkx.DiGraph.
# This graph is the input to both throughput_analyser and motif/extractor.
#
# Return: networkx.DiGraph


import networkx as nx


def build_lane_model(blueprint) -> nx.DiGraph:
    pass  # TODO: implement
