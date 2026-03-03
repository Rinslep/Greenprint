"""Load and cache vanilla Factorio 1.1 reference data.

All data is loaded from static JSON files under config.REFERENCE_DIR.
Nothing is fetched at runtime.
"""

import json
from functools import lru_cache

from config import REFERENCE_DIR


@lru_cache(maxsize=1)
def load_recipes() -> list[dict]:
    path = REFERENCE_DIR / "recipes.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_entities() -> list[dict]:
    path = REFERENCE_DIR / "entities.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_version() -> dict:
    path = REFERENCE_DIR / "version.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_modules() -> list[dict]:
    path = REFERENCE_DIR / "modules.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_entity_names() -> frozenset[str]:
    return frozenset(e["name"] for e in load_entities())


@lru_cache(maxsize=1)
def get_recipe_names() -> frozenset[str]:
    return frozenset(r["name"] for r in load_recipes())


def get_recipe(name: str) -> dict:
    for r in load_recipes():
        if r["name"] == name:
            return r
    raise KeyError(f"Unknown recipe: {name}")


def get_entity(name: str) -> dict:
    for e in load_entities():
        if e["name"] == name:
            return e
    raise KeyError(f"Unknown entity: {name}")


def get_module(name: str) -> dict:
    for m in load_modules():
        if m["name"] == name:
            return m
    raise KeyError(f"Unknown module: {name}")
