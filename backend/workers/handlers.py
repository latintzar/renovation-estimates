import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from config import settings
logger = logging.getLogger("pipeline_worker.handlers")


# Global throttles (process-wide). These are the knobs for 100-listing scaling.
DB_WRITE_SEMAPHORE = asyncio.Semaphore(1)
STORAGE_UPLOAD_SEMAPHORE = asyncio.Semaphore(2)
IMAGE_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(10)

# Gemini throttles by alias
GEMINI_PRO_SEMAPHORE = asyncio.Semaphore(int(os.getenv("GEMINI_PRO_CONCURRENCY", "30")))
GEMINI_FLASH_SEMAPHORE = asyncio.Semaphore(int(os.getenv("GEMINI_FLASH_CONCURRENCY", "30")))
GEMINI_IMAGE_SEMAPHORE = asyncio.Semaphore(int(os.getenv("GEMINI_IMAGE_CONCURRENCY", "2")))


def _feature_flag(features: Any, candidates: List[str]) -> Optional[bool]:
    """Best-effort feature detection from listing features payload."""
    if not features:
        return None
    if isinstance(features, dict):
        for key in candidates:
            val = features.get(key)
            if isinstance(val, bool) and val:
                return True
        return None
    if isinstance(features, list):
        joined = " ".join([str(x).lower() for x in features])
        return True if any(c in joined for c in candidates) else None
    return None


def _build_listing_context(listing: Dict[str, Any]) -> str:
    title = listing.get("title") or "N/A"
    bedrooms = listing.get("bedrooms") or "N/A"
    bathrooms = listing.get("bathrooms") or "N/A"
    city = listing.get("city") or "N/A"
    area = listing.get("sqm") or listing.get("area") or "N/A"
    property_type = listing.get("property_type") or listing.get("scraped_data", {}).get("property_type") or "N/A"
    floor_level = listing.get("floor_level") or listing.get("scraped_data", {}).get("floor_level") or "N/A"
    year_built = listing.get("construction_year") or listing.get("year_built") or "N/A"
    price = listing.get("price") or listing.get("asking_price") or "N/A"
    description = (listing.get("description") or listing.get("scraped_data", {}).get("description") or "").strip()
    if len(description) > 800:
        description = description[:800] + "..."
    return (
        "PROPERTY CONTEXT:\n"
        f"- Title: {title}\n"
        f"- Bedrooms: {bedrooms}\n"
        f"- Bathrooms: {bathrooms}\n"
        f"- City: {city}\n"
        f"- Area: {area}\n"
        f"- Property Type: {property_type}\n"
        f"- Floor Level: {floor_level}\n"
        f"- Year Built: {year_built}\n"
        f"- Price: {price}\n"
        f"- Description: {description or 'N/A'}"
    )


def _idem_key(run_id: str, listing_id: int, suffix: str) -> str:
    return f"run:{run_id}:listing:{listing_id}:{suffix}"


class RescheduleRequested(RuntimeError):
    """
    Signal to the worker that the current job was intentionally requeued.

    WHY THIS MATTERS: prerequisite waits are neither success nor hard failure.
    """


async def _reschedule_job(
    job: Dict[str, Any],
    db: Any,
    reason: str,
    delay_seconds: int = 30,
    max_wait_attempts: int = 20,
) -> None:
    """
    Re-queue the same job for later without counting it as a failure.

    WHY THIS MATTERS: With 30-parallel workers, downstream jobs can be claimed before
    prerequisites are ready. We reschedule instead of failing to keep the pipeline stable.
    """
    run_id = job.get("run_id")
    listing_id = job.get("listing_id")
    job_id = job.get("id")
    job_type = job.get("job_type")
    payload = job.get("payload") or {}
    wait_attempts = int(payload.get("_wait_attempts", 0)) + 1
    if not job_id:
        raise RuntimeError(f"{job_type}: missing job.id for reschedule | listing_id={listing_id}")

    if wait_attempts > max_wait_attempts:
        raise RuntimeError(f"{job_type}: wait exceeded ({wait_attempts}) | {reason} | listing_id={listing_id}")

    next_payload = {
        **payload,
        "_wait_attempts": wait_attempts,
        "_wait_reason": reason,
    }
    available_at = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
    ok = await db.requeue_pipeline_job(
        job_id=str(job_id),
        payload=next_payload,
        available_at=available_at,
        reason=f"waiting: {reason}",
    )
    if not ok:
        raise RuntimeError(f"{job_type}: failed to requeue waiting job | listing_id={listing_id} | reason={reason}")

    msg = f"{job_type}: waiting | attempt={wait_attempts} | {reason} | listing_id={listing_id} | run_id={run_id}"
    logger.info(msg)
    raise RescheduleRequested(msg)


