# pipeline/review_queue.py
#
# TODO: Interface for adding items to and reading from the manual review queue.
#
# The review queue stores cases where recipe inference was unresolvable.
# Each queue item corresponds to a specific machine (entity_number) within a specific blueprint.
#
# Functions needed:
# - add(blueprint_id, entity_number, context): insert a new unresolved review item.
#   context dict contains: adjacent_items (list), candidate_recipes (list), confidence (str/None).
# - list_unresolved() -> list[dict]: return all items where resolved == False.
# - resolve(item_id, resolution): mark an item resolved; resolution is a recipe name or 'REJECTED'.
#
# Storage: uses the storage layer (storage/models.py ReviewQueue model + storage/database.py session).
# This module should NOT talk to the DB directly — call storage layer functions.
#
# The API layer (api/v1/analysis.py) calls list_unresolved() and resolve() to power the
# GET /v1/review-queue and POST /v1/review-queue/{id} endpoints.


def add(blueprint_id: str, entity_number: int, context: dict) -> None:
    pass  # TODO: implement


def list_unresolved() -> list[dict]:
    pass  # TODO: implement


def resolve(item_id: str, resolution: str) -> None:
    pass  # TODO: implement
