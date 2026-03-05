# Greenprint Motif Specification

A precise, standalone reference for validating and generating motifs in the
Factorio Blueprint Analyser (Greenprint) project.  Any LLM with no codebase
access can use this document to check whether a proposed motif is structurally
and semantically correct, and to produce new motifs that are consistent with
the project's conventions.

---

## 1. Motif-Related Files and Modules

| File | Role |
|---|---|
| `analysis/motif/lane_model.py` | Builds the lane-level directed graph (`nx.DiGraph`) that is the input to the extractor.  Each belt tile becomes two graph nodes `(x, y, "left")` and `(x, y, "right")`; machines become `("machine", entity_number)` nodes; inserters become directed edges. |
| `analysis/motif/extractor.py` | Walks the lane graph from every machine output via BFS, collecting all nodes until a destination machine or chest is reached.  Returns a list of `nx.DiGraph` motif subgraphs, each with a `"category"` graph attribute. |
| `analysis/motif/canonicaliser.py` | Produces a stable `(canonical_hash, canonical_entities)` pair for a motif subgraph.  Applies all 8 geometric transformations (4 rotations × 2 mirror states) and selects the lexicographically smallest serialisation before MD5-hashing. |
| `analysis/motif/family_hash.py` | Computes tier-normalised grouping hashes: `compute_family_hash()` collapses belt/inserter variants to abstract types while preserving run lengths; `compute_simplified_family_hash()` additionally replaces underground belts and splitters with plain belts to identify the base SIMPLE/DIRECT family. |
| `analysis/motif/tileability.py` | Analyses repeated occurrences of the same canonical motif within a blueprint to detect a dominant spatial offset vector (`tile_vector`). |
| `analysis/motif/catalogue.py` | In-memory motif library (pre-database).  Provides `upsert`, `get`, `list_motifs`, and `get_blueprints_for_motif`. |
| `storage/models.py` (`Motif`, `BlueprintMotif`) | SQLAlchemy ORM models that persist motifs and their per-blueprint occurrence links. |
| `pipeline/orchestrator.py` | Integrates the full motif pipeline (Stage 10): calls `extract_motifs` → `canonicalise` → `compute_family_hash` → `save_motif` → `compute_blueprint_tileability`. |
| `api/v1/motifs.py` | REST endpoints: `GET /v1/motifs`, `GET /v1/motifs/{id}`, `GET /v1/motifs/{id}/blueprints`. |
| `api/v1/schemas.py` | Pydantic response schemas: `MotifSummaryResponse`, `MotifDetailResponse`. |
| `tests/test_motif_extractor.py` | Tests for `build_lane_model` and `extract_motifs`. |
| `tests/test_canonicaliser.py` | Tests for `canonicalise`, direction rotation, and mirror invariants. |
| `tests/test_motif_catalogue.py` | Tests for catalogue upsert, filtering, and recipe-count merging. |

---

## 2. Motif Concept and Data Model

### 2.1 Conceptual Definition

A **motif** is the complete subgraph of entities that lies between a single
assembling-machine output and one or more assembling-machine (or chest) inputs.
It captures the *connection pattern* — the inserters, belt tiles, underground
belt pairs, splitters, and nearby power poles — that physically transfers items
from a producer to its consumer(s).

Motifs solve two problems:
1. **Pattern library** — identical connection patterns found in different
   blueprints hash to the same canonical value, enabling cross-blueprint
   frequency analysis.
2. **Tier / orientation independence** — the canonicalisation step ensures
   that a 3-tile yellow-belt run and a 3-tile blue-belt run with the same
   topology are treated as different motifs (correct: they have different
   throughput), while the same run rotated 90° or mirrored hashes identically
   (correct: they are the same pattern in a different orientation).

### 2.2 Category Taxonomy

| Category | Criteria |
|---|---|
| `DIRECT` | No belt nodes in the motif; only an inserter edge from machine to machine. |
| `SIMPLE` | Has belt lane nodes; no splitter or underground edges; at most one inserter source. |
| `UNDERGROUND` | Has at least one `edge_type == "underground"` edge; no splitter edge. |
| `SPLIT` | Has at least one `edge_type == "splitter"` edge. |
| `MERGED` | Has belt nodes; two or more distinct belt lane nodes each receive an inserter edge (multiple machines feed one belt path). |

