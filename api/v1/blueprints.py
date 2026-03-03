"""Blueprint collection and detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import storage
from api.dependencies import envelope, get_db, paginate, parse_filter_string
from api.v1.schemas import BlueprintDetailResponse, BlueprintSummaryResponse

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("")
def list_blueprints(
    filters: dict = Depends(parse_filter_string),
    pagination: dict = Depends(paginate),
    db: Session = Depends(get_db),
):
    """List blueprints with optional filters and pagination."""
    bps, total = storage.list_blueprints(
        db, filters=filters, offset=pagination["offset"], limit=pagination["limit"],
    )
    data = [BlueprintSummaryResponse.model_validate(bp).model_dump() for bp in bps]
    return envelope(data, total=total, page=pagination["page"], per_page=pagination["per_page"])


@router.get("/{blueprint_id}")
def get_blueprint(blueprint_id: str, db: Session = Depends(get_db)):
    """Get full blueprint by ID."""
    bp = storage.get_blueprint(db, blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    data = BlueprintDetailResponse.model_validate(bp).model_dump()
    warnings = [f["flag"] for f in (bp.flags or [])]
    return envelope(data, warnings=warnings)


@router.get("/{blueprint_id}/graph")
def get_blueprint_graph(blueprint_id: str, db: Session = Depends(get_db)):
    """Get crafting graph for a blueprint."""
    bp = storage.get_blueprint(db, blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    summary = bp.summary or {}
    graph = summary.get("crafting_graph", {})
    warnings = [f["flag"] for f in (bp.flags or [])]
    return envelope(graph, warnings=warnings)


@router.get("/{blueprint_id}/ratios")
def get_blueprint_ratios(blueprint_id: str, db: Session = Depends(get_db)):
    """Get ratio analysis for a blueprint."""
    bp = storage.get_blueprint(db, blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    summary = bp.summary or {}
    ratios = summary.get("ratios", {})
    warnings = [f["flag"] for f in (bp.flags or [])]
    return envelope(ratios, warnings=warnings)


@router.get("/{blueprint_id}/throughput")
def get_blueprint_throughput(blueprint_id: str, db: Session = Depends(get_db)):
    """Get throughput analysis for a blueprint."""
    bp = storage.get_blueprint(db, blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    summary = bp.summary or {}
    throughput = summary.get("throughput", {})
    warnings = [f["flag"] for f in (bp.flags or [])]
    return envelope(throughput, warnings=warnings)


@router.get("/{blueprint_id}/motifs")
def get_blueprint_motifs(blueprint_id: str, db: Session = Depends(get_db)):
    """Get motifs found in a blueprint."""
    bp = storage.get_blueprint(db, blueprint_id)
    if bp is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    motif_links = bp.motifs or []
    data = []
    for link in motif_links:
        motif = link.motif
        data.append({
            "motif_id": motif.id,
            "canonical_hash": motif.canonical_hash,
            "category": motif.category,
            "entity_count": motif.entity_count,
            "position_context": link.position_context,
        })
    warnings = [f["flag"] for f in (bp.flags or [])]
    return envelope(data, warnings=warnings)
