# Greenprint — Pre-Build Considerations for Audit Fixes

Read this entire file before beginning any implementation. The audit findings in exec_summary.txt
are accurate but the action plan order needs adjustment and several items have dependencies that
are not obvious from the audit alone. Do not begin any implementation until all actions in this
file are understood.

---

## Critical: Do These Three Things Before Writing Any Code

### 1. Check `data/review_queue.json` for Lost Data

The review queue bug means every unresolvable recipe inference since Step 13 has been written
to `data/review_queue.json` instead of the database. These items are lost from the API's
perspective but may still exist on disk.

```bash
# Check if the file exists and how many items it contains
python -c "
import json, os
path = 'data/review_queue.json'
if os.path.exists(path):
    items = json.load(open(path))
    unresolved = [i for i in items if not i.get('resolved')]
    print(f'File exists: {len(items)} total items, {len(unresolved)} unresolved')
else:
    print('No review_queue.json — no migration needed')
"
```

If unresolved items exist, they must be migrated into the database as part of the fix —
not discarded. The migration must happen inside the same atomic change as the code fix.
Write the migration script before touching any code.

### 2. Confirm the Exact SQLAlchemy Version in Use

The `session.bind` deprecation fix depends on which SQLAlchemy 2.0 pattern was used when
the engine was set up. The correct replacement differs:

```bash
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
# Also check how the session is constructed in storage/database.py
grep -n "Session\|sessionmaker\|engine" storage/database.py
```

The fix is `session.get_bind().dialect.name` if the session has a single bind, but if
using `sessionmaker` with `bind=engine` this is deprecated too. The safest fix is to
store the dialect name at engine creation time and pass it through rather than deriving
it from the session at query time.

### 3. Verify the Current Test Count

The audit doesn't state how many tests exist. Before any changes, record the baseline:

```bash
pytest tests/ -v --tb=no -q 2>&1 | tail -5
```

Every fix group must end with all tests passing. Record the starting count so regressions
are immediately visible.

---

## Execution Order

The audit action plan has the right items but the wrong order. The correct order is:

```
Group A (data integrity — do first, atomic):
  A1: Migrate review_queue.json → DB
  A2: Fix infer_recipes return type
  A3: Update orchestrator to call storage.add_review_item
  A4: Delete pipeline/review_queue.py
  → pytest, verify review queue items appear in GET /v1/review-queue

Group B (correctness bugs — no dependencies between them, do in any order):
  B1: Fix session.bind deprecation
  B2: Fix book detection (decode returns is_book flag)
  B3: Fix source_book_id → use source_book_hash TEXT column
  B4: Fix double commit in review queue endpoint
  B5: Fix text() f-string interpolation (security low)
  → pytest after each

Group C (performance — after correctness is clean):
  C1: Replace dataset_stats memory scan with SQL aggregates
  C2: Add pre-filter to similarity search (shared motif hash JOIN)
  C3: Add exception logging to search endpoint (replace silent pass)
  C4: Fix BaseScraper persistent SQLite connection
  C5: Add compare endpoint item cap
  → pytest after each

Group D (security and reliability):
  D1: Add auth to POST /v1/review-queue/{id}
  D2: Pin dependency versions (pip-compile)
  D3: Add missing DB indexes
  D4: Upsert motifs with INSERT ON CONFLICT instead of SELECT + INSERT/UPDATE
  → pytest after each

Group E (design cleanup — last, lowest risk of breaking things):
  E1: Migrate stdlib logging to structlog in orchestrator, scraper, broken_detector
  E2: Extract _save_motifs from _process_single in orchestrator
  E3: Move raw_string out of BlueprintDetailResponse to separate /raw endpoint
  → pytest after each
```

---

## Group A — Review Queue Data Path (Atomic Change)

This is the most important fix and must be done as a single atomic change. If you do it
in multiple commits and something goes wrong mid-way, the queue will be in an inconsistent
state.

### A1 — Migration Script (write this first, before any code changes)

