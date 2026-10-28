#!/usr/bin/env python3
"""
Smoke: V5 constrained clustering (canonical room types)

Writes:
- photo_clusters (overwritten via save_photo_clusters delete+insert)
- unified_estimates: v5_clusters

Usage:
  python3 scripts/smoke_v5_clustering.py --listing-id 12 --force
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pipeline.gemini_client import set_gemini_tracking_context  # noqa: E402
from pipeline.steps.cluster_photos_v5 import cluster_photos_v5  # noqa: E402
from scripts._md_report import write_md_report  # noqa: E402
from workers.handlers import _build_listing_context  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listing-id", type=int, required=True)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    db = Database()
    listing_id = int(args.listing_id)
    force = bool(args.force)

    # Attach DB + job context so gemini_client can persist call usage rows.
    # WHY THIS MATTERS: by default the gemini client is strict about durable cost persistence.
    run_id = f"smoke_v5_clustering_{listing_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    set_gemini_tracking_context(
        db=db,
        job_ctx={
            "run_id": run_id,
            "listing_id": listing_id,
            "stage": "v5_clustering_smoke",
            "job_type": "smoke",
            "job_id": None,
        },
    )

    existing = await db.get_photo_clusters(listing_id)
    if existing and not force:
        logger.info("v5_clustering: skip (photo_clusters exist) | listing_id=%s clusters=%s", listing_id, len(existing))
        return 0

    photos = await db.get_listing_photos(listing_id)
    if not photos:
        raise RuntimeError(f"v5_clustering: no listing photos | listing_id={listing_id}")
    listing = await db.get_listing(listing_id)
    if not listing:
        raise RuntimeError(f"v5_clustering: listing not found | listing_id={listing_id}")

    listing_context = _build_listing_context(listing)
    property_flags = listing.get("property_flags") or listing.get("flags") or []

    result = await cluster_photos_v5(listing_context=listing_context, photo_urls=photos, property_flags=property_flags)
    clusters = result.get("clusters") or []
    if not clusters:
        raise RuntimeError(f"v5_clustering: no clusters returned | listing_id={listing_id}")

    ok_art = await db.save_unified_estimate(
        listing_id,
        "v5_clusters",
        {
            "listing_id": int(listing_id),
            "schema_version": "v5_clusters_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "clusters": clusters,
            "excluded_content": result.get("excluded_content") or [],
            "version": result.get("version") or "v5",
            "counts": {"clusters": len(clusters)},
        },
    )
    if not ok_art:
        raise RuntimeError(f"v5_clustering: failed to save v5_clusters | listing_id={listing_id}")

    ok = await db.save_photo_clusters(
        listing_id,
        clusters,
        excluded_content=result.get("excluded_content", []),
        ai_image_summary={"version": "v5", "note": "v5 constrained clustering"},
    )
    if not ok:
        raise RuntimeError(f"v5_clustering: failed to save photo_clusters | listing_id={listing_id}")

    sample = clusters[:2]
    report_path = os.path.join(BACKEND_ROOT, "reports", f"smoke_v5_clustering_listing_{listing_id}.md")
    write_md_report(
        report_path=report_path,
        title="Smoke V5 — Constrained clustering (canonical room types)",
        meta={"listing_id": listing_id, "keys_written": ["photo_clusters", "v5_clusters"], "clusters": len(clusters)},
        sample=sample,
        payload={"v5_clusters": await db.get_unified_estimate(listing_id, "v5_clusters")},
    )
    print({"stage": "v5_clustering", "listing_id": listing_id, "report_path": report_path, "clusters": len(clusters)})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

