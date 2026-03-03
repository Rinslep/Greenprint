"""Version unpacking and modded blueprint rejection.

check_version: Unpack the 64-bit version integer, accept only Factorio 1.1.
check_modded: Reject blueprints containing non-vanilla entity or recipe names.
"""

import structlog

from pipeline.reference_loader import get_entity_names, get_recipe_names

log = structlog.get_logger()


def unpack_version(version_int: int) -> tuple[int, int, int, int]:
    """Unpack a Factorio 64-bit packed version into (major, minor, patch, dev)."""
    major = (version_int >> 48) & 0xFFFF
    minor = (version_int >> 32) & 0xFFFF
    patch = (version_int >> 16) & 0xFFFF
    dev = (version_int >> 0) & 0xFFFF
    return major, minor, patch, dev


def check_version(version_int: int) -> tuple[bool, list[str], str | None]:
    """Check if a blueprint version is accepted.

    Returns (accepted, flags, rejection_reason).
    Accepted only if major == 1 and minor == 1.
    Adds EARLY_VERSION flag if patch < 110.
    """
    major, minor, patch, dev = unpack_version(version_int)
    flags: list[str] = []

    if major != 1 or minor != 1:
        reason = f"UNSUPPORTED_VERSION: {major}.{minor}.{patch}.{dev}"
        log.debug("version_rejected", version=f"{major}.{minor}.{patch}", reason=reason)
        return False, flags, reason

    if patch < 110:
        flags.append("EARLY_VERSION")
        log.debug("early_version_flagged", version=f"{major}.{minor}.{patch}")

    log.debug("version_accepted", version=f"{major}.{minor}.{patch}")
    return True, flags, None


def check_modded(blueprint) -> tuple[bool, str | None]:
    """Check if a blueprint uses only vanilla entities and recipes.

    Accepts either a BlueprintWrapper (Pydantic model) or a raw dict.
    Returns (accepted, rejection_reason).
    """
    vanilla_entities = get_entity_names()
    vanilla_recipes = get_recipe_names()

    # Support both Pydantic model and raw dict
    if hasattr(blueprint, "blueprint"):
        bp = blueprint.blueprint
        entities = bp.entities
    else:
        bp = blueprint.get("blueprint", blueprint)
        entities = bp.get("entities", [])

    for entity in entities:
        if hasattr(entity, "name"):
            name = entity.name
            recipe = entity.recipe
        else:
            name = entity.get("name", "")
            recipe = entity.get("recipe")

        if name not in vanilla_entities:
            reason = f"MODDED_BLUEPRINT: unknown entity '{name}'"
            log.info("modded_rejected", entity_name=name, reason=reason)
            return False, reason

        if recipe is not None and recipe not in vanilla_recipes:
            reason = f"MODDED_BLUEPRINT: unknown recipe '{recipe}'"
            log.info("modded_rejected", recipe_name=recipe, reason=reason)
            return False, reason

    return True, None