async def handle_fetch_comparables(job: Dict[str, Any], db: Any) -> None:
    """Fetch and persist comparables + market stats, then enqueue comparable jobs."""
    listing_id = job["listing_id"]
    run_id = job.get("run_id")
    if not run_id:
        raise RuntimeError(f"fetch_comparables: missing run_id | listing_id={listing_id}")

    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"fetch_comparables: listing not found | listing_id={listing_id}")

    lat = listing.get("lat")
    lng = listing.get("lng")
    if not lat or not lng:
        raise RuntimeError(f"fetch_comparables: missing lat/lng | listing_id={listing_id}")

    scraped = listing.get("scraped_data") or {}
    # Fall back to scraped_data.features when the top-level column is empty.
    # The scraper stores features as Spanish strings like ["Terraza", "Jardín", "Trastero"]
    # while the top-level column is often left as an empty [].
    features = listing.get("features") or scraped.get("features") or []

    # ── Resolve property attributes ──────────────────────────────────
    # scraped_data is the primary source (the scraper always populates it).
    # Top-level DB columns are overrides when present.
    property_type = listing.get("property_type") or scraped.get("property_type") or scraped.get("property_subtype") or "apartment"

    def _int_or(primary, *fallbacks):
        """Return first truthy int from primary value or fallback keys in scraped_data."""
        if primary is not None:
            try:
                return int(primary)
            except (ValueError, TypeError):
                pass
        for key in fallbacks:
            val = scraped.get(key)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
        return None

    bedrooms = _int_or(listing.get("bedrooms"), "bedrooms")
    bathrooms = _int_or(listing.get("bathrooms"), "bathrooms")
    total_area = _int_or(listing.get("sqm"), "m2_built", "m2_useful")
    plot_area = _int_or(listing.get("m2_plot"), "m2_plot")

    # ── Energy rating: ask Casafari for comps at least one level above target ──
    from clients.casafari_client import energy_ratings_above
    target_energy = scraped.get("energy_rating") or listing.get("energy_rating")
    energy_ratings = energy_ratings_above(target_energy)

    logger.info(
        f"fetch_comparables: resolved params | listing_id={listing_id} | "
        f"type={property_type} beds={bedrooms} baths={bathrooms} "
        f"m2={total_area} plot={plot_area} energy_target={target_energy} "
        f"energy_filter={energy_ratings}"
    )

    # ── Feature detection ────────────────────────────────────────────
    has_terrace = _feature_flag(features, ["terrace", "terraza"])
    has_balcony = _feature_flag(features, ["balcony", "balcon", "balcón"])
    has_pool    = _feature_flag(features, ["pool", "piscina"])
    has_garage  = _feature_flag(features, ["garage", "garaje"])
    has_garden  = _feature_flag(features, ["garden", "jardin", "jardín"])
    has_storage = _feature_flag(features, ["storage", "trastero"])
    has_parking = _feature_flag(features, ["parking", "aparcamiento", "plaza"])

    logger.info(
        f"fetch_comparables: features source ({len(features)} items) | listing_id={listing_id} | "
        f"terrace={has_terrace} balcony={has_balcony} pool={has_pool} "
        f"garage={has_garage} garden={has_garden} storage={has_storage} parking={has_parking}"
    )

    search_params = {
        "property_type": property_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "total_area": total_area,
        "plot_area": plot_area,
        "energy_ratings": energy_ratings,
        "has_elevator": listing.get("has_elevator"),
        "has_terrace": has_terrace,
        "has_balcony": has_balcony,
        "has_pool": has_pool,
        "has_garage": has_garage,
        "has_garden": has_garden,
        "has_storage": has_storage,
        "has_parking": has_parking,
        "floor_level": listing.get("floor_level") or scraped.get("floor_level"),
    }
    search_params = {k: v for k, v in search_params.items() if v is not None}

    from clients.casafari_client import fetch_comparables_with_full_photos

    def _prefer_thumbnails(row: Dict[str, Any]) -> Dict[str, Any]:
        features = row.get("features") or {}
        thumbs = (
            row.get("photo_urls_thumbnails")
            or features.get("photo_urls_thumbnails")
            or []
        )
        if isinstance(thumbs, list) and thumbs:
            row["photo_urls"] = thumbs
        return row

    existing = await db.get_listing_comparables(listing_id)
    reuse_only = settings.CASAFARI_REUSE_ONLY
    if reuse_only:
        logger.info(f"fetch_comparables: reuse-only enabled | listing_id={listing_id} | existing={len(existing)}")

    # If we're in reuse-only mode, treat listing_market_stats.raw_filtered_comparables as the
    # durable source-of-truth and (re)hydrate listing_comparables from it.
    #
    # WHY THIS MATTERS:
    # - Casafari calls are expensive; reuse-only must NEVER trigger paid API calls.
    # - We should use ALL comparables that passed our filters previously (non-lossy).
    # - The DB table may be empty/partial from past crashes; hydration makes runs reliable.
    if reuse_only:
        market_stats = await db.get_listing_market_stats(listing_id)
        cached_rows = (market_stats or {}).get("raw_filtered_comparables") or []
        if cached_rows:
            cached_rows = [_prefer_thumbnails(dict(row)) for row in cached_rows]
            if len(existing) != len(cached_rows):
                logger.info(
                    "fetch_comparables: hydrating listing_comparables from cached raw_filtered_comparables "
                    f"| listing_id={listing_id} | cached_rows={len(cached_rows)} | existing_before={len(existing)}"
                )
                ok = await db.replace_listing_comparables(listing_id, cached_rows)
                if not ok:
                    raise RuntimeError(f"fetch_comparables: hydrate comparables failed | listing_id={listing_id}")
                existing = await db.get_listing_comparables(listing_id)
            if not existing:
                raise RuntimeError(f"fetch_comparables: hydrate produced zero rows | listing_id={listing_id}")
        elif not existing:
            raise RuntimeError(
                f"fetch_comparables: CASAFARI_REUSE_ONLY=true but no cached rows and table empty | listing_id={listing_id}"
            )

    rows: List[Dict[str, Any]] = []
    if not existing:
        if not settings.CASAFARI_ENABLED:
            raise RuntimeError(
                f"fetch_comparables: casafari disabled and no existing comps | listing_id={listing_id}"
            )
        result = await fetch_comparables_with_full_photos(
            latitude=lat,
            longitude=lng,
            property_type=property_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            total_area=total_area,
            plot_area=plot_area,
            energy_ratings=energy_ratings,
            has_elevator=listing.get("has_elevator"),
            has_terrace=search_params.get("has_terrace"),
            has_balcony=search_params.get("has_balcony"),
            has_pool=search_params.get("has_pool"),
            has_garage=search_params.get("has_garage"),
            has_garden=search_params.get("has_garden"),
            has_storage=search_params.get("has_storage"),
            has_parking=search_params.get("has_parking"),
            floor_level=search_params.get("floor_level"),
        )

        for comp in result.comparables:
            features = comp.features or {}
            features_enriched = {
                **features,
                "photo_urls_full": comp.photo_urls_full,
                "photo_urls_thumbnails": comp.photo_urls_thumbnails,
            }
            rows.append(
                {
                    "casafari_property_id": comp.property_id,
                    "price_bucket": comp.price_bucket,
                    "sale_price": comp.sale_price,
                    "price_per_sqm": comp.price_per_sqm,
                    "total_area": comp.total_area,
                    "living_area": comp.living_area,
                    "plot_area": comp.plot_area,
                    "bedrooms": comp.bedrooms,
                    "bathrooms": comp.bathrooms,
                    "condition": comp.condition,
                    "construction_year": comp.construction_year,
                    "energy_rating": comp.energy_rating,
                    "distance_km": comp.distance_km,
                    "address": comp.address,
                    "property_url": comp.property_url,
                    "photo_urls": comp.photo_urls,
                    "coordinates": comp.coordinates,
                    "features": features_enriched,
                }
            )
    else:
        for comp in existing:
            comp = _prefer_thumbnails(dict(comp))
            rows.append(
                {
                    "casafari_property_id": comp.get("casafari_property_id"),
                    "price_bucket": comp.get("price_bucket"),
                    "sale_price": comp.get("sale_price"),
                    "price_per_sqm": comp.get("price_per_sqm"),
                    "total_area": comp.get("total_area"),
                    "living_area": comp.get("living_area"),
                    "plot_area": comp.get("plot_area"),
                    "bedrooms": comp.get("bedrooms"),
                    "bathrooms": comp.get("bathrooms"),
                    "condition": comp.get("condition"),
                    "construction_year": comp.get("construction_year"),
                    "energy_rating": comp.get("energy_rating"),
                    "distance_km": comp.get("distance_km"),
                    "address": comp.get("address"),
                    "property_url": comp.get("property_url"),
                    "photo_urls": comp.get("photo_urls") or [],
                    "coordinates": comp.get("coordinates") or {},
                    "features": comp.get("features") or {},
                }
            )

    min_photos = 10

    filtered_rows: List[Dict[str, Any]] = []
    skipped_price = 0
    skipped_photos = 0
    for row in rows:
        photo_count = len(row.get("photo_urls") or [])
        if photo_count < min_photos:
            skipped_photos += 1
            continue
        filtered_rows.append(row)

    logger.info(
        f"fetch_comparables: filtered comparables | total={len(rows)} | kept={len(filtered_rows)} "
        f"| dropped_photos={skipped_photos} | dropped_price={skipped_price}"
    )

    if not filtered_rows:
        raise RuntimeError(f"fetch_comparables: no comparables after filtering | listing_id={listing_id}")

    # ── Price/m² analysis ─────────────────────────────────────────
    # WHY: We dropped total_area from Casafari filters to get the
    # neighborhood "vibe" — more comps across different sizes. Now we
    # compute median price/m² ourselves and apply it to THIS listing's
    # area. This is more accurate than Casafari's own estimates because
    # those are skewed by the filter set.
    listing_price = float(listing.get("price_eur") or 0)
    listing_area = float(total_area or 0)

    comp_price_per_sqm_values = []
    for row in filtered_rows:
        p = row.get("sale_price") or 0
        a = row.get("total_area") or row.get("living_area") or 0
        if p > 0 and a > 0:
            comp_price_per_sqm_values.append(p / a)

    comp_psm_stats = {}
    if comp_price_per_sqm_values:
        sorted_psm = sorted(comp_price_per_sqm_values)
        n = len(sorted_psm)
        median_psm = sorted_psm[n // 2] if n % 2 == 1 else (sorted_psm[n // 2 - 1] + sorted_psm[n // 2]) / 2
        avg_psm = sum(sorted_psm) / n

        renovated_value_median = median_psm * listing_area if listing_area > 0 else 0
        renovated_value_avg = avg_psm * listing_area if listing_area > 0 else 0
        value_add_median = renovated_value_median - listing_price if listing_price > 0 else 0
        value_add_avg = renovated_value_avg - listing_price if listing_price > 0 else 0

        comp_psm_stats = {
            "comp_count": n,
            "comp_median_price_per_sqm": round(median_psm, 2),
            "comp_avg_price_per_sqm": round(avg_psm, 2),
            "comp_min_price_per_sqm": round(min(sorted_psm), 2),
            "comp_max_price_per_sqm": round(max(sorted_psm), 2),
            "renovated_value_median": round(renovated_value_median),
            "renovated_value_avg": round(renovated_value_avg),
            "value_add_median": round(value_add_median),
            "value_add_avg": round(value_add_avg),
            "listing_price": round(listing_price),
            "listing_area_sqm": round(listing_area),
        }
        logger.info(
            f"fetch_comparables: price/m² analysis | listing_id={listing_id} | "
            f"comps={n} | median={median_psm:,.0f}/m² | avg={avg_psm:,.0f}/m² | "
            f"renovated_median=€{renovated_value_median:,.0f} | "
            f"value_add=€{value_add_median:+,.0f}"
        )
    else:
        logger.warning(f"fetch_comparables: no valid price/m² data from comps | listing_id={listing_id}")

    if not existing:
        stats = {}
        market_stats = result.market_stats
        if market_stats:
            stats = {
                "average_price": market_stats.average_price,
                "average_price_per_sqm": market_stats.average_price_per_sqm,
                "average_days_on_market": market_stats.average_days_on_market,
                "sold_last_6_months": market_stats.sold_last_6_months,
                "casafari_fast_sell": market_stats.fast_sell_price,
                "casafari_fair_market": market_stats.fair_market_price,
                "casafari_premium": market_stats.out_of_market_price,
                "casafari_link": market_stats.casafari_link,
            }
        # Store price/m² analysis in search_params (JSONB), not as top-level
        # columns — listing_market_stats only has fixed integer columns for
        # Casafari's own stats. Our computed stats ride in search_params.
        search_params = search_params or {}
        if comp_psm_stats:
            search_params["comp_psm_analysis"] = comp_psm_stats
        try:
            from pathlib import Path

            repo_root = Path(__file__).resolve().parents[2]
            out_dir = repo_root / "docs" / "reference" / "casafari" / f"listing_{listing_id}"
            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            raw_path = out_dir / f"casafari_raw_{stamp}.json"
            filtered_path = out_dir / f"casafari_filtered_{stamp}.json"
            raw_path.write_text(json.dumps(result.raw_response, indent=2, ensure_ascii=False), encoding="utf-8")
            filtered_path.write_text(json.dumps(filtered_rows, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(
                f"fetch_comparables: saved raw response | listing_id={listing_id} | raw={raw_path} | filtered={filtered_path}"
            )
        except Exception:
            logger.exception(f"fetch_comparables: failed to save raw response locally | listing_id={listing_id}")
        ok = await db.save_listing_market_stats(
            listing_id,
            stats,
            search_params,
            raw_casafari_response=result.raw_response,
            raw_filtered_comparables=filtered_rows,
        )
        if not ok:
            raise RuntimeError(f"fetch_comparables: save market stats failed | listing_id={listing_id}")

    if not reuse_only:
        ok = await db.replace_listing_comparables(listing_id, filtered_rows)
        if not ok:
            raise RuntimeError(f"fetch_comparables: save comparables failed | listing_id={listing_id}")

    existing = await db.get_listing_comparables(listing_id)
    if not existing:
        raise RuntimeError(f"fetch_comparables: no comparables saved | listing_id={listing_id}")
    else:
        existing = [
            comp for comp in existing
            if comp.get("casafari_property_id") in {row.get("casafari_property_id") for row in filtered_rows}
        ]
        if not existing:
            raise RuntimeError(f"fetch_comparables: reuse-only filtered to zero comps | listing_id={listing_id}")

    # NOTE: old pipeline enqueued "generate_comparable_pir" per comparable here.
    # V5 replaced this with v5_generate_selected_comparable_room_pirs (stage v5_comparables)
    # which only runs PIR on the ONE selected comparable, not all of them.
    # Removed to avoid wasting Gemini calls and creating jobs outside the V5 stage set
    # (stage="pir" is not in V5_STAGE_SEQUENCE, so clear-from-stage could never clean them).
    logger.info(
        "fetch_comparables: %d comparables ready for V5 pipeline | listing_id=%s",
        len(existing),
        listing_id,
    )


async def handle_cluster_target(job: Dict[str, Any], db: Any) -> None:
    """Cluster target listing photos (idempotent)."""
    listing_id = job["listing_id"]

    existing = await db.get_photo_clusters(listing_id)
    if existing:
        logger.info(f"cluster_target: skip (clusters exist) | listing_id={listing_id} | clusters={len(existing)}")
        return

    from pipeline.steps.cluster_photos import cluster_photos, refine_clusters

    photo_urls = await db.get_listing_photos(listing_id)
    if not photo_urls:
        raise RuntimeError(f"cluster_target: no photos | listing_id={listing_id}")

    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"cluster_target: listing not found | listing_id={listing_id}")
    listing_context = _build_listing_context(listing)
    property_flags = listing.get("property_flags") or listing.get("flags") or []

    async with GEMINI_PRO_SEMAPHORE:
        result = await cluster_photos(
            photo_urls=photo_urls,
            listing_context=listing_context,
            property_flags=property_flags,
        )
        refined_clusters = await refine_clusters(
            photo_urls=photo_urls,
            listing_context=listing_context,
            initial_clusters=result.get("clusters", []),
            excluded_content=result.get("excluded_content", []),
        )
        result["clusters"] = refined_clusters

    clusters = result.get("clusters", [])
    if not clusters:
        raise RuntimeError(f"cluster_target: no clusters | listing_id={listing_id}")

    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_photo_clusters(
            listing_id,
            clusters,
            excluded_content=result.get("excluded_content", []),
            ai_image_summary=result.get("ai_image_summary", {}),
        )
    if not ok:
        raise RuntimeError(f"cluster_target: save failed | listing_id={listing_id}")


async def handle_v5_cluster_target_photos(job: Dict[str, Any], db: Any) -> None:
    """
    V5 constrained clustering (canonical room types + numbered cluster ids).

    IMPORTANT: This stage is authoritative for V5 runs. It OVERWRITES existing clusters
    when payload.force=true.

    Writes:
      - photo_clusters (overwritten via save_photo_clusters delete+insert)
      - unified_estimates: v5_clusters (raw V5 clustering output for replay/debug)

    Payload:
      - force (bool)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    existing = await db.get_photo_clusters(listing_id)
    if existing and not force:
        logger.info(f"v5_cluster_target: skip (clusters exist) | listing_id={listing_id} | clusters={len(existing)}")
        return

    from pipeline.steps.cluster_photos_v5 import cluster_photos_v5

    photo_urls = await db.get_listing_photos(listing_id)
    if not photo_urls:
        raise RuntimeError(f"v5_cluster_target: no photos | listing_id={listing_id}")

    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_cluster_target: listing not found | listing_id={listing_id}")
    listing_context = _build_listing_context(listing)
    property_flags = listing.get("property_flags") or listing.get("flags") or []

    async with GEMINI_PRO_SEMAPHORE:
        result = await cluster_photos_v5(
            photo_urls=photo_urls,
            listing_context=listing_context,
            property_flags=property_flags,
        )

    clusters = result.get("clusters", [])
    if not clusters:
        raise RuntimeError(f"v5_cluster_target: no clusters | listing_id={listing_id}")

    # Persist raw artifact for replay/debug.
    async with DB_WRITE_SEMAPHORE:
        ok_art = await db.save_unified_estimate(
            listing_id,
            "v5_clusters",
            {
                "listing_id": int(listing_id),
                "schema_version": "v5_clusters_v1",
                "clusters": clusters,
                "excluded_content": result.get("excluded_content") or [],
                "version": result.get("version") or "v5",
            },
        )
    if not ok_art:
        raise RuntimeError(f"v5_cluster_target: failed to save v5_clusters artifact | listing_id={listing_id}")

    # Overwrite clusters in photo_clusters.
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_photo_clusters(
            listing_id,
            clusters,
            excluded_content=result.get("excluded_content", []),
            ai_image_summary={"version": "v5", "note": "v5 constrained clustering"},
        )
    if not ok:
        raise RuntimeError(f"v5_cluster_target: save failed | listing_id={listing_id}")


async def handle_v5_fetch_listing_snapshot(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Listing Snapshot (deterministic fetch + persist).

    Writes:
      - unified_estimates: v5_listing_snapshot

    Payload:
      - force (bool)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_listing_snapshot")
    if isinstance(existing, dict) and existing.get("listing_id") == listing_id and isinstance(existing.get("photo_urls"), list):
        logger.info("v5_listing_snapshot: skip (exists) | listing_id=%s photos=%s", listing_id, len(existing.get("photo_urls") or []))
        return

    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_listing_snapshot: listing not found | listing_id={listing_id}")
    photo_urls = await db.get_listing_photos(listing_id)
    if not photo_urls:
        raise RuntimeError(f"v5_listing_snapshot: no photos | listing_id={listing_id}")

    # Keep snapshot payload compact (avoid dumping full scraped_data blobs).
    snapshot = {
        "listing_id": int(listing_id),
        "schema_version": "v5_listing_snapshot_v1",
        "created_at": datetime.utcnow().isoformat(),
        "listing": {
            "id": listing_id,
            "title": listing.get("title"),
            "city": listing.get("city"),
            "property_type": listing.get("property_type") or (listing.get("scraped_data") or {}).get("property_type"),
            "bedrooms": listing.get("bedrooms"),
            "bathrooms": listing.get("bathrooms"),
            "sqm": listing.get("sqm") or listing.get("area"),
            "lat": listing.get("lat"),
            "lng": listing.get("lng"),
            "year_built": listing.get("year_built") or listing.get("construction_year"),
            "features": listing.get("features") or [],
        },
        "photo_urls": [str(u) for u in photo_urls if isinstance(u, str) and u.strip()],
        "counts": {"photos": len(photo_urls)},
    }

    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "v5_listing_snapshot", snapshot)
    if not ok:
        raise RuntimeError(f"v5_listing_snapshot: save failed | listing_id={listing_id}")


async def handle_v5_fetch_comparables_snapshot(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Comparables Snapshot (deterministic read + persist).

    NOTE:
    - The pipeline already fetches comparables into `listing_comparables`.
    - This stage persists the chosen comparable set (for replay/debug) under a stable key.

    Writes:
      - unified_estimates: v5_comparables

    Payload:
      - force (bool)
      - max_comparables (int, default 20)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    max_comps = int(payload.get("max_comparables") or 20)

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_comparables")
    if isinstance(existing, dict) and isinstance(existing.get("comparables"), list) and existing.get("comparables"):
        logger.info("v5_comparables: skip (exists) | listing_id=%s comps=%s", listing_id, len(existing.get("comparables") or []))
        return

    comps = await db.get_listing_comparables(listing_id)
    if not comps:
        await _reschedule_job(job, db, reason="v5_comparables: no listing_comparables yet", delay_seconds=30)
        return

    # Keep snapshot compact; include IDs + a few fields used for debugging.
    slim = []
    for c in comps[: max(1, max_comps)]:
        if not isinstance(c, dict):
            continue
        cid = c.get("casafari_property_id") or c.get("id") or c.get("comparable_id") or c.get("listing_id")
        if cid is None:
            continue
        slim.append(
            {
                "casafari_property_id": cid,
                "sale_price": c.get("sale_price"),
                "price_per_sqm": c.get("price_per_sqm"),
                "total_area": c.get("total_area"),
                "bedrooms": c.get("bedrooms"),
                "bathrooms": c.get("bathrooms"),
                "condition": c.get("condition"),
                "distance_km": c.get("distance_km"),
                "photo_count": len(c.get("photo_urls") or []),
            }
        )

    out = {
        "listing_id": int(listing_id),
        "schema_version": "v5_comparables_v1",
        "created_at": datetime.utcnow().isoformat(),
        "comparables": slim,
        "counts": {"comparables": len(slim)},
    }
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "v5_comparables", out)
    if not ok:
        raise RuntimeError(f"v5_comparables: save failed | listing_id={listing_id}")


async def handle_v5_room_tags(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Room Tags (deterministic tags derived from canonical clusters).

    Writes:
      - unified_estimates: v5_room_tags

    Preconditions:
      - photo_clusters exist (V5 constrained clustering recommended)

    Payload:
      - force (bool)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_room_tags")
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        logger.info("v5_room_tags: skip (exists) | listing_id=%s rooms=%s", listing_id, len(existing.get("rooms") or []))
        return

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="v5_room_tags: missing clusters", delay_seconds=30)
        return

    from pricing.v5_room_tags import build_room_tags_v5

    tags = build_room_tags_v5(listing_id=int(listing_id), clusters=clusters)
    out = {**tags, "schema_version": "v5_room_tags_v1", "created_at": datetime.utcnow().isoformat(), "counts": {"rooms": len(tags.get("rooms") or [])}}
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "v5_room_tags", out)
    if not ok:
        raise RuntimeError(f"v5_room_tags: save failed | listing_id={listing_id}")


async def handle_v5_cluster_selected_comparable_photos(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Comparable Clustering (selected-only; canonical room types).

    Writes:
      - unified_estimates: v5_selected_comparable_clusters_{comp_id} (includes excluded_content)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    selected = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    if not (isinstance(selected, dict) and selected.get("selected_comparable_id")):
        await _reschedule_job(job, db, reason="v5_cluster_selected_comparable: missing v5_selected_comparable", delay_seconds=30)
        return
    comp_id = int(selected.get("selected_comparable_id"))

    key = f"v5_selected_comparable_clusters_{comp_id}"
    existing = None if force else await db.get_unified_estimate(listing_id, key)
    if isinstance(existing, dict) and isinstance(existing.get("clusters"), list) and existing.get("clusters"):
        logger.info("v5_cluster_selected_comparable: skip (exists) | listing_id=%s comp_id=%s", listing_id, comp_id)
        return

    comps = await db.get_listing_comparables(listing_id)
    comp_row = None
    for c in comps or []:
        if not isinstance(c, dict):
            continue
        cid_raw = c.get("casafari_property_id") or c.get("id") or c.get("comparable_id") or c.get("listing_id")
        try:
            if int(cid_raw) == comp_id:
                comp_row = c
                break
        except Exception:
            continue
    if not comp_row:
        raise RuntimeError(f"v5_cluster_selected_comparable: comparable not found | listing_id={listing_id} comp_id={comp_id}")

    photo_urls = [str(u) for u in (comp_row.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
    if not photo_urls:
        raise RuntimeError(f"v5_cluster_selected_comparable: no photo_urls | comp_id={comp_id}")

    # Build a minimal context string (comparable rows are partial).
    ctx = (
        "COMPARABLE CONTEXT:\n"
        f"- property_id: {comp_id}\n"
        f"- bedrooms: {comp_row.get('bedrooms')}\n"
        f"- bathrooms: {comp_row.get('bathrooms')}\n"
        f"- total_area: {comp_row.get('total_area')}\n"
        f"- distance_km: {comp_row.get('distance_km')}\n"
    )

    from pipeline.steps.cluster_photos_v5 import cluster_photos_v5

    async with GEMINI_PRO_SEMAPHORE:
        result = await cluster_photos_v5(listing_context=ctx, photo_urls=photo_urls, property_flags=None)

    clusters = result.get("clusters") or []
    if not clusters:
        raise RuntimeError(f"v5_cluster_selected_comparable: no clusters returned | comp_id={comp_id}")

    artifact = {
        "listing_id": int(listing_id),
        "comparable_id": int(comp_id),
        "schema_version": "v5_comparable_clusters_v1",
        "created_at": datetime.utcnow().isoformat(),
        "clusters": clusters,
        "excluded_content": result.get("excluded_content") or [],
        "counts": {"clusters": len(clusters), "photos": len(photo_urls)},
    }
    async with DB_WRITE_SEMAPHORE:
        ok_art = await db.save_unified_estimate(listing_id, key, artifact)
    if not ok_art:
        raise RuntimeError(f"v5_cluster_selected_comparable: failed to save artifact | key={key} listing_id={listing_id}")


async def handle_v5_generate_selected_comparable_room_pirs(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Comparable Room PIRs (selected-only; per-cluster slot protocol).

    Writes:
      - unified_estimates:
          - v5_selected_comparable_room_pirs_{comp_id}
          - v5_selected_comparable_slot_standard_{comp_id}
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    max_photos_per_room = int(payload.get("max_photos_per_room") or 8)
    concurrency = int(payload.get("concurrency") or 5)
    if concurrency < 1:
        raise ValueError(f"v5_selected_comparable_room_pirs: concurrency must be >= 1 (got {concurrency})")

    selected = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    if not (isinstance(selected, dict) and selected.get("selected_comparable_id")):
        await _reschedule_job(job, db, reason="v5_selected_comparable_room_pirs: missing v5_selected_comparable", delay_seconds=30)
        return
    comp_id = int(selected.get("selected_comparable_id"))

    key_rooms = f"v5_selected_comparable_room_pirs_{comp_id}"
    key_std = f"v5_selected_comparable_slot_standard_{comp_id}"
    existing = None if force else await db.get_unified_estimate(listing_id, key_std)
    if isinstance(existing, dict) and isinstance(existing.get("slot_standard"), dict) and existing.get("slot_standard"):
        logger.info("v5_selected_comparable_room_pirs: skip (exists) | listing_id=%s comp_id=%s", listing_id, comp_id)
        return

    clusters_art = await db.get_unified_estimate(listing_id, f"v5_selected_comparable_clusters_{comp_id}")
    clusters = (clusters_art or {}).get("clusters") if isinstance(clusters_art, dict) else None
    if not (isinstance(clusters, list) and clusters):
        await _reschedule_job(job, db, reason="v5_selected_comparable_room_pirs: missing v5_selected_comparable_clusters", delay_seconds=30)
        return

    from pipeline.gemini_client import call_gemini, fetch_images_batch
    from pricing.v5_pir import generate_v5_target_room_pir
    from pricing.v5_comparable_standard import build_v5_comparable_slot_standard

    rooms_out: List[Dict[str, Any]] = []
    room_jobs: List[Dict[str, Any]] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        rt = str(c.get("room_type") or "").strip() or "unknown_room"
        # Skip clearly non-room content if it slipped in.
        if rt in ("floorplan", "street_view", "views_outlook", "unknown_exterior"):
            continue
        rid = str(c.get("cluster_id") or c.get("cluster_name") or "").strip() or rt
        urls = [str(u) for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        if not urls:
            continue
        urls = urls[: max(1, max_photos_per_room)]
        room_jobs.append({"rid": rid, "room_type": rt, "photo_urls": urls})

    if not room_jobs:
        raise RuntimeError(f"v5_selected_comparable_room_pirs: no usable clusters | comp_id={comp_id}")

    logger.info(
        "v5_selected_comparable_room_pirs: start | listing_id=%s comp_id=%s rooms=%s concurrency=%s max_photos_per_room=%s",
        listing_id,
        comp_id,
        len(room_jobs),
        concurrency,
        max_photos_per_room,
    )

    sem = asyncio.Semaphore(concurrency)

    async def _run_one(entry: Dict[str, Any]) -> Dict[str, Any]:
        rid_local = str(entry["rid"])
        rt_local = str(entry["room_type"])
        urls_local = entry["photo_urls"]
        async with sem:
            async with GEMINI_PRO_SEMAPHORE:
                return await generate_v5_target_room_pir(
                    room_id=f"comp_{comp_id}:{rid_local}",
                    room_type=rt_local,
                    photo_urls=urls_local,
                    max_photos=max_photos_per_room,
                    call_gemini_fn=call_gemini,
                    fetch_images_batch_fn=fetch_images_batch,
                )

    tasks = [asyncio.create_task(_run_one(e)) for e in room_jobs]
    try:
        for t in asyncio.as_completed(tasks):
            rooms_out.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    if not rooms_out:
        raise RuntimeError(f"v5_selected_comparable_room_pirs: no room PIRs produced | comp_id={comp_id}")

    slot_standard = build_v5_comparable_slot_standard(room_pirs=rooms_out)
    payload_rooms = {
        "listing_id": int(listing_id),
        "comparable_id": int(comp_id),
        "schema_version": "v5_selected_comparable_room_pirs_v1",
        "created_at": datetime.utcnow().isoformat(),
        "rooms": rooms_out,
        "counts": {"rooms": len(rooms_out)},
    }
    payload_std = {
        "listing_id": int(listing_id),
        "selected_comparable_id": int(comp_id),
        "schema_version": "v5_selected_comparable_slot_standard_v1",
        "created_at": datetime.utcnow().isoformat(),
        "slot_standard": slot_standard,
        "counts": {"slots": len(slot_standard)},
    }
    async with DB_WRITE_SEMAPHORE:
        ok1 = await db.save_unified_estimate(listing_id, key_rooms, payload_rooms)
        ok2 = await db.save_unified_estimate(listing_id, key_std, payload_std)
    if not (ok1 and ok2):
        raise RuntimeError(f"v5_selected_comparable_room_pirs: save failed | listing_id={listing_id} comp_id={comp_id}")


async def handle_v5_select_median_comparable(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Median Comparable Selector (no-LLM, deterministic).

    Writes:
      - unified_estimates: v5_selected_comparable

    Preconditions:
      - listing_comparables exist

    Payload:
      - force (bool)
      - price_field (str, default: sale_price)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    # WHY price_per_sqm: We no longer filter Casafari by total_area, so comps
    # have varied sizes (67m²-145m²). Median by absolute price is meaningless.
    # Median by price/m² gives the neighborhood "vibe", then we multiply by
    # this listing's area to get the renovated value.
    price_field = str(payload.get("price_field") or "price_per_sqm").strip() or "price_per_sqm"

    key = "v5_selected_comparable"
    existing = None if force else await db.get_unified_estimate(listing_id, key)
    if isinstance(existing, dict) and existing.get("selected_comparable_id"):
        logger.info(
            "v5_selected_comparable(median): skip (exists) | listing_id=%s selected=%s",
            listing_id,
            existing.get("selected_comparable_id"),
        )
        return

    comps = await db.get_listing_comparables(listing_id)
    if not comps:
        await _reschedule_job(job, db, reason="v5_selected_comparable(median): no comparables", delay_seconds=30)
        return

    # Fetch listing area so we can compute renovated value from median price/m²
    listing = await db.get_listing(listing_id)
    listing_area = 0.0
    if listing:
        scraped = listing.get("scraped_data") or {}
        for src in [listing.get("sqm"), scraped.get("m2_built"), scraped.get("m2_useful")]:
            if src is not None:
                try:
                    listing_area = float(src)
                    break
                except (ValueError, TypeError):
                    pass

    from pricing.v5_comparable_selector import select_v5_median_price_comparable

    selected = select_v5_median_price_comparable(
        listing_id=int(listing_id),
        comparables=comps,
        price_field=price_field,
    )

    # Compute reference_sold_price from median price/m² × listing area.
    # This is what the frontend uses as target_price for the value-add display.
    median_value = selected.get("median_value")
    if median_value and listing_area > 0 and price_field == "price_per_sqm":
        selected["reference_sold_price"] = round(float(median_value) * listing_area)
        selected["listing_area_sqm"] = listing_area
        logger.info(
            "v5_selected_comparable(median): computed reference_sold_price | "
            "listing_id=%s | median_psm=%.0f | area=%.0f | ref_price=%s",
            listing_id, float(median_value), listing_area, selected["reference_sold_price"],
        )
    else:
        # Fallback: find the selected comp in the list and use its sale_price
        sel_id = selected.get("selected_comparable_id")
        if sel_id:
            for c in comps:
                cid = c.get("casafari_property_id") or c.get("id") or c.get("comparable_id")
                try:
                    if int(cid) == int(sel_id):
                        selected["reference_sold_price"] = c.get("sale_price", 0)
                        break
                except (ValueError, TypeError):
                    continue

    out = {
        **selected,
        "schema_version": "v5_selected_comparable_v2",
        "created_at": datetime.utcnow().isoformat(),
    }
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, key, out)
    if not ok:
        raise RuntimeError(f"v5_selected_comparable(median): save failed | listing_id={listing_id}")


async def handle_v5_select_comparable(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Comparable Selector (market_standard reference).

    Writes:
      - unified_estimates: v5_selected_comparable

    Preconditions:
      - v5_pir_target
      - comparable_v5 PIRs available for some comparables

    Payload:
      - force (bool)
      - max_comparables (int, default 5)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    max_comps = int(payload.get("max_comparables") or 5)

    existing = None if force else await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    if isinstance(existing, dict) and existing.get("selected_comparable_id"):
        logger.info("v5_selected_comparable: skip (exists) | listing_id=%s selected=%s", listing_id, existing.get("selected_comparable_id"))
        return

    target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
    if not target_pir:
        await _reschedule_job(job, db, reason="v5_selected_comparable: missing v5_pir_target", delay_seconds=30)
        return

    comparables = await db.get_listing_comparables(listing_id)
    if not comparables:
        await _reschedule_job(job, db, reason="v5_selected_comparable: no comparables", delay_seconds=30)
        return

    comparable_pirs: List[Dict[str, Any]] = []
    for comp in (comparables or [])[: max(1, max_comps)]:
        comp_id_raw = comp.get("casafari_property_id") or comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id_raw:
            continue
        pir = await db.get_pir(int(comp_id_raw), pir_type="comparable_v5")
        if pir:
            comparable_pirs.append(pir)
    if not comparable_pirs:
        await _reschedule_job(job, db, reason="v5_selected_comparable: missing comparable_v5 PIRs", delay_seconds=30)
        return

    from pricing.v5_comparable_selector import select_v5_market_standard_comparable
    from pipeline.gemini_client import call_gemini

    async with GEMINI_FLASH_SEMAPHORE:
        selected = await select_v5_market_standard_comparable(
            listing_id=int(listing_id),
            target_pir=target_pir,
            comparables=comparables[: max(1, max_comps)],
            comparable_pirs=comparable_pirs,
            call_gemini_fn=call_gemini,
        )
    out = {**selected, "schema_version": "v5_selected_comparable_v1", "created_at": datetime.utcnow().isoformat()}
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "v5_selected_comparable", out)
    if not ok:
        raise RuntimeError(f"v5_selected_comparable: save failed | listing_id={listing_id}")


async def handle_v5_delta_slots_market_standard(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Delta Slots (market_standard) — per room.

    Writes:
      - unified_estimates: v5_delta_slots_market_standard
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    concurrency = int(payload.get("concurrency") or 5)
    if concurrency < 1:
        raise ValueError(f"v5_delta_slots: concurrency must be >= 1 (got {concurrency})")

    key = "v5_delta_slots_market_standard"
    existing = None if force else await db.get_unified_estimate(listing_id, key)
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        try:
            clusters = await db.get_photo_clusters(listing_id)
            cluster_ids = {
                str(c.get("cluster_id") or "").strip()
                for c in (clusters or [])
                if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()
            }
            existing_room_ids = {
                str(r.get("room_id") or "").strip()
                for r in (existing.get("rooms") or [])
                if isinstance(r, dict) and str(r.get("room_id") or "").strip()
            }
            missing = sorted([rid for rid in existing_room_ids if rid and rid not in cluster_ids])
            if not missing:
                schema_version = str(existing.get("schema_version") or "")
                if "cross_room_review" in schema_version:
                    logger.info(
                        "v5_delta_slots: skip (exists + consistent) | listing_id=%s rooms=%s",
                        listing_id,
                        len(existing.get("rooms") or []),
                    )
                    return
                logger.info(
                    "v5_delta_slots: exists + consistent but missing cross-room review; will upgrade | listing_id=%s rooms=%s schema_version=%s",
                    listing_id,
                    len(existing.get("rooms") or []),
                    schema_version or "unknown",
                )
            logger.warning(
                "v5_delta_slots: stale existing (room_ids not in current clusters) -> regenerating | listing_id=%s missing=%s",
                listing_id,
                missing[:10],
            )
        except Exception as exc:
            logger.warning(
                "v5_delta_slots: consistency check failed, regenerating | listing_id=%s | %s: %s",
                listing_id,
                type(exc).__name__,
                exc,
            )

    target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
    if not target_pir:
        await _reschedule_job(job, db, reason="v5_delta_slots: missing v5_pir_target", delay_seconds=30)
        return

    selected = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    if not (isinstance(selected, dict) and selected.get("selected_comparable_id")):
        await _reschedule_job(job, db, reason="v5_delta_slots: missing v5_selected_comparable", delay_seconds=30)
        return
    selected_id = int(selected.get("selected_comparable_id"))

    comp_rooms_key = f"v5_selected_comparable_room_pirs_{selected_id}"
    comp_rooms_payload = await db.get_unified_estimate(listing_id, comp_rooms_key)
    comp_rooms_all = (comp_rooms_payload or {}).get("rooms") if isinstance(comp_rooms_payload, dict) else None
    if not isinstance(comp_rooms_all, list) or not comp_rooms_all:
        await _reschedule_job(job, db, reason=f"v5_delta_slots: missing {comp_rooms_key}", delay_seconds=30)
        return

    # Whole-home comparable slot standard (derived from selected comparable room PIRs).
    comp_std_key = f"v5_selected_comparable_slot_standard_{selected_id}"
    comp_std_payload = await db.get_unified_estimate(listing_id, comp_std_key)

    # Optional: full comparable home PIR (archetypes + home_summary), stored in property_intelligence_reports.
    comparable_home_pir = None
    try:
        comparable_home_pir = await db.get_pir(selected_id, pir_type="comparable_v5")
    except Exception as exc:
        logger.warning(
            "v5_delta_slots: failed to load comparable_v5 PIR (non-fatal) | listing_id=%s comp_id=%s | %s: %s",
            listing_id,
            selected_id,
            type(exc).__name__,
            exc,
        )

    review_key = "v5_delta_review_market_standard"

    async def _maybe_cross_room_review_and_save(*, base_payload: Dict[str, Any]) -> bool:
        """
        Best-effort cross-room delta review (tracked changes) and persistence.

        Returns True if it wrote the delta artifact (successfully), else False.
        Never raises unless the final save fails.
        """
        from pricing.v5_strategy_delta_decompose import (
            apply_v5_delta_cross_room_patches,
            review_v5_delta_slots_cross_room,
        )

        rooms_in = base_payload.get("rooms") or []
        if not isinstance(rooms_in, list) or not rooms_in:
            async with DB_WRITE_SEMAPHORE:
                ok = await db.save_unified_estimate(listing_id, key, base_payload)
            return bool(ok)

        review = await review_v5_delta_slots_cross_room(
            listing_id=int(listing_id),
            strategy_name="market_standard",
            selected_comparable_id=int(selected_id),
            delta_rooms=rooms_in,
            target_pir=target_pir,
            selected_comparable_room_pirs=comp_rooms_payload if isinstance(comp_rooms_payload, dict) else None,
            selected_comparable_slot_standard=comp_std_payload if isinstance(comp_std_payload, dict) else None,
            comparable_home_pir=comparable_home_pir if isinstance(comparable_home_pir, dict) else None,
        )

        success = bool(isinstance(review, dict) and review.get("success") is True)
        patches_list = review.get("patches") if isinstance(review, dict) and isinstance(review.get("patches"), list) else []
        err = (review or {}).get("error") if isinstance(review, dict) else "unknown"

        rooms_out = rooms_in
        stats: Dict[str, Any] = {}
        if success:
            applied_info = apply_v5_delta_cross_room_patches(delta_rooms=rooms_in, patches=patches_list)
            rooms_out = applied_info.get("rooms") if isinstance(applied_info, dict) else rooms_in
            stats = (applied_info or {}).get("stats") if isinstance(applied_info, dict) else {}
        else:
            logger.warning(
                "v5_delta_slots: cross-room review failed (non-blocking) | listing_id=%s | err=%s",
                listing_id,
                err or "unknown",
            )

        # Persist review artifact (tracked changes) for debugging + frontend transparency.
        review_payload = {
            "listing_id": int(listing_id),
            "strategy_name": "market_standard",
            "selected_comparable_id": int(selected_id),
            "schema_version": "v5_delta_review_v1",
            "created_at": datetime.utcnow().isoformat(),
            "success": bool(success),
            "error": (str(err) if err else None),
            "counts": {
                "patch_rooms": len([p for p in patches_list if isinstance(p, dict) and p.get("room_id")]),
                "patch_slot_changes": sum(
                    len((p.get("slot_changes") or [])) for p in patches_list if isinstance(p, dict)
                ),
                "slot_changes_applied": int((stats or {}).get("slot_changes_applied") or 0),
                "slot_changes_skipped": int((stats or {}).get("slot_changes_skipped") or 0),
            },
            "patches": patches_list,
            "source_keys": {
                "delta_slots": key,
                "target_pir": "v5_pir_target",
                "selected_comparable": "v5_selected_comparable",
                "selected_comparable_room_pirs": comp_rooms_key,
                "selected_comparable_slot_standard": comp_std_key,
                "comparable_home_pir": "property_intelligence_reports:comparable_v5",
            },
        }
        try:
            async with DB_WRITE_SEMAPHORE:
                await db.save_unified_estimate(listing_id, review_key, review_payload)
        except Exception as exc:
            logger.warning(
                "v5_delta_slots: failed to save review artifact (non-fatal) | listing_id=%s | %s: %s",
                listing_id,
                type(exc).__name__,
                exc,
            )

        # Save delta slots artifact (patched if success; otherwise the base payload).
        out_payload = dict(base_payload)
        if success:
            out_payload["rooms"] = sorted(rooms_out, key=lambda x: str((x or {}).get("room_id") or ""))
            out_payload["schema_version"] = "v5_delta_slots_v3_cross_room_review"
        # Always link the review artifact key for traceability without changing the delta schema shape.
        src = out_payload.get("source_keys")
        if not isinstance(src, dict):
            src = {}
        src["delta_review"] = review_key
        out_payload["source_keys"] = src
        async with DB_WRITE_SEMAPHORE:
            ok = await db.save_unified_estimate(listing_id, key, out_payload)
        return bool(ok)

    # Upgrade path: existing delta artifact is consistent but lacks cross-room review.
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        existing_review = None
        try:
            existing_review = await db.get_unified_estimate(listing_id, review_key)
        except Exception:
            existing_review = None
        if not isinstance(existing_review, dict):
            ok = await _maybe_cross_room_review_and_save(base_payload=existing)
            if not ok:
                raise RuntimeError(f"v5_delta_slots: save failed | listing_id={listing_id}")
            return

    # ── Fuzzy room matching via flash-lite ──────────────────────────────────
    # Instead of exact room_type string matching, ask flash-lite to map each
    # target room to the most relevant comparable room(s). This prevents e.g.
    # a kitchen's ceramic tiles overriding a living room's wood floors when
    # room_type strings don't match exactly.
    from pricing.v5_slots import slot_ids_for_room_type
    from pipeline.gemini_client import call_gemini_json

    target_rooms_summary = [
        {"room_id": str(r.get("room_id") or ""), "room_type": str(r.get("room_type") or "")}
        for r in (target_pir.get("rooms") or [])
        if isinstance(r, dict) and r.get("room_id") and r.get("room_type")
    ]
    comp_rooms_summary = [
        {"room_id": str(r.get("room_id") or ""), "room_type": str(r.get("room_type") or "")}
        for r in comp_rooms_all
        if isinstance(r, dict) and r.get("room_id") and r.get("room_type")
    ]

    # Build the fuzzy mapping with flash-lite (cheap, ~$0.001)
    fuzzy_mapping: Dict[str, List[str]] = {}
    try:
        fuzzy_prompt = f"""You are matching rooms between two properties for a renovation comparison.

TARGET PROPERTY rooms (the property being renovated):
{json.dumps(target_rooms_summary, ensure_ascii=False)}

COMPARABLE PROPERTY rooms (the reference property we want to match):
{json.dumps(comp_rooms_summary, ensure_ascii=False)}

TASK: For each target room, pick the 1-3 most relevant comparable rooms whose finishes
(flooring, walls, fixtures) would be the best reference for that target room.

How to think:
- A living room should match to living rooms or open-plan spaces that INCLUDE a living area.
- A kitchen should match to kitchens or open-plan spaces that INCLUDE a kitchen.
- An open_plan_kitchen_living should match to BOTH the kitchen AND living comparable rooms.
- Bedrooms should match to bedrooms (primary→primary preferred, but any bedroom is valid).
- Bathrooms should match to bathrooms of similar type.
- Hallways/entries can match to any dry room if no direct match exists.
- If no comparable room is relevant at all, return an empty array for that target room.

Return JSON: {{"mapping": {{"<target_room_id>": ["<comp_room_id>", ...]}}}}"""

        fuzzy_result = await call_gemini_json(
            prompt=fuzzy_prompt,
            model="flash-lite",
            temperature=0.0,
            max_tokens=4096,
        )
        if isinstance(fuzzy_result, dict) and isinstance(fuzzy_result.get("mapping"), dict):
            fuzzy_mapping = fuzzy_result["mapping"]
            logger.info(
                "v5_delta_slots: fuzzy room matching OK | listing_id=%s | mappings=%s",
                listing_id,
                {k: v for k, v in fuzzy_mapping.items()},
            )
        else:
            logger.warning(
                "v5_delta_slots: fuzzy matching returned unexpected shape, falling back to exact match | listing_id=%s | result=%s",
                listing_id,
                str(fuzzy_result)[:300],
            )
    except Exception as exc:
        logger.warning(
            "v5_delta_slots: fuzzy matching failed, falling back to exact match | listing_id=%s | %s: %s",
            listing_id,
            type(exc).__name__,
            exc,
        )

    # Build a lookup: comp_room_id → comp_room_payload
    comp_room_by_id: Dict[str, Dict[str, Any]] = {}
    for r in comp_rooms_all:
        if isinstance(r, dict):
            crid = str(r.get("room_id") or "").strip()
            if crid:
                comp_room_by_id[crid] = r

    def _is_inferred(text: str) -> bool:
        s = str(text or "").strip().lower()
        return s.startswith("no visible en fotos") or s.startswith("no se aprecia")

    def _slot_map(room_payload: Dict[str, Any]) -> Dict[str, str]:
        m = room_payload.get("slot_narratives") if isinstance(room_payload, dict) else None
        if not isinstance(m, dict):
            return {}
        return {str(k): str(v).strip() for k, v in m.items() if isinstance(k, str) and isinstance(v, str) and v.strip()}

    def _build_targets_for_room(*, room_id: str, room_type: str, slot_ids: List[str]) -> Dict[str, Any]:
        # 1. Use fuzzy mapping if available
        matched_comp_ids = fuzzy_mapping.get(room_id) or []
        matched_rooms = [comp_room_by_id[cid] for cid in matched_comp_ids if cid in comp_room_by_id]

        # 2. Fallback: exact room_type match
        if not matched_rooms:
            rt = str(room_type or "").strip()
            matched_rooms = [r for r in comp_rooms_all if isinstance(r, dict) and str(r.get("room_type") or "").strip() == rt]

        # 3. Last resort: all comparable rooms
        candidates = matched_rooms if matched_rooms else [r for r in comp_rooms_all if isinstance(r, dict)]

        out: Dict[str, str] = {}
        inferred: Dict[str, bool] = {}
        for sid in slot_ids:
            # First non-empty comparable narrative wins from the ranked candidates.
            picked = ""
            for r in candidates:
                val = _slot_map(r).get(sid, "")
                if val:
                    picked = val
                    break
            if not picked:
                picked = (
                    "No visible en fotos; pero dado el estado general de la vivienda en el comparable, "
                    "asumimos un estado funcional acorde. Confirmar en visita."
                )
            out[sid] = picked
            inferred[sid] = _is_inferred(picked)
        return {"targets": out, "target_inferred": inferred}

    targets_by_room: Dict[str, Dict[str, str]] = {}
    target_inferred_by_room: Dict[str, Dict[str, bool]] = {}
    current_inferred_by_room: Dict[str, Dict[str, bool]] = {}
    for room in target_pir.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        rid = str(room.get("room_id") or "").strip()
        rt = str(room.get("room_type") or "").strip()
        if not rid or not rt:
            continue
        slot_ids = slot_ids_for_room_type(rt)
        built = _build_targets_for_room(room_id=rid, room_type=rt, slot_ids=slot_ids)
        targets_by_room[rid] = built["targets"]
        target_inferred_by_room[rid] = built["target_inferred"]
        narrs = room.get("slot_narratives") if isinstance(room.get("slot_narratives"), dict) else {}
        current_inferred_by_room[rid] = {sid: _is_inferred(str(narrs.get(sid) or "")) for sid in slot_ids}

    from pricing.v5_strategy_delta_decompose import generate_v5_delta_for_room

    room_jobs: List[Dict[str, Any]] = []
    for room in target_pir.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        rid = str(room.get("room_id") or "").strip()
        rt = str(room.get("room_type") or "").strip()
        narrs = room.get("slot_narratives") or {}
        if not rid or not rt or not isinstance(narrs, dict):
            continue
        tier_targets = targets_by_room.get(rid)
        if not isinstance(tier_targets, dict) or not tier_targets:
            await _reschedule_job(job, db, reason=f"v5_delta_slots: missing derived targets for room_id={rid}", delay_seconds=30)
            return
        room_jobs.append(
            {
                "room_id": rid,
                "room_type": rt,
                "room_slot_narratives": {str(k): str(v) for k, v in narrs.items() if isinstance(k, str) and isinstance(v, str)},
                "tier_slot_targets": tier_targets,
                "current_inferred": current_inferred_by_room.get(rid) or {},
                "target_inferred": target_inferred_by_room.get(rid) or {},
            }
        )

    if not room_jobs:
        raise RuntimeError(f"v5_delta_slots: produced 0 room jobs | listing_id={listing_id}")

    logger.info(
        "v5_delta_slots: start | listing_id=%s rooms=%s concurrency=%s selected_comparable_id=%s",
        listing_id,
        len(room_jobs),
        concurrency,
        selected_id,
    )

    sem = asyncio.Semaphore(concurrency)

    async def _run_one(j: Dict[str, Any]) -> Dict[str, Any]:
        async with sem:
            # Delta is a single-room call on Gemini Pro (cost control = one call per room).
            async with GEMINI_PRO_SEMAPHORE:
                out_room = await generate_v5_delta_for_room(
                    listing_id=int(listing_id),
                    strategy_name="market_standard",
                    room_id=str(j["room_id"]),
                    room_type=str(j["room_type"]),
                    room_slot_narratives=j["room_slot_narratives"],
                    tier_slot_targets=j["tier_slot_targets"],
                )
            # Attach per-slot inference flags so downstream BOQ can mark assumption-derived items.
            slot_work = out_room.get("slot_work_narratives") if isinstance(out_room, dict) else None
            if isinstance(slot_work, dict):
                out_room["slot_inference"] = {
                    str(sid): {
                        "current_inferred": bool((j.get("current_inferred") or {}).get(str(sid))),
                        "target_inferred": bool((j.get("target_inferred") or {}).get(str(sid))),
                    }
                    for sid in slot_work.keys()
                }
            return out_room

    rooms_out: List[Dict[str, Any]] = []
    tasks = [asyncio.create_task(_run_one(j)) for j in room_jobs]
    try:
        for t in asyncio.as_completed(tasks):
            rooms_out.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    out = {
        "listing_id": int(listing_id),
        "strategy_name": "market_standard",
        "rooms": sorted(rooms_out, key=lambda x: str((x or {}).get("room_id") or "")),
        "schema_version": "v5_delta_slots_v2_from_comparable_standard",
        "created_at": datetime.utcnow().isoformat(),
        "counts": {"rooms": len(rooms_out)},
        "selected_comparable_id": int(selected_id),
        "source_keys": {
            "target_pir": "v5_pir_target",
            "selected_comparable": "v5_selected_comparable",
            "selected_comparable_room_pirs": comp_rooms_key,
        },
    }
    ok = await _maybe_cross_room_review_and_save(base_payload=out)
    if not ok:
        raise RuntimeError(f"v5_delta_slots: save failed | listing_id={listing_id}")


async def handle_v5_work_items_market_standard(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Work Items (market_standard) — decomposed, flat list for catalog matching.

    Writes:
      - unified_estimates: v5_work_items_market_standard
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    concurrency = int(payload.get("concurrency") or 5)
    if concurrency < 1:
        raise ValueError(f"v5_work_items: concurrency must be >= 1 (got {concurrency})")

    key = "v5_work_items_market_standard"
    existing = None if force else await db.get_unified_estimate(listing_id, key)
    if isinstance(existing, dict) and isinstance(existing.get("items"), list) and existing.get("items"):
        try:
            clusters = await db.get_photo_clusters(listing_id)
            cluster_ids = {
                str(c.get("cluster_id") or "").strip()
                for c in (clusters or [])
                if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()
            }
            item_room_ids = sorted({
                str(i.get("room_id") or "").strip()
                for i in (existing.get("items") or [])
                if isinstance(i, dict) and str(i.get("room_id") or "").strip()
            })
            missing = [rid for rid in item_room_ids if rid and rid not in cluster_ids]
            if not missing:
                logger.info(
                    "v5_work_items: skip (exists + consistent) | listing_id=%s items=%s",
                    listing_id,
                    len(existing.get("items") or []),
                )
                return
            logger.warning(
                "v5_work_items: stale existing (room_ids not in current clusters) -> regenerating | listing_id=%s missing=%s",
                listing_id,
                missing[:10],
            )
        except Exception as exc:
            logger.warning(
                "v5_work_items: consistency check failed, regenerating | listing_id=%s | %s: %s",
                listing_id,
                type(exc).__name__,
                exc,
            )

    delta = await db.get_unified_estimate(listing_id, "v5_delta_slots_market_standard")
    if not delta:
        await _reschedule_job(job, db, reason="v5_work_items: missing v5_delta_slots_market_standard", delay_seconds=30)
        return

    from pricing.v5_work_items import build_v5_work_items_for_strategy

    work_items = await build_v5_work_items_for_strategy(
        listing_id=int(listing_id),
        strategy_name="market_standard",
        delta_slots=delta,
        concurrency=concurrency,
        gemini_semaphore=GEMINI_FLASH_SEMAPHORE,
    )
    out = {**work_items, "schema_version": "v5_work_items_v1", "created_at": datetime.utcnow().isoformat(), "counts": {"items": len(work_items.get("items") or [])}}
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, key, out)
    if not ok:
        raise RuntimeError(f"v5_work_items: save failed | listing_id={listing_id}")


async def handle_v5_run_market_standard(job: Dict[str, Any], db: Any) -> None:
    """
    DEPRECATED: monolithic V5 run. Now split into v5_boq / v5_eli5 / v5_architect_report /
    v5_room_images / v5_finalize sub-stages. Kept for backwards-compat with old runs.
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    from pricing.v5_run_market_standard import run_v5_market_standard

    await run_v5_market_standard(
        listing_id=int(listing_id),
        db=db,
        force=bool(force),
        max_comparables=int(payload.get("max_comparables") or 5),
        max_photos_per_comparable=int(payload.get("max_photos_per_comparable") or 24),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# V5 sub-stages: split from monolithic v5_run for visible pipeline progress.
#
# V4-tail stages (the construction pricing engine):
#   v5_smart_m2  →  v5_bcca_match  →  v5_quant_plan  →  v5_forage  →  v5_boq_assembly
#
# Presentation stages:
#   v5_eli5  →  v5_architect_report  →  v5_room_images  →  v5_finalize
#
# Each stage is independently idempotent (checks for existing data, skips if present).
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_v5_smart_m2(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Smart M²: ensure room dimensions (floor area, wall area, perimeter, openings).

    Reads: photo_clusters, listing
    Writes: smart_m2 (via db.save_smart_m2 inside _ensure_smart_m2)
    """
    listing_id = job["listing_id"]
    logger.info("v5_smart_m2: starting | listing_id=%s", listing_id)

    from pricing.v4_quantification_pipeline import (
        _ensure_smart_m2,
        _extract_listing_sqm,
    )

    listing = await db.get_listing(listing_id)
    listing_sqm = _extract_listing_sqm(listing)

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="v5_smart_m2: missing photo_clusters", delay_seconds=30)
        return

    v5_room_ids = sorted({
        str(c.get("cluster_id") or "").strip()
        for c in clusters if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()
    })

    smart_m2 = await _ensure_smart_m2(
        listing_id=listing_id,
        listing=listing,
        listing_sqm=listing_sqm,
        clusters=clusters,
        v5_room_ids=v5_room_ids,
        db=db,
    )
    rooms = len((smart_m2 or {}).get("rooms") or [])
    logger.info("v5_smart_m2: complete | listing_id=%s | rooms=%d", listing_id, rooms)


async def handle_gla_opinion(job: Dict[str, Any], db: Any) -> None:
    """
    GLA Opinion: generate Leo's per-room per-slot "what I'd do" narratives.

    Reads:
      - unified_estimates: v5_pir_target
      - photo_clusters
      - smart_m2
      - listings metadata (construction year, description)

    Writes:
      - unified_estimates: gla_opinion

    Payload:
      - force (bool)
      - max_photos_per_room (int, default 8)
      - concurrency (int, default 5)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    max_photos = int(payload.get("max_photos_per_room") or 8)
    concurrency = int(payload.get("concurrency") or 5)
    if concurrency < 1:
        raise ValueError(f"gla_opinion: concurrency must be >= 1 (got {concurrency})")

    listing = await db.get_listing(listing_id)
    if not listing:
        await _reschedule_job(job, db, reason="gla_opinion: listing not found", delay_seconds=30)
        return
    construction_year = listing.get("construction_year") or listing.get("year_built")

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="gla_opinion: missing photo_clusters", delay_seconds=30)
        return

    pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
    if not (isinstance(pir, dict) and isinstance(pir.get("rooms"), list) and pir.get("rooms")):
        await _reschedule_job(job, db, reason="gla_opinion: missing v5_pir_target", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)
    if not (isinstance(smart_m2, dict) and smart_m2.get("rooms")):
        await _reschedule_job(job, db, reason="gla_opinion: missing smart_m2", delay_seconds=30)
        return

    # Reuse only if consistent with current clusters (room ids match).
    existing = None if force else await db.get_unified_estimate(listing_id, "gla_opinion")
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        existing_room_ids = {
            str(r.get("room_id") or "").strip()
            for r in (existing.get("rooms") or [])
            if isinstance(r, dict) and str(r.get("room_id") or "").strip()
        }
        cluster_ids = {
            str(c.get("cluster_id") or "").strip()
            for c in clusters
            if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()
        }
        missing = sorted([rid for rid in existing_room_ids if rid and rid not in cluster_ids])
        if not missing:
            logger.info(
                "gla_opinion: skip (exists + consistent) | listing_id=%s rooms=%s",
                listing_id,
                len(existing_room_ids),
            )
            return
        logger.warning(
            "gla_opinion: stale existing (room_ids not in current clusters) -> regenerating | listing_id=%s missing=%s",
            listing_id,
            missing[:10],
        )

    # Build room entries from clusters (skip non-room content).
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
        raise RuntimeError(f"gla_opinion: no usable room clusters | listing_id={listing_id}")

    # Map PIR slot narratives by room_id and ensure alignment.
    pir_by_room: Dict[str, Dict[str, str]] = {}
    for r in pir.get("rooms") or []:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("room_id") or "").strip()
        slots = r.get("slot_narratives") or {}
        if rid and isinstance(slots, dict):
            pir_by_room[rid] = {str(k): str(v) for k, v in slots.items() if isinstance(v, str)}

    missing_pir = sorted([e["room_id"] for e in room_entries if e["room_id"] not in pir_by_room])
    if missing_pir:
        await _reschedule_job(
            job,
            db,
            reason=f"gla_opinion: PIR missing for some rooms | missing={missing_pir[:6]}",
            delay_seconds=30,
        )
        return

    from pipeline.gemini_client import call_gemini
    from pricing.gla_opinion import generate_gla_opinion
    from datetime import datetime, timezone

    sem = asyncio.Semaphore(concurrency)
    rooms_out: List[Dict[str, Any]] = []

    async def _run_one(entry: Dict[str, Any]) -> Dict[str, Any]:
        rid_local = str(entry["room_id"])
        rt_local = str(entry["room_type"])
        urls_local = entry["photo_urls"]
        slot_narratives_local = pir_by_room[rid_local]
        async with sem:
            async with GEMINI_FLASH_SEMAPHORE:
                return await generate_gla_opinion(
                    listing_id=int(listing_id),
                    room_id=rid_local,
                    room_type=rt_local,
                    slot_narratives=slot_narratives_local,
                    photo_urls=urls_local,
                    smart_m2=smart_m2,
                    construction_year=construction_year if isinstance(construction_year, int) else None,
                    call_gemini=call_gemini,
                    max_photos=max_photos,
                )

    tasks = [asyncio.create_task(_run_one(e)) for e in sorted(room_entries, key=lambda x: str(x.get("room_id") or ""))]
    try:
        for t in asyncio.as_completed(tasks):
            rooms_out.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    payload_out = {
        "listing_id": int(listing_id),
        "rooms": sorted(rooms_out, key=lambda r: str(r.get("room_id") or "")),
        "schema_version": "gla_opinion_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"rooms": len(rooms_out)},
    }
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "gla_opinion", payload_out)
    if not ok:
        raise RuntimeError(f"gla_opinion: save failed | listing_id={listing_id}")

    # ── WhatsApp completion hook (best-effort; never crash the pipeline) ──
    try:
        from whatsapp.agent import LEO_SOUL, _get_processing_conversation_for_listing, _append_message
        from whatsapp.twilio_client import send_text

        conv = await _get_processing_conversation_for_listing(int(listing_id))
        if not conv:
            logger.debug("gla_opinion: no pending WhatsApp conversation | listing_id=%s", listing_id)
            return

        phone = conv.get("phone_number")
        if not phone:
            logger.debug("gla_opinion: conversation missing phone_number | listing_id=%s", listing_id)
            return

        listing_context = _build_listing_context(listing)
        opinion_compact = json.dumps(payload_out.get("rooms") or [], ensure_ascii=False)[:12000]
        first_impression_prompt = f"""
Eres Leo, asesor de reformas por WhatsApp. Escribe tu PRIMER mensaje despues de analizar un anuncio.

POR QUE IMPORTA: Este primer mensaje crea confianza. Tiene que sonar humano, directo y util.

REQUISITOS:
- Max ~200 palabras.
- Nada de lenguaje corporativo.
- Se concreto: menciona 2-4 observaciones claras (por ejemplo cocina/banos/suelos/ventanas/instalaciones).
- No inventes hechos. Si es una suposicion, dilo ("probable", "habria que confirmar").
- Termina con 1-2 preguntas para guiar al usuario (presupuesto, estilo, prioridad).

{listing_context}

OPINIONES POR ESTANCIA (JSON, resumidas):
{opinion_compact}
""".strip()

        msg = await call_gemini(
            prompt=first_impression_prompt,
            model="flash",
            temperature=0.4,
            max_tokens=600,
            system_instruction=LEO_SOUL,
            use_spanish=False,
            strict_db_write=False,
        )
        if not msg.success or not (msg.text or "").strip():
            logger.warning(
                "gla_opinion: first-impression gemini failed (non-fatal) | listing_id=%s err=%s",
                listing_id,
                msg.error,
            )
            return

        text = (msg.text or "").strip()
        send_text(str(phone), text)
        await _append_message(
            phone_number=str(phone),
            role="assistant",
            message_text=text,
            message_type="text",
            listing_id=int(listing_id),
            model=msg.model or "flash",
            usage=msg.usage,
        )
        logger.info("gla_opinion: first-impression sent | listing_id=%s phone=%s", listing_id, phone)
    except Exception as wa_exc:
        logger.warning(
            "gla_opinion: first-impression WhatsApp hook failed (non-fatal) | listing_id=%s | err=%s",
            listing_id,
            wa_exc,
        )


async def handle_v5_bcca_match(job: Dict[str, Any], db: Any) -> None:
    """
    V5 BCCA Match: embed work items → match to BCCA codes (per dimension, parallel).

    Reads: v5_work_items_market_standard
    Writes: v4_bcca_matches_market_standard_{dim} for each dimension
    """
    import asyncio
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    logger.info("v5_bcca_match: starting | listing_id=%s | force=%s", listing_id, force)

    work_items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    if not (isinstance(work_items, dict) and isinstance(work_items.get("items"), list) and work_items.get("items")):
        await _reschedule_job(job, db, reason="v5_bcca_match: missing v5_work_items_market_standard", delay_seconds=30)
        return
    items = work_items["items"]

    from pricing.embedding_runtime import embed_texts
    from pricing.v4_quantification_pipeline import (
        _get_default_bcca_matcher,
        _worklist_dim_from_flat_items,
        match_v4_bcca,
    )
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS

    matcher = _get_default_bcca_matcher()

    async def _match_dim(dim: str) -> None:
        pkg_key = f"v4_bcca_matches_{strategy_name}_{dim}"
        if not force:
            existing = await db.get_unified_estimate(listing_id, pkg_key)
            if isinstance(existing, dict) and isinstance(existing.get("matches"), list) and existing.get("matches"):
                logger.info("v5_bcca_match: reused %s | listing_id=%s", dim, listing_id)
                return
        worklist_dim = _worklist_dim_from_flat_items(dimension=dim, items=items)
        dim_items = [it for it in items if str(it.get("dimension") or "").strip() == dim]
        if not dim_items:
            logger.info("v5_bcca_match: skipped %s (no work items) | listing_id=%s", dim, listing_id)
            return
        bcca_matches = await match_v4_bcca(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dim,
            worklist_dim=worklist_dim,
            matcher=matcher,
            embed_texts_fn=embed_texts,
        )
        await db.save_unified_estimate(listing_id, pkg_key, {"matches": bcca_matches})
        logger.info("v5_bcca_match: matched %s | listing_id=%s | items=%d", dim, listing_id, len(bcca_matches))

    await asyncio.gather(*[_match_dim(dim) for dim in V2_DIMENSIONS])
    logger.info("v5_bcca_match: complete | listing_id=%s", listing_id)


async def handle_v5_quant_plan(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Quant Plan: LLM generates quantity formulas for each work item (per dimension).

    Reads: v5_work_items, v4_bcca_matches per dim, photo_clusters, listing
    Writes: v4_quant_plan_market_standard_{dim} for each dimension
    """
    import asyncio
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    logger.info("v5_quant_plan: starting | listing_id=%s | force=%s", listing_id, force)

    work_items = await db.get_unified_estimate(listing_id, "v5_work_items_market_standard")
    if not (isinstance(work_items, dict) and isinstance(work_items.get("items"), list) and work_items.get("items")):
        await _reschedule_job(job, db, reason="v5_quant_plan: missing v5_work_items_market_standard", delay_seconds=30)
        return
    items = work_items["items"]

    listing = await db.get_listing(listing_id)
    listing_sqm = None
    if listing:
        from pricing.v4_quantification_pipeline import _extract_listing_sqm
        listing_sqm = _extract_listing_sqm(listing)

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="v5_quant_plan: missing photo_clusters", delay_seconds=30)
        return

    from pricing.v4_quantification_pipeline import (
        _extract_floorplan_urls,
        _get_default_bcca_matcher,
        _room_photo_urls_by_id,
        _worklist_dim_from_flat_items,
        generate_v4_quant_plan,
        _plans_validate_or_raise,
    )
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pipeline.gemini_client import call_gemini

    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    room_has_photos = {rid: True for rid in room_photos.keys()}
    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    async def _plan_dim(dim: str) -> None:
        pkg_plan_key = f"v4_quant_plan_{strategy_name}_{dim}"
        pkg_match_key = f"v4_bcca_matches_{strategy_name}_{dim}"

        # Load BCCA matches for this dimension (must exist from v5_bcca_match)
        matches_payload = await db.get_unified_estimate(listing_id, pkg_match_key)
        bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
        if not isinstance(bcca_matches, list) or not bcca_matches:
            logger.info("v5_quant_plan: no BCCA matches for %s, skipping | listing_id=%s", dim, listing_id)
            return

        if not force:
            quant_plan = await db.get_unified_estimate(listing_id, pkg_plan_key)
            has_cached = (
                isinstance(quant_plan, dict)
                and isinstance(quant_plan.get("plans"), list)
                and bool(quant_plan.get("plans"))
            )
            if has_cached:
                try:
                    matches_by_item = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
                    _plans_validate_or_raise(plan=quant_plan, bcca_matches_by_item=matches_by_item, bcca_meta_by_code=bcca_meta_by_code)
                    logger.info("v5_quant_plan: reused %s | listing_id=%s", dim, listing_id)
                    return
                except Exception:
                    pass  # Invalid cached plan, regenerate

        worklist_dim = _worklist_dim_from_flat_items(dimension=dim, items=items)
        quant_plan = await generate_v4_quant_plan(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dim,
            worklist_dim=worklist_dim,
            bcca_matches=bcca_matches,
            floorplan_available=floorplan_available,
            room_has_photos=room_has_photos,
            call_gemini=call_gemini,
            bcca_meta_by_code=bcca_meta_by_code,
            listing_sqm=listing_sqm,
        )
        await db.save_unified_estimate(listing_id, pkg_plan_key, quant_plan)
        logger.info("v5_quant_plan: planned %s | listing_id=%s | plans=%d", dim, listing_id, len(quant_plan.get("plans") or []))

    await asyncio.gather(*[_plan_dim(dim) for dim in V2_DIMENSIONS])
    logger.info("v5_quant_plan: complete | listing_id=%s", listing_id)


async def handle_v5_forage(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Forage: visual measurement signals from photos (per room, parallel).
    Includes zero-rescue pass (Pro + photos to resolve value=0 signals).

    Reads: v4_quant_plan_*, v4_bcca_matches_*, photo_clusters, smart_m2, listing
    Writes: v4_signals_market_standard, v4_signals_shared
    """
    import asyncio
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    strategy_name = "market_standard"
    forage_concurrency = 5

    logger.info("v5_forage: starting | listing_id=%s", listing_id)

    from pricing.v4_quantification_pipeline import (
        _extract_floorplan_urls,
        _extract_listing_sqm,
        _room_photo_urls_by_id,
        forage_v4_signals_for_room,
        resolve_zero_signals_for_room,
        _safe_float,
    )
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pipeline.gemini_client import call_gemini_json, fetch_images_batch

    listing = await db.get_listing(listing_id)
    listing_sqm = _extract_listing_sqm(listing) if listing else None

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"v5_forage: missing photo_clusters | listing_id={listing_id}")

    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)

    # Load smart_m2
    smart_m2 = await db.get_smart_m2(listing_id) or {"rooms": []}

    # Load existing signals
    signals_store_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _load_signals(sig_payload: Any) -> None:
        if not isinstance(sig_payload, dict):
            return
        for rr in sig_payload.get("rooms") or []:
            if not isinstance(rr, dict):
                continue
            rid = str(rr.get("room_id") or "").strip()
            sigs = rr.get("signals") or []
            if not rid or not isinstance(sigs, list):
                continue
            signals_store_by_room.setdefault(rid, {})
            for s in sigs:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("signal_id") or "").strip()
                if sid:
                    signals_store_by_room[rid][sid] = s

    try:
        _load_signals(await db.get_unified_estimate(listing_id, "v4_signals_shared"))
    except Exception:
        pass
    try:
        _load_signals(await db.get_unified_estimate(listing_id, f"v4_signals_{strategy_name}"))
    except Exception:
        pass

    signals_checkpoint_lock = asyncio.Lock()

    async def _checkpoint_signals(reason: str) -> None:
        async with signals_checkpoint_lock:
            rooms_payload = []
            for rid in sorted(signals_store_by_room.keys()):
                sigs_by_id = signals_store_by_room.get(rid) or {}
                rooms_payload.append({"room_id": rid, "signals": [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]})
            p = {"rooms": rooms_payload}
            await db.save_unified_estimate(listing_id, f"v4_signals_{strategy_name}", p)
            await db.save_unified_estimate(listing_id, "v4_signals_shared", p)

    # Collect required signals from ALL dimension quant plans
    required_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    signal_work_items_map: Dict[tuple, list] = {}

    def _infer_unit(sid: str) -> str:
        s = sid.strip().lower()
        for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
            if s.endswith(suf):
                return uf
        return "m2"

    def _collect_signal_ids(node: Dict[str, Any]) -> list:
        out = []
        if node.get("op") == "SIGNAL":
            sid = str(node.get("signal_id") or "").strip()
            if sid:
                out.append(sid)
            return out
        arg = node.get("arg")
        if isinstance(arg, dict):
            out.extend(_collect_signal_ids(arg))
        for a in node.get("args") or []:
            if isinstance(a, dict):
                out.extend(_collect_signal_ids(a))
        return out

    for dim in V2_DIMENSIONS:
        matches_payload = await db.get_unified_estimate(listing_id, f"v4_bcca_matches_{strategy_name}_{dim}")
        bcca_matches = (matches_payload or {}).get("matches") or [] if isinstance(matches_payload, dict) else []
        quant_payload = await db.get_unified_estimate(listing_id, f"v4_quant_plan_{strategy_name}_{dim}")
        quant_plan = quant_payload if isinstance(quant_payload, dict) else {}

        matches_by_item = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
        for p in quant_plan.get("plans") or []:
            if not isinstance(p, dict):
                continue
            wid = str(p.get("work_item_id") or "").strip()
            match = matches_by_item.get(wid)
            rid = str((match or {}).get("room_id") or "").strip()
            if not rid:
                continue
            formula = p.get("formula_ast")
            if not isinstance(formula, dict):
                continue
            for sid in sorted(set(_collect_signal_ids(formula))):
                required_by_room.setdefault(rid, {})
                required_by_room[rid][sid] = {"signal_id": sid, "unit_family": _infer_unit(sid)}
            # Build signal→work_items map for zero rescue
            if str(formula.get("op") or "").strip() == "SIGNAL":
                f_sid = str(formula.get("signal_id") or "").strip()
                if f_sid and match:
                    signal_work_items_map.setdefault((rid, f_sid), []).append({
                        "work_item_id": wid,
                        "work_description": str(match.get("work_description") or "").strip(),
                        "bcca_desc_100": str(match.get("bcca_desc_100") or "").strip(),
                    })

    logger.info("v5_forage: signal requirements collected | rooms=%d | listing_id=%s", len(required_by_room), listing_id)

    # Forage pass
    forage_sem = asyncio.Semaphore(forage_concurrency)
    room_locks: Dict[str, asyncio.Lock] = {}

    async def _forage_room(rid: str) -> None:
        async with forage_sem:
            signals_store_by_room.setdefault(rid, {})
            reqs = required_by_room.get(rid) or {}
            want = [sid for sid in reqs.keys() if sid not in signals_store_by_room[rid]]
            if not want:
                return
            room_locks.setdefault(rid, asyncio.Lock())
            async with room_locks[rid]:
                want2 = [sid for sid in reqs.keys() if sid not in signals_store_by_room[rid]]
                if not want2:
                    return
                measured = await forage_v4_signals_for_room(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    room_id=rid,
                    measurement_requests=[reqs[sid] for sid in want2 if sid in reqs],
                    floorplan_available=floorplan_available,
                    listing_sqm=listing_sqm,
                    room_photo_urls=room_photos.get(rid) or [],
                    floorplan_urls=floorplan_urls,
                    smart_m2=smart_m2,
                    call_gemini_json=call_gemini_json,
                    fetch_images_batch=fetch_images_batch,
                    allow_missing_smart_m2_room=True,
                )
                signals_store_by_room[rid].update(measured)
                await _checkpoint_signals(f"forage room_id={rid} new={len(measured)}")

    await asyncio.gather(*[_forage_room(rid) for rid in sorted(required_by_room.keys())])

    # Zero rescue pass
    async def _zero_rescue(rid: str) -> None:
        async with forage_sem:
            room_sigs = signals_store_by_room.get(rid) or {}
            reqs = required_by_room.get(rid) or {}
            zero_sids = []
            for sid in reqs.keys():
                sig = room_sigs.get(sid)
                try:
                    v = float((sig or {}).get("value") or 0)
                except Exception:
                    v = 0.0
                if v == 0.0:
                    zero_sids.append(sid)
            if not zero_sids:
                return
            room_urls = room_photos.get(rid) or []
            if not room_urls:
                return
            zero_ctx = []
            for sid in sorted(set(zero_sids)):
                wi = signal_work_items_map.get((rid, sid)) or []
                zero_ctx.append({
                    "signal_id": sid,
                    "unit_family": str((reqs.get(sid) or {}).get("unit_family") or _infer_unit(sid)),
                    "work_items": wi,
                })
            nonzero = [
                {"signal_id": s.get("signal_id"), "unit_family": s.get("unit_family"), "value": s.get("value"), "confidence": s.get("confidence")}
                for s in room_sigs.values()
                if isinstance(s, dict) and _safe_float(s.get("value")) is not None and float(s.get("value")) > 0
            ]
            resolved = await resolve_zero_signals_for_room(
                listing_id=listing_id, strategy_name=strategy_name, room_id=rid,
                zero_signals_with_context=zero_ctx, nonzero_signals=nonzero,
                floorplan_available=floorplan_available, listing_sqm=listing_sqm,
                room_estimated_m2=None, room_photo_urls=room_urls, floorplan_urls=floorplan_urls,
                call_gemini_json=call_gemini_json, fetch_images_batch=fetch_images_batch,
            )
            if not isinstance(resolved, dict):
                return
            updated = 0
            for sid, sig in resolved.items():
                try:
                    v = float((sig or {}).get("value") or 0)
                except Exception:
                    v = 0.0
                if v > 0:
                    signals_store_by_room.setdefault(rid, {})[sid] = sig
                    updated += 1
            if updated:
                await _checkpoint_signals(f"zero_rescue room_id={rid} updated={updated}")

    await asyncio.gather(*[_zero_rescue(rid) for rid in sorted(required_by_room.keys())])
    await _checkpoint_signals("final")
    logger.info("v5_forage: complete | listing_id=%s", listing_id)