Create `scripts/migrate_review_queue.py`:

```python
"""
One-time migration: copy unresolved items from data/review_queue.json into the
ReviewQueueItem table. Run once before deleting pipeline/review_queue.py.
Safe to run multiple times — skips items already in the DB by blueprint_id + entity_number.
"""
```

The migration must:
1. Load `data/review_queue.json` if it exists
2. For each unresolved item, check if a matching row already exists in `review_queue_items`
   by `blueprint_id` + `entity_number` (use the truncated hash as a text match, not UUID FK)
3. Insert items that don't already exist
4. Print a summary: N migrated, N skipped, N failed
5. Rename the file to `data/review_queue.json.migrated` on success

**Important:** the items in the JSON file have `blueprint_id` set to a 12-character truncated
hash (e.g. `"a3f9c1d2e4b7"`), not a DB UUID. The `ReviewQueueItem.blueprint_id` FK expects
a UUID. These won't match any blueprint row. Store the truncated hash in a separate
`legacy_ref TEXT` column on ReviewQueueItem, or accept that the FK will be NULL for
migrated items and store the hash in the `context` JSON. Document this clearly.

### A2 — `infer_recipes` Return Type Change

Change `infer_recipes()` to return structured item dicts instead of calling `review_queue.add()`
directly:

```python
def infer_recipes(wrapper) -> tuple[list[dict], list[ReviewItem]]:
    """
    Returns:
      - inference_flags: list of INFERRED_RECIPE flag dicts
      - review_items: list of structured dicts for items needing manual review
        Each dict: {entity_number, context, candidates}
        Caller is responsible for persisting these after blueprint is saved.
    """
```

Do not call `review_queue.add()` or `storage.add_review_item()` from inside
`infer_recipes()`. The function must be side-effect-free with respect to storage.
This makes it testable in isolation and removes the ordering dependency on `bp.id`.

### A3 — Orchestrator Change

After `save_blueprint()` (when `bp.id` is known), iterate over the returned review items
and call `storage.add_review_item(session, blueprint_id=bp.id, ...)` for each.

The `blueprint_id` passed to `infer_recipes` can be removed entirely — the function no
longer needs it since it no longer writes to the queue.

### A4 — Delete `pipeline/review_queue.py`

Delete the file only after:
- The migration script has been run successfully
- All imports of `pipeline.review_queue` have been removed
- All tests pass

Search for all imports before deleting:
```bash
grep -rn "from pipeline.review_queue\|import review_queue" .
```

---

## Group B — Correctness Bugs

### B1 — `session.bind` Deprecation

The safest fix is to not derive the dialect from the session at query time. Instead, store
it once at startup:

```python
# storage/database.py
_dialect: str = "sqlite"

def init_db():
    global _dialect
    engine = _create_engine()
    _dialect = engine.dialect.name
    Base.metadata.create_all(engine)
    ...

# storage/__init__.py
from storage.database import _dialect

def _apply_blueprint_json_filters(stmt, filters):
    # use _dialect directly, no session.bind needed
```

This is simpler and more reliable than deriving the dialect per-query.

### B2 — Book Detection

The audit correctly identifies that a book with one child sets `is_book = False`. The fix
is to check for `"blueprint_book"` in the decoded data before dissolving, not to infer
from the length of the result list.

Change `decoder.py` to return `(list[dict], bool)` where the bool is `True` if the
original string was a blueprint book. Update all call sites — the orchestrator is the
only consumer.

### B3 — `source_book_id` Fix

