"""analysis/motif — public API for the motif pipeline.

Exports:
    build_lane_model   — construct the lane-level graph from a validated blueprint
    extract_motifs     — BFS extraction of motif subgraphs from a lane graph
    canonicalise       — produce a stable (canonical_hash, canonical_entities) pair
    compute_family_hash          — tier-normalised family hash
    compute_simplified_family_hash — base-form family hash (underground/splitter stripped)
    detect_tileability           — tileability for one motif within one blueprint
    compute_blueprint_tileability — tileability for all motifs in one blueprint
    catalogue.upsert / get / list_motifs / get_blueprints_for_motif / clear
"""

from analysis.motif.canonicaliser import canonicalise
from analysis.motif.extractor import extract_motifs
from analysis.motif.family_hash import compute_family_hash, compute_simplified_family_hash
from analysis.motif.lane_model import build_lane_model
from analysis.motif.tileability import compute_blueprint_tileability, detect_tileability
from analysis.motif import catalogue

__all__ = [
    "build_lane_model",
    "extract_motifs",
    "canonicalise",
    "compute_family_hash",
    "compute_simplified_family_hash",
    "detect_tileability",
    "compute_blueprint_tileability",
    "catalogue",
]