async def handle_v5_boq_assembly(job: Dict[str, Any], db: Any) -> None:
    """
    V5 BOQ Assembly: evaluate formulas, cap quantities, write BOQ line items, aggregate.

    Reads: v4_bcca_matches_*, v4_quant_plan_*, v4_signals_*, listing
    Writes: boq_line_items (dimension=v4), v2_market_standard, v4_run_summary_*
    """
    import asyncio
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    logger.info("v5_boq_assembly: starting | listing_id=%s | force=%s", listing_id, force)

    from pricing.v4_quantification_pipeline import (
        _extract_listing_sqm,
        assemble_v4_boq,
        validate_catalog,
    )
    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS

    validate_catalog()

    listing = await db.get_listing(listing_id)
    listing_sqm = _extract_listing_sqm(listing) if listing else None

    if force:
        await db.clear_boq_line_items_by_dimension(listing_id, strategy_name=strategy_name, dimension="v4")

    # Load signals
    signals_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for key in [f"v4_signals_{strategy_name}", "v4_signals_shared"]:
        sig_payload = await db.get_unified_estimate(listing_id, key)
        if not isinstance(sig_payload, dict):
            continue
        for rr in sig_payload.get("rooms") or []:
            if not isinstance(rr, dict):
                continue
            rid = str(rr.get("room_id") or "").strip()
            if not rid:
                continue
            signals_by_room.setdefault(rid, {})
            for s in rr.get("signals") or []:
                if isinstance(s, dict):
                    sid = str(s.get("signal_id") or "").strip()
                    if sid:
                        signals_by_room[rid][sid] = s

    sem = asyncio.Semaphore(6)
    summary: Dict[str, Any] = {"listing_id": listing_id, "strategy_name": strategy_name, "dimensions": {}}

    async def _assemble_dim(dim: str) -> tuple:
        async with sem:
            matches_payload = await db.get_unified_estimate(listing_id, f"v4_bcca_matches_{strategy_name}_{dim}")
            bcca_matches = (matches_payload or {}).get("matches") or [] if isinstance(matches_payload, dict) else []
            quant_plan = await db.get_unified_estimate(listing_id, f"v4_quant_plan_{strategy_name}_{dim}")
            if not isinstance(quant_plan, dict) or not quant_plan.get("plans"):
                return dim, 0
            saved = await assemble_v4_boq(
                listing_id=listing_id,
                strategy_name=strategy_name,
                dimension=dim,
                bcca_matches=bcca_matches,
                quant_plan=quant_plan,
                signals_by_room=signals_by_room,
                db=db,
                listing_sqm=listing_sqm,
            )
            return dim, int(saved)

    assembled = await asyncio.gather(*[_assemble_dim(dim) for dim in V2_DIMENSIONS])
    total_saved = 0
    for dim, saved in assembled:
        total_saved += int(saved)
        summary["dimensions"][dim] = {"saved_boq_items": int(saved)}

    summary["saved_boq_items_total"] = total_saved
    await db.save_unified_estimate(listing_id, f"v4_run_summary_{strategy_name}", summary)
    if total_saved <= 0:
        await _reschedule_job(job, db, reason="v5_boq_assembly: no line items for market_standard", delay_seconds=30)
        return

    # Aggregate BOQ → v2_market_standard (frontend reads this)
    from pricing.v2_boq_generator import aggregate_boq_from_db

    try:
        boq_agg = await aggregate_boq_from_db(listing_id, strategy_name, db)
    except RuntimeError as exc:
        await _reschedule_job(job, db, reason=f"v5_boq_assembly: {exc}", delay_seconds=30)
        return
    ok = await db.save_unified_estimate(listing_id, f"v2_{strategy_name}", boq_agg)
    if not ok:
        raise RuntimeError(f"v5_boq_assembly: failed to save v2_{strategy_name} | listing_id={listing_id}")
    logger.info(
        "v5_boq_assembly: complete | listing_id=%s | total_pem=%.0f | grand_total=%.0f | lines=%d",
        listing_id, boq_agg.get("total_pem", 0), boq_agg.get("grand_total_with_iva", 0),
        len(boq_agg.get("line_items") or []),
    )


