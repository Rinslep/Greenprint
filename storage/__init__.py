"""Storage layer public interface — repository functions."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from storage.database import _dialect as _db_dialect
from storage.database import get_session, init_db  # noqa: F401 — re-export
from storage.models import Blueprint, BlueprintMotif, Motif, ReviewQueueItem


# ---------------------------------------------------------------------------
# Dialect-aware JSON filter helpers
# ---------------------------------------------------------------------------

def _apply_blueprint_json_filters(stmt, filters: dict):
    """Apply JSON-path filters to a blueprint SELECT statement.

    Supports: final_product, is_self_contained, flag.
    Uses dialect-appropriate SQL for SQLite vs PostgreSQL.
    Dialect is read from _db_dialect set at engine creation — no session.bind needed.
    """
    dialect = _db_dialect

    if "final_product" in filters:
        value = filters["final_product"]
        if dialect == "postgresql":
            stmt = stmt.where(
                text("summary->'crafting_graph'->'final_products' @> :val").bindparams(
                    val=f'["{value}"]'
                )
            )
        else:  # sqlite
            stmt = stmt.where(
                text(
                    "EXISTS (SELECT 1 FROM json_each(json_extract(summary, '$.crafting_graph.final_products')) "
                    "WHERE value = :val)"
                ).bindparams(val=value)
            )

    if "is_self_contained" in filters:
        value = filters["is_self_contained"]
        if dialect == "postgresql":
            stmt = stmt.where(
                text("(summary->'crafting_graph'->>'is_self_contained')::boolean = :val").bindparams(
                    val=value
                )
            )
        else:
            sqlite_val = 1 if value else 0
            stmt = stmt.where(
                text(
                    "CAST(json_extract(summary, '$.crafting_graph.is_self_contained') AS INTEGER) = :val"
                ).bindparams(val=sqlite_val)
            )

    if "flag" in filters:
        value = filters["flag"]
        if dialect == "postgresql":
            stmt = stmt.where(
                text("EXISTS (SELECT 1 FROM jsonb_array_elements(flags) f WHERE f->>'flag' = :val)").bindparams(
                    val=value
                )
            )
        else:
            stmt = stmt.where(
                text(
                    "EXISTS (SELECT 1 FROM json_each(flags) WHERE json_extract(value, '$.flag') = :val)"
                ).bindparams(val=value)
            )

    return stmt


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
    """List blueprints with optional filtering and pagination.

    Supported filter keys: source_site, game_version, final_product,
    is_self_contained, flag.
    """
    stmt = select(Blueprint)

    if filters:
        if "source_site" in filters:
            stmt = stmt.where(Blueprint.source_site == filters["source_site"])
        if "game_version" in filters:
            stmt = stmt.where(Blueprint.game_version == filters["game_version"])
        # JSON-path filters (dialect-aware)
        stmt = _apply_blueprint_json_filters(stmt, filters)

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
    is_multi_destination: bool = False,
    entity_count: int = 0,
    example_blueprint_id: str | None = None,
    blueprint_id: str | None = None,
    position_context: dict | None = None,
    # P3: family hash fields
    family_hash: str | None = None,
    elaboration_depth: int = 0,
    sub_motif_of_family: str | None = None,
) -> Motif:
    """Upsert a motif: increment occurrence_count if hash exists, else create.

    Also increments ``family_occurrence_count`` on all motifs sharing the same
    ``family_hash``, keeping the denormalised family aggregate in sync.
    """
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
            is_multi_destination=is_multi_destination,
            entity_count=entity_count,
            example_blueprint_id=example_blueprint_id,
            family_hash=family_hash,
            elaboration_depth=elaboration_depth,
            sub_motif_of_family=sub_motif_of_family,
        )
        session.add(motif)

    session.flush()

    # Increment family_occurrence_count on all motifs in the same family
    if family_hash:
        session.execute(
            update(Motif)
            .where(Motif.family_hash == family_hash)
            .values(family_occurrence_count=Motif.family_occurrence_count + 1)
        )

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


def update_motif_tileability(
    session: Session,
    canonical_hash: str,
    tile_vector: dict,
    tile_count: int,
) -> None:
    """Mark a motif as tileable and record the dominant tile vector.

    Only updates if ``tile_count`` exceeds the motif's current ``tile_count``,
    so repeated calls from different blueprints accumulate the best evidence.
    """
    stmt = select(Motif).where(Motif.canonical_hash == canonical_hash)
    motif = session.execute(stmt).scalar_one_or_none()
    if motif is None:
        return
    if tile_count > (motif.tile_count or 0):
        motif.is_tileable = True
        motif.tile_vector = tile_vector
        motif.tile_count = tile_count
    session.flush()


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
    order_by: str = "occurrence_count",
) -> tuple[list[Motif], int]:
    """List motifs with optional filtering, ordering, and pagination.

    Supported filter keys: category, belt_type, uses_underground, uses_splitter,
    is_multi_destination, is_tileable, family_hash, elaboration_depth.
    Supported order_by values: occurrence_count (desc), family_occurrence_count (desc),
    first_seen_at (asc).
    """
    stmt = select(Motif)

    if filters:
        if "category" in filters:
            stmt = stmt.where(Motif.category == filters["category"])
        if "belt_type" in filters:
            stmt = stmt.where(Motif.belt_type == filters["belt_type"])
        if "uses_underground" in filters:
            stmt = stmt.where(Motif.uses_underground == bool(filters["uses_underground"]))
        if "uses_splitter" in filters:
            stmt = stmt.where(Motif.uses_splitter == bool(filters["uses_splitter"]))
        if "is_multi_destination" in filters:
            stmt = stmt.where(Motif.is_multi_destination == bool(filters["is_multi_destination"]))
        if "is_tileable" in filters:
            stmt = stmt.where(Motif.is_tileable == bool(filters["is_tileable"]))
        if "family_hash" in filters:
            stmt = stmt.where(Motif.family_hash == filters["family_hash"])
        if "elaboration_depth" in filters:
            stmt = stmt.where(Motif.elaboration_depth == int(filters["elaboration_depth"]))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar_one()

    if order_by == "first_seen_at":
        stmt = stmt.order_by(Motif.first_seen_at.asc())
    elif order_by == "family_occurrence_count":
        stmt = stmt.order_by(Motif.family_occurrence_count.desc())
    else:
        stmt = stmt.order_by(Motif.occurrence_count.desc())

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


def get_blueprint_motif_hashes(session: Session) -> dict[str, set[str]]:
    """Return {blueprint_id: {canonical_hash, ...}} for all blueprints with motifs.

    Used by the similarity search endpoint to compute Jaccard scores.
    """
    stmt = select(BlueprintMotif.blueprint_id, Motif.canonical_hash).join(
        Motif, Motif.id == BlueprintMotif.motif_id
    )
    rows = session.execute(stmt).all()
    result: dict[str, set[str]] = {}
    for bp_id, hash_ in rows:
        result.setdefault(bp_id, set()).add(hash_)
    return result


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


def count_blueprints_by_source_site(session: Session) -> dict[str, int]:
    """Return {source_site: count} using a SQL GROUP BY — no Python loop."""
    rows = session.execute(
        text("SELECT COALESCE(source_site, 'unknown'), COUNT(*) FROM blueprints GROUP BY source_site")
    ).all()
    return {site: count for site, count in rows}


def count_flag_distribution(session: Session) -> dict[str, int]:
    """Return {flag_name: count} by unnesting the flags JSON array in SQL.

    Uses dialect-appropriate JSON functions (SQLite json_each vs PostgreSQL jsonb_array_elements).
    """
    dialect = _db_dialect
    if dialect == "postgresql":
        rows = session.execute(
            text(
                "SELECT f->>'flag', COUNT(*) FROM blueprints, "
                "jsonb_array_elements(flags) AS f "
                "WHERE flags IS NOT NULL GROUP BY f->>'flag'"
            )
        ).all()
    else:  # sqlite
        rows = session.execute(
            text(
                "SELECT json_extract(value, '$.flag'), COUNT(*) "
                "FROM blueprints, json_each(flags) "
                "WHERE flags IS NOT NULL GROUP BY json_extract(value, '$.flag')"
            )
        ).all()
    return {flag: count for flag, count in rows if flag}


def get_candidate_blueprint_ids(
    session: Session, query_hashes: set[str], limit: int = 200
) -> list[str]:
    """Return blueprint IDs that share at least one canonical motif hash with the query set.

    Used by the similarity search endpoint to pre-filter candidates before computing
    full Jaccard scores, avoiding a full join scan of the entire junction table.
    """
    if not query_hashes:
        return []
    stmt = (
        select(BlueprintMotif.blueprint_id)
        .distinct()
        .join(Motif, Motif.id == BlueprintMotif.motif_id)
        .where(Motif.canonical_hash.in_(query_hashes))
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())


def get_blueprint_motif_hashes_for_ids(
    session: Session, blueprint_ids: list[str]
) -> dict[str, set[str]]:
    """Return {blueprint_id: {canonical_hash, ...}} for the given blueprint IDs only.

    Narrowed version of get_blueprint_motif_hashes — used after candidate pre-filtering
    to fetch only the hash sets needed for Jaccard computation.
    """
    if not blueprint_ids:
        return {}
    stmt = (
        select(BlueprintMotif.blueprint_id, Motif.canonical_hash)
        .join(Motif, Motif.id == BlueprintMotif.motif_id)
        .where(BlueprintMotif.blueprint_id.in_(blueprint_ids))
    )
    rows = session.execute(stmt).all()
    result: dict[str, set[str]] = {}
    for bp_id, hash_ in rows:
        result.setdefault(bp_id, set()).add(hash_)
    return result


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
