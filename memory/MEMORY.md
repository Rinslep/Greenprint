# Greenprint — Persistent Memory

## Project Identity
- **Name**: Greenprint (Factorio Blueprint Analyser)
- **Target**: Factorio 1.1.110 vanilla only
- **Language**: Python throughout
- **Status**: Scaffold created (March 2026), no implementation yet

## Key Architecture
- `config.py` — settings via pydantic-settings + python-dotenv
- `reference/` — static JSON data (recipes, entities, version). Never fetched at runtime.
- `pipeline/` — decode → validate → version_filter → broken_detector → recipe_inference
- `analysis/` — crafting_graph → ratio_analyser → throughput_analyser → motif/
- `storage/` — SQLAlchemy 2.0 ORM, Alembic migrations, PostgreSQL (SQLite for dev)
- `api/` — FastAPI, all routes under `/v1/`, SlowAPI rate limiting
- `scraper/` — BaseScraper + 4 sources (factorio_prints, factorio_school, reddit, forums)
- `tests/` — pytest, fixtures in tests/fixtures/, no network calls in any test

## Build Order (from CLAUDE.md)
1. Reference data loader + validator
2. Blueprint decoder
3. Schema + semantic validator
4. Version filter + modded rejection
5. Broken blueprint detector
6. Recipe inference + review queue
7. Crafting graph analyser
8. Ratio analyser
9. Throughput analyser
10. Lane model
11. Motif extractor + canonicaliser
12. Motif catalogue
13. Database models + storage layer
14. Scrapers
15. Full pipeline orchestrator
16. API

## Critical Invariants (never break these)
- Inferred recipes are ALWAYS flagged (INFERRED_RECIPE), no exceptions
- Mirrored motifs hash identically to unmirrored (8-transformation canonicalisation)
- Blueprint books are ALWAYS dissolved — never stored as a unit
- Modded blueprints are ALWAYS rejected at decode time
- Reference data is NEVER fetched at runtime
- Author usernames are NEVER exposed in API — only anonymised SHA256 hash
- All ratios stored as `fractions.Fraction` internally, serialised to float at API layer
- Direct machine-to-machine inserter = first-class DIRECT motif type

## Key Technical Details
- Version unpacking: major=(v>>48)&0xFFFF, minor=(v>>32)&0xFFFF, patch=(v>>16)&0xFFFF
- Accept only major==1, minor==1. patch<110 → EARLY_VERSION flag (not rejection)
- Factorio direction: 0=N, 2=E, 4=S, 6=W. Rotate 90° CW: add 2 mod 8
- Belt speeds: yellow=7.5, red=15, blue=22.5 items/sec/lane
- Graph library: networkx.DiGraph for both crafting graph and lane model
