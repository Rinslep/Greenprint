# api/main.py
#
# TODO: FastAPI application entry point.
#
# Setup:
# - Create the FastAPI app instance with title, version, and description.
# - Mount the v1 router from api/v1/ under the prefix '/v1'.
# - Add SlowAPI rate limiting middleware (per-IP, limit from config.API_RATE_LIMIT_PER_MINUTE).
# - Add a startup event to call storage.database.init_db() in dev mode only.
# - Add a global exception handler that wraps unhandled errors in the standard response envelope.
#
# Standard response envelope (all responses, including errors):
#   {
#     "data": { ... } | null,
#     "meta": { "total": int, "page": int, "per_page": int } | null,
#     "warnings": ["FLAG_NAME", ...],
#     "error": "message" | null
#   }
# Flags are ALWAYS included in responses — never silently hidden.
#
# Running: uvicorn api.main:app --reload


from fastapi import FastAPI

app = FastAPI(title="Greenprint — Factorio Blueprint Analyser", version="0.1.0")

# TODO: include v1 router
# TODO: add rate limiting middleware
# TODO: add startup/shutdown events
# TODO: add global exception handler
