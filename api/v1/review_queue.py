"""Review queue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

import storage
from api.dependencies import RATE_LIMIT, envelope, get_db, limiter, paginate
from api.v1.schemas import ReviewQueueItemResponse

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


class ResolveRequest(BaseModel):
    resolution: str


@router.get("")
@limiter.limit(RATE_LIMIT)
def list_review_queue(
    request: Request,
    pagination: dict = Depends(paginate),
    db: Session = Depends(get_db),
):
    """List unresolved review queue items."""
    items, total = storage.list_review_queue(
        db, resolved=False, offset=pagination["offset"], limit=pagination["limit"],
    )
    data = [ReviewQueueItemResponse.model_validate(item).model_dump() for item in items]
    return envelope(data, total=total, page=pagination["page"], per_page=pagination["per_page"])


@router.post("/{item_id}")
@limiter.limit(RATE_LIMIT)
def resolve_review_item(
    request: Request,
    item_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
):
    """Submit a resolution for a review queue item."""
    try:
        item = storage.resolve_review_item(db, item_id, body.resolution)
    except KeyError:
        raise HTTPException(status_code=404, detail="Review queue item not found")
    data = ReviewQueueItemResponse.model_validate(item).model_dump()
    return envelope(data)
