# analysis/motif/extractor.py
#
# TODO: Extract connection motifs from the lane model graph.
#
# A motif is the complete subgraph of entities between a machine output and the next machine input(s).
#
# Extraction algorithm:
# 1. For each machine node in the lane graph, find all outgoing connections:
#    - Output inserters (machine → lane node edges).
#    - Direct inserter connections (machine → machine edges with inserter attribute).
# 2. For each output connection, trace the path forward through the lane graph until reaching
#    another machine's input inserter (or a chest/loader endpoint).
# 3. If the path forks (splitter or sideload), the entire forked structure is ONE motif —
#    do not split at forks.
# 4. Collect all entity nodes touched (belts, inserters, undergrounds, splitters) into a subgraph.
#    Include the source machine and destination machine(s) as anchor nodes.
#
# Motif categories (assign based on the entities present):
# - DIRECT:      inserter connects two machines with no belt (direct machine-to-machine edge).
# - SIMPLE:      inserter → one or more belt tiles → inserter (no underground, no splitter).
# - UNDERGROUND: includes at least one underground belt pair.
# - SPLIT:       includes at least one splitter.
# - MERGED:      multiple source inserters feed into one shared belt path before the destination.
#
# Return: list of motif subgraphs (networkx.DiGraph) with category attached as a graph attribute.


import networkx as nx


def extract_motifs(lane_graph: nx.DiGraph) -> list[nx.DiGraph]:
    pass  # TODO: implement