Classification is determined by `_classify_motif(subgraph)` in `extractor.py`.
`SPLIT` takes priority over `UNDERGROUND`; `DIRECT` takes priority over all
belt-based categories.

### 2.3 Canonical Entity Record

Each entity in a motif is reduced to a flat dict for hashing:

```
{
  "entity_type": str,   # vanilla entity name, e.g. "transport-belt"
  "x":           int,   # tile position relative to source machine anchor (0,0)
  "y":           int,   # tile position relative to source machine anchor (0,0)
  "direction":   int,   # Factorio direction 0/2/4/6 (N/E/S/W); 0 for non-directional entities
  "extra":       str,   # sorted comma-separated filter item names, or "" if none
}
```

**Direction encoding:** 0 = North, 2 = East, 4 = South, 6 = West.
Direction is set to 0 for entities that lack directional meaning (e.g.
assembling machines, chests, power poles).

**Directional entities** (those where direction affects the hash) are:
any entity with `belt_speed`, `inserter_reach`, or `underground_max_distance`
in the reference data, plus all splitter names.

### 2.4 Full Motif Record Schema

Fields present in the in-memory catalogue and the `Motif` database table:

```
canonical_hash        : str    — MD5 hex digest (32 chars); primary key in catalogue
canonical_entities    : list[CanonicalEntity]
                                — the entity list in the lexicographically minimal form
category              : str    — "DIRECT" | "SIMPLE" | "UNDERGROUND" | "SPLIT" | "MERGED"
occurrence_count      : int    — total appearances across all blueprints; starts at 1
belt_type             : str|None
                                — name of the first belt-lane entity found in the motif,
                                  e.g. "transport-belt"; null for DIRECT motifs
uses_underground      : bool   — true iff any edge has edge_type=="underground"
uses_splitter         : bool   — true iff any edge has edge_type=="splitter"
is_multi_destination  : bool   — true iff dest_machines has >1 entry
entity_count          : int    — number of nodes in the motif subgraph
source_recipes        : dict[str,int]
                                — map of recipe_name → occurrence count for the source machine
dest_recipes          : dict[str,int]
                                — map of recipe_name → occurrence count for destination machine(s)
first_seen_at         : ISO-8601 timestamp
example_blueprint_id  : UUID str
```

Extended fields (database only, computed in orchestrator):

```
family_hash           : str    — MD5 of tier-normalised entity list
                                  (belt/inserter variants collapsed to abstract types)
family_occurrence_count : int  — occurrence count across all motifs sharing this family_hash
elaboration_depth     : int    — int(uses_underground) + int(uses_splitter); 0 for base motifs
sub_motif_of_family   : str    — family_hash of the maximally simplified form;
                                  equals family_hash for base (DIRECT/SIMPLE) motifs
is_tileable           : bool   — true iff tileability detection found a dominant offset
tile_vector           : dict|None
                                — {"dx": float, "dy": float}; null if not tileable
tile_count            : int    — number of pairs sharing the dominant offset
is_sideloaded         : bool   — reserved; not yet computed (always False)
```

### 2.5 Invariants and Constraints

| Constraint | Rule |
|---|---|
| Unique hash | `canonical_hash` is unique per distinct physical motif pattern. |
| Anchor at origin | The source machine anchor is always translated to (0, 0) before hashing. |
| Rotation/mirror invariance | Rotating by any multiple of 90° or mirroring horizontally yields the same `canonical_hash`. |
| Entity uniqueness in canonical list | Each entity appears at most once; de-duplication is by `entity_number`. |
| Vanilla entities only | All `entity_type` values must be valid vanilla Factorio 1.1 entity names. |
| Minimal category | A motif with a splitter is always `SPLIT`, regardless of whether it also has underground edges. |
| Belt type consistency | `belt_type` is the tier of the first belt-lane entity found; a motif with mixed tiers stores only the first encountered. |
| family_hash reproducibility | `family_hash` must be reproducible from `canonical_entities` alone (no runtime state required). |
| elaboration_depth | Always equal to `int(uses_underground) + int(uses_splitter)`, range 0–2. |

---

## 3. Motif Lifecycle and Control Flow

### 3.1 End-to-End Flow

