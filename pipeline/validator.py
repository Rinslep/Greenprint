"""Schema and semantic validation of decoded blueprint dicts.

Stage 1 (SCHEMA_VALIDATION): Pydantic v2 models for the blueprint JSON structure.
Stage 2 (SEMANTIC_VALIDATION): Logical consistency checks on the validated data.
"""

import math
from typing import Any

from pydantic import BaseModel, Field, model_validator

import structlog

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SchemaError(Exception):
    """Raised when the blueprint JSON does not match the expected schema."""
    pass


class SemanticError(Exception):
    """Raised when the blueprint is structurally valid but logically inconsistent."""
    pass


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Position(BaseModel):
    x: float
    y: float


class Connection(BaseModel, extra="allow"):
    """A single connection entry (entity_id + optional circuit_id)."""
    entity_id: int | None = None
    circuit_id: int | None = None


class ConnectionPoint(BaseModel, extra="allow"):
    """Wire connections at a single point — red and/or green lists."""
    red: list[Connection] | None = None
    green: list[Connection] | None = None


class Connections(BaseModel, extra="allow"):
    """Full connection data for an entity (points '1' and/or '2')."""
    point_1: ConnectionPoint | None = Field(None, alias="1")
    point_2: ConnectionPoint | None = Field(None, alias="2")


class Entity(BaseModel, extra="allow"):
    entity_number: int
    name: str
    position: Position
    direction: int | None = None
    recipe: str | None = None
    items: dict[str, Any] | None = None
    connections: Connections | None = None
    control_behavior: dict[str, Any] | None = None
    neighbours: list[int] | None = None
    type: str | None = None
    bar: int | None = None
    filters: list[dict[str, Any]] | None = None
    request_filters: list[dict[str, Any]] | None = None
    override_stack_size: int | None = None
    infinity_settings: dict[str, Any] | None = None
    color: dict[str, Any] | None = None
    station: str | None = None
    manual_trains_limit: int | None = None
    switch_state: bool | None = None


class Blueprint(BaseModel, extra="allow"):
    item: str
    label: str | None = None
    label_color: dict[str, Any] | None = None
    entities: list[Entity] = Field(default_factory=list)
    tiles: list[dict[str, Any]] | None = None
    icons: list[dict[str, Any]] | None = None
    schedules: list[dict[str, Any]] | None = None
    version: int | None = None

    @model_validator(mode="after")
    def check_item_is_blueprint(self):
        if self.item != "blueprint":
            raise ValueError(f"item must be 'blueprint', got '{self.item}'")
        return self


class BlueprintWrapper(BaseModel, extra="allow"):
    blueprint: Blueprint


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(decoded: dict) -> BlueprintWrapper:
    """Validate a decoded blueprint dict through schema and semantic checks.

    Returns the validated BlueprintWrapper model instance.
    Raises SchemaError or SemanticError on failure.
    """
    # Stage 1: Schema validation via Pydantic
    try:
        wrapper = BlueprintWrapper.model_validate(decoded)
    except Exception as exc:
        log.warning("schema_validation_failed", error=str(exc))
        raise SchemaError(str(exc)) from exc

    bp = wrapper.blueprint

    # Stage 2: Semantic validation
    _check_unique_entity_numbers(bp.entities)
    _check_finite_positions(bp.entities)
    _check_connection_references(bp.entities)

    return wrapper


def _check_unique_entity_numbers(entities: list[Entity]) -> None:
    seen: set[int] = set()
    for e in entities:
        if e.entity_number in seen:
            raise SemanticError(
                f"Duplicate entity_number: {e.entity_number}"
            )
        seen.add(e.entity_number)


def _check_finite_positions(entities: list[Entity]) -> None:
    for e in entities:
        if not math.isfinite(e.position.x) or not math.isfinite(e.position.y):
            raise SemanticError(
                f"Entity {e.entity_number} has non-finite position: "
                f"({e.position.x}, {e.position.y})"
            )


def _check_connection_references(entities: list[Entity]) -> None:
    valid_numbers = {e.entity_number for e in entities}
    for e in entities:
        if e.connections is None:
            continue
        for point in (e.connections.point_1, e.connections.point_2):
            if point is None:
                continue
            for wire_list in (point.red, point.green):
                if wire_list is None:
                    continue
                for conn in wire_list:
                    if conn.entity_id is not None and conn.entity_id not in valid_numbers:
                        raise SemanticError(
                            f"Entity {e.entity_number} references non-existent "
                            f"entity_id {conn.entity_id} in connections"
                        )
