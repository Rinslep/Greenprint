# api/v1/recipes.py
#
# TODO: Reference recipe data endpoints (read-only, served from reference/recipes.json).
#
# Endpoints:
#
# GET /v1/recipes
#   - Accepts: ?filter=..., ?page=, ?per_page=
#   - Filter fields: category, valid_machine (entity name), input_item, output_item.
#   - Returns: paginated list of recipe objects from the reference dataset.
#   - This endpoint reads from reference/recipes.json (cached at startup) — NOT the DB.
#
# GET /v1/recipes/{name}
#   - Returns: a single recipe by its internal name.
#   - 404 if the name is not in the vanilla 1.1 reference set.
#   - Useful for API consumers looking up crafting details.
#
# Note: this data never changes between requests (it's the static reference set).
# Cache the loaded recipes in memory at startup — do not re-read the file per request.


from fastapi import APIRouter

router = APIRouter(prefix="/recipes", tags=["recipes"])

# TODO: implement all route handlers
