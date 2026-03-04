"""Extract connection motifs from the lane model graph.

A motif is the complete subgraph of entities between a machine output
and the next machine input(s).
"""

import networkx as nx


def _entity_position(node, graph):
    """Return (x, y) for a graph node, reading from entity data or lane key."""
    data = graph.nodes.get(node, {})
    entity = data.get("entity")
    if entity and hasattr(entity, "position"):
        return (entity.position.x, entity.position.y)
    # Belt lane nodes are keyed as (x, y, side)
    if isinstance(node, tuple) and len(node) == 3:
        return (node[0], node[1])
    return None


def _find_nearby_poles(lane_graph, motif_nodes):
    """Find power pole nodes within a 3-tile margin of the motif bounding box."""
    # Compute bounding box of all motif nodes
    xs = []
    ys = []
    for node in motif_nodes:
        pos = _entity_position(node, lane_graph)
        if pos:
            xs.append(pos[0])
            ys.append(pos[1])

    if not xs:
        return set()

    margin = 3
    min_x, max_x = min(xs) - margin, max(xs) + margin
    min_y, max_y = min(ys) - margin, max(ys) + margin

    poles = set()
    for node in lane_graph.nodes():
        if not (isinstance(node, tuple) and len(node) == 2 and node[0] == "pole"):
            continue
        pos = _entity_position(node, lane_graph)
        if pos and min_x <= pos[0] <= max_x and min_y <= pos[1] <= max_y:
            poles.add(node)

    return poles


def _find_input_belt_predecessors(lane_graph, motif_nodes):
    """Walk one step backward from boundary belt nodes to include feeder belts.

    Only follows belt_flow, splitter, and underground edges backward
    (not inserter edges, which would pull in unrelated machines).
    """
    _FOLLOW_TYPES = {"belt_flow", "splitter", "underground"}
    predecessors = set()

    # Find belt lane nodes at the boundary of the motif
    belt_nodes = {
        n for n in motif_nodes
        if isinstance(n, tuple) and len(n) == 3  # (x, y, side)
    }

    for belt_node in belt_nodes:
        for pred, _, edge_data in lane_graph.in_edges(belt_node, data=True):
            if pred in motif_nodes:
                continue
            if edge_data.get("edge_type") in _FOLLOW_TYPES:
                predecessors.add(pred)

    return predecessors


def _classify_motif(subgraph):
    """Classify a motif based on its edge types."""
    edge_types = set()
    for _, _, data in subgraph.edges(data=True):
        edge_types.add(data.get("edge_type", ""))

    # Check for direct machine-to-machine (no belt nodes)
    has_belt = any(
        data.get("node_type") == "belt_lane"
        for _, data in subgraph.nodes(data=True)
    )

    if not has_belt and "inserter" in edge_types:
        return "DIRECT"
    if "splitter" in edge_types:
        return "SPLIT"

    # MERGED: multiple inserter edges feed into belt nodes
    if has_belt:
        belt_nodes_with_inserter_in = set()
        for u, v, data in subgraph.edges(data=True):
            if data.get("edge_type") == "inserter":
                # Check if the target is a belt lane node
                if isinstance(v, tuple) and len(v) == 3:
                    belt_nodes_with_inserter_in.add(v)
        if len(belt_nodes_with_inserter_in) > 1:
            return "MERGED"

    if "underground" in edge_types:
        return "UNDERGROUND"
    return "SIMPLE"


def extract_motifs(lane_graph: nx.DiGraph) -> list[nx.DiGraph]:
    """Extract motifs from the lane graph.

    Returns list of motif subgraphs with 'category' graph attribute.
    """
    motifs = []
    visited_starts = set()

    # Find machine nodes
    machine_nodes = [
        n for n in lane_graph.nodes()
        if isinstance(n, tuple) and len(n) == 2 and n[0] == "machine"
    ]

    for source_machine in machine_nodes:
        if source_machine not in lane_graph:
            continue

        # For each outgoing edge from a machine
        for _, next_node, edge_data in lane_graph.out_edges(source_machine, data=True):
            if edge_data.get("edge_type") != "inserter":
                continue

            # Create a unique key for this motif start
            start_key = (source_machine, next_node)
            if start_key in visited_starts:
                continue
            visited_starts.add(start_key)

            # Trace the path forward via BFS
            motif_nodes = {source_machine}
            motif_edges = [(source_machine, next_node, edge_data)]
            dest_machines = set()

            queue = [next_node]
            visited = {source_machine}

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                motif_nodes.add(current)

                # Check if we've reached a destination machine
                if isinstance(current, tuple) and len(current) == 2 and current[0] == "machine":
                    if current != source_machine:
                        dest_machines.add(current)
                        continue  # Don't traverse beyond destination machine

                # Check if we've reached a chest
                if isinstance(current, tuple) and len(current) == 2 and current[0] == "chest":
                    continue

                # Follow outgoing edges
                if current in lane_graph:
                    for _, successor, succ_data in lane_graph.out_edges(current, data=True):
                        motif_edges.append((current, successor, succ_data))
                        if successor not in visited:
                            queue.append(successor)

            # Only create a motif if we reached at least one destination
            if not dest_machines and not any(
                isinstance(n, tuple) and len(n) == 2 and n[0] == "chest"
                for n in motif_nodes
            ):
                continue

            # Enrichment: add input belt predecessors and nearby poles
            input_preds = _find_input_belt_predecessors(lane_graph, motif_nodes)
            motif_nodes |= input_preds
            for pred in input_preds:
                # Add edges from predecessors into the motif
                for _, succ, edata in lane_graph.out_edges(pred, data=True):
                    if succ in motif_nodes:
                        motif_edges.append((pred, succ, edata))

            nearby_poles = _find_nearby_poles(lane_graph, motif_nodes)
            motif_nodes |= nearby_poles

            # Build subgraph
            motif = nx.DiGraph()
            for node in motif_nodes:
                node_data = lane_graph.nodes.get(node, {})
                motif.add_node(node, **node_data)
            for u, v, data in motif_edges:
                if u in motif_nodes and v in motif_nodes:
                    motif.add_edge(u, v, **data)

            motif.graph["category"] = _classify_motif(motif)
            motif.graph["source_machine"] = source_machine
            motif.graph["dest_machines"] = dest_machines
            motifs.append(motif)

    return motifs