async def handle_v5_eli5(job: Dict[str, Any], db: Any) -> None:
    """
    V5 ELI5: buyer-friendly "product configurator" summary per room.

    Reads: v2_market_standard (BOQ aggregation), listing, v5_pir_target
    Writes: v5_eli5_market_standard
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    eli5_key = f"v5_eli5_{strategy_name}"
    if not force:
        existing = await db.get_unified_estimate(listing_id, eli5_key)
        if isinstance(existing, dict) and existing.get("rooms"):
            logger.info("v5_eli5: reused | listing_id=%s", listing_id)
            return

    # Load BOQ aggregation (must exist from v5_boq stage)
    boq_agg = await db.get_unified_estimate(listing_id, f"v2_{strategy_name}")
    if not (isinstance(boq_agg, dict) and boq_agg.get("line_items")):
        await _reschedule_job(job, db, reason=f"v5_eli5: missing v2_{strategy_name}", delay_seconds=30)
        return

    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_eli5: listing not found | listing_id={listing_id}")

    target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")

    from pipeline.gemini_client import call_gemini_json
    from pricing.v5_eli5 import generate_v5_eli5

    result = await generate_v5_eli5(
        listing_id=int(listing_id),
        strategy_name=strategy_name,
        boq_aggregation=boq_agg,
        listing=listing,
        db=db,
        call_gemini_json=call_gemini_json,
        target_pir=target_pir,
    )
    logger.info("v5_eli5: generated | listing_id=%s | rooms=%d", listing_id, len(result.get("rooms") or []))


# ═══════════════════════════════════════════════════════════════════════════════
# V5 NEGOTIATION ADVISOR — data-driven price negotiation strategy
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_v5_negotiation(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Negotiation: buyer-friendly negotiation guide based on all pipeline data.

    WHY: The buyer has forensic data — PIR, delta, BOQ, comparable — that most
    buyers never have. This step translates that data into practical negotiation
    advice with a main issue, supporting arguments, and a realistic discount range.

    CONDITION-AWARE: If the property is in good condition (not "a reformar"),
    the strategy shifts from defect-based to market-data-based, using Casafari
    brackets (fast_sell, fair_market, premium) and comparable pricing as the
    primary negotiation levers.

    Reads: listing, v5_pir_target, v5_delta_slots_market_standard,
           v2_market_standard, v5_eli5_market_standard, v5_selected_comparable,
           listing_market_stats (Casafari brackets)
    Writes: v5_negotiation
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    if not force:
        existing = await db.get_unified_estimate(listing_id, "v5_negotiation")
        if isinstance(existing, dict) and existing.get("main_issue"):
            logger.info("v5_negotiation: reused | listing_id=%s", listing_id)
            return

    # Load all inputs
    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_negotiation: listing not found | listing_id={listing_id}")

    boq_agg = await db.get_unified_estimate(listing_id, "v2_market_standard")
    if not (isinstance(boq_agg, dict) and boq_agg.get("line_items")):
        await _reschedule_job(job, db, reason="v5_negotiation: missing v2_market_standard", delay_seconds=30)
        return

    target_pir = await db.get_unified_estimate(listing_id, "v5_pir_target")
    delta_slots = await db.get_unified_estimate(listing_id, "v5_delta_slots_market_standard")
    eli5 = await db.get_unified_estimate(listing_id, "v5_eli5_market_standard")
    selected_comparable = await db.get_unified_estimate(listing_id, "v5_selected_comparable")
    market_stats = await db.get_listing_market_stats(listing_id)

    from pipeline.gemini_client import call_gemini_json
    from pricing.v5_negotiation import generate_v5_negotiation

    result = await generate_v5_negotiation(
        listing_id=int(listing_id),
        listing=listing,
        target_pir=target_pir,
        delta_slots=delta_slots,
        boq_aggregation=boq_agg,
        eli5=eli5,
        selected_comparable=selected_comparable,
        market_stats=market_stats,
        db=db,
        call_gemini_json=call_gemini_json,
    )
    logger.info(
        "v5_negotiation: complete | listing_id=%s | issues=%d",
        listing_id, len(result.get("supporting_issues") or []) + 1,
    )


async def handle_v5_architect_report(job: Dict[str, Any], db: Any) -> None:
    """
    DEPRECATED (2026-02-15): Architect report is no longer generated or shown in the product.

    WHY THIS MATTERS: This stage was an extra LLM call chain with ongoing cost and UI surface
    area. We keep the handler as a safe no-op so any already-enqueued jobs can complete
    successfully instead of getting stuck or failing workers.
    """
    listing_id = job.get("listing_id")
    logger.warning("v5_architect_report: deprecated no-op | listing_id=%s", listing_id)
    return


async def handle_v5_room_images(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Room Images: before/after renovation renderings.

    Reads: v2_market_standard, photo_clusters, v5_eli5, v5_delta_slots
    Writes: v5_generated_images_market_standard
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    img_key = f"v5_generated_images_{strategy_name}"
    if not force:
        existing = await db.get_unified_estimate(listing_id, img_key)
        if isinstance(existing, dict) and existing.get("generated_images"):
            logger.info("v5_room_images: reused | listing_id=%s", listing_id)
            return

    boq_agg = await db.get_unified_estimate(listing_id, f"v2_{strategy_name}")
    if not (isinstance(boq_agg, dict) and boq_agg.get("line_items")):
        await _reschedule_job(job, db, reason=f"v5_room_images: missing v2_{strategy_name}", delay_seconds=30)
        return

    photo_clusters = await db.get_photo_clusters(listing_id)
    if not photo_clusters:
        await _reschedule_job(job, db, reason="v5_room_images: missing photo_clusters", delay_seconds=30)
        return

    eli5 = await db.get_unified_estimate(listing_id, f"v5_eli5_{strategy_name}")
    delta_slots = await db.get_unified_estimate(listing_id, f"v5_delta_slots_{strategy_name}")

    from pipeline.gemini_client import call_gemini, call_gemini_image, call_gemini_json
    from pricing.v5_room_images import generate_v5_room_images

    result = await generate_v5_room_images(
        listing_id=int(listing_id),
        strategy_name=strategy_name,
        photo_clusters=photo_clusters,
        boq_aggregation=boq_agg,
        eli5=eli5,
        delta_slots=delta_slots,
        db=db,
        call_gemini_image=call_gemini_image,
        call_gemini_json=call_gemini_json,
        call_gemini=call_gemini,
    )
    logger.info(
        "v5_room_images: generated | listing_id=%s | ok=%d fail=%d",
        listing_id, result.get("images_generated", 0), result.get("images_failed", 0),
    )

    # ── WhatsApp notification (best-effort) ───────────────────────────────
    # If this listing was triggered via WhatsApp, send the results back.
    # This must NEVER crash the pipeline — wrap in try/except.
    try:
        public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip()
        if public_base_url:
            from whatsapp.agent import handle_pipeline_complete
            sent = await handle_pipeline_complete(
                listing_id=int(listing_id),
                public_base_url=public_base_url,
            )
            if sent:
                logger.info("v5_room_images: WhatsApp notification sent | listing_id=%s", listing_id)
        else:
            # Only log at debug — most runs won't have WhatsApp configured
            logger.debug("v5_room_images: PUBLIC_BASE_URL not set, skipping WhatsApp notification")
    except Exception as wa_exc:
        logger.warning(
            "v5_room_images: WhatsApp notification failed (non-fatal) | listing_id=%s | error=%s",
            listing_id, wa_exc,
        )


async def handle_v5_finalize(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Finalize: build v2_delta compatibility layer for the frontend.

    Reads: v5_delta_slots_market_standard
    Writes: v2_delta_market_standard
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    strategy_name = "market_standard"

    delta_key_v2 = f"v2_delta_{strategy_name}"
    if not force:
        existing = await db.get_unified_estimate(listing_id, delta_key_v2)
        if isinstance(existing, dict) and existing.get("dimension_deltas"):
            logger.info("v5_finalize: reused | listing_id=%s", listing_id)
            return

    v5_delta = await db.get_unified_estimate(listing_id, f"v5_delta_slots_{strategy_name}")
    if not (isinstance(v5_delta, dict) and v5_delta.get("rooms")):
        await _reschedule_job(job, db, reason=f"v5_finalize: missing v5_delta_slots_{strategy_name}", delay_seconds=30)
        return

    dimension_deltas: Dict[str, Any] = {}
    for room in v5_delta.get("rooms") or []:
        rid = str(room.get("room_id") or room.get("cluster_id") or "unknown")
        for slot in room.get("slots") or []:
            action = str(slot.get("action") or "")
            if action.lower() in ("no_change", "sin_cambio", ""):
                continue
            dim = str(slot.get("dimension") or "general")
            dimension_deltas.setdefault(dim, {"room_scopes": []})
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
    ok = await db.save_unified_estimate(listing_id, delta_key_v2, delta_v2)
    if not ok:
        raise RuntimeError(f"v5_finalize: failed to save {delta_key_v2} | listing_id={listing_id}")
    logger.info("v5_finalize: saved %s | listing_id=%s", delta_key_v2, listing_id)


async def handle_smart_m2_target_indoorgml(job: Dict[str, Any], db: Any) -> None:
    """
    Target Smart M2 (M1): produce IndoorGML-lite + deterministic quantity primitives.

    Idempotent: skip if smart_m2 exists unless force=true.
    Reschedules until clusters exist.
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    focus_cluster_ids = payload.get("cluster_ids")

    existing = await db.get_smart_m2(listing_id)
    if existing and not force:
        logger.info(f"smart_m2: skip (exists) | listing_id={listing_id}")
        return

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="smart_m2: missing clusters", delay_seconds=45)
        return

    from pipeline.steps.smart_m2 import run_m1_smart_m2

    class _Orchestrator:
        def __init__(self, db: Any) -> None:
            self.db = db

    orchestrator = _Orchestrator(db=db)

    async with GEMINI_PRO_SEMAPHORE:
        await run_m1_smart_m2(
            orchestrator=orchestrator,
            listing_id=listing_id,
            persist_to_db=True,
            focus_cluster_ids=focus_cluster_ids,
        )


