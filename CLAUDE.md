# Factorio Blueprint Analyser — Claude Code Instructions

## Project Overview

This is a personal data pipeline and analysis tool that scrapes Factorio 1.1 blueprints from
community sources, decodes and validates them, analyses their production logic and physical layout
patterns, and stores everything in a queryable database. The intention is to start as a local tool
and host it publicly once functional.

---

## Ground Rules

- Target game version is **Factorio 1.1**, specifically 1.1.110 as the reference version
- Only **vanilla** blueprints are accepted — any entity or recipe name not in the vanilla 1.1
  reference dataset causes the blueprint to be rejected
- Blueprint books are dissolved into their constituent blueprints at import time
- All analysis is reproducible — no runtime external dependencies for reference data
- The API is designed as if already public, even while used privately
- All routes are versioned under `/v1/`
- Python is the language for the entire pipeline

---

## Project Structure

```
factorio-blueprint-analyser/
├── CLAUDE.md                  # This file
├── README.md
├── requirements.txt
├── config.py                  # Environment config, paths, constants
│
├── reference/                 # Static 1.1 reference data — never fetched at runtime
│   ├── recipes.json           # All vanilla 1.1 recipes
│   ├── entities.json          # All vanilla 1.1 entity metadata
│   └── version.json           # Reference version metadata (1.1.110)
│
├── scraper/                   # One module per source
│   ├── __init__.py
│   ├── base.py                # Base scraper class with resumability, rate limiting
│   ├── factorio_prints.py     # Firebase REST client (covers factorio.school too)
│   ├── reddit.py              # Uses PRAW
│   └── forums.py              # httpx + BeautifulSoup (phpBB)
│
├── pipeline/                  # Core processing pipeline
│   ├── __init__.py
│   ├── decoder.py             # Base64 → zlib → JSON, failure categories
│   ├── validator.py           # Schema + semantic validation
│   ├── version_filter.py      # Version unpacking, modded rejection
│   ├── broken_detector.py     # Detects non-functional blueprints
│   ├── recipe_inference.py    # Infers missing recipes from context
│   ├── review_queue.py        # Review queue (DB-backed in Step 13+)
│   └── orchestrator.py        # Full pipeline: decode → analyse → store
│
├── analysis/                  # Analysis modules
│   ├── __init__.py
│   ├── crafting_graph.py      # Directed item/recipe graph, final products, raw inputs
│   ├── ratio_analyser.py      # Ideal machine counts, efficiency score, bottleneck
│   ├── throughput_analyser.py # Items/sec at each stage, bottleneck detection
│   └── motif/
│       ├── __init__.py
│       ├── extractor.py       # Extract connection motifs from blueprints
│       ├── lane_model.py      # Lane-level belt graph representation
│       ├── canonicaliser.py   # Normalise + hash motifs (8 transformations)
│       └── catalogue.py       # Motif library management
│
├── storage/                   # Database layer
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # Connection, session management
│   └── migrations/            # Schema migrations
│
├── cli.py                     # Typer CLI entry points
├── __main__.py                # python -m greenprint support
│
├── api/                       # REST API (FastAPI)
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py        # Shared dependencies, rate limiting
│   └── v1/
│       ├── __init__.py        # Router aggregation
│       ├── schemas.py         # Pydantic response models
│       ├── blueprints.py
│       ├── motifs.py
│       ├── recipes.py
│       ├── analysis.py
│       └── review_queue.py    # Review queue endpoints (separate from analysis)
│
└── tests/
    ├── fixtures/              # Sample blueprint strings for testing
    ├── test_decoder.py
    ├── test_validator.py
    ├── test_crafting_graph.py
    ├── test_ratio_analyser.py
    ├── test_throughput_analyser.py
    ├── test_motif_extractor.py
    └── test_canonicaliser.py
```

---

## Build Order

Build and test each component in this order. Do not move to the next until the current one has
tests passing.

1. Reference data loader and validator
2. Blueprint decoder
3. Schema and semantic validator
4. Version filter and modded blueprint rejection
5. Broken blueprint detector
6. Recipe inference and review queue
7. Crafting graph analyser
8. Ratio analyser
9. Lane model
10. Throughput analyser (depends on lane model)
11. Motif extractor and canonicaliser
12. Motif catalogue
13. Database models and storage layer
14. Scrapers (base class first, then each source)
15. Full pipeline orchestrator
16. API

