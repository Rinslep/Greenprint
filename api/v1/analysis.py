"""Cross-blueprint analysis, search, and stats endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import storage
from api.dependencies import RATE_LIMIT, envelope, get_db, limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


class CompareRequest(BaseModel):
    blueprint_ids: list[str] = Field(..., max_length=20)


class SearchRequest(BaseModel):
    blueprint_string: str


@router.post("/analysis/compare")
@limiter.limit(RATE_LIMIT)
def compare_blueprints(request: Request, body: CompareRequest, db: Session = Depends(get_db)):
    """Side-by-side comparison of up to 20 blueprints."""
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
@limiter.limit(RATE_LIMIT)
def search_similar(request: Request, body: SearchRequest, db: Session = Depends(get_db)):
    """Decode a blueprint string on-the-fly and find similar stored blueprints by motif overlap.

    Uses Jaccard similarity over canonical motif hash sets. Pre-filters candidates via a
    shared-hash JOIN before computing full scores. Returns 503 if no blueprints are ingested.
    """
    from analysis.motif.canonicaliser import canonicalise
    from analysis.motif.extractor import extract_motifs
    from analysis.motif.lane_model import build_lane_model
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

    entities = decoded.get("blueprint", {}).get("entities", [])
    if len(entities) > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Blueprint has {len(entities)} entities (max 500 for search)",
        )

    # Extract canonical motif hashes from the query blueprint
    query_hashes: set[str] = set()
    try:
        lane_graph = build_lane_model(decoded)
        motif_subgraphs = extract_motifs(lane_graph)
        for sg in motif_subgraphs:
            hash_, _ = canonicalise(sg)
            if hash_:
                query_hashes.add(hash_)
    except Exception as exc:
        logger.warning("search_motif_extraction_failed: %s", exc, exc_info=True)
        # query_hashes stays empty — all candidates will score 0

    # Readiness check — 503 if no motif data in the index
    if not query_hashes:
        # No query hashes: either empty blueprint or extraction failed — return 503 only
        # if the index is also empty, else return empty results.
        _, bp_total = storage.list_blueprints(db, limit=0)
        if bp_total == 0:
            raise HTTPException(
                status_code=503,
                detail="Motif index not yet populated. Ingest blueprints first.",
            )
        return envelope([])

    # Pre-filter: only blueprints sharing at least one motif hash with the query
    candidate_ids = storage.get_candidate_blueprint_ids(db, query_hashes, limit=200)
    if not candidate_ids:
        return envelope([])

    hash_sets = storage.get_blueprint_motif_hashes_for_ids(db, candidate_ids)

    # Compute Jaccard similarity for each candidate
    similarities = []
    for bp_id, stored_hashes in hash_sets.items():
        if not stored_hashes:
            continue
        intersection = len(query_hashes & stored_hashes)
        union = len(query_hashes | stored_hashes)
        score = intersection / union if union > 0 else 0.0
        if score > 0:
            similarities.append({"id": bp_id, "score": round(score, 4)})

    similarities.sort(key=lambda x: x["score"], reverse=True)
    return envelope(similarities[:20])


@router.get("/analysis/stats")
@limiter.limit(RATE_LIMIT)
def dataset_stats(request: Request, db: Session = Depends(get_db)):
    """Dataset-level aggregate statistics."""
    _, bp_total = storage.list_blueprints(db, limit=0)
    _, motif_total = storage.list_motifs(db, limit=0)
    _, review_total = storage.list_review_queue(db)

    by_site = storage.count_blueprints_by_source_site(db)
    flag_dist = storage.count_flag_distribution(db)

    data = {
        "total_blueprints": bp_total,
        "total_motifs": motif_total,
        "unresolved_reviews": review_total,
        "blueprints_by_source_site": by_site,
        "flag_distribution": flag_dist,
    }
    return envelope(data)