The current approach (first child gets None, siblings point to first child's UUID) is wrong.
The audit's suggestion of `source_book_hash TEXT` is correct.

Add a `source_book_hash TEXT` column to the Blueprint model (not a FK — just a plain text
column storing the raw string hash of the parent book). This requires a schema migration.

```python
# In Blueprint model:
source_book_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
```

When dissolving a book:
1. Compute `book_hash = sha256(raw_book_string)`
2. Set `source_book_hash = book_hash` on every child blueprint
3. Remove `source_book_id` FK entirely (or keep it as NULL for now and add it properly later)

This lets you find all children of a book with a simple `WHERE source_book_hash = ?` without
needing to know the first child's UUID.

**This requires an Alembic migration.** Generate it before implementing:
```bash
alembic revision --autogenerate -m "add_source_book_hash_column"
alembic upgrade head
```

### B4 — Double Commit

Remove the explicit `db.commit()` call in `api/v1/review_queue.py:44`. The `get_db()`
context manager handles commit on exit. Verify `storage.resolve_review_item()` uses
`session.flush()` not `session.commit()` — flush is correct inside a managed session,
commit is not.

### B5 — `text()` f-string Interpolation

Replace:
```python
stmt = stmt.where(text(f"...::boolean = {pg_val}"))
```
With:
```python
stmt = stmt.where(text("...::boolean = :val").bindparams(val=value))
```
The current code is not exploitable but is a fragile pattern that must not be copied.

---

## Group C — Performance

### C1 — `dataset_stats` SQL Aggregates

Replace the `list_blueprints(limit=10000)` loop with:

```sql
SELECT source_site, COUNT(*) as count FROM blueprints GROUP BY source_site
```

For flag distribution, SQLite and PostgreSQL need different approaches:
- SQLite: `SELECT json_each.value->>'$.flag', COUNT(*) FROM blueprints, json_each(blueprints.flags)`
- PostgreSQL: `SELECT flag->>'flag', COUNT(*) FROM blueprints, jsonb_array_elements(flags) as flag`

Use the same `_dialect` approach from B1 to branch. This query will be fast regardless
of dataset size.

### C2 — Similarity Search Pre-Filter

The current approach loads all `(blueprint_id, motif_hash)` pairs for every search request.
Replace with a two-step approach:

**Step 1:** Get the query blueprint's motif hash set (small, from the submitted string).

**Step 2:** Find candidate blueprint IDs that share at least one hash with the query:
```sql
SELECT DISTINCT blueprint_id
FROM blueprint_motifs bm
JOIN motifs m ON bm.motif_id = m.id
WHERE m.canonical_hash IN (:hash1, :hash2, ...)
```

**Step 3:** Load only those candidates' full motif hash sets for Jaccard computation.

This reduces the data loaded from O(all blueprints × avg motifs) to O(matching blueprints
× avg motifs), which is dramatically smaller for specific queries.

Add a hard cap: if the query blueprint has 0 motifs extracted, return empty results rather
than scanning everything.

### C3 — Search Exception Logging

Replace:
```python
except Exception:
    pass
```
With:
```python
except Exception as e:
    logger.warning("motif_extraction_failed_for_search", error=str(e), exc_info=True)
```

A crafted malicious blueprint that crashes the motif pipeline would otherwise be completely
invisible in logs.

### C4 — BaseScraper Persistent Connection

Store the progress SQLite connection as `self._progress_conn` in `__init__`, opened once,
closed in a `__del__` or context manager exit. Do not open a new connection per URL check.

### C5 — Compare Endpoint Cap

Add to the `CompareRequest` Pydantic model:
```python
blueprint_ids: list[str] = Field(..., max_length=20)
```
Return `422 Unprocessable Entity` if the list exceeds 20 items.

---

## Group D — Security and Reliability

### D1 — Auth on POST /v1/review-queue/{id}

Add a simple FastAPI dependency for write routes:

```python
# api/dependencies.py
def require_admin_key(x_admin_key: str = Header(None)):
    if x_admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")
```

Add `admin_key: str = ""` to `config.Settings`. When empty, the check passes (dev mode).
When set via environment variable, write routes require the key.

Apply to POST /v1/review-queue/{id} and any future write endpoints.

### D2 — Pin Dependency Versions

```bash
pip install pip-tools
# Create requirements.in with current unpinned deps
cp requirements.txt requirements.in
# Generate locked requirements.txt
pip-compile requirements.in --generate-hashes -o requirements.txt
```

Commit both `requirements.in` (human-editable) and `requirements.txt` (locked, generated).

### D3 — Missing Indexes

Generate an Alembic migration that adds:
```python
Index("ix_blueprints_game_version", Blueprint.game_version)
Index("ix_blueprints_source_book_hash", Blueprint.source_book_hash)  # from B3
Index("ix_blueprints_author_hash", Blueprint.author_hash)
Index("ix_motifs_family_hash", Motif.family_hash)  # for when family_hash is added
```

### D4 — Motif Upsert

Replace the SELECT + INSERT/UPDATE pattern in `storage.save_motif` with a single
`INSERT ... ON CONFLICT DO UPDATE` statement. Both SQLite (3.24+) and PostgreSQL support
this syntax. Reduces N motif saves from 2N round-trips to N round-trips.

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
# or use a dialect-agnostic merge pattern
```

---

## Group E — Design Cleanup

### E1 — Logging Consolidation

Files using `logging` (stdlib) that should use `structlog`:
- `pipeline/orchestrator.py`
- `scraper/base.py`
- `pipeline/broken_detector.py`

Pattern:
```python
# Replace:
import logging
logger = logging.getLogger(__name__)
logger.info("message")

# With:
import structlog
logger = structlog.get_logger(__name__)
logger.info("message")
```

Structlog is already configured via `logging_config.py`. The output format is consistent
with the rest of the pipeline.

### E2 — Extract `_save_motifs` from `_process_single`

Extract lines ~279–390 of `orchestrator.py` into a separate function:

```python
def _save_motifs(session, bp, lane_graph, result) -> None:
    """Extract, canonicalise, and persist motifs for a single blueprint."""
```

This makes the motif pipeline independently testable and reduces `_process_single` to a
readable sequence of stage calls.

### E3 — Move `raw_string` to Separate Endpoint

Remove `raw_string` from `BlueprintDetailResponse` in `api/v1/schemas.py`.
Add `GET /v1/blueprints/{id}/raw` that returns just the encoded string with content-type
`text/plain`. The main detail response should contain metadata and analysis, not a 50KB string.

---

## Schema Migration Checklist

The following schema changes are required across the groups above. All must go through
Alembic. Generate and apply migrations in this order:

1. `add_source_book_hash_column` — Group B3
   - Add `source_book_hash TEXT` to `blueprints`
   - Remove or keep-as-null `source_book_id` (decide before migrating)

2. `add_missing_indexes` — Group D3
   - Add indexes listed in D3

3. `add_review_queue_legacy_ref` — Group A1 (if storing legacy hash in context JSON,
   no migration needed; if adding a column, add here)

Each migration: `alembic revision --autogenerate -m "{name}"` then `alembic upgrade head`
then `pytest tests/ -v` before the next migration.

---

## Verification Gates

After Group A:
```bash
pytest tests/ -v
# Then manually verify:
python -c "
from storage.database import get_session
from storage.models import ReviewQueueItem
with get_session() as s:
    count = s.query(ReviewQueueItem).count()
    print(f'Review queue items in DB: {count}')
"
# Confirm pipeline/review_queue.py is gone:
ls pipeline/review_queue.py 2>/dev/null && echo "ERROR: still exists" || echo "OK: deleted"
```

After Group B:
```bash
pytest tests/ -v
# Verify session.bind is gone:
grep -rn "session.bind" storage/
# Verify source_book_hash column exists:
python -c "
from storage.database import get_session
from storage.models import Blueprint
with get_session() as s:
    cols = [c.name for c in Blueprint.__table__.columns]
    print('source_book_hash' in cols)
"
```

After Group C:
```bash
pytest tests/ -v
# Verify stats endpoint uses no Python loop:
grep -n "for bp in\|list_blueprints" api/v1/analysis.py
# Should return no results (the loop is gone)
```

After all groups:
```bash
pytest tests/ -v
# All tests pass, count >= baseline recorded at start
```
