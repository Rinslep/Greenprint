"""Review queue endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import storage
from api.dependencies import envelope, get_db, paginate
from api.v1.schemas import ReviewQueueItemResponse

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


class ResolveRequest(BaseModel):
    resolution: str


@router.get("")
def list_review_queue(
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
def resolve_review_item(
    item_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
):
    """Submit a resolution for a review queue item."""
    try:
        item = storage.resolve_review_item(db, item_id, body.resolution)
        db.commit()
    except KeyError:
        raise HTTPException(status_code=404, detail="Review queue item not found")
    data = ReviewQueueItemResponse.model_validate(item).model_dump()
    return envelope(data)