---

## Reference Data

### File: `reference/recipes.json`

Each recipe entry:
```json
{
  "name": "electronic-circuit",
  "category": "crafting",
  "crafting_time": 0.5,
  "inputs": [
    { "name": "iron-plate", "amount": 1 },
    { "name": "copper-cable", "amount": 3 }
  ],
  "outputs": [
    { "name": "electronic-circuit", "amount": 1 }
  ],
  "valid_machines": ["assembling-machine-1", "assembling-machine-2", "assembling-machine-3"]
}
```

### File: `reference/entities.json`

Each entity entry should cover all of the following where relevant:
- `size`: tile footprint as `[width, height]`
- `crafting_speed`: multiplier (assembling-machine-2 = 0.75, assembling-machine-3 = 1.25)
- `module_slots`: integer count
- `energy_consumption_kw`: number
- `belt_speed`: items per second per lane (yellow=7.5, red=15, blue=22.5)
- `underground_max_distance`: including end tiles (yellow=9, red=11, blue=13)
- `inserter_reach`: tile distance (standard=1, long=2)
- `inserter_swing_speed`: swings per second
- `inserter_stack_size`: default stack size (1 for standard, up to 12 for stack inserters)
- `inserter_filter`: boolean — whether it can filter by item type
- `pole_supply_area`: tile radius
- `pole_wire_reach`: tile distance
- `splitter_has_filter`: boolean
- `splitter_has_priority`: boolean

Important entity belt speeds (items/sec/lane):
- `transport-belt`: 7.5
- `fast-transport-belt`: 15.0
- `express-transport-belt`: 22.5

---

## Decoding Pipeline

### Failure Categories

Every failure is logged with `source_url`, `raw_string_hash`, `failure_stage`, and `failure_reason`.

| Stage | Name | Description |
|---|---|---|
| 1 | `STRING_EXTRACTION` | Regex match was not a valid blueprint |
| 2 | `DECODE_FAILURE` | Base64 valid but zlib decompression failed |
| 3 | `JSON_PARSE` | Decompressed but not valid JSON |
| 4 | `SCHEMA_VALIDATION` | Valid JSON but wrong shape |
| 5 | `SEMANTIC_VALIDATION` | Valid shape but nonsensical content |

### Decode Steps

1. Strip the leading version character (`0` for 1.1)
2. Base64 decode
3. zlib decompress
4. JSON parse
5. Schema validate against a defined Pydantic model
6. Semantic validate (unique entity numbers, valid positions, valid connection references)

### Version Unpacking

The version integer is a packed 64-bit value:
```
major = (version >> 48) & 0xFFFF
minor = (version >> 32) & 0xFFFF
patch = (version >> 16) & 0xFFFF
dev   = (version >>  0) & 0xFFFF
```

Accept `major == 1, minor == 1`. Flag blueprints where `patch < 110`.

### Modded Blueprint Rejection

After decoding, check every `entity.name` and `entity.recipe` value against the vanilla 1.1
reference lists. Any unknown name → reject with reason `MODDED_BLUEPRINT`.

---

## Blueprint Books

On decode, detect `item == "blueprint-book"`. Recursively extract all child blueprints.
Each child is stored as an independent blueprint with `source_book_id` set to the parent's hash.
Books are never stored or analysed as a unit.

---

## Broken Blueprint Detection

Run after successful decode and validation. Attach a `flags` list to each blueprint.

| Flag | Severity | Description |
|---|---|---|
| `NO_POWER` | HIGH | No electric poles present |
| `POWER_GAP` | MEDIUM | Poles present but don't cover all machines |
| `FLOATING_INSERTER` | LOW | Inserter has no valid source or destination |
| `BELT_DEAD_END` | MEDIUM | Belt segment doesn't reach a machine, chest, or loader |
| `UNSUPPLIED_RECIPE` | HIGH | Machine recipe requires input with no supply path |
| `INFERRED_RECIPE` | INFO | One or more recipes were inferred, not explicitly set |
| `CONDITIONAL_BEHAVIOUR` | INFO | Circuit network connects to machines or inserters |
| `EARLY_VERSION` | INFO | Blueprint patch version < 110 |

Severity HIGH does not prevent storage but is surfaced prominently in API responses.

