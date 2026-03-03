"""V1 router aggregation."""

from fastapi import APIRouter

from api.v1.blueprints import router as blueprints_router
from api.v1.motifs import router as motifs_router
from api.v1.recipes import router as recipes_router
from api.v1.analysis import router as analysis_router
from api.v1.review_queue import router as review_queue_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(blueprints_router)
v1_router.include_router(motifs_router)
v1_router.include_router(recipes_router)
v1_router.include_router(analysis_router)
v1_router.include_router(review_queue_router)
