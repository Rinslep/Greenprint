# storage/models.py
#
# TODO: SQLAlchemy ORM models for all four tables.
#
# Table: blueprints
#   id              UUID, primary key (use uuid.uuid4)
#   raw_string_hash TEXT, unique, not null  — SHA256 of the original encoded string
#   raw_string      TEXT, not null
#   decoded_json    JSONB (use sqlalchemy.dialects.postgresql.JSONB; fall back to JSON for SQLite)
#   source_url      TEXT
#   source_site     TEXT  — 'factorio_prints' | 'factorio_school' | 'reddit' | 'forums'
#   author_hash     TEXT  — one-way SHA256 of the raw username; NEVER store the username
#   scraped_at      TIMESTAMP WITH TIME ZONE, default now()
#   game_version    TEXT  — e.g. '1.1.57'
#   game_version_int BIGINT
#   source_book_id  UUID, nullable, FK → blueprints.id
#   similar_to_id   UUID, nullable, FK → blueprints.id
#   flags           JSONB — list of {flag, severity, detail} dicts
#   summary         JSONB — compact computed summary (crafting graph, ratios, throughput)
#
# Table: motifs
#   id                  UUID, primary key
#   canonical_hash      TEXT, unique, not null
#   canonical_entities  JSONB
#   occurrence_count    INT, default 0
#   category            TEXT — 'DIRECT' | 'SIMPLE' | 'UNDERGROUND' | 'SPLIT' | 'MERGED'
#   source_recipes      JSONB
#   dest_recipes        JSONB
#   belt_type           TEXT, nullable
#   uses_underground    BOOL
#   uses_splitter       BOOL
#   entity_count        INT
#   first_seen_at       TIMESTAMP WITH TIME ZONE
#   example_blueprint_id UUID, FK → blueprints.id
#
# Table: blueprint_motifs (junction)
#   id              UUID, primary key
#   blueprint_id    UUID, FK → blueprints.id, not null
#   motif_id        UUID, FK → motifs.id, not null
#   position_context JSONB — position within the blueprint where this motif appears
#
# Table: review_queue
#   id              UUID, primary key
#   blueprint_id    UUID, FK → blueprints.id
#   entity_number   INT
#   context         JSONB — {adjacent_items, candidate_recipes, confidence}
#   resolved        BOOL, default False
#   resolution      TEXT, nullable — recipe name or 'REJECTED'
#   resolved_at     TIMESTAMP WITH TIME ZONE, nullable
#
# Use SQLAlchemy 2.0 declarative style (DeclarativeBase).
# All UUID columns should use the UUID type with as_uuid=True.
# Add indexes on: raw_string_hash, source_site, scraped_at, canonical_hash, resolved.
