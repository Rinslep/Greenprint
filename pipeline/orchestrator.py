"""Pipeline orchestrator — single entry point for processing blueprint strings.

Wires decode → validate → filter → analyse → store into one function.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from fractions import Fraction

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from analysis.crafting_graph import build_crafting_graph
from analysis.motif.canonicaliser import canonicalise
from analysis.motif.extractor import extract_motifs
from analysis.motif.family_hash import compute_family_hash, compute_simplified_family_hash
from analysis.motif.lane_model import build_lane_model
from analysis.motif.tileability import compute_blueprint_tileability
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

    # Process each decoded blueprint (books are dissolved into list).
    # Detect books via the _from_book sentinel set by the decoder — a single-child
    # book would be missed if we relied on len(decoded_list) > 1.
    is_book = bool(decoded_list) and decoded_list[0].get("_from_book", False)
    first_child_id: str | None = None

    for i, decoded in enumerate(decoded_list):
        if is_book:
            child_raw = json.dumps(decoded, sort_keys=True)
            child_hash = hashlib.sha256(child_raw.encode("utf-8")).hexdigest()
        else:
            child_raw = raw
            child_hash = raw_hash

        # Per-child dedup check (books can share identical children)
        if is_book:
            existing_child = storage.get_blueprint_by_hash(session, child_hash)
            if existing_child:
                result.blueprint_ids.append(existing_child.id)
                if first_child_id is None:
                    first_child_id = existing_child.id
                continue

        # First child gets source_book_id=None; subsequent siblings point to it.
        source_book_id = first_child_id if (is_book and i > 0) else None

        bp_result = _process_single(
            session, decoded, child_raw, child_hash,
            source_url, source_site, author_raw, source_book_id,
        )
        result.blueprint_ids.extend(bp_result.blueprint_ids)
        result.flags.extend(bp_result.flags)
        result.review_queue_items += bp_result.review_queue_items
        result.errors.extend(bp_result.errors)
        if bp_result.rejected:
            result.rejected = True
            result.rejection_reason = bp_result.rejection_reason

        # After the first child is saved, record its UUID for sibling linking.
        if is_book and first_child_id is None and bp_result.blueprint_ids:
            first_child_id = bp_result.blueprint_ids[0]

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
    source_book_id: str | None = None,
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
    # review_items are persisted to DB after blueprint is saved (Stage 9) so bp.id is known.
    pending_review_items: list[dict] = []
    try:
        inference_flags, pending_review_items = infer_recipes(wrapper)
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
            # Convert lane_saturation tuple keys to a list of structured objects
            # before serialisation so API consumers receive structured data.
            raw_saturation = throughput.get("lane_saturation", {})
            throughput["lane_saturation"] = [
                {"x": x, "y": y, "side": side, "saturation": pct}
                for (x, y, side), pct in raw_saturation.items()
            ]
            summary["throughput"] = _serialise_summary(throughput)
        except Exception as exc:
            result.errors.append(f"analyse_throughput: {exc}")
            logger.warning("Throughput analysis error for %s: %s", raw_hash[:12], exc)

    # Stage 9: Save blueprint
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
            source_book_id=source_book_id,
            flags=all_flags if all_flags else None,
            summary=summary if summary else None,
        )
        result.blueprint_ids.append(bp.id)
        result.flags = all_flags
    except IntegrityError:
        session.rollback()
        existing = storage.get_blueprint_by_hash(session, raw_hash)
        if existing:
            result.blueprint_ids.append(existing.id)
            result.flags = all_flags
            logger.info("Duplicate hash %s — using existing record", raw_hash[:12])
        else:
            logger.error("IntegrityError but no existing record for %s", raw_hash[:12])
            result.errors.append("IntegrityError: duplicate hash but lookup failed")
        return result

    try:
        # Persist review queue items now that bp.id is known
        for item in pending_review_items:
            try:
                storage.add_review_item(
                    session,
                    blueprint_id=bp.id,
                    entity_number=item["entity_number"],
                    context=item["context"],
                )
                result.review_queue_items += 1
            except Exception as exc:
                result.errors.append(f"add_review_item: {exc}")

        # Stage 10: Extract motifs and save with fully-populated metadata
        if lane_graph is not None:
            try:
                motif_subgraphs = extract_motifs(lane_graph)
                # Track per-blueprint positions for tileability detection:
                # canonical_hash → list of (x, y) source machine anchor positions
                motif_positions: dict[str, list[tuple[float, float]]] = {}

                for motif_sg in motif_subgraphs:
                    try:
                        canon_hash, canon_entities = canonicalise(motif_sg)
                        category = motif_sg.graph.get("category", "SIMPLE")

                        uses_underground = any(
                            d.get("edge_type") == "underground"
                            for _, _, d in motif_sg.edges(data=True)
                        )
                        uses_splitter = any(
                            d.get("edge_type") == "splitter"
                            for _, _, d in motif_sg.edges(data=True)
                        )

                        source_recipes: dict[str, int] = {}
                        source_node = motif_sg.graph.get("source_machine")
                        if source_node and source_node in motif_sg:
                            src_entity = motif_sg.nodes[source_node].get("entity")
                            if src_entity and hasattr(src_entity, "recipe") and src_entity.recipe:
                                r = src_entity.recipe
                                source_recipes[r] = source_recipes.get(r, 0) + 1

                        dest_recipes: dict[str, int] = {}
                        for dest_node in motif_sg.graph.get("dest_machines", set()):
                            if dest_node in motif_sg:
                                dest_entity = motif_sg.nodes[dest_node].get("entity")
                                if dest_entity and hasattr(dest_entity, "recipe") and dest_entity.recipe:
                                    r = dest_entity.recipe
                                    dest_recipes[r] = dest_recipes.get(r, 0) + 1

                        belt_type = None
                        for _, node_data in motif_sg.nodes(data=True):
                            if node_data.get("node_type") == "belt_lane":
                                entity = node_data.get("entity")
                                if entity and hasattr(entity, "name"):
                                    belt_type = entity.name
                                    break

                        is_multi_destination = (
                            len(motif_sg.graph.get("dest_machines", set())) > 1
                        )

                        # P3: family hash + sub-motif hierarchy
                        fhash = compute_family_hash(canon_entities)
                        simplified_fhash = compute_simplified_family_hash(canon_entities)
                        # elaboration_depth = number of complex features present
                        elaboration_depth = (
                            int(uses_underground) + int(uses_splitter)
                        )
                        # sub_motif_of_family is only meaningful when there
                        # are features to strip; base motifs point to themselves
                        sub_motif = (
                            simplified_fhash if elaboration_depth > 0 else fhash
                        )

                        # Track source machine position for tileability detection
                        src_pos: tuple[float, float] | None = None
                        if source_node and source_node in motif_sg:
                            src_ent = motif_sg.nodes[source_node].get("entity")
                            if src_ent and hasattr(src_ent, "position"):
                                src_pos = (
                                    float(src_ent.position.x),
                                    float(src_ent.position.y),
                                )
                        if src_pos is not None:
                            motif_positions.setdefault(canon_hash, []).append(src_pos)

                        storage.save_motif(
                            session,
                            canonical_hash=canon_hash,
                            canonical_entities=canon_entities,
                            category=category,
                            source_recipes=source_recipes or None,
                            dest_recipes=dest_recipes or None,
                            belt_type=belt_type,
                            uses_underground=uses_underground,
                            uses_splitter=uses_splitter,
                            is_multi_destination=is_multi_destination,
                            entity_count=motif_sg.number_of_nodes(),
                            blueprint_id=bp.id,
                            example_blueprint_id=bp.id,
                            family_hash=fhash,
                            elaboration_depth=elaboration_depth,
                            sub_motif_of_family=sub_motif,
                        )
                    except Exception as exc:
                        result.errors.append(f"save_motif: {exc}")

                # P3: Tileability detection — runs after all motifs saved
                try:
                    tileability = compute_blueprint_tileability(motif_positions)
                    for canon_hash, tile_result in tileability.items():
                        if tile_result is not None:
                            storage.update_motif_tileability(
                                session,
                                canonical_hash=canon_hash,
                                tile_vector=tile_result["tile_vector"],
                                tile_count=tile_result["tile_count"],
                            )
                except Exception as exc:
                    result.errors.append(f"tileability: {exc}")

            except Exception as exc:
                result.errors.append(f"extract_motifs: {exc}")
                logger.warning("Motif extraction error for %s: %s", raw_hash[:12], exc)

    except Exception as exc:
        result.errors.append(f"save_blueprint: {exc}")
        logger.error("Save failed for %s: %s", raw_hash[:12], exc)
        return result

    return result