---

## Recipe Inference

For machines with no recipe set:

1. Check what items inserters adjacent to the machine are carrying (from `filters` or `control_behavior`)
2. Check what items are on connected belt lanes leading to input inserters
3. Cross-reference with the recipe database to find recipes consistent with those inputs and the machine type
4. If exactly one recipe matches → apply it, set `INFERRED_RECIPE` flag
5. If multiple recipes match → add to review queue with all candidates listed
6. If no recipe matches → add to review queue with "no candidate found"
7. If unreviewed → exclude machine from crafting graph but keep blueprint

**Inferred recipes are always flagged regardless of confidence level.**

---

## Crafting Graph

Model as a directed graph where:
- Nodes are item names (strings)
- Edges are recipes connecting input items to output items
- Node attributes: whether produced/consumed within blueprint
- Edge attributes: recipe name, machine count, machine type

Derived properties:
- `final_products`: produced internally, not consumed internally
- `raw_inputs`: consumed internally, not produced internally  
- `intermediates`: both produced and consumed internally
- `is_self_contained`: all intermediates are produced within the blueprint
- `has_cycle`: detected via DFS, flagged not errored

Use `networkx.DiGraph`. Cycle detection via `networkx.find_cycle`.

---

## Ratio Analysis

For each recipe in the crafting graph, calculate:

```
items_per_second = (output_count / crafting_time) * machine_speed * module_speed_multiplier
                   * (1 + productivity_bonus)
```

Store as `fractions.Fraction` not float to avoid rounding errors.

For each machine-to-machine relationship:
- `ideal_ratio`: Fraction — ideal supplier machines per consumer machine
- `actual_ratio`: Fraction — actual counts in blueprint
- `efficiency`: float — how close actual is to ideal (1.0 = perfect)

Beacon effects: if beacon entities are present in the blueprint, apply their module bonuses to
machines within their supply range before calculating rates.

---

## Throughput Analysis

Work through four layers per connection:

1. **Machine output rate**: crafting speed × tier × modules ÷ crafting time × count
2. **Inserter delivery rate**: items_per_swing × swings_per_second × count
   - Inserters can connect two machines directly with no belt — this is a first-class case
   - Filter inserters only move their target item type
   - Stack inserters move multiple items per swing
3. **Belt lane capacity**: sum consumption on shared lane vs lane capacity by tier
4. **Bottleneck**: minimum across all three layers

Store:
- `actual_output_rate`: items/sec per final product
- `bottleneck_entity`: which entity is the constraint
- `bottleneck_type`: `machine` | `inserter` | `belt_lane`
- `lane_saturation`: map of lane position to saturation percentage

---

## Lane Model

Model belt connections at the lane level, not the belt level.

Each belt tile contributes two graph nodes:
```
(x, y, "left")
(x, y, "right")
```

Edges connect lane nodes:
- Belt flow: lane node → adjacent lane node in belt direction
- Inserter swing: machine tile → lane node (or lane node → machine tile)
- Direct inserter: machine tile → machine tile (no belt, inserter spans both)
- Underground pair: entrance lane node → exit lane node (single logical edge)
- Splitter: up to 2 input lane nodes → up to 2 output lane nodes, respecting priority/filter

**Direct machine-to-machine inserter connections have no belt nodes in the path.**
Model these as a direct edge between the two machine entity nodes with the inserter as an edge
attribute.

Rules:
- Inserter targets the lane closest to its pickup/drop position
- Sideloading places onto the near lane only
- Splitter with filter: one output lane only carries the filtered item type
- Splitter with priority: items prefer the priority output when both outputs are available

---

## Motif Extraction

A motif is the complete subgraph of entities between a machine output and the next machine
input(s). Extract motifs by:

1. For each machine, find all output inserters (or direct output connections)
2. Trace each lane path forward until reaching another machine's input inserter
3. If path forks (splitter, sideload), the entire forked structure is one motif
4. Collect all entities touched into a motif subgraph

Motif categories:
- `DIRECT`: inserter connects two machines with no belt
- `SIMPLE`: inserter → belt tiles → inserter
- `UNDERGROUND`: includes underground belt pair
- `SPLIT`: includes splitter (1-to-N or 2-to-2)
- `MERGED`: multiple inputs combine onto one belt path

---

## Canonicalisation

