"""Reference recipe data endpoints (read-only, from reference/recipes.json)."""

import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import RATE_LIMIT, envelope, limiter, paginate
from config import REFERENCE_DIR

router = APIRouter(prefix="/recipes", tags=["recipes"])


@lru_cache(maxsize=1)
def _load_recipes() -> tuple:
    """Load and cache recipes from the reference JSON file."""
    path = REFERENCE_DIR / "recipes.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Return as tuple for lru_cache hashability
    return tuple(data) if isinstance(data, list) else (data,)


def _get_recipes_list() -> list[dict]:
    return list(_load_recipes())


@lru_cache(maxsize=1)
def _recipes_by_name() -> dict:
    """Build a name->recipe lookup dict."""
    return {r["name"]: r for r in _load_recipes()}


@router.get("")
@limiter.limit(RATE_LIMIT)
def list_recipes(
    request: Request,
    pagination: dict = Depends(paginate),
):
    """List recipes from the reference dataset."""
    all_recipes = _get_recipes_list()
    total = len(all_recipes)
    start = pagination["offset"]
    end = start + pagination["limit"]
    page = all_recipes[start:end]
    return envelope(page, total=total, page=pagination["page"], per_page=pagination["per_page"])


@router.get("/{name}")
@limiter.limit(RATE_LIMIT)
def get_recipe(request: Request, name: str):
    """Get a single recipe by name."""
    lookup = _recipes_by_name()
    recipe = lookup.get(name)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")
    return envelope(recipe)
