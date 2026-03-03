"""Pipeline orchestrator — single entry point for processing blueprint strings.

Wires decode → validate → filter → analyse → store into one function.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from fractions import Fraction

from sqlalchemy.orm import Session

from analysis.crafting_graph import build_crafting_graph
from analysis.motif.canonicaliser import canonicalise
from analysis.motif.extractor import extract_motifs
from analysis.motif.lane_model import build_lane_model
from analysis.ratio_analyser import analyse_ratios
from analysis.throughput_analyser import analyse_throughput
from pipeline.broken_detector import detect as detect_broken
from pipeline.decoder import decode
from pipeline.recipe_inference import infer_recipes
from pipeline.validator import validate
from pipeline.version_filter import check_modded, check_version
import storage

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    success: bool = False
    blueprint_ids: list[str] = field(default_factory=list)
    rejected: bool = False
    rejection_reason: str | None = None
    flags: list[dict] = field(default_factory=list)
    review_queue_items: int = 0
    errors: list[str] = field(default_factory=list)


def _serialise_summary(obj):
    """Recursively convert Fraction values to float for JSON storage.

    Also converts tuple dict keys to strings and sets to sorted lists,
    since JSON only supports string keys.
    """
    if isinstance(obj, Fraction):
        return float(obj)
    if isinstance(obj, dict):
        return {
            str(k) if not isinstance(k, str) else k: _serialise_summary(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_serialise_summary(item) for item in obj]
    if isinstance(obj, (set, frozenset)):
        return [_serialise_summary(item) for item in sorted(obj, key=str)]
    return obj


def process_string(
    session: Session,
    raw: str,
    source_url: str | None = None,
    source_site: str | None = None,
    author_raw: str | None = None,
) -> PipelineResult:
    """Process a raw blueprint string through the full pipeline.

    Returns a PipelineResult with the outcome of the processing.
    """
    result = PipelineResult()
    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # Dedup check
    existing = storage.get_blueprint_by_hash(session, raw_hash)
    if existing:
        result.success = True
        result.blueprint_ids = [existing.id]
        return result

    # Stage 1: Decode
    try:
        decoded_list = decode(raw)
    except Exception as exc:
        result.rejected = True
        result.rejection_reason = f"DECODE_FAILURE: {exc}"
        logger.warning("Decode failed for %s: %s", raw_hash[:12], exc)
        return result

    if not decoded_list:
        result.rejected = True
        result.rejection_reason = "DECODE_FAILURE: empty result"
        return result

    # Process each decoded blueprint (books are dissolved into list)
    is_book = len(decoded_list) > 1
    for i, decoded in enumerate(decoded_list):
        # Each child of a book needs its own unique hash
        if is_book:
            import json
            child_raw = json.dumps(decoded, sort_keys=True)
            child_hash = hashlib.sha256(child_raw.encode("utf-8")).hexdigest()
        else:
            child_raw = raw
            child_hash = raw_hash

        bp_result = _process_single(
            session, decoded, child_raw, child_hash, source_url, source_site, author_raw
        )
        result.blueprint_ids.extend(bp_result.blueprint_ids)
        result.flags.extend(bp_result.flags)
        result.review_queue_items += bp_result.review_queue_items
        result.errors.extend(bp_result.errors)
        if bp_result.rejected:
            result.rejected = True
            result.rejection_reason = bp_result.rejection_reason

    result.success = len(result.blueprint_ids) > 0
    return result


def _process_single(
    session: Session,
    decoded: dict,
    raw: str,
    raw_hash: str,
    source_url: str | None,
    source_site: str | None,
    author_raw: str | None,
) -> PipelineResult:
    """Process a single decoded blueprint through validation and analysis."""
    result = PipelineResult()
    all_flags = []

    # Stage 2: Validate
    try:
        wrapper = validate(decoded)
    except Exception as exc:
        result.rejected = True
        result.rejection_reason = f"VALIDATION_FAILURE: {exc}"
        logger.warning("Validation failed for %s: %s", raw_hash[:12], exc)
        return result

    # Stage 3: Version check
    try:
        version_int = decoded.get("blueprint", {}).get("version")
        if version_int:
            accepted, version_flags, rejection = check_version(version_int)
            for flag_name in version_flags:
                all_flags.append({"flag": flag_name, "severity": "INFO", "detail": ""})
            if not accepted:
                result.rejected = True
                result.rejection_reason = rejection
                return result
    except Exception as exc:
        result.errors.append(f"check_version: {exc}")
        logger.warning("Version check error for %s: %s", raw_hash[:12], exc)

    # Stage 3b: Modded check
    try:
        mod_accepted, mod_reason = check_modded(decoded)
        if not mod_accepted:
            result.rejected = True
            result.rejection_reason = mod_reason
            return result
    except Exception as exc:
        result.errors.append(f"check_modded: {exc}")
        logger.warning("Modded check error for %s: %s", raw_hash[:12], exc)

    # Stage 4: Broken detection (continue on failure)
    try:
        broken_flags = detect_broken(wrapper)
        all_flags.extend(broken_flags)
    except Exception as exc:
        result.errors.append(f"detect_broken: {exc}")
        logger.warning("Broken detection error for %s: %s", raw_hash[:12], exc)

    # Stage 5: Recipe inference (continue on failure)
    review_count = 0
    try:
        inference_flags = infer_recipes(wrapper, blueprint_id=raw_hash[:12])
        all_flags.extend(inference_flags)
    except Exception as exc:
        result.errors.append(f"infer_recipes: {exc}")
        logger.warning("Recipe inference error for %s: %s", raw_hash[:12], exc)

    # Stage 6: Crafting graph (continue on failure)
    summary = {}
    crafting_graph = None
    try:
        crafting_graph = build_crafting_graph(wrapper)
        summary["crafting_graph"] = _serialise_summary({
            "final_products": list(crafting_graph.graph.get("final_products", set())),
            "raw_inputs": list(crafting_graph.graph.get("raw_inputs", set())),
            "intermediates": list(crafting_graph.graph.get("intermediates", set())),
            "is_self_contained": crafting_graph.graph.get("is_self_contained", False),
            "has_cycle": crafting_graph.graph.get("has_cycle", False),
        })
    except Exception as exc:
        result.errors.append(f"build_crafting_graph: {exc}")
        logger.warning("Crafting graph error for %s: %s", raw_hash[:12], exc)

    # Stage 7: Ratio analysis (continue on failure)
    try:
        if crafting_graph is not None:
            ratios = analyse_ratios(wrapper, crafting_graph)
            summary["ratios"] = _serialise_summary(ratios)
    except Exception as exc:
        result.errors.append(f"analyse_ratios: {exc}")
        logger.warning("Ratio analysis error for %s: %s", raw_hash[:12], exc)

    # Stage 8: Lane model + throughput (continue on failure)
    lane_graph = None
    try:
        lane_graph = build_lane_model(wrapper)
    except Exception as exc:
        result.errors.append(f"build_lane_model: {exc}")
        logger.warning("Lane model error for %s: %s", raw_hash[:12], exc)

    if lane_graph is not None and crafting_graph is not None:
        try:
            throughput = analyse_throughput(wrapper, crafting_graph, lane_graph)
            summary["throughput"] = _serialise_summary(throughput)
        except Exception as exc:
            result.errors.append(f"analyse_throughput: {exc}")
            logger.warning("Throughput analysis error for %s: %s", raw_hash[:12], exc)

    # Stage 9: Motif extraction (continue on failure)
    if lane_graph is not None:
        try:
            motif_subgraphs = extract_motifs(lane_graph)
            for motif_sg in motif_subgraphs:
                try:
                    canon_hash, canon_entities = canonicalise(motif_sg)
                    category = motif_sg.graph.get("category", "SIMPLE")

                    # Build metadata from motif subgraph
                    metadata = {
                        "belt_type": None,
                        "uses_underground": False,
                        "uses_splitter": False,
                        "entity_count": motif_sg.number_of_nodes(),
                        "source_recipes": {},
                        "dest_recipes": {},
                    }

                    # save_motif is deferred until after save_blueprint
                except Exception as exc:
                    result.errors.append(f"canonicalise motif: {exc}")
        except Exception as exc:
            result.errors.append(f"extract_motifs: {exc}")
            logger.warning("Motif extraction error for %s: %s", raw_hash[:12], exc)

    # Stage 10: Save blueprint
    game_version = None
    game_version_int = None
    version_int = decoded.get("blueprint", {}).get("version")
    if version_int:
        game_version_int = version_int
        major = (version_int >> 48) & 0xFFFF
        minor = (version_int >> 32) & 0xFFFF
        patch = (version_int >> 16) & 0xFFFF
        game_version = f"{major}.{minor}.{patch}"

    try:
        bp = storage.save_blueprint(
            session,
            raw_string=raw,
            raw_string_hash=raw_hash,
            decoded_json=decoded,
            source_url=source_url,
            source_site=source_site,
            author_raw=author_raw,
            game_version=game_version,
            game_version_int=game_version_int,
            flags=all_flags if all_flags else None,
            summary=summary if summary else None,
        )
        result.blueprint_ids.append(bp.id)
        result.flags = all_flags

        # Now save motifs with the blueprint ID
        if lane_graph is not None:
            try:
                motif_subgraphs = extract_motifs(lane_graph)
                for motif_sg in motif_subgraphs:
                    try:
                        canon_hash, canon_entities = canonicalise(motif_sg)
                        category = motif_sg.graph.get("category", "SIMPLE")
                        storage.save_motif(
                            session,
                            canonical_hash=canon_hash,
                            canonical_entities=canon_entities,
                            category=category,
                            entity_count=motif_sg.number_of_nodes(),
                            blueprint_id=bp.id,
                            example_blueprint_id=bp.id,
                        )
                    except Exception:
                        pass
            except Exception:
                pass

    except Exception as exc:
        result.errors.append(f"save_blueprint: {exc}")
        logger.error("Save failed for %s: %s", raw_hash[:12], exc)
        return result

    result.review_queue_items = review_count
    return result
