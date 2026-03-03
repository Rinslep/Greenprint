# pipeline/version_filter.py
#
# TODO: Unpack the 64-bit version integer and apply version and mod checks.
#
# Version unpacking:
#   major = (version >> 48) & 0xFFFF
#   minor = (version >> 32) & 0xFFFF
#   patch = (version >> 16) & 0xFFFF
#   dev   = (version >>  0) & 0xFFFF
# Accept only major == 1, minor == 1. Anything else → reject (log as UNSUPPORTED_VERSION).
# If patch < 110 → do NOT reject, but attach EARLY_VERSION flag to the blueprint.
#
# Modded blueprint rejection:
# - Load vanilla entity names from reference/entities.json (via config.REFERENCE_DIR).
# - Load vanilla recipe names from reference/recipes.json.
# - For each entity in blueprint.entities:
#     - Check entity.name against the entity reference set.
#     - Check entity.recipe (if present) against the recipe reference set.
#     - Any unknown name → reject entire blueprint with reason MODDED_BLUEPRINT.
# - Reference data is loaded once at module import and cached — never fetched at runtime.
#
# Return: (accepted: bool, flags: list[str], rejection_reason: str | None)


def check_version(version_int: int) -> tuple[bool, list[str], str | None]:
    pass  # TODO: implement


def check_modded(blueprint) -> tuple[bool, str | None]:
    pass  # TODO: implement