For each motif, produce a canonical hash:

1. Translate all positions so the source machine anchor is at (0, 0)
2. Apply all 8 transformations: 4 rotations (0°, 90°, 180°, 270°) × 2 mirror states
3. For each transformation, serialize entities as a sorted tuple of
   `(entity_type, x, y, direction, extra_attributes)`
4. Select the lexicographically smallest serialization
5. MD5 hash the canonical serialization

Mirrored motifs are treated as identical — include mirrored transformations in the 8 candidates
so the same canonical minimum is reached regardless of orientation.

Direction rotation: Factorio uses 0=N, 2=E, 4=S, 6=W. Rotating 90° clockwise adds 2 mod 8.
Mirror: negate the x coordinate, then adjust direction accordingly.

---

## Scraper Design

### Base Class

All scrapers extend a base class providing:
- Resumability: a local SQLite progress tracker recording fetched page IDs and URLs
- Rate limiting: configurable delay between requests, respects `Retry-After` headers
- robots.txt checking before any request to a new domain
- Deduplication: hash raw string before inserting, skip if already seen
- Metadata capture: source URL, scrape timestamp, author identifier (stored raw, anonymised on export)

### Per-Source Notes

**Factorio Prints / factorio.school:** These are the same database — a single Firebase Realtime
Database backend (project `facorio-blueprints`, note the typo). `factorio_prints.py` is a Firebase
REST client, not an HTML scraper. There is no separate `factorio_school.py`. Use 0.5–1s delay
between requests (Firebase is a paid service for the site owner).

**Reddit (r/factorio):** Use PRAW. Rate limit is 60 requests/minute. Search for posts containing
blueprint strings. Extract from post body and comments. Credentials via `.env` (see `.env.example`).

**Factorio Forums:** phpBB — fully server-rendered HTML. Use `httpx` + `BeautifulSoup` only (no
Playwright needed). Target subforums: Show your Creations (f=8), Mechanical Throughput Magic
(f=194), Combinator Creations (f=193).

### String Extraction Regex

Blueprint strings start with `0` followed by base64 characters. Account for:
- Line breaks within the string
- Code block wrapping (backticks or `[code]` tags)
- Surrounding whitespace

---

## Storage Layer

All UUIDs are generated in Python via `uuid.uuid4()` (not by the database) for SQLite/PostgreSQL
portability. Use `String(36)` columns. Use `JSON` type (becomes JSONB on PostgreSQL automatically).

Use `create_all()` for schema creation during development. Alembic migrations will be configured
before first public deployment (the `migrations/` directory is scaffolded for this).

### Author Anonymisation

Author anonymisation happens at a single chokepoint: `save_blueprint()` in `storage/__init__.py`.
The `author_raw` parameter (a username string) is converted to `author_hash` (SHA-256 hex digest)
before anything touches the database. The `Blueprint` model has no `author_raw` column. The API
response schemas must not include `author_hash` either — it is stored but never exposed.

## Storage Schema

### Table: `blueprints`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `raw_string_hash` | TEXT | SHA256 of raw blueprint string, unique |
| `raw_string` | TEXT | Original encoded string |
| `decoded_json` | JSONB | Full decoded blueprint |
| `source_url` | TEXT | Where it was scraped from |
| `source_site` | TEXT | `factorio_prints` \| `reddit` \| `forums` |
| `author_hash` | TEXT | Anonymised author identifier (one-way hash of username) |
| `scraped_at` | TIMESTAMP | |
| `game_version` | TEXT | e.g. `"1.1.57"` |
| `game_version_int` | BIGINT | Raw packed version integer |
| `source_book_id` | UUID | FK to parent book blueprint, nullable |
| `similar_to_id` | UUID | FK to canonical version if near-duplicate, nullable |
| `flags` | JSONB | List of flag objects with severity and detail |
| `summary` | JSONB | Compact computed summary (crafting graph, ratios, throughput) |

### Table: `motifs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `canonical_hash` | TEXT | Unique |
| `canonical_entities` | JSONB | One stored example in canonical form |
| `occurrence_count` | INT | Total appearances across all blueprints |
| `category` | TEXT | `DIRECT` \| `SIMPLE` \| `UNDERGROUND` \| `SPLIT` \| `MERGED` |
| `source_recipes` | JSONB | Map of recipe name to count |
| `dest_recipes` | JSONB | Map of recipe name to count |
| `belt_type` | TEXT | Belt tier used, nullable |
| `uses_underground` | BOOL | |
| `uses_splitter` | BOOL | |
| `entity_count` | INT | |
| `first_seen_at` | TIMESTAMP | |
| `example_blueprint_id` | UUID | FK to blueprints |