```
raw blueprint string
    │
    ▼  pipeline/decoder.py
decode() → list[dict]
    │
    ▼  pipeline/validator.py
validate() → BlueprintWrapper
    │
    ▼  analysis/motif/lane_model.py
build_lane_model() → nx.DiGraph   (lane graph)
    │
    ▼  analysis/motif/extractor.py
extract_motifs(lane_graph) → list[nx.DiGraph]   (motif subgraphs)
    │
    ├─ for each motif subgraph:
    │   ├─  analysis/motif/canonicaliser.py
    │   │   canonicalise(sg) → (canonical_hash, canonical_entities)
    │   │
    │   ├─  analysis/motif/family_hash.py
    │   │   compute_family_hash(canonical_entities) → family_hash
    │   │   compute_simplified_family_hash(canonical_entities) → sub_motif_of_family
    │   │
    │   └─  storage.save_motif(session, ...) → upserts Motif row + BlueprintMotif link
    │
    └─  analysis/motif/tileability.py
        compute_blueprint_tileability(motif_positions) → per-hash tileability
            │
            └─  storage.update_motif_tileability(session, ...) → patches Motif rows
```

### 3.2 Lane Graph Node / Edge Types

**Nodes:**

| Key form | node_type | Represents |
|---|---|---|
| `(x, y, "left")` | `"belt_lane"` | Left lane of a belt tile at position (x, y) |
| `(x, y, "right")` | `"belt_lane"` | Right lane of a belt tile at position (x, y) |
| `("machine", entity_number)` | `"machine"` | Assembling machine |
| `("chest", entity_number)` | `"chest"` or `"loader"` | Chest or loader |
| `("pole", entity_number)` | `"pole"` | Power pole |

**Edges:**

| `edge_type` | Source → Target | Extra attributes |
|---|---|---|
| `"belt_flow"` | lane node → adjacent lane node | — |
| `"underground"` | entrance lane node → exit lane node | — |
| `"splitter"` | input lane node → output lane node | `entity`, optional `filter_item` |
| `"inserter"` | machine/lane → machine/lane/chest | `inserter`, optional `filter_items` |

### 3.3 BFS Extraction Rules

1. Start from each `("machine", ...)` node.
2. Follow only outgoing `inserter` edges as the initial step from a machine.
3. From belt/lane nodes, follow all outgoing edges (`belt_flow`, `underground`, `splitter`, `inserter`).
4. Stop traversal when a `("machine", ...)` or `("chest", ...)` node is reached (it is added to the motif but not traversed further).
5. A motif is only emitted if `dest_machines` is non-empty, or a chest was reached.
6. After BFS, enrich by: (a) adding one step of backward belt predecessors (feeder belts), (b) adding power poles within a 3-tile margin around the bounding box.

### 3.4 Core Functions

| Function | Signature (pseudo) | Purpose |
|---|---|---|
| `build_lane_model` | `(blueprint) → nx.DiGraph` | Lane-level graph from a validated blueprint |
| `extract_motifs` | `(lane_graph: nx.DiGraph) → list[nx.DiGraph]` | BFS extraction; attaches `category`, `source_machine`, `dest_machines` graph attributes |
| `canonicalise` | `(motif_subgraph) → (str, list[dict])` | 8-transformation canonical hash + entity list |
| `compute_family_hash` | `(canonical_entities: list[dict]) → str` | Tier-normalised family hash |
| `compute_simplified_family_hash` | `(canonical_entities: list[dict]) → str` | Base-form family hash (no underground/splitter) |
| `detect_tileability` | `(positions: list[tuple]) → dict|None` | Dominant offset for one motif within one blueprint |
| `compute_blueprint_tileability` | `(motif_positions: dict) → dict` | Runs `detect_tileability` for all hashes in one blueprint |
| `catalogue.upsert` | `(hash, entities, category, metadata, blueprint_id) → None` | Insert or increment occurrence count |
| `storage.save_motif` | `(session, canonical_hash, ...) → None` | Upsert `Motif` row and add `BlueprintMotif` link |

---

## 4. Validation Rules and Quality Criteria

### 4.1 Structural Validity Rules