async def handle_generate_target_pir(job: Dict[str, Any], db: Any) -> None:
    """Generate target PIR (idempotent)."""
    listing_id = job["listing_id"]
    existing_row = None
    try:
        existing_row = await db.get_pir_row(listing_id, pir_type="target")
    except Exception:
        # Backwards compatibility: older Database impls won't have get_pir_row().
        existing_row = None

    if existing_row and isinstance(existing_row, dict):
        model_version = str(existing_row.get("model_version") or "").strip()
        # Only skip if the PIR is already a current-format PIR.
        # WHY THIS MATTERS: many listings have legacy PIRs that must be regenerated.
        if model_version.lower().startswith("v0.5.0"):
            logger.info(f"target_pir: skip (exists) | listing_id={listing_id} | model_version={model_version}")
        return

    from pricing.pir_generator import generate_target_pir

    listing_data = await db.get_listing(listing_id)
    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="target_pir: missing clusters", delay_seconds=30)
        return

    year_built = listing_data.get("year_built") or listing_data.get("construction_year") or 1990
    year_source = listing_data.get("year_source") or ("listing" if listing_data.get("year_built") else "estimate")
    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        await _reschedule_job(job, db, reason="target_pir: missing smart_m2", delay_seconds=45)
        return

    async with GEMINI_PRO_SEMAPHORE:
        pir = await generate_target_pir(
            listing_id=listing_id,
            listing_data=listing_data,
            room_clusters=clusters,
            year_built=year_built,
            year_source=year_source,
            smart_m2_data=smart_m2,
        )
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_pir(listing_id, {"type": "target", **pir})
    if not ok:
        raise RuntimeError(f"target_pir: save failed | listing_id={listing_id}")


