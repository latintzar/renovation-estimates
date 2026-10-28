"""
Queue Scheduler (v3)
====================

Single place to define the *wired* pipeline job graph.

WHY THIS MATTERS:
- Prevents "hidden legacy" from multiple orchestrators doing similar work.
- Makes the actual pipeline explicit: enqueue graph → worker executes handlers.
- Lets routes/scripts reuse the same scheduler logic (no drift).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_run_id(listing_id: int, now: Optional[datetime] = None) -> str:
    dt = now or datetime.utcnow()
    return f"run_{listing_id}_{dt.strftime('%Y%m%d_%H%M%S')}"

def _idem_key(run_id: str, listing_id: int, suffix: str) -> str:
    """
    Build a run-scoped idempotency key.

    WHY THIS MATTERS: We frequently re-run pipelines for the same listing while iterating.
    If idempotency keys aren't scoped to run_id, a "new run" can't enqueue jobs because
    it collides with old jobs from prior runs (creating empty runs and muddy status).
    """
    return f"run:{run_id}:listing:{listing_id}:{suffix}"


async def enqueue_v3_run(db: Any, listing_id: int, run_id: Optional[str] = None) -> str:
    """
    Enqueue the full V3 pipeline run for a listing into pipeline_jobs.

    Returns:
      run_id (string)
    """
    rid = run_id or build_run_id(listing_id)

    ok = await db.create_pipeline_run(run_id=rid, listing_id=listing_id, config={"mode": "queue", "pipeline": "v3"})
    if not ok:
        raise RuntimeError("create_pipeline_run failed")

    # Stage: comparables (must run first)
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="comparables",
        job_type="fetch_comparables",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "fetch_comparables"),
    )

    # Stage: target clustering
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="clustering",
        job_type="cluster_target_photos",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "cluster_target_photos"),
    )

    # Stage: Smart M2 (target takeoff / IndoorGML-lite ledger)
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="smart_m2",
        job_type="smart_m2_target_indoorgml",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "smart_m2_target_indoorgml"),
    )

    # Stage: target PIR (room-by-room; requires clusters + smart_m2)
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="pir",
        job_type="generate_target_pir",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "generate_target_pir"),
    )

    # Strategy selection + v3 delta scopes split
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="strategy",
        job_type="strategy_selection",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "strategy_selection"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="delta_scopes",
        job_type="delta_strategy_spec",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "delta_strategy_spec"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="delta_scopes",
        job_type="delta_bcca_worklist",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "delta_bcca_worklist"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="delta_scopes",
        job_type="validate_and_repair_worklist",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "validate_and_repair_worklist"),
    )

    # V3 BOQ + coverage ledger
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="boq_v3",
        job_type="v3_boq_generate",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "v3_boq_generate"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="boq_v3",
        job_type="coverage_ledger_glue",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "coverage_ledger_glue"),
    )

    logger.info(f"Enqueued V3 pipeline run | run_id={rid} | listing_id={listing_id}")
    return rid


async def enqueue_v5_run(
    db: Any,
    listing_id: int,
    *,
    strategy_name: str = "market_standard",
    run_id: Optional[str] = None,
    force: bool = False,
) -> str:
    """
    Enqueue a V5 (slot-first) run (single strategy: market_standard).

    Stages:
    - snapshot (fetch listing inputs once; persist for replay/debug)
    - comparables (reuse-only friendly) + snapshot persist
    - clustering (V5 constrained; overwrites photo_clusters)
    - room tags (deterministic from clusters)
    - target PIR (slot-first per room)
    - select ONE comparable (deterministic median price)
    - comparable clustering (selected comparable; canonical room types)
    - comparable room PIRs (per cluster) + aggregate to whole-property slot standard
    - market targets (single-strategy: market_standard)
    - delta slots (market_standard)
    - decompose → work items (market_standard)
    - V4 tail (BCCA match → quant plan → forage → BOQ) from V5 work items
    """
    from pipeline.v5_stages import V5_ORDERED_JOB_TYPES, get_stage_versions

    rid = run_id or build_run_id(listing_id)

    sname = str(strategy_name or "").strip()
    if sname != "market_standard":
        raise RuntimeError(
            f"enqueue_v5_run: only market_standard is supported | requested={strategy_name}"
        )

    planned_job_types: List[str] = [
        "v5_fetch_listing_snapshot",
        "fetch_comparables",
        "v5_fetch_comparables_snapshot",
        "v5_cluster_target_photos",
        "v5_room_tags",
        "v5_generate_target_pir_slots",
        "v5_select_median_comparable",
        "v5_cluster_selected_comparable_photos",
        "v5_generate_selected_comparable_room_pirs",
        "v5_delta_slots_market_standard",
        "v5_work_items_market_standard",
        "v5_smart_m2",
        "v5_bcca_match",
        "v5_quant_plan",
        "v5_forage",
        "v5_boq_assembly",
        "v5_finalize",
        "v5_eli5",
        "v5_negotiation",
        "v5_room_images",
        "v5_translations",
    ]
    if planned_job_types != V5_ORDERED_JOB_TYPES:
        raise RuntimeError(
            "enqueue_v5_run drift: scheduler job order does not match V5 stage registry "
            f"| planned={planned_job_types} | registry={V5_ORDERED_JOB_TYPES}"
        )

    # Only create the run after we've validated the registry order.
    # WHY THIS MATTERS: if the drift check fails, we do NOT want to create empty runs.
    ok = await db.create_pipeline_run(
        run_id=rid,
        listing_id=listing_id,
        config={
            "mode": "queue",
            "pipeline": "v5",
            "stage_versions": get_stage_versions(),
        },
    )
    if not ok:
        raise RuntimeError("create_pipeline_run failed")

    # Snapshot: fetch listing inputs (photos + minimal meta) for replay/debug.
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="snapshot",
        job_type="v5_fetch_listing_snapshot",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_fetch_listing_snapshot"),
    )

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="comparables",
        job_type="fetch_comparables",
        payload={},
        idempotency_key=_idem_key(rid, listing_id, "fetch_comparables"),
    )

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="comparables",
        job_type="v5_fetch_comparables_snapshot",
        payload={"force": bool(force), "max_comparables": 20},
        idempotency_key=_idem_key(rid, listing_id, "v5_fetch_comparables_snapshot"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="clustering",
        job_type="v5_cluster_target_photos",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_cluster_target_photos"),
    )

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_room_tags",
        job_type="v5_room_tags",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_room_tags"),
    )

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_pir",
        job_type="v5_generate_target_pir_slots",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_generate_target_pir_slots"),
    )

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_select",
        job_type="v5_select_median_comparable",
        payload={"force": bool(force), "price_field": "sale_price"},
        idempotency_key=_idem_key(rid, listing_id, "v5_select_median_comparable"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_comparables",
        job_type="v5_cluster_selected_comparable_photos",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_cluster_selected_comparable_photos"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_comparables",
        job_type="v5_generate_selected_comparable_room_pirs",
        payload={"force": bool(force), "max_photos_per_room": 8},
        idempotency_key=_idem_key(rid, listing_id, "v5_generate_selected_comparable_room_pirs"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_delta",
        job_type="v5_delta_slots_market_standard",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_delta_slots_market_standard"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="v5_decompose",
        job_type="v5_work_items_market_standard",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_work_items_market_standard"),
    )
    # ── V4-tail sub-stages (construction pricing engine) ──
    # Order: smart_m2 → bcca_match → quant_plan → forage → boq_assembly
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_smart_m2", job_type="v5_smart_m2",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_smart_m2"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_bcca_match", job_type="v5_bcca_match",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_bcca_match"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_quant_plan", job_type="v5_quant_plan",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_quant_plan"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_forage", job_type="v5_forage",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_forage"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_boq_assembly", job_type="v5_boq_assembly",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_boq_assembly"),
    )

    # ── Presentation sub-stages ──
    # Order: finalize → eli5 → room_images
    #
    # WHY THIS MATTERS: `v5_finalize` writes `v2_delta_market_standard` used by the frontend
    # alongside `v2_market_standard`. It's safe and cheap, and makes the UI usable immediately
    # even while ELI5 / reports / images are still processing.
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_finalize", job_type="v5_finalize",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_finalize"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_eli5", job_type="v5_eli5",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_eli5"),
    )
    # ── Negotiation advisor — data-driven price negotiation strategy ──
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_negotiation", job_type="v5_negotiation",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_negotiation"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_room_images", job_type="v5_room_images",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_room_images"),
    )
    # ── Translations — pre-compute all language translations for instant switching ──
    await db.enqueue_pipeline_job(
        run_id=rid, listing_id=listing_id,
        stage="v5_translations", job_type="v5_translations",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "v5_translations"),
    )

    logger.info(f"Enqueued V5 pipeline run | run_id={rid} | listing_id={listing_id} | strategy=market_standard")
    return rid


async def enqueue_gla_run(
    db: Any,
    listing_id: int,
    *,
    run_id: Optional[str] = None,
    force: bool = False,
) -> str:
    """
    Enqueue a GLA (General Listing Analysis) run.

    GLA is a no-comparables "light" pipeline intended to power the WhatsApp agent:
    snapshot → clustering → room tags → target PIR → smart_m2 → opinion.
    """
    from pipeline.gla_stages import GLA_ORDERED_JOB_TYPES, get_gla_stage_versions

    rid = run_id or build_run_id(listing_id)

    planned_job_types: List[str] = [
        "gla_fetch_listing_snapshot",
        "gla_cluster_target_photos",
        "gla_room_tags",
        "gla_generate_target_pir_slots",
        "gla_smart_m2",
        "gla_opinion",
    ]
    if planned_job_types != GLA_ORDERED_JOB_TYPES:
        raise RuntimeError(
            "enqueue_gla_run drift: scheduler job order does not match GLA stage registry "
            f"| planned={planned_job_types} | registry={GLA_ORDERED_JOB_TYPES}"
        )

    ok = await db.create_pipeline_run(
        run_id=rid,
        listing_id=listing_id,
        config={
            "mode": "queue",
            "pipeline": "gla",
            "stage_versions": get_gla_stage_versions(),
        },
    )
    if not ok:
        raise RuntimeError("create_pipeline_run failed")

    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="snapshot",
        job_type="gla_fetch_listing_snapshot",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_fetch_listing_snapshot"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="clustering",
        job_type="gla_cluster_target_photos",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_cluster_target_photos"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="room_tags",
        job_type="gla_room_tags",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_room_tags"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="pir",
        job_type="gla_generate_target_pir_slots",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_generate_target_pir_slots"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="smart_m2",
        job_type="gla_smart_m2",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_smart_m2"),
    )
    await db.enqueue_pipeline_job(
        run_id=rid,
        listing_id=listing_id,
        stage="opinion",
        job_type="gla_opinion",
        payload={"force": bool(force)},
        idempotency_key=_idem_key(rid, listing_id, "gla_opinion"),
    )

    logger.info(f"Enqueued GLA pipeline run | run_id={rid} | listing_id={listing_id}")
    return rid


async def enqueue_v2_run(db: Any, listing_id: int, run_id: Optional[str] = None) -> str:
    """
    Backwards-compatible wrapper for v2 routes.

    Routes to V5 (slot-first) pipeline — the current production pipeline.
    V3 is deprecated; rollback is via git history.
    """
    logger.info("enqueue_v2_run routed to V5 pipeline")
    return await enqueue_v5_run(db=db, listing_id=listing_id, run_id=run_id)

