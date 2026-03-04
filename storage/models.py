"""SQLAlchemy ORM models for the Greenprint database."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Blueprint(Base):
    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    raw_string_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    raw_string: Mapped[str] = mapped_column(Text, nullable=False)
    decoded_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_site: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=lambda: datetime.now(timezone.utc)
    )
    game_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_version_int: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_book_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("blueprints.id"), nullable=True
    )
    similar_to_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("blueprints.id"), nullable=True
    )
    flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    motifs: Mapped[list["BlueprintMotif"]] = relationship(
        back_populates="blueprint",
        cascade="all, delete-orphan",
        foreign_keys="BlueprintMotif.blueprint_id",
    )
    review_items: Mapped[list["ReviewQueueItem"]] = relationship(
        back_populates="blueprint",
        cascade="all, delete-orphan",
        foreign_keys="ReviewQueueItem.blueprint_id",
    )

    __table_args__ = (
        Index("ix_blueprints_source_site", "source_site"),
        Index("ix_blueprints_scraped_at", "scraped_at"),
        Index("ix_blueprints_game_version", "game_version"),
        Index("ix_blueprints_source_book_id", "source_book_id"),
        Index("ix_blueprints_author_hash", "author_hash"),
    )


class Motif(Base):
    __tablename__ = "motifs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    canonical_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    canonical_entities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_recipes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dest_recipes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    belt_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    uses_underground: Mapped[bool] = mapped_column(Boolean, default=False)
    uses_splitter: Mapped[bool] = mapped_column(Boolean, default=False)
    is_multi_destination: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sideloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)
    # P3: family hash (tier-normalised grouping)
    family_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    family_occurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    # P3: sub-motif hierarchy
    elaboration_depth: Mapped[int] = mapped_column(Integer, default=0)
    sub_motif_of_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    # P3: tileability
    is_tileable: Mapped[bool] = mapped_column(Boolean, default=False)
    tile_vector: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tile_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=lambda: datetime.now(timezone.utc)
    )
    example_blueprint_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("blueprints.id"), nullable=True
    )

    blueprints: Mapped[list["BlueprintMotif"]] = relationship(
        back_populates="motif", cascade="all, delete-orphan"
    )


class BlueprintMotif(Base):
    __tablename__ = "blueprint_motifs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    blueprint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("blueprints.id"), nullable=False
    )
    motif_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motifs.id"), nullable=False
    )
    position_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    blueprint: Mapped["Blueprint"] = relationship(back_populates="motifs")
    motif: Mapped["Motif"] = relationship(back_populates="blueprints")


class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    blueprint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("blueprints.id"), nullable=False
    )
    entity_number: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    blueprint: Mapped["Blueprint"] = relationship(back_populates="review_items")

    __table_args__ = (
        Index("ix_review_queue_items_resolved", "resolved"),
    )