| # | Rule |
|---|---|
| V1 | `canonical_hash` is an MD5 hex string (exactly 32 lowercase hex characters). |
| V2 | `canonical_entities` is a non-empty list for all non-trivial motifs. |
| V3 | Every `entity_type` in `canonical_entities` is a known vanilla Factorio 1.1 entity name. |
| V4 | Every `direction` value in `canonical_entities` is one of `{0, 2, 4, 6}`. |
| V5 | Non-directional entities (machines, chests, poles) always have `direction == 0` in canonical form. |
| V6 | The source machine anchor must appear at position `(x=0, y=0)` in the canonical entity list (after translation). |
| V7 | No duplicate `(entity_type, x, y)` tuples in `canonical_entities` (enforced by `entity_number` deduplication). |
| V8 | `category` is one of `{"DIRECT", "SIMPLE", "UNDERGROUND", "SPLIT", "MERGED"}`. |
| V9 | `uses_underground == True` implies `"underground"` edge type present in the subgraph. |
| V10 | `uses_splitter == True` implies `"splitter"` edge type present in the subgraph AND `category == "SPLIT"`. |
| V11 | `is_multi_destination == True` implies `len(dest_machines) > 1`. |
| V12 | `elaboration_depth == int(uses_underground) + int(uses_splitter)`, range `[0, 2]`. |

### 4.2 Semantic / Quality Criteria

| # | Criterion |
|---|---|
| Q1 | **Rotation invariance** — rotating all entity positions/directions by 90° CW and re-canonicalising must produce the same `canonical_hash`. |
| Q2 | **Mirror invariance** — mirroring all positions on the X axis (negating x) and adjusting directions must produce the same `canonical_hash`. |
| Q3 | **Tier sensitivity** — swapping `transport-belt` for `fast-transport-belt` must produce a different `canonical_hash` but the same `family_hash`. |
| Q4 | **Run-length sensitivity** — a 3-tile belt run and a 5-tile belt run must produce different `canonical_hash` AND different `family_hash`. |
| Q5 | **Source anchor** — the source machine entity must always be represented at position `(0, 0)` in `canonical_entities`; all other positions are relative offsets. |
| Q6 | **Splitter priority** — a motif containing a splitter edge must be classified `SPLIT` even if it also contains an underground edge. |
| Q7 | **Filter fidelity** — the `extra` field of a filter-inserter entity must contain the sorted, comma-separated item name(s) from its `filters`; two inserters filtering different items must produce different `canonical_hash` values. |
| Q8 | **family_hash abstraction** — `compute_family_hash` on the canonical entities of a yellow-belt motif and a red-belt motif with identical topology must return equal values. |
| Q9 | **sub_motif_of_family** — for a SPLIT or UNDERGROUND motif, `sub_motif_of_family` must equal the `family_hash` of the equivalent SIMPLE/DIRECT motif (underground and splitter entities replaced with plain belts). |
| Q10 | **Empty motif handling** — if `canonical_entities` is empty, `canonical_hash` must equal `md5(b"empty").hexdigest()`. |

### 4.3 Implicit Assumptions (not formally validated)

- Positions are integer tile coordinates.  Sub-tile offsets are snapped via
  `_snap(v) = floor(v + 0.5)` at lane-model construction time.
- A motif contains exactly one source machine.  Multi-source topologies
  (MERGED) are captured by having multiple inserter edges entering the same
  belt lane node, but the BFS starts from one machine at a time.
- Power poles are included in the motif subgraph (and thus the canonical
  entity list) for completeness, even though they do not affect item flow.
  They contribute to the canonical hash.
- Splitter entities live on edge attributes, not node attributes, in the lane
  graph.  `_extract_entities_from_motif` handles this by scanning edge data
  for `edge_type == "splitter"`.

---

## 5. Failure Modes and Edge Cases

