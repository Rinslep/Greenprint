"""Motif catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import storage
from api.dependencies import RATE_LIMIT, envelope, get_db, limiter, paginate, parse_filter_string
from api.v1.schemas import BlueprintSummaryResponse, MotifDetailResponse, MotifSummaryResponse

router = APIRouter(prefix="/motifs", tags=["motifs"])


@router.get("")
@limiter.limit(RATE_LIMIT)
def list_motifs(
    request: Request,
    filters: dict = Depends(parse_filter_string),
    pagination: dict = Depends(paginate),
    db: Session = Depends(get_db),
):
    """List motifs with optional filters and pagination."""
    motifs, total = storage.list_motifs(
        db, filters=filters, offset=pagination["offset"], limit=pagination["limit"],
    )
    data = [MotifSummaryResponse.model_validate(m).model_dump() for m in motifs]
    return envelope(data, total=total, page=pagination["page"], per_page=pagination["per_page"])


@router.get("/{motif_id}")
@limiter.limit(RATE_LIMIT)
def get_motif(request: Request, motif_id: str, db: Session = Depends(get_db)):
    """Get full motif by ID."""
    motif = storage.get_motif(db, motif_id)
    if motif is None:
        raise HTTPException(status_code=404, detail="Motif not found")
    data = MotifDetailResponse.model_validate(motif).model_dump()
    return envelope(data)


@router.get("/{motif_id}/blueprints")
@limiter.limit(RATE_LIMIT)
def get_motif_blueprints(
    request: Request,
    motif_id: str,
    pagination: dict = Depends(paginate),
    db: Session = Depends(get_db),
):
    """Get blueprints that contain a given motif."""
    motif = storage.get_motif(db, motif_id)
    if motif is None:
        raise HTTPException(status_code=404, detail="Motif not found")
    bps = storage.get_blueprints_for_motif(db, motif_id)
    total = len(bps)
    start = pagination["offset"]
    end = start + pagination["limit"]
    page_bps = bps[start:end]
    data = [BlueprintSummaryResponse.model_validate(bp).model_dump() for bp in page_bps]
    return envelope(data, total=total, page=pagination["page"], per_page=pagination["per_page"])
