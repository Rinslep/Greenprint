# pipeline/recipe_inference.py
#
# TODO: Infer missing recipes for machines where no recipe is explicitly set.
#
# Algorithm (run per machine with no recipe):
# 1. Inspect inserters adjacent to this machine:
#    - Check inserter.filters (explicit item filter list).
#    - Check inserter.control_behavior for circuit-defined filters.
#    - Collect the set of items any input inserter is configured to carry.
# 2. Inspect belt lanes feeding input inserters:
#    - Trace belt connections backward from input inserter drop positions.
#    - Identify item types on those lanes (where determinable from splitter filters, etc.).
# 3. Cross-reference against reference/recipes.json:
#    - Filter recipes to those valid for this machine type.
#    - Keep only recipes whose full input set is a subset of the observed items.
# 4. Resolution:
#    - Exactly one match → assign recipe, add INFERRED_RECIPE flag (always, no exceptions).
#    - Multiple matches → add to review queue with all candidates; exclude machine from crafting graph.
#    - No match → add to review queue with "no candidate found"; exclude machine from crafting graph.
#    - Unreviewed machines are excluded from analysis but the blueprint is kept.
#
# Inferred recipes are ALWAYS flagged regardless of how confident the inference is.
# This function must call review_queue.add() for unresolvable cases.


def infer_recipes(blueprint) -> None:
    """Mutates blueprint in place: sets inferred recipes and populates review queue."""
    pass  # TODO: implement