| Failure | Where handled | Notes |
|---|---|---|
| Empty motif (no entities reach a destination) | `extractor.py` — motif is discarded if `dest_machines` is empty and no chest was reached. | Produces no output; not logged. |
| All-empty entity list after extraction | `canonicaliser.py` — returns `(md5(b"empty"), [])`. | Downstream callers still receive a valid hash. |
| Duplicate entity numbers in subgraph | `canonicaliser.py` — `seen` set deduplicates by `entity_number`. | Can occur when multiple lane nodes share the same underlying entity (e.g. splitter). |
| Splitter entity on edge (not node) | `canonicaliser.py` — second pass over `edge_data` for `edge_type == "splitter"`. | Required because splitters are stored as edge attributes in the lane graph. |
| Mismatched underground pairs (no valid exit) | `lane_model.py` — entrance nodes are added to the graph with no underground edge; no crash. | Produces dangling lane nodes that BFS will follow to dead ends. |
| Blueprint with no machines | `extractor.py` — `machine_nodes` is empty; returns `[]`. | No motifs emitted; not an error. |
| Non-directional entity with non-zero direction | `canonicaliser.py` — direction forced to 0 before hashing. | Prevents spurious hash differences for entities like assembling machines. |
| Mixed belt tiers in one motif | `orchestrator.py` — `belt_type` captures only the first belt entity found. | Not a correctness issue; `family_hash` captures tier-independent grouping. |
| Very large blueprints (>500 entities) | No hard limit in extraction; BFS is linear in graph size. | The `/v1/analysis/search` endpoint enforces a 500-entity cap at the API level. |
| save_motif exception | `orchestrator.py` — caught per-motif, appended to `result.errors`, pipeline continues. | Partial motif saves are possible within one blueprint. |
| Circular belt loops | BFS uses a `visited` set; does not re-visit nodes. | Loops are traversed once; no infinite loop. |
| `is_sideloaded` flag | `storage/models.py` — column exists; not yet computed anywhere. | Always `False` in current data. |

---

## 6. Concrete Motif Examples

### 6.1 DIRECT Motif

```
canonical_entities:
  - {entity_type: "assembling-machine-1", x: 0, y: 0, direction: 0, extra: ""}
  - {entity_type: "inserter",             x: 2, y: 0, direction: 2, extra: ""}
  - {entity_type: "assembling-machine-1", x: 4, y: 0, direction: 0, extra: ""}

category:              "DIRECT"
uses_underground:      false
uses_splitter:         false
is_multi_destination:  false
entity_count:          3
```

**Why valid:** No belt-lane nodes appear in the subgraph.  The only non-machine
entity is an inserter spanning the two machines.  The source machine is
translated to (0, 0).  Direction 0 for assembling machines (non-directional).

---

### 6.2 SIMPLE Motif (3-tile belt run)

```
canonical_entities:
  - {entity_type: "assembling-machine-1", x:  0, y: 0, direction: 0, extra: ""}
  - {entity_type: "inserter",             x:  2, y: 0, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  3, y: 0, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  4, y: 0, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  5, y: 0, direction: 2, extra: ""}
  - {entity_type: "inserter",             x:  6, y: 0, direction: 2, extra: ""}
  - {entity_type: "assembling-machine-1", x:  8, y: 0, direction: 0, extra: ""}

category:         "SIMPLE"
belt_type:        "transport-belt"
entity_count:     7
```

**Why valid:** Belt-lane nodes are present; no splitter or underground edges.
The topology is a linear inserter → belt tiles → inserter chain.  Three belt
tiles at relative x = 3, 4, 5 encode the exact run length in the canonical
hash (a 5-tile run would hash differently).

---

### 6.3 UNDERGROUND Motif

```
canonical_entities:
  - {entity_type: "assembling-machine-1",   x:  0, y: 0, direction: 0, extra: ""}
  - {entity_type: "inserter",                x:  2, y: 0, direction: 2, extra: ""}
  - {entity_type: "underground-belt",        x:  3, y: 0, direction: 2, extra: ""}
  - {entity_type: "underground-belt",        x:  7, y: 0, direction: 2, extra: ""}
  - {entity_type: "inserter",                x:  8, y: 0, direction: 2, extra: ""}
  - {entity_type: "assembling-machine-1",    x: 10, y: 0, direction: 0, extra: ""}

category:           "UNDERGROUND"
uses_underground:   true
uses_splitter:      false
entity_count:       6
```

**Why valid:** An `"underground"` edge connects the entrance node at (3,0) to
the exit node at (7,0), skipping 3 internal tiles.  Category is `UNDERGROUND`
(no splitter edge present).  `elaboration_depth == 1`.

---

### 6.4 SPLIT Motif (1-to-2 splitter)