async def handle_generate_cluster_panos(job: Dict[str, Any], db: Any) -> None:
    # Panoramas were removed from the pipeline (quality + reliability reasons).
    # We keep this handler as a no-op for backwards compatibility with any legacy queued jobs.
    listing_id = job.get("listing_id")
    logger.warning(f"cluster_panos: deprecated; skipping | listing_id={listing_id}")
    try:
        await db.add_pipeline_job_event(
            job_id=str(job.get("id")),
            event_type="progress",
            message="cluster_panos deprecated; skipping (panoramas removed from pipeline)",
            data={"listing_id": listing_id},
        )
    except Exception:
        pass
        return


async def handle_cache_comparable_images(job: Dict[str, Any], db: Any) -> None:
    logger.info("cache_comparable_images: skipped (comparables no longer use clustering)")
    return


async def handle_cluster_comparable(job: Dict[str, Any], db: Any) -> None:
    logger.info("cluster_comparable_photos: skipped (comparables no longer use clustering)")
    return


async def handle_strategy_selection(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]
    existing = await db.get_unified_estimate(listing_id, "v2_strategy_selection")

    target_pir = await db.get_pir(listing_id, pir_type="target")
    if not target_pir:
        await _reschedule_job(job, db, reason="strategy_selection: missing target PIR", delay_seconds=30)
        return

    comparables = await db.get_listing_comparables(listing_id)
    if not comparables:
        await _reschedule_job(job, db, reason="strategy_selection: no comparables", delay_seconds=30)
        return

    comp_pirs = []
    comp_prices = {}
    for comp in comparables:
        comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id:
            continue
        pir = await db.get_pir(comp_id, pir_type="comparable")
        if pir:
            comp_pirs.append(pir)
            comp_prices[comp_id] = comp.get("sale_price") or comp.get("price") or comp.get("price_eur") or comp.get("sold_price", 0)

    if existing:
        ref_ids = {
            strategy.get("reference_comparable_id")
            for strategy in existing.get("strategies", [])
            if strategy.get("reference_comparable_id")
        }
        missing_refs = [rid for rid in ref_ids if rid not in comp_prices]
        if not missing_refs and comp_pirs:
            logger.info(f"strategy_selection: skip (valid existing) | listing_id={listing_id}")
            return
        logger.warning(
            f"strategy_selection: stale selection, recomputing | missing_refs={missing_refs} | listing_id={listing_id}"
        )

    if not comp_pirs:
        await _reschedule_job(
            job,
            db,
            reason="strategy_selection: no comparable PIRs",
            delay_seconds=30,
        )
        return

    if len(comp_pirs) < 3:
        logger.warning(
            f"strategy_selection: proceeding with limited comparables | count={len(comp_pirs)} | listing_id={listing_id}"
        )

    from pricing.strategy_selector import select_strategies

    async with GEMINI_FLASH_SEMAPHORE:
        selection = await select_strategies(target_pir=target_pir, comparable_pirs=comp_pirs, comparable_prices=comp_prices)

    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_v2_strategy_selection(listing_id, selection)
    if not ok:
        raise RuntimeError(f"strategy_selection: save failed | listing_id={listing_id}")


