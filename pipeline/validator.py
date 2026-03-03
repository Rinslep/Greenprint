# pipeline/validator.py
#
# TODO: Schema and semantic validation of decoded blueprint dicts.
#
# Stage 1 — Schema validation (SCHEMA_VALIDATION failure):
# - Define a Pydantic v2 model for the blueprint JSON structure.
#   Key fields: blueprint.label (optional str), blueprint.entities (list), blueprint.version (int),
#   blueprint.item (must be 'blueprint'), plus optional tiles, icons, wires, schedules.
# - Each entity in blueprint.entities must have: entity_number (int), name (str), position {x, y}.
#   Optional: direction (int 0-7), recipe (str), items (dict), connections (dict), control_behavior (dict).
# - Validate with model.model_validate(decoded_dict, strict=False). Failure → raise SchemaError.
#
# Stage 2 — Semantic validation (SEMANTIC_VALIDATION failure):
# - entity_number values must be unique across all entities in the blueprint.
# - All position values must be finite floats (no NaN, no Inf).
# - All connection references (entity_id values in connections dicts) must refer to valid entity_numbers.
# - Raise SemanticError with a description of the first violation found.
#
# Both stages raise typed exceptions caught by the orchestrator.
# The Pydantic models defined here are reused by the storage layer for serialisation.


def validate(decoded: dict) -> object:
    """Returns a validated Pydantic blueprint model instance."""
    pass  # TODO: implement