```
canonical_entities:
  - {entity_type: "assembling-machine-1", x:  0, y:  0, direction: 0, extra: ""}
  - {entity_type: "inserter",             x:  2, y:  0, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  3, y:  0, direction: 2, extra: ""}
  - {entity_type: "splitter",             x:  4, y: -1, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  5, y:  0, direction: 2, extra: ""}
  - {entity_type: "transport-belt",       x:  5, y: -1, direction: 2, extra: ""}
  - {entity_type: "inserter",             x:  6, y:  0, direction: 2, extra: ""}
  - {entity_type: "inserter",             x:  6, y: -1, direction: 2, extra: ""}
  - {entity_type: "assembling-machine-1", x:  8, y:  0, direction: 0, extra: ""}
  - {entity_type: "assembling-machine-1", x:  8, y: -2, direction: 0, extra: ""}

category:              "SPLIT"
uses_splitter:         true
is_multi_destination:  true
entity_count:          10
elaboration_depth:     1
```

**Why valid:** A `"splitter"` edge is present in the subgraph, making
`category == "SPLIT"`.  Two destination machines are reached, so
`is_multi_destination == true`.  `elaboration_depth == 1` (splitter present,
no underground).

---

### 6.5 Filter-Inserter Motif (extra field non-empty)

```
canonical_entities:
  - {entity_type: "assembling-machine-2",  x: 0, y: 0, direction: 0, extra: ""}
  - {entity_type: "filter-inserter",        x: 2, y: 0, direction: 2,
     extra: "iron-plate"}
  - {entity_type: "assembling-machine-2",  x: 4, y: 0, direction: 0, extra: ""}

category:         "DIRECT"
entity_count:     3
```

**Why valid:** The filter inserter's `filters` list contains `{"name": "iron-plate"}`,
which is serialised as `extra = "iron-plate"` (sorted comma-separated).  A
second motif with `extra = "copper-plate"` would produce a different
`canonical_hash`, correctly distinguishing the two filter configurations.

---

## 7. Reusable Motif Specification for Other LLMs

### 7.1 Short Definition

A motif is an immutable, orientation-normalised, tier-specific connection
pattern between one source assembling machine and one or more destination
machines (or chests) in a Factorio 1.1 vanilla blueprint.  It is identified
by an MD5 canonical hash that is invariant under rotation (90°, 180°, 270°)
and horizontal mirroring.

### 7.2 Required Fields

| Field | Type | Semantics |
|---|---|---|
| `canonical_hash` | `str` (32-char hex) | Unique identifier; must reproduce from `canonical_entities` alone. |
| `canonical_entities` | `list[dict]` | One dict per entity; must contain `entity_type`, `x`, `y`, `direction`, `extra`. |
| `category` | `str` | One of `DIRECT`, `SIMPLE`, `UNDERGROUND`, `SPLIT`, `MERGED`. |
| `occurrence_count` | `int ≥ 1` | How many times this canonical pattern has been seen. |
| `uses_underground` | `bool` | True iff an underground edge is present. |
| `uses_splitter` | `bool` | True iff a splitter edge is present. |
| `entity_count` | `int ≥ 1` | Number of nodes in the motif subgraph. |

### 7.3 Optional Fields

| Field | Type | Semantics |
|---|---|---|
| `belt_type` | `str` or `null` | First belt-tier entity name found; null for DIRECT motifs. |
| `is_multi_destination` | `bool` | More than one destination machine. |
| `source_recipes` | `dict[str,int]` or `null` | Recipes running on the source machine. |
| `dest_recipes` | `dict[str,int]` or `null` | Recipes running on destination machine(s). |
| `first_seen_at` | ISO-8601 `str` | Timestamp of first insertion. |
| `example_blueprint_id` | UUID `str` | Blueprint where first seen. |
| `family_hash` | `str` (32-char hex) | Tier-normalised hash; shared across all belt tiers with same topology. |
| `elaboration_depth` | `int` 0–2 | `int(uses_underground) + int(uses_splitter)`. |
| `sub_motif_of_family` | `str\|null` | `family_hash` of the base form; equals `family_hash` for base motifs. |
| `is_tileable` | `bool` | Repeats with a consistent spatial offset within a blueprint. |
| `tile_vector` | `{"dx":float,"dy":float}\|null` | Dominant offset vector; null if not tileable. |
| `tile_count` | `int` | Number of pairs sharing the dominant offset. |

### 7.4 Structural Constraints (machine-checkable)