### Table: `blueprint_motifs`

Junction table linking blueprints to the motifs they contain, with position context.

### Table: `review_queue`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `blueprint_id` | UUID | FK to blueprints |
| `entity_number` | INT | Which entity needs review |
| `context` | JSONB | Adjacent items, candidate recipes, confidence |
| `resolved` | BOOL | |
| `resolution` | TEXT | Recipe name chosen, or `REJECTED` |
| `resolved_at` | TIMESTAMP | |

---

## API Design

Use **FastAPI**. All endpoints under `/v1/`.

### Response Envelope

Every response:
```json
{
  "data": { ... },
  "meta": {
    "total": 1234,
    "page": 1,
    "per_page": 20
  },
  "warnings": ["INFERRED_RECIPE", "EARLY_VERSION"]
}
```

### Filter Language

Consistent across all collection endpoints:
`?filter=final_product:electronic-circuit,efficiency:>0.9,flag:INFERRED_RECIPE`

### Endpoints

```
GET  /v1/blueprints
GET  /v1/blueprints/{id}
GET  /v1/blueprints/{id}/graph
GET  /v1/blueprints/{id}/ratios
GET  /v1/blueprints/{id}/throughput
GET  /v1/blueprints/{id}/motifs

GET  /v1/motifs
GET  /v1/motifs/{id}
GET  /v1/motifs/{id}/blueprints

GET  /v1/recipes
GET  /v1/recipes/{name}

POST /v1/analysis/compare       — body: list of blueprint IDs
POST /v1/analysis/search        — body: blueprint string, returns similar (max 500 entities, 5s timeout)
GET  /v1/analysis/stats         — dataset-level statistics

GET  /v1/review-queue           — list unresolved items
POST /v1/review-queue/{id}      — submit resolution
```

Rate limiting: apply per IP from day one. Flags are always included in responses — never silently
hidden.

---

## Pipeline Orchestrator

Single entry point: `process_string(raw, source_url, source_site, author_raw) → PipelineResult`.

Stages run sequentially. Non-critical stage failures are caught, logged, and flagged — the pipeline
continues. Only decode, validate, version/mod check, and save failures abort the pipeline.

`Fraction` values from ratio/throughput analysis are converted to `float` at the storage boundary
via `_serialise_summary()` in the orchestrator. Analysis modules keep exact `Fraction` values
internally.

`PipelineResult` is a dataclass with: `success`, `blueprint_ids`, `rejected`,
`rejection_reason`, `flags`, `review_queue_items`, `errors`.

---

## CLI

Typer-based CLI at `cli.py`, invoked via `python -m greenprint`. Subcommands: `scrape`, `ingest`,
`analyse`, `review`, `serve` (starts uvicorn), `stats`. Each subcommand delegates to the
underlying function — no logic in CLI handlers.

---

## Testing

Every module has a corresponding test file. Fixtures in `tests/fixtures/` include:
- A simple valid 1.1 blueprint (small, known content)
- A blueprint book with nested blueprints
- A blueprint with no recipes set
- A blueprint from a modded game
- A blueprint with a cycle in the crafting graph
- A blueprint with splitters
- A corrupt/truncated string
- A blueprint with direct machine-to-machine inserter connections

Tests are deterministic — no network calls, no runtime reference data fetching.

---

## Key Behaviours to Preserve Across All Changes

- Inferred recipes are **always** flagged, regardless of confidence
- Mirrored motifs hash to the same canonical value as their unmirrored counterparts
- Blueprint books are **always** dissolved — never stored or analysed as a unit
- Modded blueprints are **always** rejected at decode time
- The reference dataset is **never** fetched at runtime
- Author usernames are **never** exposed in any API response — not even the anonymised hash
- All ratios are stored as `fractions.Fraction` internally, converted to `float` only at storage boundary
- Direct machine-to-machine inserter connections are a first-class motif type, not an edge case
- factorioprints.com and factorio.school are the same database — only one scraper needed