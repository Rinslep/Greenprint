"""
Convert data-1-1.json into reference/recipes.json and reference/entities.json.

Run once:  python scripts/convert_reference_data.py
Reads:     data-1-1.json  (Factorio 1.1 data export from factoriolab/factorio)
Writes:    reference/recipes.json, reference/entities.json, reference/version.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data-1-1.json"
REF_DIR = ROOT / "reference"


# ---------------------------------------------------------------------------
# Recipe conversion
# ---------------------------------------------------------------------------

def convert_recipes(data: dict) -> list[dict]:
    """Convert data-1-1.json recipes to our schema."""
    recipes = []
    for r in data["recipes"]:
        producers = r.get("producers", [])
        if not producers:
            continue

        inputs = [{"name": name, "amount": amount} for name, amount in r["in"].items()]
        outputs = [{"name": name, "amount": amount} for name, amount in r["out"].items()]

        # Map category from data-1-1 display categories to Factorio crafting categories
        crafting_category = _infer_crafting_category(r, producers)

        recipes.append({
            "name": r["id"],
            "category": crafting_category,
            "crafting_time": r["time"],
            "inputs": inputs,
            "outputs": outputs,
            "valid_machines": producers,
        })

    return recipes


def _infer_crafting_category(recipe: dict, producers: list[str]) -> str:
    """Infer the Factorio crafting category from producer list."""
    producer_set = set(producers)

    if producer_set & {"oil-refinery"}:
        return "oil-processing"
    if producer_set & {"chemical-plant"} and not producer_set & {"assembling-machine-1"}:
        return "chemistry"
    if producer_set & {"centrifuge"} and not producer_set & {"assembling-machine-1"}:
        return "centrifuging"
    if producer_set & {"rocket-silo"}:
        return "rocket-building"
    if producer_set & {"stone-furnace", "steel-furnace", "electric-furnace"}:
        if not producer_set & {"assembling-machine-1"}:
            return "smelting"
    return "crafting"


# ---------------------------------------------------------------------------
# Entity conversion
# ---------------------------------------------------------------------------

# Hardcoded entity data for types not in data-1-1.json.
# Values from Factorio 1.1.110 game source / wiki.

INSERTER_DATA = {
    "burner-inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 0.6,
        "inserter_stack_size": 1, "inserter_filter": False,
        "energy_consumption_kw": 94,
    },
    "inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 0.83,
        "inserter_stack_size": 1, "inserter_filter": False,
        "energy_consumption_kw": 13,
    },
    "long-handed-inserter": {
        "size": [1, 1], "inserter_reach": 2, "inserter_swing_speed": 1.2,
        "inserter_stack_size": 1, "inserter_filter": False,
        "energy_consumption_kw": 18,
    },
    "fast-inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 2.31,
        "inserter_stack_size": 1, "inserter_filter": False,
        "energy_consumption_kw": 46,
    },
    "filter-inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 2.31,
        "inserter_stack_size": 1, "inserter_filter": True,
        "energy_consumption_kw": 46,
    },
    "stack-inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 2.31,
        "inserter_stack_size": 12, "inserter_filter": False,
        "energy_consumption_kw": 132,
    },
    "stack-filter-inserter": {
        "size": [1, 1], "inserter_reach": 1, "inserter_swing_speed": 2.31,
        "inserter_stack_size": 12, "inserter_filter": True,
        "energy_consumption_kw": 132,
    },
}

BELT_ENTITY_DATA = {
    "transport-belt": {"size": [1, 1], "belt_speed": 7.5},
    "fast-transport-belt": {"size": [1, 1], "belt_speed": 15.0},
    "express-transport-belt": {"size": [1, 1], "belt_speed": 22.5},
}

UNDERGROUND_BELT_DATA = {
    "underground-belt": {"size": [1, 1], "belt_speed": 7.5, "underground_max_distance": 5},
    "fast-underground-belt": {"size": [1, 1], "belt_speed": 15.0, "underground_max_distance": 7},
    "express-underground-belt": {"size": [1, 1], "belt_speed": 22.5, "underground_max_distance": 9},
}

SPLITTER_DATA = {
    "splitter": {
        "size": [2, 1], "belt_speed": 7.5,
        "splitter_has_filter": True, "splitter_has_priority": True,
    },
    "fast-splitter": {
        "size": [2, 1], "belt_speed": 15.0,
        "splitter_has_filter": True, "splitter_has_priority": True,
    },
    "express-splitter": {
        "size": [2, 1], "belt_speed": 22.5,
        "splitter_has_filter": True, "splitter_has_priority": True,
    },
}

POLE_DATA = {
    "small-electric-pole": {
        "size": [1, 1], "pole_supply_area": 5, "pole_wire_reach": 7.5,
    },
    "medium-electric-pole": {
        "size": [1, 1], "pole_supply_area": 7, "pole_wire_reach": 9,
    },
    "big-electric-pole": {
        "size": [2, 2], "pole_supply_area": 4, "pole_wire_reach": 30,
    },
    "substation": {
        "size": [2, 2], "pole_supply_area": 18, "pole_wire_reach": 18,
    },
}

# Other blueprint-placeable entities with basic size data
OTHER_ENTITIES = {
    # Chests
    "wooden-chest": {"size": [1, 1]},
    "iron-chest": {"size": [1, 1]},
    "steel-chest": {"size": [1, 1]},
    "logistic-chest-active-provider": {"size": [1, 1]},
    "logistic-chest-passive-provider": {"size": [1, 1]},
    "logistic-chest-storage": {"size": [1, 1]},
    "logistic-chest-buffer": {"size": [1, 1]},
    "logistic-chest-requester": {"size": [1, 1]},
    # Pipes
    "pipe": {"size": [1, 1]},
    "pipe-to-ground": {"size": [1, 1]},
    "pump": {"size": [1, 2], "energy_consumption_kw": 30},
    "storage-tank": {"size": [3, 3]},
    # Roboport
    "roboport": {"size": [4, 4], "energy_consumption_kw": 50},
    # Combinators & speakers
    "arithmetic-combinator": {"size": [1, 2]},
    "decider-combinator": {"size": [1, 2]},
    "constant-combinator": {"size": [1, 1]},
    "programmable-speaker": {"size": [1, 1]},
    "power-switch": {"size": [2, 2]},
    # Lamps
    "small-lamp": {"size": [1, 1]},
    # Rails & trains
    "straight-rail": {"size": [2, 2]},
    "curved-rail": {"size": [2, 2]},
    "train-stop": {"size": [2, 2]},
    "rail-signal": {"size": [1, 1]},
    "rail-chain-signal": {"size": [1, 1]},
    "locomotive": {"size": [2, 6]},
    "cargo-wagon": {"size": [2, 6]},
    "fluid-wagon": {"size": [2, 6]},
    "artillery-wagon": {"size": [2, 6]},
    # Defense
    "stone-wall": {"size": [1, 1]},
    "gate": {"size": [1, 1]},
    "gun-turret": {"size": [2, 2]},
    "laser-turret": {"size": [2, 2], "energy_consumption_kw": 800},
    "flamethrower-turret": {"size": [2, 3]},
    "artillery-turret": {"size": [3, 3]},
    "radar": {"size": [3, 3], "energy_consumption_kw": 300},
    # Solar & accumulators
    "solar-panel": {"size": [3, 3]},
    "accumulator": {"size": [2, 2]},
    # Loader (vanilla has loaders but they're not normally available without commands)
    "loader": {"size": [1, 2], "belt_speed": 7.5},
    "fast-loader": {"size": [1, 2], "belt_speed": 15.0},
    "express-loader": {"size": [1, 2], "belt_speed": 22.5},
    # Misc
    "land-mine": {"size": [1, 1]},
    "offshore-pump": {"size": [1, 2]},
    "heat-pipe": {"size": [1, 1]},
    "steam-engine": {"size": [3, 5]},
    "steam-turbine": {"size": [3, 5]},
}


def convert_entities(data: dict) -> list[dict]:
    """Build entity reference from data-1-1.json items + hardcoded data."""
    entities = []
    seen = set()

    # 1. Machines from data-1-1.json
    for item in data["items"]:
        if "machine" not in item:
            continue
        m = item["machine"]
        entity = {"name": item["id"], "size": m.get("size", [1, 1])}

        if "speed" in m:
            entity["crafting_speed"] = m["speed"]
        if "modules" in m:
            entity["module_slots"] = m["modules"]
        if "usage" in m:
            entity["energy_consumption_kw"] = m["usage"]

        entities.append(entity)
        seen.add(item["id"])

    # 2. Beacon from data-1-1.json
    for item in data["items"]:
        if "beacon" not in item:
            continue
        b = item["beacon"]
        entity = {
            "name": item["id"],
            "size": b.get("size", [3, 3]),
            "module_slots": b.get("modules", 2),
            "energy_consumption_kw": b.get("usage", 480),
            "beacon_effectivity": b.get("effectivity", 0.5),
            "beacon_range": b.get("range", 3),
        }
        entities.append(entity)
        seen.add(item["id"])

    # 3. Belts
    for name, ent_data in BELT_ENTITY_DATA.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    # 4. Underground belts
    for name, ent_data in UNDERGROUND_BELT_DATA.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    # 5. Splitters
    for name, ent_data in SPLITTER_DATA.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    # 6. Inserters
    for name, ent_data in INSERTER_DATA.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    # 7. Poles
    for name, ent_data in POLE_DATA.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    # 8. Other entities
    for name, ent_data in OTHER_ENTITIES.items():
        if name not in seen:
            entities.append({"name": name, **ent_data})
            seen.add(name)

    return entities


# ---------------------------------------------------------------------------
# Module conversion
# ---------------------------------------------------------------------------

MODULE_TYPE_MAP = {
    "speed": "speed",
    "effectivity": "effectivity",
    "productivity": "productivity",
}


def convert_modules(data: dict) -> list[dict]:
    """Extract module data from data-1-1.json items with a 'module' key."""
    modules = []
    for item in data["items"]:
        if "module" not in item:
            continue
        m = item["module"]
        name = item["id"]

        # Determine type and tier from name
        mod_type = "speed"
        for prefix in MODULE_TYPE_MAP:
            if name.startswith(prefix):
                mod_type = MODULE_TYPE_MAP[prefix]
                break

        # Tier: name ends with -2 or -3, otherwise tier 1
        if name.endswith("-3"):
            tier = 3
        elif name.endswith("-2"):
            tier = 2
        else:
            tier = 1

        modules.append({
            "name": name,
            "tier": tier,
            "type": mod_type,
            "effect": {
                "speed": m.get("speed", 0.0),
                "energy": m.get("consumption", 0.0),
                "productivity": m.get("productivity", 0.0),
                "pollution": m.get("pollution", 0.0),
            },
        })

    return modules


# ---------------------------------------------------------------------------
# Version file
# ---------------------------------------------------------------------------

def build_version() -> dict:
    packed_int = (1 << 48) | (1 << 32) | (110 << 16) | 0
    return {
        "major": 1,
        "minor": 1,
        "patch": 110,
        "dev": 0,
        "packed_int": packed_int,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    recipes = convert_recipes(data)
    entities = convert_entities(data)
    modules = convert_modules(data)
    version = build_version()

    REF_DIR.mkdir(exist_ok=True)

    (REF_DIR / "recipes.json").write_text(
        json.dumps(recipes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (REF_DIR / "entities.json").write_text(
        json.dumps(entities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (REF_DIR / "modules.json").write_text(
        json.dumps(modules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (REF_DIR / "version.json").write_text(
        json.dumps(version, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote {len(recipes)} recipes to reference/recipes.json")
    print(f"Wrote {len(entities)} entities to reference/entities.json")
    print(f"Wrote {len(modules)} modules to reference/modules.json")
    print(f"Wrote version.json (packed_int={version['packed_int']})")


if __name__ == "__main__":
    main()
