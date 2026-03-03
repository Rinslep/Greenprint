"""In-memory review queue with JSON file persistence.

Stores cases where recipe inference was unresolvable. Each queue item
corresponds to a specific machine (entity_number) within a specific blueprint.

Persistence: on every mutation, the full queue is written to data/review_queue.json.
On module load, existing data is restored from that file if present.
This is a temporary measure — replaced by the database in Step 13.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PERSIST_PATH = Path(__file__).resolve().parent.parent / "data" / "review_queue.json"

_queue: list[dict] = []


def _load_from_disk() -> None:
    """Load queue from disk if the persistence file exists."""
    global _queue
    if _PERSIST_PATH.exists():
        _queue = json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))


def _save_to_disk() -> None:
    """Write the full queue to disk."""
    _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PERSIST_PATH.write_text(
        json.dumps(_queue, indent=2, default=str) + "\n", encoding="utf-8"
    )


def add(blueprint_id: str, entity_number: int, context: dict) -> None:
    """Insert a new unresolved review item."""
    item = {
        "id": str(uuid.uuid4()),
        "blueprint_id": blueprint_id,
        "entity_number": entity_number,
        "context": context,
        "resolved": False,
        "resolution": None,
        "resolved_at": None,
    }
    _queue.append(item)
    _save_to_disk()


def list_unresolved() -> list[dict]:
    """Return all items where resolved is False."""
    return [item for item in _queue if not item["resolved"]]


def resolve(item_id: str, resolution: str) -> None:
    """Mark an item as resolved with the given resolution."""
    for item in _queue:
        if item["id"] == item_id:
            item["resolved"] = True
            item["resolution"] = resolution
            item["resolved_at"] = datetime.now(timezone.utc).isoformat()
            _save_to_disk()
            return
    raise KeyError(f"Review queue item not found: {item_id}")


def clear() -> None:
    """Clear the queue (for testing)."""
    global _queue
    _queue = []
    if _PERSIST_PATH.exists():
        _PERSIST_PATH.unlink()


# Load existing data on module import
_load_from_disk()
