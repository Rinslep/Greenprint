# analysis/ratio_analyser.py
#
# TODO: Calculate ideal and actual machine ratios for each recipe pair in the crafting graph.
#
# Per machine, compute items/sec produced:
#   rate = (output_count / crafting_time) * crafting_speed * module_speed_multiplier
#          * (1 + productivity_bonus)
# ALL intermediate values must be stored as fractions.Fraction — never float — to avoid
# rounding drift when computing ratios. Serialise to float only at the API response layer.
#
# Module effects:
# - Iterate each entity's items (module dict) to find speed and productivity modules.
# - Apply speed bonus: each speed-module-N adds a defined speed bonus (load from entities.json).
# - Apply productivity bonus similarly.
# - Beacon effects: if beacon entities are present, identify which machines fall within
#   each beacon's supply area (use entity positions + pole_supply_area from entities.json).
#   Apply the beacon's module bonuses to those machines before computing rates.
#
# For each supplier→consumer recipe relationship in the crafting graph:
# - ideal_ratio: Fraction — how many supplier machines are needed per consumer machine.
# - actual_ratio: Fraction — the count ratio of actual machines in the blueprint.
# - efficiency: float — actual_ratio / ideal_ratio clamped to [0, 1] (over-supply = 1.0).
#
# Bottleneck: the recipe relationship with the lowest efficiency score.
#
# Return: a dict keyed by (supplier_recipe, consumer_recipe) tuples, values are ratio dicts.


from fractions import Fraction


def analyse_ratios(blueprint, crafting_graph) -> dict:
    pass  # TODO: implement
