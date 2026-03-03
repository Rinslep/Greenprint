# pipeline/broken_detector.py
#
# TODO: Detect non-functional patterns in validated blueprints and attach flags.
#
# Run AFTER successful decode, schema validation, and version filter pass.
# Attach a `flags` list to the blueprint — flags do NOT prevent storage.
#
# Flags to detect (use these exact string names):
#
# NO_POWER (HIGH):
#   - No entity with type 'electric-pole' (or any pole variant) is present.
#
# POWER_GAP (MEDIUM):
#   - Electric poles are present but their combined supply areas do not cover all machines.
#   - Use pole_supply_area from reference/entities.json and entity positions.
#   - A machine is "uncovered" if no pole's supply area tile-overlaps the machine's footprint.
#
# FLOATING_INSERTER (LOW):
#   - An inserter entity has no valid source tile and no valid destination tile within its reach.
#   - Valid source/destination: machine tile, chest, belt, loader, or another inserter's drop.
#
# BELT_DEAD_END (MEDIUM):
#   - A belt segment (chain of connected belts) does not terminate at a machine, chest, or loader.
#   - Identify by tracing belt flow; flag any belt whose output is neither a machine input nor storage.
#
# UNSUPPLIED_RECIPE (HIGH):
#   - A machine has a recipe set, and at least one recipe input has no belt/inserter supply path.
#   - Requires partial lane model traversal — check if any input inserter to the machine is fed.
#
# INFERRED_RECIPE (INFO):
#   - Set by recipe_inference.py when a recipe was not explicit. Do NOT set it here.
#
# CONDITIONAL_BEHAVIOUR (INFO):
#   - Any entity has a non-empty control_behavior connecting to a circuit network.
#
# EARLY_VERSION (INFO):
#   - Set by version_filter.py. Do NOT duplicate here.
#
# Return: list of flag dicts, each with {flag: str, severity: str, detail: str}.


def detect(blueprint) -> list[dict]:
    pass  # TODO: implement
