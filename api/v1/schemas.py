"""Pydantic response models for the API.

IMPORTANT: author_hash is never exposed in any API response.
"""

from datetime import datetime

from pydantic import BaseModel


class BlueprintSummaryResponse(BaseModel):
    """Blueprint list item — excludes decoded_json and raw_string for brevity."""
    id: str
    source_url: str | None = None
    source_site: str | None = None
    scraped_at: datetime | None = None
    game_version: str | None = None
    flags: list[dict] | None = None
    summary: dict | None = None

    model_config = {"from_attributes": True}


class BlueprintDetailResponse(BaseModel):
    """Full blueprint record — never includes author_hash."""
    id: str
    raw_string_hash: str
    raw_string: str
    decoded_json: dict | None = None
    source_url: str | None = None
    source_site: str | None = None
    scraped_at: datetime | None = None
    game_version: str | None = None
    game_version_int: int | None = None
    source_book_id: str | None = None
    similar_to_id: str | None = None
    flags: list[dict] | None = None
    summary: dict | None = None

    model_config = {"from_attributes": True}


class MotifSummaryResponse(BaseModel):
    """Motif list item."""
    id: str
    canonical_hash: str
    canonical_entities: list | None = None
    occurrence_count: int = 0
    category: str | None = None
    source_recipes: dict | None = None
    dest_recipes: dict | None = None
    belt_type: str | None = None
    uses_underground: bool = False
    uses_splitter: bool = False
    is_multi_destination: bool = False
    entity_count: int = 0
    family_hash: str | None = None
    family_occurrence_count: int = 0
    elaboration_depth: int = 0
    sub_motif_of_family: str | None = None
    is_tileable: bool = False
    tile_vector: dict | None = None
    tile_count: int = 0
    first_seen_at: datetime | None = None

    model_config = {"from_attributes": True}


class MotifDetailResponse(BaseModel):
    """Full motif record including canonical entities."""
    id: str
    canonical_hash: str
    canonical_entities: list | None = None
    occurrence_count: int = 0
    category: str | None = None
    source_recipes: dict | None = None
    dest_recipes: dict | None = None
    belt_type: str | None = None
    uses_underground: bool = False
    uses_splitter: bool = False
    is_multi_destination: bool = False
    entity_count: int = 0
    family_hash: str | None = None
    family_occurrence_count: int = 0
    elaboration_depth: int = 0
    sub_motif_of_family: str | None = None
    is_tileable: bool = False
    tile_vector: dict | None = None
    tile_count: int = 0
    first_seen_at: datetime | None = None
    example_blueprint_id: str | None = None

    model_config = {"from_attributes": True}


class ReviewQueueItemResponse(BaseModel):
    """Review queue item."""
    id: str
    blueprint_id: str
    entity_number: int
    context: dict | None = None
    resolved: bool = False
    resolution: str | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class RecipeResponse(BaseModel):
    """Recipe from reference data."""
    name: str
    category: str | None = None
    crafting_time: float | None = None
    inputs: list[dict] | None = None
    outputs: list[dict] | None = None
    valid_machines: list[str] | None = None
