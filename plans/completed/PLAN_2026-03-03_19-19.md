# Plan: Next Steps — Build Steps 1–4 (Foundation)

## Context
The project scaffold is complete: all modules, test files, and reference data stubs exist but contain
no working code. The CLAUDE.md build order requires that each step passes its tests before moving to
the next. Steps 1–4 form the data-ingestion foundation — nothing downstream (analysis, storage, API)
can work until these pass. This plan covers implementing those four steps to completion.

---

## Scope: Build Steps 1–4

| Step | Component | Key output |
|------|-----------|------------|
| 1 | Reference data + loader | Populated JSON files, `pipeline/reference_loader.py` |
| 2 | Blueprint decoder | Working `pipeline/decoder.py`, 3 fixtures, passing `test_decoder.py` |
| 3 | Schema + semantic validator | Working `pipeline/validator.py`, passing `test_validator.py` |
| 4 | Version filter + modded rejection | Working `pipeline/version_filter.py`, passing `test_version_filter.py` |

---

## Step 1 — Reference Data & Loader

### 1a. Populate `reference/version.json`
Compute and fill `packed_int`:
```python
packed_int = (1 << 48) | (1 << 32) | (110 << 16) | 0  # = 281479288520704
```

### 1b. Populate `reference/recipes.json`
Source: Factorio 1.1.110 data export (`factorio --dump-data` or the community wiki dump).
Every recipe executable in an assembler, chemical plant, oil refinery, centrifuge, rocket silo,
furnace, or lab must be present. Schema per entry (from CLAUDE.md):
```json
{
  "name": "electronic-circuit",
  "category": "crafting",
  "crafting_time": 0.5,
  "inputs": [{"name": "iron-plate", "amount": 1}, {"name": "copper-cable", "amount": 3}],
  "outputs": [{"name": "electronic-circuit", "amount": 1}],
  "valid_machines": ["assembling-machine-1", "assembling-machine-2", "assembling-machine-3"]
}
```
No Space Age / modded entries. Strip any recipe whose `valid_machines` list is empty.

### 1c. Populate `reference/entities.json`
Source: same Factorio 1.1.110 data export.
Include all blueprint-placeable entity types. Fields are conditional on entity type
(e.g. only inserters have `inserter_reach`). Critical values to verify against game source:
- Belt speeds: transport-belt=7.5, fast=15.0, express=22.5 items/sec/lane
- Underground max distances (including end tiles): yellow=9, red=11, blue=13
- Assembler crafting speeds: AM-1=0.5, AM-2=0.75, AM-3=1.25

### 1d. Create `pipeline/reference_loader.py` (new file — not yet scaffolded)
This module is implicitly required by build step 1 ("Reference data loader and validator"):
```python
# Functions:
def load_recipes() -> list[dict]      # load + cache reference/recipes.json
def load_entities() -> list[dict]     # load + cache reference/entities.json
def load_version() -> dict            # load reference/version.json
def get_entity_names() -> frozenset   # set of all vanilla entity name strings
def get_recipe_names() -> frozenset   # set of all vanilla recipe name strings
def get_recipe(name: str) -> dict     # single recipe lookup (raises KeyError if unknown)
def get_entity(name: str) -> dict     # single entity lookup
```
All functions cache on first call using a module-level dict. Files are loaded from
`config.REFERENCE_DIR`. Never fetch at runtime.

### 1e. Implement `config.py` fully
Replace the stub with a pydantic-settings `BaseSettings` class:
```python
class Settings(BaseSettings):
    db_url: str = "sqlite:///./blueprints.db"
    log_level: str = "INFO"
    scraper_rate_limit_delay: float = 1.0
    scraper_progress_db: Path = BASE_DIR / "scraper_progress.db"
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    api_rate_limit_per_minute: int = 60
    target_game_version: tuple = (1, 1, 110)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

## Step 2 — Blueprint Decoder (`pipeline/decoder.py`)

### Implementation
```python
class DecodeError(Exception):
    def __init__(self, failure_stage: str, failure_reason: str, raw_string_hash: str, source_url: str): ...