```
canonical_hash length == 32
all(c in "0123456789abcdef" for c in canonical_hash)
category in {"DIRECT", "SIMPLE", "UNDERGROUND", "SPLIT", "MERGED"}
occurrence_count >= 1
entity_count >= 1
len(canonical_entities) >= 1  OR  canonical_hash == md5(b"empty").hexdigest()
all(e["direction"] in {0,2,4,6} for e in canonical_entities)
uses_splitter == True  =>  category == "SPLIT"
uses_underground == True  =>  category in {"UNDERGROUND", "SPLIT"}
elaboration_depth == int(uses_underground) + int(uses_splitter)
tile_vector is null  OR  ("dx" in tile_vector AND "dy" in tile_vector)
```

### 7.5 Semantic Constraints

```
# Rotation invariance
canonicalise(rotate_90cw(motif)) == canonicalise(motif)

# Mirror invariance
canonicalise(mirror_x(motif)) == canonicalise(motif)

# Tier sensitivity: different belt tier → different canonical_hash
canonical_hash("transport-belt run") != canonical_hash("fast-transport-belt run")

# Family invariance across tiers
family_hash("transport-belt run") == family_hash("fast-transport-belt run")

# Run-length sensitivity
canonical_hash("3-tile run") != canonical_hash("5-tile run")
family_hash("3-tile run") != family_hash("5-tile run")

# Filter sensitivity
extra("filter-inserter", filters=["iron-plate"]) != extra("filter-inserter", filters=["copper-plate"])
```

### 7.6 Direction Transformation Rules

```
# Rotation 90° clockwise (Factorio direction convention)
rotate_pos_90cw(x, y)       = (y, -x)
rotate_direction_90cw(d)    = (d + 2) % 8

# Horizontal mirror
mirror_pos(x, y)            = (-x, y)
mirror_direction(d):
    0 → 0  (North ↔ North)
    2 → 6  (East  ↔ West)
    4 → 4  (South ↔ South)
    6 → 2  (West  ↔ East)

# Direction is only transformed for directional entities (belts, inserters, splitters,
# underground belts); all others keep direction = 0.
```

### 7.7 Worked Validation Examples

#### Example A — Valid SIMPLE motif

```json
{
  "canonical_hash": "a1b2c3d4e5f6...",
  "canonical_entities": [
    {"entity_type": "assembling-machine-1", "x": 0, "y": 0, "direction": 0, "extra": ""},
    {"entity_type": "inserter",             "x": 2, "y": 0, "direction": 2, "extra": ""},
    {"entity_type": "transport-belt",       "x": 3, "y": 0, "direction": 2, "extra": ""},
    {"entity_type": "inserter",             "x": 4, "y": 0, "direction": 2, "extra": ""},
    {"entity_type": "assembling-machine-1", "x": 6, "y": 0, "direction": 0, "extra": ""}
  ],
  "category": "SIMPLE",
  "uses_underground": false,
  "uses_splitter": false,
  "entity_count": 5
}
```

**Verdict: Valid.**  Belt-lane nodes present (transport-belt tile); no
underground or splitter edges; category is `SIMPLE`.  Source machine at (0, 0)
(V6 ✓).  All directions in {0, 2, 4, 6} (V4 ✓).  Non-directional entities
have direction 0 (V5 ✓).

---

#### Example B — Invalid: splitter present but category is UNDERGROUND

```json
{
  "category": "UNDERGROUND",
  "uses_splitter": true,
  ...
}
```

**Verdict: Invalid.**  Rule V10 states that `uses_splitter == True` implies
`category == "SPLIT"`.  A motif with a splitter must always be classified
`SPLIT`; the classification algorithm gives splitter-presence priority over
underground-presence.

---

#### Example C — Invalid: non-directional entity with non-zero direction

```json
{
  "canonical_entities": [
    {"entity_type": "assembling-machine-2", "x": 0, "y": 0, "direction": 4, "extra": ""}
  ],
  ...
}
```

**Verdict: Invalid.**  Rule V5 states that non-directional entities
(assembling machines, chests, power poles) must have `direction == 0` in
canonical form.  The canonicaliser forces `direction = 0` for these entities
before hashing, so any record storing a non-zero direction here was not
produced by the canonical pipeline.