async def handle_delta_scopes(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="delta_scopes: missing strategy selection", delay_seconds=30)
        return

    target_pir = await db.get_pir(listing_id, pir_type="target")
    if not target_pir:
        await _reschedule_job(job, db, reason="delta_scopes: missing target PIR", delay_seconds=30)
        return

    comparables = await db.get_listing_comparables(listing_id)
    comparable_pirs: Dict[int, Dict[str, Any]] = {}
    for comp in comparables:
        comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id:
            continue
        pir = await db.get_pir(comp_id, pir_type="comparable")
        if pir:
            comparable_pirs[comp_id] = pir

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="delta_scopes: no strategies", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)

    from pricing.delta_scope_generator import generate_delta_scopes

    async with GEMINI_FLASH_SEMAPHORE:
        delta_scopes = await generate_delta_scopes(
            target_pir=target_pir,
            comparable_pirs=comparable_pirs,
            strategies=strategies,
            target_smart_m2=smart_m2,
        )

    async with DB_WRITE_SEMAPHORE:
        for strategy_name, package in delta_scopes.items():
            ok = await db.save_v2_delta_scopes(listing_id, strategy_name, package)
            if not ok:
                raise RuntimeError(f"delta_scopes: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_delta_strategy_spec(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="delta_strategy_spec: missing strategy selection", delay_seconds=30)
        return

    target_pir = await db.get_pir(listing_id, pir_type="target")
    if not target_pir:
        await _reschedule_job(job, db, reason="delta_strategy_spec: missing target PIR", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        await _reschedule_job(job, db, reason="delta_strategy_spec: missing smart_m2", delay_seconds=45)
        return

    comparables = await db.get_listing_comparables(listing_id)
    comparable_pirs: Dict[int, Dict[str, Any]] = {}
    for comp in comparables:
        comp_id = comp.get("id") or comp.get("comparable_id") or comp.get("listing_id")
        if not comp_id:
            continue
        pir = await db.get_pir(comp_id, pir_type="comparable")
        if pir:
            comparable_pirs[comp_id] = pir

    from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
    from pricing.v3_delta_scopes import generate_strategy_spec_for_strategy_incremental

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="delta_strategy_spec: no strategies", delay_seconds=30)
        return

    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue

        existing = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
        existing_dims = (existing or {}).get("dimensions") if isinstance(existing, dict) else None
        if isinstance(existing_dims, dict) and all(d in existing_dims for d in V2_DIMENSIONS):
            logger.info(f"delta_strategy_spec: skip (complete) | {strategy_name} | listing_id={listing_id}")
            continue

        ref_id = strategy.get("reference_comparable_id")
        ref_pir = comparable_pirs.get(ref_id)
        if not ref_pir:
            await _reschedule_job(
                job,
                db,
                reason=f"delta_strategy_spec: missing comparable PIR | ref_id={ref_id}",
                delay_seconds=30,
            )
            return

        async def _on_dim(dim: str, _payload: Dict[str, Any], partial_spec: Dict[str, Any]) -> None:
            async with DB_WRITE_SEMAPHORE:
                ok = await db.save_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}", partial_spec)
            if not ok:
                raise RuntimeError(f"delta_strategy_spec: partial save failed | {strategy_name} | dim={dim} | listing_id={listing_id}")

        async with GEMINI_FLASH_SEMAPHORE:
            spec = await generate_strategy_spec_for_strategy_incremental(
                target_pir=target_pir,
                comparable_pir=ref_pir,
                smart_m2=smart_m2,
                strategy_name=strategy_name,
                strategy_rationale=strategy.get("strategy_rationale") or strategy.get("rationale") or "",
                existing_dimensions=existing_dims if isinstance(existing_dims, dict) else None,
                on_dimension=_on_dim,
            )

        async with DB_WRITE_SEMAPHORE:
            ok = await db.save_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}", spec)
        if not ok:
            raise RuntimeError(f"delta_strategy_spec: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_delta_bcca_worklist(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="delta_bcca_worklist: missing strategy selection", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        await _reschedule_job(job, db, reason="delta_bcca_worklist: missing smart_m2", delay_seconds=45)
        return

    from pricing.v3_delta_scopes import generate_bcca_worklist_for_strategy

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="delta_bcca_worklist: no strategies", delay_seconds=30)
        return

    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue

        existing = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_{strategy_name}")
        if existing:
            logger.info(f"delta_bcca_worklist: skip (exists) | {strategy_name} | listing_id={listing_id}")
            continue

        strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
        if not strategy_spec:
            await _reschedule_job(
                job,
                db,
                reason=f"delta_bcca_worklist: missing strategy_spec | {strategy_name}",
                delay_seconds=30,
            )
            return
        async with GEMINI_FLASH_SEMAPHORE:
            worklist = await generate_bcca_worklist_for_strategy(
                strategy_spec=strategy_spec,
                smart_m2=smart_m2,
                strategy_name=strategy_name,
            )

        async with DB_WRITE_SEMAPHORE:
            ok = await db.save_unified_estimate(listing_id, f"v3_bcca_worklist_{strategy_name}", worklist)
        if not ok:
            raise RuntimeError(f"delta_bcca_worklist: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_validate_and_repair_worklist(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="validate_worklist: missing strategy selection", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        await _reschedule_job(job, db, reason="validate_worklist: missing smart_m2", delay_seconds=45)
        return

    from pricing.schemas.gemini_schemas_v3 import V3_WORKLIST_REPAIR_SCHEMA
    from pricing.takeoff_menu import build_takeoff_menu
    from pricing.worklist_validator import validate_worklist_items
    from pipeline.gemini_client import call_gemini

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="validate_worklist: no strategies", delay_seconds=30)
        return

    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue

        existing = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_validated_{strategy_name}")
        if existing:
            logger.info(f"validate_worklist: skip (exists) | {strategy_name} | listing_id={listing_id}")
            continue

        raw_worklist = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_{strategy_name}")
        if not raw_worklist:
            await _reschedule_job(
                job,
                db,
                reason=f"validate_worklist: missing raw worklist | {strategy_name}",
                delay_seconds=30,
            )
        return

        dimensions = raw_worklist.get("dimensions") or {}
        takeoff_menu = raw_worklist.get("takeoff_menu") or build_takeoff_menu(smart_m2)

        # Flatten item-centric worklist (worklist_items[].rooms[]) into per-room items for deterministic validation + BOQ.
        items: List[Dict[str, Any]] = []
        for dim, payload in dimensions.items():
            worklist_items = payload.get("worklist_items") or []
            if not isinstance(worklist_items, list):
                continue
            for wi_idx, wi in enumerate(worklist_items):
                if not isinstance(wi, dict):
                    continue
                bcca_description = wi.get("bcca_description")
                unit = wi.get("unit")
                rooms_list = wi.get("rooms") or []
                if not isinstance(rooms_list, list):
                    continue
                for room_idx, r in enumerate(rooms_list):
                    if not isinstance(r, dict):
                        continue
                    next_item = {
                        "dimension": dim,
                        "room_id": r.get("room_id"),
                        "quantity_ref": r.get("quantity_ref"),
                        "unit": unit,
                        "bcca_description": bcca_description,
                    }
                    next_item["_item_id"] = f"{dim}:{wi_idx}:{room_idx}"
                    items.append(next_item)

        if not items:
            raise RuntimeError(f"validate_worklist: empty items | {strategy_name} | listing_id={listing_id}")

        failures = validate_worklist_items(
            items=items,
            smart_m2_rooms=smart_m2.get("rooms") or [],
            takeoff_menu=takeoff_menu,
        )

        if failures:
            failure_payload = [
                {"item_id": f.get("item_id"), "error": f.get("error"), "item": f.get("item")} for f in failures
            ]

            repair_prompt = f"""
You are fixing invalid BCCA worklist items (per-room line items).

WHY THIS MATTERS: The pipeline is deterministic; invalid references break BOQ generation.

For each failed item, return a corrected item with the SAME item_id.
Only fix invalid fields (room_id, quantity_ref, unit, bcca_description).
Do NOT invent new quantities. Select quantity_ref ONLY from TAKEOFF_MENU.

FAILED ITEMS:
{json.dumps(failure_payload, ensure_ascii=False, indent=2)}

TAKEOFF_MENU:
{json.dumps(takeoff_menu, ensure_ascii=False, indent=2)}
""".strip()

            async with GEMINI_FLASH_SEMAPHORE:
                response = await call_gemini(
                    prompt=repair_prompt,
                    model="flash",
                    temperature=0.1,
                    response_schema=V3_WORKLIST_REPAIR_SCHEMA,
                    use_spanish=True,
                )
            if not response.success:
                raise RuntimeError(f"validate_worklist: repair call failed | {strategy_name} | {response.error}")

            repairs = json.loads(response.text).get("repairs") or []
            repairs_by_id = {r.get("item_id"): r for r in repairs if r.get("item_id")}
            if not repairs_by_id:
                raise RuntimeError(f"validate_worklist: repair returned empty | {strategy_name}")

            updated_items: List[Dict[str, Any]] = []
            for item in items:
                item_id = item.get("_item_id")
                if item_id in repairs_by_id:
                    repaired = repairs_by_id[item_id]
                    updated_items.append({**repaired, "_item_id": item_id})
                else:
                    updated_items.append(item)

            failures = validate_worklist_items(
                items=updated_items,
                smart_m2_rooms=smart_m2.get("rooms") or [],
                takeoff_menu=takeoff_menu,
            )
            if failures:
                raise RuntimeError(f"validate_worklist: unrepaired failures | {strategy_name} | count={len(failures)}")
            items = updated_items

        validated_payload = {
            "strategy_name": strategy_name,
            "items": items,
            "dimensions": dimensions,
            "takeoff_menu": takeoff_menu,
            "item_count": len(items),
        }
        async with DB_WRITE_SEMAPHORE:
            ok = await db.save_unified_estimate(
                listing_id,
                f"v3_bcca_worklist_validated_{strategy_name}",
                validated_payload,
            )
        if not ok:
            raise RuntimeError(f"validate_worklist: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_v3_boq_generate(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="v3_boq_generate: missing strategy selection", delay_seconds=30)
        return

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="v3_boq_generate: no strategies", delay_seconds=30)
        return

    from pricing.bcca_embedding_matcher import BccaEmbeddingMatcher
    from pricing.embedding_runtime import embed_text, embed_texts
    from pricing.v3_boq_generator import generate_boq_v3
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    # Prefer richer “full description” embeddings if present, fallback to the smaller optimized index.
    full_embeddings_path = repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_full_f32.npy"
    full_metadata_path = repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_full_metadata.json"
    embeddings_path = full_embeddings_path if full_embeddings_path.exists() else (repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_f32.npy")
    metadata_path = full_metadata_path if full_metadata_path.exists() else (repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_metadata.json")

    matcher = BccaEmbeddingMatcher(embeddings_path=embeddings_path, metadata_path=metadata_path)
    matcher.load()

    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue

        # IMPORTANT: allow foreground timeout slicing without re-embedding/pricing completed strategies.
        # This prevents repeated embedding API calls across slices (cost + time).
        try:
            existing_count = await db.count_boq_line_items(listing_id, strategy_name)
        except Exception:
            existing_count = 0
        if existing_count > 0:
            logger.info(
                f"v3_boq_generate: skip (already has boq_line_items) | {strategy_name} | listing_id={listing_id} | count={existing_count}"
            )
            continue

        worklist = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_validated_{strategy_name}")
        if not worklist:
            await _reschedule_job(
                job,
                db,
                reason=f"v3_boq_generate: missing validated worklist | {strategy_name}",
                delay_seconds=30,
            )
            return

        saved = await generate_boq_v3(
            listing_id=listing_id,
            strategy_name=strategy_name,
            worklist_payload={"cost_components": worklist.get("items") or []},
            db=db,
            matcher=matcher,
            embed_text_fn=embed_text,
            embed_texts_fn=embed_texts,
        )
        logger.info(f"v3_boq_generate: saved line items | {strategy_name} | count={saved}")


async def handle_coverage_ledger_glue(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]

    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="coverage_ledger: missing strategy selection", delay_seconds=30)
        return

    smart_m2 = await db.get_smart_m2(listing_id)
    if not smart_m2:
        await _reschedule_job(job, db, reason="coverage_ledger: missing smart_m2", delay_seconds=45)
        return

    from pricing.coverage_ledger import build_coverage_ledger

    strategies = strategy_selection.get("strategies", [])
    if not strategies:
        await _reschedule_job(job, db, reason="coverage_ledger: no strategies", delay_seconds=30)
        return

    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue

        existing = await db.get_unified_estimate(listing_id, f"v3_coverage_ledger_{strategy_name}")
        if existing:
            logger.info(f"coverage_ledger: skip (exists) | {strategy_name} | listing_id={listing_id}")
            continue

        worklist = await db.get_unified_estimate(listing_id, f"v3_bcca_worklist_validated_{strategy_name}")
        if not worklist:
            await _reschedule_job(
                job,
                db,
                reason=f"coverage_ledger: missing validated worklist | {strategy_name}",
                delay_seconds=30,
            )
            return

        ledger = build_coverage_ledger(
            worklist_items=worklist.get("items") or [],
            smart_m2_rooms=smart_m2.get("rooms") or [],
            takeoff_menu=worklist.get("takeoff_menu") or {},
        )

        async with DB_WRITE_SEMAPHORE:
            ok = await db.save_unified_estimate(listing_id, f"v3_coverage_ledger_{strategy_name}", ledger)
            if not ok:
                raise RuntimeError(f"coverage_ledger: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_v4_run_strategy(job: Dict[str, Any], db: Any) -> None:
    """
    Run the full V4 quantification pipeline for a single strategy (all 6 dimensions).

    Payload:
      - strategy_name (default: conservative)
      - force (bool): if true, clear existing v4 BOQ + rerun.
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    strategy_name = str(payload.get("strategy_name") or "conservative").strip()
    force = bool(payload.get("force", True))

    from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch
    from pricing.embedding_runtime import embed_texts
    from pricing.v4_quantification_pipeline import run_v4_for_strategy

    # Preconditions (fail loud)
    strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
    if not strategy_spec:
        await _reschedule_job(
            job,
            db,
            reason=f"v4_run_strategy: missing strategy_spec | strategy={strategy_name}",
            delay_seconds=30,
        )
        return

    logger.info(f"v4_run_strategy: start | listing_id={listing_id} strategy={strategy_name} force={force}")

    async with GEMINI_FLASH_SEMAPHORE:
        # Worklist + quant planner are flash; forage uses pro internally via call_gemini_json(model="pro").
        summary = await run_v4_for_strategy(
            listing_id=listing_id,
            strategy_name=strategy_name,
            db=db,
            call_gemini=call_gemini,
            call_gemini_json=call_gemini_json,
            fetch_images_batch=fetch_images_batch,
            embed_texts_fn=embed_texts,
            clear_existing_v4=force,
        )

    logger.info(
        "v4_run_strategy: complete | listing_id=%s strategy=%s saved_boq_items_total=%s",
        listing_id,
        strategy_name,
        summary.get("saved_boq_items_total"),
    )


async def handle_v5_generate_target_pir_slots(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Target PIR (slot-first, per-room).

    Writes:
      - unified_estimates: v5_pir_target

    Preconditions:
      - photo_clusters (V5 constrained clustering recommended)

    Payload:
      - force (bool)
      - max_photos_per_room (int, default 12)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))
    max_photos = int(payload.get("max_photos_per_room") or 12)
    concurrency = int(payload.get("concurrency") or 5)
    if concurrency < 1:
        raise ValueError(f"v5_pir_target: concurrency must be >= 1 (got {concurrency})")

    listing_data = await db.get_listing(listing_id)
    if not listing_data:
        await _reschedule_job(job, db, reason="v5_pir_target: listing not found", delay_seconds=30)
        return
    construction_year = listing_data.get("construction_year") or listing_data.get("year_built")

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        await _reschedule_job(job, db, reason="v5_pir_target: missing clusters", delay_seconds=30)
        return
    cluster_ids = {
        str(c.get("cluster_id") or "").strip()
        for c in clusters
        if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()
    }

    # Reuse only if consistent with CURRENT clusters.
    # WHY THIS MATTERS: clustering can change canonical room IDs; reusing a stale PIR will
    # generate downstream work_items for room_ids that no longer exist in photo_clusters.
    existing = None if force else await db.get_unified_estimate(listing_id, "v5_pir_target")
    if isinstance(existing, dict) and isinstance(existing.get("rooms"), list) and existing.get("rooms"):
        existing_room_ids = {
            str(r.get("room_id") or "").strip()
            for r in (existing.get("rooms") or [])
            if isinstance(r, dict) and str(r.get("room_id") or "").strip()
        }
        missing = sorted([rid for rid in existing_room_ids if rid and rid not in cluster_ids])
        if not missing:
            logger.info(
                "v5_pir_target: skip (exists + consistent) | listing_id=%s rooms=%s",
                listing_id,
                len(existing.get("rooms") or []),
            )
            return
        logger.warning(
            "v5_pir_target: stale existing (room_ids not in current clusters) -> regenerating | listing_id=%s missing=%s",
            listing_id,
            missing[:10],
        )

    # Smart M2 is obsolete in the V5 path; clusters are authoritative for room ids/types.
    room_entries: List[Dict[str, Any]] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        rid = str(c.get("cluster_id") or "").strip()
        rt = str(c.get("room_type") or "").strip() or "unknown_room"
        urls = [u for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        if not rid or not urls:
            continue
        # Skip clearly non-room content.
        if rt in ("floorplan", "street_view", "views_outlook"):
            continue
        room_entries.append({"room_id": rid, "room_type": rt, "photo_urls": urls})
    if not room_entries:
        raise RuntimeError(f"v5_pir_target: no usable room clusters | listing_id={listing_id}")

    from pipeline.gemini_client import call_gemini, fetch_images_batch
    from pricing.v5_pir import generate_v5_target_room_pir
    from datetime import datetime, timezone

    rooms_out: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(concurrency)

    async def _run_one(entry: Dict[str, Any]) -> Dict[str, Any]:
        rid_local = str(entry["room_id"])
        rt_local = str(entry["room_type"])
        urls_local = entry["photo_urls"]
        async with sem:
            async with GEMINI_PRO_SEMAPHORE:
                return await generate_v5_target_room_pir(
                    room_id=rid_local,
                    room_type=rt_local,
                    photo_urls=urls_local,
                    construction_year=construction_year,
                    max_photos=max_photos,
                    call_gemini_fn=call_gemini,
                    fetch_images_batch_fn=fetch_images_batch,
                )

    tasks = [asyncio.create_task(_run_one(e)) for e in sorted(room_entries, key=lambda x: str(x.get("room_id") or ""))]
    try:
        for t in asyncio.as_completed(tasks):
            rooms_out.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    payload_out = {
        "listing_id": int(listing_id),
        "rooms": sorted(rooms_out, key=lambda r: str(r.get("room_id") or "")),
        "schema_version": "v5_pir_target_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"rooms": len(rooms_out)},
    }
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, "v5_pir_target", payload_out)
    if not ok:
        raise RuntimeError(f"v5_pir_target: save failed | listing_id={listing_id}")


async def handle_boq_enqueue_jobs(job: Dict[str, Any], db: Any) -> None:
    raise RuntimeError(
        "DISABLED: per-scope-item Gemini BOQ enqueue path was removed to prevent runaway costs. "
        "Use v3 BOQ (deterministic + embeddings-only) via `v3_boq_generate`."
    )


async def handle_boq_llm_scope_item(job: Dict[str, Any], db: Any) -> None:
    raise RuntimeError(
        "DISABLED: per-scope-item Gemini BOQ generation (boq_llm_scope_item) was removed to prevent runaway costs. "
        "Use v3 BOQ (deterministic + embeddings-only) via `v3_boq_generate`."
    )


async def handle_boq_write_items(job: Dict[str, Any], db: Any) -> None:
    raise RuntimeError(
        "DISABLED: boq_write_items belongs to the removed per-scope-item Gemini BOQ path. "
        "Use v3 BOQ (deterministic + embeddings-only) via `v3_boq_generate`."
    )


async def handle_boq_finalize_strategy(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]
    strategy_name = job["payload"]["strategy_name"]

    from pricing.v2_boq_generator import aggregate_boq_from_db

    boq = await aggregate_boq_from_db(listing_id=listing_id, strategy_name=strategy_name, db=db)
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_v2_boq(listing_id, strategy_name, boq)
    if not ok:
        raise RuntimeError(f"boq_finalize: save failed | {strategy_name} | listing_id={listing_id}")


async def handle_boq_finalize_all(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]
    run_id = job.get("run_id")
    if not run_id:
        raise RuntimeError(f"boq_finalize_all: missing run_id | listing_id={listing_id}")
    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="boq_finalize_all: missing strategy selection", delay_seconds=45)
        return

    strategies = strategy_selection.get("strategies", [])
    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue
        await db.enqueue_pipeline_job(
            run_id=job["run_id"],
            listing_id=listing_id,
            stage="boq_finalize",
            job_type="boq_finalize_strategy",
            payload={"strategy_name": strategy_name},
            idempotency_key=_idem_key(run_id=run_id, listing_id=listing_id, suffix=f"boq_finalize:{strategy_name}"),
        )


async def handle_post_boq_enqueue_all(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]
    run_id = job.get("run_id")
    if not run_id:
        raise RuntimeError(f"post_boq_enqueue: missing run_id | listing_id={listing_id}")
    strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection")
    if not strategy_selection:
        await _reschedule_job(job, db, reason="post_boq_enqueue: missing strategy selection", delay_seconds=45)
        return

    strategies = strategy_selection.get("strategies", [])
    for strategy in strategies:
        strategy_name = strategy.get("strategy_name")
        if not strategy_name:
            continue
        boq = await db.get_v2_boq(listing_id, strategy_name)
        if not boq:
            await _reschedule_job(
                job,
                db,
                reason=f"post_boq_enqueue: missing BOQ | {strategy_name}",
                delay_seconds=45,
            )
            return

        await db.enqueue_pipeline_job(
            run_id=run_id,
            listing_id=listing_id,
            stage="post_boq",
            job_type="post_boq_strategy",
            payload={"strategy_name": strategy_name},
            idempotency_key=_idem_key(run_id=run_id, listing_id=listing_id, suffix=f"post_boq:{strategy_name}"),
        )


async def handle_post_boq(job: Dict[str, Any], db: Any) -> None:
    listing_id = job["listing_id"]
    strategy_name = job["payload"]["strategy_name"]

    boq = await db.get_v2_boq(listing_id, strategy_name)
    if not boq:
        await _reschedule_job(job, db, reason=f"post_boq: missing BOQ | {strategy_name}", delay_seconds=45)
        return

    from pricing.v2_orchestrator import V2Orchestrator

    orchestrator = V2Orchestrator(db=db)
    orchestrator.target_pir = await db.get_pir(listing_id, pir_type="target")
    orchestrator.strategy_selection = await db.get_unified_estimate(listing_id, "v2_strategy_selection") or {}
    smart_m2 = await db.get_smart_m2(listing_id)
    orchestrator.smart_m2_rooms = (smart_m2 or {}).get("rooms", [])
    listing_data = await db.get_listing(listing_id)

    enhanced = await orchestrator._run_post_boq_phases(
        listing_id=listing_id,
        strategy_name=strategy_name,
        boq_output=boq,
        listing_data=listing_data,
    )
    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_v2_boq(listing_id, strategy_name, enhanced)
    if not ok:
        raise RuntimeError(f"post_boq: save failed | {strategy_name} | listing_id={listing_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# V5 TRANSLATIONS — pre-compute all language translations for instant switching
# ═══════════════════════════════════════════════════════════════════════════════

TARGET_LANGUAGES = ["en", "de", "fr", "ca", "it"]

async def handle_v5_translations(job: Dict[str, Any], db: Any) -> None:
    """
    V5 Translations: pre-compute translations for all non-Spanish languages.

    WHY THIS MATTERS: The frontend currently translates on-demand via Google
    Translate API calls, which adds 1-3s latency per language switch. By
    pre-computing translations during the pipeline, language switching becomes
    instant for the user.

    Reads:
      - listing (title, description/comments)
      - v5_eli5_market_standard (ELI5 summary sections)
      - v5_room_tags (room labels)
    Writes:
      - v5_translations (all translations keyed by language code)
    """
    listing_id = job["listing_id"]
    payload = job.get("payload") or {}
    force = bool(payload.get("force"))

    translations_key = "v5_translations"

    # Skip if already computed (unless forced)
    if not force:
        existing = await db.get_unified_estimate(listing_id, translations_key)
        if isinstance(existing, dict) and existing.get("languages"):
            logger.info("v5_translations: reused | listing_id=%s", listing_id)
            return

    # ── Gather source texts ──
    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_translations: listing not found | listing_id={listing_id}")

    eli5 = await db.get_unified_estimate(listing_id, "v5_eli5_market_standard")
    room_tags = await db.get_unified_estimate(listing_id, "v5_room_tags")

    # Collect all translatable texts with keys so we can reassemble later
    texts_to_translate: Dict[str, str] = {}

    # Listing basics
    title = listing.get("title") or ""
    description = listing.get("description") or listing.get("comments") or ""
    address = listing.get("address") or ""
    if title:
        texts_to_translate["listing_title"] = title
    if description:
        texts_to_translate["listing_description"] = description
    if address:
        texts_to_translate["listing_address"] = address

    # ELI5 sections — these are the main visible texts in the UI
    if isinstance(eli5, dict):
        rooms = eli5.get("rooms") or []
        summary = eli5.get("summary") or {}
        concept = eli5.get("concept") or {}
        timeline = eli5.get("timeline") or {}

        # Concept: the "Ahora" and "Después" texts
        for key in ["intro_before", "intro_after", "vision_statement", "design_style", "value_story"]:
            val = concept.get(key)
            if isinstance(val, str) and val.strip():
                texts_to_translate[f"eli5_concept_{key}"] = val

        # Timeline summary
        if isinstance(timeline.get("summary"), str) and timeline["summary"].strip():
            texts_to_translate["eli5_timeline_summary"] = timeline["summary"]

        # Summary sections (legacy)
        for key in ["scope_overview", "reasoning_line", "key_rooms",
                     "investment_highlight", "timeline_hook"]:
            val = summary.get(key)
            if isinstance(val, str) and val.strip():
                texts_to_translate[f"eli5_summary_{key}"] = val

        # Room names, taglines, and key changes
        for i, room in enumerate(rooms):
            room_name = room.get("room_name") or room.get("room_type") or ""
            if room_name:
                texts_to_translate[f"room_{i}_name"] = room_name
            tagline = room.get("tagline") or ""
            if tagline:
                texts_to_translate[f"room_{i}_tagline"] = tagline
            # key_changes are the package+cost strings shown per room
            for j, kc in enumerate(room.get("key_changes") or []):
                if isinstance(kc, str) and kc.strip():
                    texts_to_translate[f"room_{i}_kc_{j}"] = kc
            room_desc = room.get("description") or ""
            if room_desc:
                texts_to_translate[f"room_{i}_description"] = room_desc
            # Room items (legacy)
            items = room.get("items") or []
            for j, item in enumerate(items):
                item_desc = item.get("description") or item.get("name") or ""
                if item_desc:
                    texts_to_translate[f"room_{i}_item_{j}"] = item_desc

        # Room packages (name of each package shown in the breakdown)
        for i, room in enumerate(rooms):
            for j, pkg in enumerate(room.get("packages") or []):
                pkg_name = pkg.get("name") or ""
                if pkg_name:
                    texts_to_translate[f"room_{i}_pkg_{j}"] = pkg_name

        # General items key_items
        general_items = eli5.get("general_items") or {}
        for j, ki in enumerate(general_items.get("key_items") or []):
            if isinstance(ki, str) and ki.strip():
                texts_to_translate[f"general_item_{j}"] = ki

    # ── Negotiation data ──
    negotiation = await db.get_unified_estimate(listing_id, "v5_negotiation")
    if isinstance(negotiation, dict):
        main_issue = negotiation.get("main_issue") or {}
        for key in ["title", "explanation"]:
            val = main_issue.get(key)
            if isinstance(val, str) and val.strip():
                texts_to_translate[f"neg_main_{key}"] = val
        for i, si in enumerate(negotiation.get("supporting_issues") or []):
            for key in ["title", "explanation"]:
                val = si.get(key)
                if isinstance(val, str) and val.strip():
                    texts_to_translate[f"neg_si_{i}_{key}"] = val
        for i, tip in enumerate(negotiation.get("framing_tips") or []):
            if isinstance(tip, str) and tip.strip():
                texts_to_translate[f"neg_tip_{i}"] = tip
        rc = negotiation.get("reality_check")
        if isinstance(rc, str) and rc.strip():
            texts_to_translate["neg_reality_check"] = rc

    # Room tag labels
    if isinstance(room_tags, dict):
        for tag_key, tag_val in room_tags.items():
            if isinstance(tag_val, str) and tag_val.strip() and tag_key not in ("listing_id", "schema_version"):
                texts_to_translate[f"tag_{tag_key}"] = tag_val

    if not texts_to_translate:
        logger.warning("v5_translations: nothing to translate | listing_id=%s", listing_id)
        ok = await db.save_unified_estimate(listing_id, translations_key, {
            "listing_id": int(listing_id),
            "schema_version": "v1",
            "languages": {},
            "source_count": 0,
        })
        if not ok:
            raise RuntimeError(f"v5_translations: save failed | listing_id={listing_id}")
        return

    # ── Translate into each target language ──
    from services.translation_service import get_translation_service
    service = get_translation_service()

    source_texts = list(texts_to_translate.values())
    source_keys = list(texts_to_translate.keys())
    total_texts = len(source_texts)

    logger.info(
        "v5_translations: starting | listing_id=%s | texts=%d | languages=%d",
        listing_id, total_texts, len(TARGET_LANGUAGES),
    )

    languages_result: Dict[str, Dict[str, str]] = {}

    for lang in TARGET_LANGUAGES:
        try:
            translated = await asyncio.to_thread(
                service.translate_batch, source_texts, lang, "es"
            )
            lang_dict: Dict[str, str] = {}
            for k, t in zip(source_keys, translated):
                lang_dict[k] = t
            languages_result[lang] = lang_dict
            logger.info(
                "v5_translations: done %s | listing_id=%s | translated=%d",
                lang, listing_id, len(translated),
            )
        except Exception as exc:
            logger.error(
                "v5_translations: failed %s | listing_id=%s | error=%s",
                lang, listing_id, exc,
            )
            # Store what we have; don't fail the whole step for one language
            languages_result[lang] = {"_error": str(exc)}

    # ── Save ──
    # Store source texts alongside translations so the frontend can seed its
    # cache using original_text → translated_text pairs.
    result = {
        "listing_id": int(listing_id),
        "schema_version": "v1",
        "source_language": "es",
        "source_texts": texts_to_translate,  # {key: original_spanish_text}
        "languages": languages_result,       # {lang: {key: translated_text}}
        "source_keys": source_keys,
        "source_count": total_texts,
    }

    async with DB_WRITE_SEMAPHORE:
        ok = await db.save_unified_estimate(listing_id, translations_key, result)
    if not ok:
        raise RuntimeError(f"v5_translations: save failed | listing_id={listing_id}")

    logger.info(
        "v5_translations: complete | listing_id=%s | languages=%d | texts=%d",
        listing_id, len(languages_result), total_texts,
    )