def decode(raw_string: str, source_url: str) -> list[dict]:
```

Logic:
1. SHA256-hash `raw_string` immediately (used in all error logging).
2. Check first character is `'0'` — if not, raise `DecodeError(stage='STRING_EXTRACTION')`.
3. `base64.b64decode(raw_string[1:])` — failure → `DecodeError(stage='DECODE_FAILURE')`.
4. `zlib.decompress(bytes)` — failure → `DecodeError(stage='DECODE_FAILURE', reason distinguishes from b64)`.
5. `json.loads(text)` — failure → `DecodeError(stage='JSON_PARSE')`.
6. If `decoded.get('blueprint_book')` exists: recursively extract children; set `source_book_id` on
   each child equal to the SHA256 of the raw string. Return list of children only — never the book itself.
7. Return `[decoded]` for a single blueprint.

### Test fixtures to create (in `tests/fixtures/`)
Three fixtures are needed to unblock `test_decoder.py`:
- **`simple_valid.txt`** — encode a minimal known blueprint programmatically.
- **`blueprint_book.txt`** — a book wrapping 2 minimal blueprints.
- **`corrupt.txt`** — a truncated/malformed base64 string.

Remaining fixtures (`no_recipes.txt`, `modded.txt`, `cycle.txt`, `splitters.txt`, `direct_inserter.txt`)
are not needed until steps 6–11.

---

## Step 3 — Schema + Semantic Validator (`pipeline/validator.py`)

Pydantic v2 models: `Position`, `Entity`, `Blueprint`, `BlueprintWrapper`.
Typed exceptions: `SchemaError`, `SemanticError`.

`validate(decoded: dict)` logic:
1. `BlueprintWrapper.model_validate(decoded)` — Pydantic error → `SchemaError`.
2. Check entity_number uniqueness → `SemanticError` on duplicate.
3. Check all position values are finite floats → `SemanticError` on NaN/Inf.
4. Check all connection references point to valid entity_numbers → `SemanticError`.
5. Return the validated `BlueprintWrapper` model instance.

---

## Step 4 — Version Filter + Modded Rejection (`pipeline/version_filter.py`)

`check_version(version_int)`: unpack 64-bit int, accept only major==1 minor==1,
attach EARLY_VERSION flag if patch < 110.

`check_modded(blueprint_wrapper)`: check every entity.name and entity.recipe against
`reference_loader.get_entity_names()` / `get_recipe_names()`. Unknown name → reject with
`MODDED_BLUEPRINT`.

New test file `tests/test_version_filter.py` must be created (not in scaffold).

---

## File Paths

**Create/modify:**
- `config.py` — full pydantic-settings implementation
- `reference/version.json` — fill `packed_int`
- `reference/recipes.json` — full vanilla 1.1 recipe data
- `reference/entities.json` — full vanilla 1.1 entity data
- `pipeline/reference_loader.py` — **new file**
- `pipeline/decoder.py` — implement `decode()` and `DecodeError`
- `pipeline/validator.py` — implement Pydantic models, `validate()`, typed exceptions
- `pipeline/version_filter.py` — implement `check_version()` and `check_modded()`
- `tests/fixtures/simple_valid.txt`
- `tests/fixtures/blueprint_book.txt`
- `tests/fixtures/corrupt.txt`
- `tests/test_version_filter.py` — **new file**

**No changes needed yet:**
- All `analysis/`, `storage/`, `api/`, `scraper/` files (build steps 7–16)

---

## Verification

After each step: `pytest tests/test_<module>.py -v`

Full gate before moving to step 5:
```bash
pytest tests/test_decoder.py tests/test_validator.py tests/test_version_filter.py -v
```
All tests must pass with no network calls.
