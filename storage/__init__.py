"""Storage layer public interface — repository functions."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from storage.database import get_session, init_db  # noqa: F401 — re-export
from storage.models import Blueprint, BlueprintMotif, Motif, ReviewQueueItem


# ---------------------------------------------------------------------------
# Blueprint operations
# ---------------------------------------------------------------------------

def save_blueprint(
    session: Session,
    *,
    raw_string: str,
    raw_string_hash: str,
    decoded_json: dict | None = None,
    source_url: str | None = None,
    source_site: str | None = None,
    author_raw: str | None = None,
    game_version: str | None = None,
    game_version_int: int | None = None,
    source_book_id: str | None = None,
    flags: list | None = None,
    summary: dict | None = None,
) -> Blueprint:
    """Save a blueprint. Hashes author_raw to author_hash (anonymisation chokepoint)."""
    author_hash = None
    if author_raw:
        author_hash = hashlib.sha256(author_raw.encode("utf-8")).hexdigest()

    bp = Blueprint(
        raw_string=raw_string,
        raw_string_hash=raw_string_hash,
        decoded_json=decoded_json,
        source_url=source_url,
        source_site=source_site,
        author_hash=author_hash,
        game_version=game_version,
        game_version_int=game_version_int,
        source_book_id=source_book_id,
        flags=flags,
        summary=summary,
    )
    session.add(bp)
    session.flush()
    return bp


def get_blueprint(session: Session, blueprint_id: str) -> Blueprint | None:
    """Fetch a single blueprint by ID."""
    return session.get(Blueprint, blueprint_id)


def get_blueprint_by_hash(session: Session, raw_string_hash: str) -> Blueprint | None:
    """Fetch a blueprint by its raw string hash."""
    stmt = select(Blueprint).where(Blueprint.raw_string_hash == raw_string_hash)
    return session.execute(stmt).scalar_one_or_none()


def list_blueprints(
    session: Session,
    filters: dict | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Blueprint], int]:
    """List blueprints with optional filtering and pagination."""
    stmt = select(Blueprint)

    if filters:
        if "source_site" in filters:
            stmt = stmt.where(Blueprint.source_site == filters["source_site"])
        if "game_version" in filters:
            stmt = stmt.where(Blueprint.game_version == filters["game_version"])

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    results = list(session.execute(stmt).scalars().all())
    return results, total


# ---------------------------------------------------------------------------
# Motif operations
# ---------------------------------------------------------------------------

def save_motif(
    session: Session,
    *,
    canonical_hash: str,
    canonical_entities: list | None = None,
    category: str | None = None,
    source_recipes: dict | None = None,
    dest_recipes: dict | None = None,
    belt_type: str | None = None,
    uses_underground: bool = False,
    uses_splitter: bool = False,
    entity_count: int = 0,
    example_blueprint_id: str | None = None,
    blueprint_id: str | None = None,
    position_context: dict | None = None,
) -> Motif:
    """Upsert a motif: increment occurrence_count if hash exists, else create."""
    stmt = select(Motif).where(Motif.canonical_hash == canonical_hash)
    existing = session.execute(stmt).scalar_one_or_none()

    if existing:
        existing.occurrence_count += 1
        # Merge recipe counts
        if source_recipes:
            merged = dict(existing.source_recipes or {})
            for recipe, count in source_recipes.items():
                merged[recipe] = merged.get(recipe, 0) + count
            existing.source_recipes = merged
        if dest_recipes:
            merged = dict(existing.dest_recipes or {})
            for recipe, count in dest_recipes.items():
                merged[recipe] = merged.get(recipe, 0) + count
            existing.dest_recipes = merged
        motif = existing
    else:
        motif = Motif(
            canonical_hash=canonical_hash,
            canonical_entities=canonical_entities,
            occurrence_count=1,
            category=category,
            source_recipes=source_recipes,
            dest_recipes=dest_recipes,
            belt_type=belt_type,
            uses_underground=uses_underground,
            uses_splitter=uses_splitter,
            entity_count=entity_count,
            example_blueprint_id=example_blueprint_id,
        )
        session.add(motif)

    session.flush()

    # Create junction record if blueprint_id provided
    if blueprint_id:
        link = BlueprintMotif(
            blueprint_id=blueprint_id,
            motif_id=motif.id,
            position_context=position_context,
        )
        session.add(link)
        session.flush()

    return motif


def get_motif(session: Session, motif_id: str) -> Motif | None:
    """Fetch a single motif by ID."""
    return session.get(Motif, motif_id)


def get_motif_by_hash(session: Session, canonical_hash: str) -> Motif | None:
    """Fetch a motif by its canonical hash."""
    stmt = select(Motif).where(Motif.canonical_hash == canonical_hash)
    return session.execute(stmt).scalar_one_or_none()


def list_motifs(
    session: Session,
    filters: dict | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Motif], int]:
    """List motifs with optional filtering and pagination."""
    stmt = select(Motif)

    if filters:
        if "category" in filters:
            stmt = stmt.where(Motif.category == filters["category"])
        if "belt_type" in filters:
            stmt = stmt.where(Motif.belt_type == filters["belt_type"])

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    results = list(session.execute(stmt).scalars().all())
    return results, total


def get_blueprints_for_motif(
    session: Session, motif_id: str
) -> list[Blueprint]:
    """Return blueprints that contain the given motif."""
    stmt = (
        select(Blueprint)
        .join(BlueprintMotif, BlueprintMotif.blueprint_id == Blueprint.id)
        .where(BlueprintMotif.motif_id == motif_id)
    )
    return list(session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Review queue operations
# ---------------------------------------------------------------------------

def add_review_item(
    session: Session,
    *,
    blueprint_id: str,
    entity_number: int,
    context: dict | None = None,
) -> ReviewQueueItem:
    """Insert a new unresolved review queue item."""
    item = ReviewQueueItem(
        blueprint_id=blueprint_id,
        entity_number=entity_number,
        context=context,
    )
    session.add(item)
    session.flush()
    return item


def list_review_queue(
    session: Session,
    resolved: bool | None = False,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[ReviewQueueItem], int]:
    """List review queue items, default unresolved only."""
    stmt = select(ReviewQueueItem)
    if resolved is not None:
        stmt = stmt.where(ReviewQueueItem.resolved == resolved)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    results = list(session.execute(stmt).scalars().all())
    return results, total


def resolve_review_item(
    session: Session,
    item_id: str,
    resolution: str,
) -> ReviewQueueItem:
    """Mark a review queue item as resolved."""
    item = session.get(ReviewQueueItem, item_id)
    if item is None:
        raise KeyError(f"Review queue item not found: {item_id}")
    item.resolved = True
    item.resolution = resolution
    item.resolved_at = datetime.now(timezone.utc)
    session.flush()
    return item
