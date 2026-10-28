"""
V5 Orchestrator (single strategy = market_standard)
===================================================

This module provides an explicit, replayable orchestration path that:
- reuses V5 constrained clusters (photo_clusters) + V5 target PIR (unified_estimates:v5_pir_target)
- clusters the selected comparable and generates comparable per-room PIRs (slot protocol)
- aggregates comparable room PIRs into a whole-property comparable slot standard
- selects one market-standard comparable (unified_estimates:v5_selected_comparable)
- generates delta per room×slot (unified_estimates:v5_delta_slots_market_standard)
- decomposes to work items (unified_estimates:v5_work_items_market_standard)
- ensures Smart M² (room dimensions) exists or regenerates it from current clusters
- runs the V4 tail directly from V5 work items (boq_line_items dimension="v4")
  - BCCA matching: dimension-scoped embeddings + Flash Lite LLM rerank + denylist
  - Forage: signals anchored to Smart M² room dimensions
  - BOQ: quantity sanity caps (per-room ud, flat-level accumulation, area-based m²/ml)

WHY THIS MATTERS:
- This is the “proper” undisturbed run path for listing-12 smokes: stage outputs are persisted
  under stable keys so the run is replayable and debuggable.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch
from pricing.embedding_runtime import embed_texts
from pricing.v4_quantification_pipeline import run_v4_tail_from_v5_work_items
from pricing.v5_comparable_selector import select_v5_median_price_comparable
from pricing.v5_comparable_standard import build_v5_comparable_slot_standard
from pricing.v5_pir import generate_v5_target_room_pir
from pricing.v5_strategy_delta_decompose import generate_v5_delta_for_room
from pricing.v5_work_items import build_v5_work_items_for_strategy

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_v5_market_standard(
    *,
    listing_id: int,
    db: Any,
    force: bool = False,
    max_comparables: int = 5,
    max_photos_per_comparable: int = 24,
) -> Dict[str, Any]:
    """
    Run the V5 single-strategy chain through V4 tail.
    Returns a summary dict (also persists v4_run_summary_market_standard inside the V4 tail).
    """
    strategy_name = "market_standard"

    target_pir_key = "v5_pir_target"
    target_pir = None if force else await db.get_unified_estimate(listing_id, target_pir_key)
    if not target_pir:
        # Orchestrator should be end-to-end: generate target PIR if missing.
        # WHY THIS MATTERS: callers should not have to remember to run smokes in the right order.
        listing = await db.get_listing(listing_id)
        if not listing:
            raise RuntimeError(f"v5_market_standard: listing not found | listing_id={listing_id}")
        construction_year = listing.get("construction_year") or listing.get("year_built")

        clusters = await db.get_photo_clusters(listing_id)
        if not clusters:
            raise RuntimeError(f"v5_market_standard: missing photo_clusters | listing_id={listing_id}")

        room_entries: List[Dict[str, Any]] = []
        for c in clusters:
            if not isinstance(c, dict):
                continue
            rid = str(c.get("cluster_id") or "").strip()
            rt = str(c.get("room_type") or "").strip() or "unknown_room"
            urls = [u for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
            if not rid or not urls:
                continue
            if rt in ("floorplan", "street_view", "views_outlook"):
                continue
            room_entries.append({"room_id": rid, "room_type": rt, "photo_urls": urls})

        if not room_entries:
            raise RuntimeError(f"v5_market_standard: no usable room clusters | listing_id={listing_id}")

        concurrency = 5
        sem = asyncio.Semaphore(concurrency)

        async def _run_one(entry: Dict[str, Any]) -> Dict[str, Any]:
            rid_local = str(entry["room_id"])
            rt_local = str(entry["room_type"])
            urls_local = entry["photo_urls"]
            async with sem:
                return await generate_v5_target_room_pir(
                    room_id=rid_local,
                    room_type=rt_local,
                    photo_urls=urls_local,
                    construction_year=int(construction_year) if isinstance(construction_year, int) else None,
                    max_photos=12,
                    call_gemini_fn=call_gemini,
                    fetch_images_batch_fn=fetch_images_batch,
                )

        tasks = [asyncio.create_task(_run_one(e)) for e in sorted(room_entries, key=lambda x: str(x.get("room_id") or ""))]
        rooms_out: List[Dict[str, Any]] = []
        try:
            for t in asyncio.as_completed(tasks):
                rooms_out.append(await t)
        except Exception:
            for t in tasks:
                if not t.done():
                    t.cancel()
            raise

        target_pir = {
            "listing_id": int(listing_id),
            "rooms": sorted(rooms_out, key=lambda r: str(r.get("room_id") or "")),
            "schema_version": "v5_pir_target_v1",
            "created_at": _now_iso(),
            "counts": {"rooms": len(rooms_out)},
        }
        ok = await db.save_unified_estimate(listing_id, target_pir_key, target_pir)
        if not ok:
            raise RuntimeError(f"v5_market_standard: save failed | key={target_pir_key} listing_id={listing_id}")

    comparables = await db.get_listing_comparables(listing_id)
    if not comparables:
        raise RuntimeError(f"v5_market_standard: no comparables | listing_id={listing_id}")

    # Select one deterministic median comparable (no LLM).
    selected_key = "v5_selected_comparable"
    selected = None if force else await db.get_unified_estimate(listing_id, selected_key)
    if not (isinstance(selected, dict) and selected.get("selected_comparable_id")):
        selected = select_v5_median_price_comparable(listing_id=int(listing_id), comparables=comparables, price_field="price_per_sqm")

        # Compute reference_sold_price = median price/m² × listing area
        _listing = await db.get_listing(listing_id)
        listing_area = 0.0
        if _listing:
            scraped = _listing.get("scraped_data") or {}
            for src in [_listing.get("sqm"), scraped.get("m2_built"), scraped.get("m2_useful")]:
                if src is not None:
                    try:
                        listing_area = float(src)
                        break
                    except (ValueError, TypeError):
                        pass
        median_value = selected.get("median_value")
        if median_value and listing_area > 0:
            selected["reference_sold_price"] = round(float(median_value) * listing_area)
            selected["listing_area_sqm"] = listing_area

        selected = {**selected, "schema_version": "v5_selected_comparable_v2", "created_at": _now_iso()}
        ok = await db.save_unified_estimate(listing_id, selected_key, selected)
        if not ok:
            raise RuntimeError(f"v5_market_standard: save failed | key={selected_key} listing_id={listing_id}")

    selected_id = int(selected.get("selected_comparable_id"))
    # Ensure we have comparable slot_standard derived from clustered comparable room PIRs.
    std_key = f"v5_selected_comparable_slot_standard_{selected_id}"
    slot_std = None if force else await db.get_unified_estimate(listing_id, std_key)
    if not (isinstance(slot_std, dict) and isinstance(slot_std.get("slot_standard"), dict) and slot_std.get("slot_standard")):
        sel_comp = None
        for c in comparables:
            cid = c.get("casafari_property_id") or c.get("id") or c.get("comparable_id") or c.get("listing_id")
            try:
                if int(cid) == selected_id:
                    sel_comp = c
                    break
            except Exception:
                continue
        if not sel_comp:
            raise RuntimeError(f"v5_market_standard: selected comparable missing from listing_comparables | selected_id={selected_id}")

        from pipeline.steps.cluster_photos_v5 import cluster_photos_v5

        comp_photo_urls = [str(u) for u in (sel_comp.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        comp_photo_urls = comp_photo_urls[: max(1, int(max_photos_per_comparable))]
        ctx = (
            "COMPARABLE CONTEXT:\n"
            f"- property_id: {selected_id}\n"
            f"- bedrooms: {sel_comp.get('bedrooms')}\n"
            f"- bathrooms: {sel_comp.get('bathrooms')}\n"
            f"- total_area: {sel_comp.get('total_area')}\n"
            f"- distance_km: {sel_comp.get('distance_km')}\n"
        )

        clusters_key = f"v5_selected_comparable_clusters_{selected_id}"
        clusters_art = None if force else await db.get_unified_estimate(listing_id, clusters_key)
        clusters = (clusters_art or {}).get("clusters") if isinstance(clusters_art, dict) else None
        if not (isinstance(clusters, list) and clusters):
            cluster_out = await cluster_photos_v5(listing_context=ctx, photo_urls=comp_photo_urls, property_flags=None)
            clusters = cluster_out.get("clusters") or []
            if not clusters:
                raise RuntimeError(f"v5_market_standard: comparable clustering returned 0 clusters | comp_id={selected_id}")
            await db.save_unified_estimate(
                listing_id,
                clusters_key,
                {
                    "listing_id": int(listing_id),
                    "comparable_id": int(selected_id),
                    "schema_version": "v5_comparable_clusters_v1",
                    "created_at": _now_iso(),
                    "clusters": clusters,
                    "excluded_content": cluster_out.get("excluded_content") or [],
                    "counts": {"clusters": len(clusters), "photos": len(comp_photo_urls)},
                },
            )

        rooms_key = f"v5_selected_comparable_room_pirs_{selected_id}"
        rooms_payload = None if force else await db.get_unified_estimate(listing_id, rooms_key)
        rooms = rooms_payload.get("rooms") if isinstance(rooms_payload, dict) else None
        if not (isinstance(rooms, list) and rooms):
            rooms_out: List[Dict[str, Any]] = []
            for c in clusters or []:
                if not isinstance(c, dict):
                    continue
                rt = str(c.get("room_type") or "").strip() or "unknown_room"
                rid = str(c.get("cluster_id") or c.get("cluster_name") or "").strip() or rt
                urls = [str(u) for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
                if not urls:
                    continue
                urls = urls[: max(1, 8)]
                rooms_out.append(
                    await generate_v5_target_room_pir(
                        room_id=f"comp_{selected_id}:{rid}",
                        room_type=rt,
                        photo_urls=urls,
                        max_photos=8,
                        call_gemini_fn=call_gemini,
                        fetch_images_batch_fn=fetch_images_batch,
                    )
                )
            if not rooms_out:
                raise RuntimeError(f"v5_market_standard: comparable room PIRs returned 0 rooms | comp_id={selected_id}")
            await db.save_unified_estimate(
                listing_id,
                rooms_key,
                {
                    "listing_id": int(listing_id),
                    "comparable_id": int(selected_id),
                    "schema_version": "v5_selected_comparable_room_pirs_v1",
                    "created_at": _now_iso(),
                    "rooms": rooms_out,
                    "counts": {"rooms": len(rooms_out)},
                },
            )
            rooms = rooms_out

        slot_standard = build_v5_comparable_slot_standard(room_pirs=rooms)
        slot_std = {
            "listing_id": int(listing_id),
            "selected_comparable_id": int(selected_id),
            "schema_version": "v5_selected_comparable_slot_standard_v1",
            "created_at": _now_iso(),
            "slot_standard": slot_standard,
            "counts": {"slots": len(slot_standard)},
        }
        await db.save_unified_estimate(listing_id, std_key, slot_std)

    # Delta slots (per room)
    delta_key = "v5_delta_slots_market_standard"
    delta_slots = None if force else await db.get_unified_estimate(listing_id, delta_key)
    if not (isinstance(delta_slots, dict) and isinstance(delta_slots.get("rooms"), list) and delta_slots.get("rooms")):
        # DROP market_targets:
        # Derive per-room targets directly from selected comparable ROOM PIRs:
        # - Prefer comparable rooms matching this room_type
        # - If none match, fall back to any comparable room
        from pricing.v5_slots import slot_ids_for_room_type

        def _slot_map(room_payload: Dict[str, Any]) -> Dict[str, str]:
            m = room_payload.get("slot_narratives") if isinstance(room_payload, dict) else None
            if not isinstance(m, dict):
                return {}
            return {str(k): str(v).strip() for k, v in m.items() if isinstance(k, str) and isinstance(v, str) and v.strip()}

        def _build_targets_for_room(*, room_type: str, slot_ids: List[str]) -> Dict[str, str]:
            rt = str(room_type or "").strip()
            preferred = [r for r in rooms if isinstance(r, dict) and str(r.get("room_type") or "").strip() == rt]
            candidates = preferred if preferred else [r for r in rooms if isinstance(r, dict)]
            out: Dict[str, str] = {}
            for sid in slot_ids:
                picked = ""
                for r in candidates:
                    val = _slot_map(r).get(sid, "")
                    if val:
                        picked = val
                        break
                out[sid] = picked or "Confirmar en visita."
            return out

        targets_by_room: Dict[str, Dict[str, str]] = {}
        for room in target_pir.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            rid_t = str(room.get("room_id") or "").strip()
            rt_t = str(room.get("room_type") or "").strip()
            if not rid_t or not rt_t:
                continue
            slot_ids = slot_ids_for_room_type(rt_t)
            targets_by_room[rid_t] = _build_targets_for_room(room_type=rt_t, slot_ids=slot_ids)

        rooms_out: List[Dict[str, Any]] = []
        for room in target_pir.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            rid = str(room.get("room_id") or "").strip()
            rt = str(room.get("room_type") or "").strip()
            slot_narrs = room.get("slot_narratives") or {}
            if not rid or not rt or not isinstance(slot_narrs, dict):
                continue
            tier_targets = targets_by_room.get(rid) or {}
            if not tier_targets:
                raise RuntimeError(f"v5_market_standard: missing derived targets for room_id={rid} | listing_id={listing_id}")
            rooms_out.append(
                await generate_v5_delta_for_room(
                    listing_id=int(listing_id),
                    strategy_name=strategy_name,
                    room_id=rid,
                    room_type=rt,
                    room_slot_narratives={str(k): str(v) for k, v in slot_narrs.items() if isinstance(k, str) and isinstance(v, str)},
                    tier_slot_targets=tier_targets,
                )
            )
        delta_slots = {
            "listing_id": int(listing_id),
            "strategy_name": str(strategy_name),
            "rooms": rooms_out,
            "schema_version": "v5_delta_slots_v2_from_comparable_standard",
            "created_at": _now_iso(),
            "counts": {"rooms": len(rooms_out)},
        }
        ok = await db.save_unified_estimate(listing_id, delta_key, delta_slots)
        if not ok:
            raise RuntimeError(f"v5_market_standard: save failed | key={delta_key} listing_id={listing_id}")

    # Work items
    items_key = "v5_work_items_market_standard"
    work_items = None if force else await db.get_unified_estimate(listing_id, items_key)
    if not (isinstance(work_items, dict) and isinstance(work_items.get("items"), list) and work_items.get("items")):
        work_items = await build_v5_work_items_for_strategy(
            listing_id=int(listing_id),
            strategy_name=strategy_name,
            delta_slots=delta_slots,
        )
        work_items = {**work_items, "schema_version": "v5_work_items_v1", "created_at": _now_iso(), "counts": {"items": len(work_items.get("items") or [])}}
        ok = await db.save_unified_estimate(listing_id, items_key, work_items)
        if not ok:
            raise RuntimeError(f"v5_market_standard: save failed | key={items_key} listing_id={listing_id}")

    # V4 tail: Smart M² (ensure/regen) → BCCA match (embed+rerank+denylist) → quant plan → forage → BOQ
    logger.info("v5_market_standard: starting v4 tail | listing_id=%s strategy=%s items=%s", listing_id, strategy_name, len(work_items.get("items") or []))
    v4_summary = await run_v4_tail_from_v5_work_items(
        listing_id=int(listing_id),
        strategy_name=strategy_name,
        v5_work_items=work_items,
        db=db,
        call_gemini=call_gemini,
        call_gemini_json=call_gemini_json,
        fetch_images_batch=fetch_images_batch,
        embed_texts_fn=embed_texts,
        clear_existing_v4=bool(force),
    )

    # ── Post-BOQ finalization: aggregate line items → v2_{strategy} for frontend ──
    # WHY: The frontend reads v2_market_standard (aggregated totals + line items array)
    # and v2_delta_market_standard (scopes). Without this step, the UI shows nothing.
    from pricing.v2_boq_generator import aggregate_boq_from_db

    boq_agg = await aggregate_boq_from_db(listing_id, strategy_name, db)
    ok = await db.save_unified_estimate(listing_id, f"v2_{strategy_name}", boq_agg)
    if not ok:
        raise RuntimeError(f"v5_market_standard: failed to save v2_{strategy_name} | listing_id={listing_id}")
    logger.info(
        "v5_market_standard: finalized BOQ | listing_id=%s | total_pem=%.0f | grand_total_with_iva=%.0f | lines=%d",
        listing_id, boq_agg.get("total_pem", 0), boq_agg.get("grand_total_with_iva", 0), len(boq_agg.get("line_items") or []),
    )

    # ── ELI5: buyer-friendly "product configurator" summary ──────────────────
    # WHY: Raw BOQ is construction jargon. Pro regroups line items per room into
    # 2-5 buyer-understandable "packages" (surfaces, fixtures, installations…).
    eli5_key = f"v5_eli5_{strategy_name}"
    existing_eli5 = None if force else await db.get_unified_estimate(listing_id, eli5_key)
    if not (isinstance(existing_eli5, dict) and existing_eli5.get("rooms")):
        from pricing.v5_eli5 import generate_v5_eli5

        # Ensure we have listing metadata for the prompt
        try:
            _listing_for_eli5 = listing  # type: ignore[possibly-undefined]
        except NameError:
            _listing_for_eli5 = None
        if not _listing_for_eli5:
            _listing_for_eli5 = await db.get_listing(listing_id)
        if not _listing_for_eli5:
            raise RuntimeError(f"v5_market_standard: listing not found for ELI5 | listing_id={listing_id}")
        eli5_result = await generate_v5_eli5(
            listing_id=int(listing_id),
            strategy_name=strategy_name,
            boq_aggregation=boq_agg,
            listing=_listing_for_eli5,
            db=db,
            call_gemini_json=call_gemini_json,
            target_pir=target_pir,
        )
        logger.info(
            "v5_market_standard: ELI5 generated | listing_id=%s | rooms=%d",
            listing_id, len(eli5_result.get("rooms") or []),
        )
    else:
        logger.info("v5_market_standard: ELI5 reused | listing_id=%s", listing_id)

    # ── Room Images: before/after renderings ─────────────────────────────────
    # WHY: The frontend shows a before/after slider per room. Each image costs
    # ~$0.04 so we limit to the top 5 rooms by BOQ cost.
    img_key = f"v5_generated_images_{strategy_name}"
    existing_images = None if force else await db.get_unified_estimate(listing_id, img_key)
    if not (isinstance(existing_images, dict) and existing_images.get("generated_images")):
        from pricing.v5_room_images import generate_v5_room_images
        # Import only image-specific helper here. call_gemini/call_gemini_json are
        # already imported at module scope and used earlier in this function.
        # Re-importing them inside this block makes Python treat them as local vars,
        # which triggers UnboundLocalError before this block runs.
        from pipeline.gemini_client import call_gemini_image

        # Ensure photo clusters are loaded
        try:
            _clusters_for_img = clusters  # type: ignore[possibly-undefined]
        except NameError:
            _clusters_for_img = None
        if not _clusters_for_img:
            _clusters_for_img = await db.get_photo_clusters(listing_id)

        # ELI5 (just generated or loaded)
        try:
            _eli5_for_img = eli5_result  # type: ignore[possibly-undefined]
        except NameError:
            _eli5_for_img = None
        if not _eli5_for_img:
            _eli5_for_img = await db.get_unified_estimate(listing_id, f"v5_eli5_{strategy_name}")

        img_result = await generate_v5_room_images(
            listing_id=int(listing_id),
            strategy_name=strategy_name,
            photo_clusters=_clusters_for_img or [],
            boq_aggregation=boq_agg,
            eli5=_eli5_for_img,
            delta_slots=delta_slots,
            db=db,
            call_gemini_image=call_gemini_image,
            call_gemini_json=call_gemini_json,
            call_gemini=call_gemini,
        )
        logger.info(
            "v5_market_standard: Room images generated | listing_id=%s | ok=%d fail=%d",
            listing_id, img_result.get("images_generated", 0), img_result.get("images_failed", 0),
        )
    else:
        logger.info("v5_market_standard: Room images reused | listing_id=%s", listing_id)

    # Build v2_delta_{strategy} from V5 delta slots (frontend needs both delta + boq to show a package)
    delta_key_v2 = f"v2_delta_{strategy_name}"
    existing_delta = await db.get_unified_estimate(listing_id, delta_key_v2)
    if not existing_delta:
        v5_delta = delta_slots  # already loaded above
        if v5_delta and isinstance(v5_delta, dict) and v5_delta.get("rooms"):
            dimension_deltas: Dict[str, Any] = {}
            for room in v5_delta.get("rooms") or []:
                rid = str(room.get("room_id") or room.get("cluster_id") or "unknown")
                for slot in room.get("slots") or []:
                    action = str(slot.get("action") or "")
                    if action.lower() in ("no_change", "sin_cambio", ""):
                        continue
                    dim = str(slot.get("dimension") or "general")
                    dimension_deltas.setdefault(dim, {"room_scopes": []})
                    # Find or create room scope for this dimension
                    room_scope = None
                    for rs in dimension_deltas[dim]["room_scopes"]:
                        if rs.get("room_name") == rid:
                            room_scope = rs
                            break
                    if not room_scope:
                        room_scope = {"room_name": rid, "specification_strategy": "", "cost_components": []}
                        dimension_deltas[dim]["room_scopes"].append(room_scope)
                    room_scope["cost_components"].append({
                        "action": action,
                        "element": str(slot.get("slot_id") or ""),
                        "description": str(slot.get("work_sentence") or action),
                    })
            delta_v2 = {"strategy_name": strategy_name, "dimension_deltas": dimension_deltas}
            await db.save_unified_estimate(listing_id, delta_key_v2, delta_v2)
            logger.info("v5_market_standard: saved %s | listing_id=%s", delta_key_v2, listing_id)

    return {
        "listing_id": int(listing_id),
        "strategy_name": strategy_name,
        "schema_version": "v5_market_standard_run_v1",
        "created_at": _now_iso(),
        "counts": {
            "comparables_considered": len(comparables or []),
            "comparable_room_pirs": len(((await db.get_unified_estimate(listing_id, f"v5_selected_comparable_room_pirs_{selected_id}")) or {}).get("rooms") or []),
            "rooms": len((target_pir.get("rooms") or [])),
            "work_items": len((work_items.get("items") or [])),
        },
        "artifact_keys": {
            "target_pir": "v5_pir_target",
            "selected_comparable": "v5_selected_comparable",
            "selected_comparable_slot_standard": std_key,
            "delta_slots": "v5_delta_slots_market_standard",
            "work_items": "v5_work_items_market_standard",
            "v4_run_summary": f"v4_run_summary_{strategy_name}",
            "eli5": f"v5_eli5_{strategy_name}",
            "generated_images": f"v5_generated_images_{strategy_name}",
        },
        "v4_tail_summary": v4_summary,
    }

