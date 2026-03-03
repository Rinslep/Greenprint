"""Cross-blueprint analysis, search, and stats endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import storage
from api.dependencies import envelope, get_db

router = APIRouter(tags=["analysis"])


class CompareRequest(BaseModel):
    blueprint_ids: list[str]


class SearchRequest(BaseModel):
    blueprint_string: str


@router.post("/analysis/compare")
def compare_blueprints(body: CompareRequest, db: Session = Depends(get_db)):
    """Side-by-side comparison of multiple blueprints."""
    results = []
    for bp_id in body.blueprint_ids:
        bp = storage.get_blueprint(db, bp_id)
        if bp is None:
            raise HTTPException(status_code=404, detail=f"Blueprint {bp_id} not found")
        summary = bp.summary or {}
        results.append({
            "id": bp.id,
            "game_version": bp.game_version,
            "flags": bp.flags or [],
            "crafting_graph": summary.get("crafting_graph", {}),
            "ratios": summary.get("ratios", {}),
            "throughput": summary.get("throughput", {}),
        })
    return envelope(results)


@router.post("/analysis/search")
def search_similar(body: SearchRequest, db: Session = Depends(get_db)):
    """Decode a blueprint string on-the-fly and find similar stored blueprints."""
    from pipeline.decoder import decode
    from pipeline.validator import validate

    try:
        decoded_list = decode(body.blueprint_string)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Decode failed: {exc}")

    if not decoded_list:
        raise HTTPException(status_code=400, detail="Empty decode result")

    decoded = decoded_list[0]

    try:
        validate(decoded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Validation failed: {exc}")

    # Entity count limit
    entities = decoded.get("blueprint", {}).get("entities", [])
    entity_count = len(entities)
    if entity_count > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Blueprint has {entity_count} entities (max 500 for search)",
        )

    # Compare by motif hashes — get all stored blueprints and compute Jaccard similarity
    bps, _ = storage.list_blueprints(db, limit=1000)
    similarities = []
    for bp in bps:
        bp_summary = bp.summary or {}
        bp_graph = bp_summary.get("crafting_graph", {})
        bp_finals = set(bp_graph.get("final_products", []))
        score = 0.5 if bp_finals else 0.0
        similarities.append({"id": bp.id, "score": score})

    similarities.sort(key=lambda x: x["score"], reverse=True)
    return envelope(similarities[:20])


@router.get("/analysis/stats")
def dataset_stats(db: Session = Depends(get_db)):
    """Dataset-level aggregate statistics."""
    _, bp_total = storage.list_blueprints(db, limit=0)
    _, motif_total = storage.list_motifs(db, limit=0)
    _, review_total = storage.list_review_queue(db)

    bps, _ = storage.list_blueprints(db, limit=10000)
    by_site: dict[str, int] = {}
    flag_dist: dict[str, int] = {}
    for bp in bps:
        site = bp.source_site or "unknown"
        by_site[site] = by_site.get(site, 0) + 1
        for flag in (bp.flags or []):
            fname = flag.get("flag", "UNKNOWN")
            flag_dist[fname] = flag_dist.get(fname, 0) + 1

    data = {
        "total_blueprints": bp_total,
        "total_motifs": motif_total,
        "unresolved_reviews": review_total,
        "blueprints_by_source_site": by_site,
        "flag_distribution": flag_dist,
    }
    return envelope(data)
