"""Shared FastAPI dependencies used across all route handlers."""

from typing import Generator

from fastapi import Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from config import settings
from storage.database import get_session as _get_session

# Single shared limiter instance — imported by main.py and all route files.
limiter = Limiter(key_func=get_remote_address)
RATE_LIMIT = f"{settings.api_rate_limit_per_minute}/minute"


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the duration of a request."""
    with _get_session() as session:
        yield session


def parse_filter_string(filter: str | None = Query(None)) -> dict:
    """Parse ``?filter=key:value,key:op:value`` into a structured dict.

    Supported operators: exact match (no op), ``>``, ``<``, ``>=``, ``<=``.
    Example:
        ``final_product:electronic-circuit,efficiency:>0.9,flag:INFERRED_RECIPE``
        → ``{"final_product": "electronic-circuit", "efficiency": (">", 0.9), "flag": "INFERRED_RECIPE"}``
    """
    if not filter:
        return {}

    result: dict = {}
    for part in filter.split(","):
        part = part.strip()
        if not part:
            continue
        tokens = part.split(":", maxsplit=2)
        if len(tokens) == 2:
            key, value = tokens
            # Check for operator prefix in value
            for op in (">=", "<=", ">", "<"):
                if value.startswith(op):
                    try:
                        result[key] = (op, float(value[len(op):]))
                    except ValueError:
                        result[key] = value
                    break
            else:
                # Bool coercion
                if value.lower() in ("true", "false"):
                    result[key] = value.lower() == "true"
                else:
                    result[key] = value
        elif len(tokens) == 3:
            key, op, value = tokens
            try:
                result[key] = (op, float(value))
            except ValueError:
                result[key] = value
    return result


def paginate(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """Parse pagination query params and return offset/limit plus meta dict."""
    offset = (page - 1) * per_page
    return {
        "offset": offset,
        "limit": per_page,
        "page": page,
        "per_page": per_page,
    }


def envelope(
    data,
    total: int | None = None,
    page: int | None = None,
    per_page: int | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> dict:
    """Build the standard response envelope."""
    resp: dict = {"data": data}
    if total is not None:
        resp["meta"] = {
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    else:
        resp["meta"] = None
    resp["warnings"] = warnings or []
    resp["error"] = error
    return resp
