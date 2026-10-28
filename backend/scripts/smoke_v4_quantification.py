"""
Smoke Test: V4 Quantification (Listing 12)
=========================================

Runs the full V4 pipeline for a single strategy on a single listing and emits a
markdown audit report.

This is a *smoke test* runner, not a prototype: it exercises the full V4 chain.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smoke_v4_quantification")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, default=12)
    parser.add_argument("--strategy", type=str, default="conservative")
    parser.add_argument("--force", action="store_true", default=True)
    args = parser.parse_args()

    # Ensure backend root is on sys.path when running as a script.
    import sys
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from database import Database
    from pipeline.gemini_client import call_gemini, call_gemini_json, fetch_images_batch
    from pricing.embedding_runtime import embed_texts
    from pricing.v4_quantification_pipeline import run_v4_for_strategy

    db = Database()
    listing_id = int(args.listing_id)
    strategy = str(args.strategy).strip()

    logger.info(f"smoke_v4: start | listing_id={listing_id} strategy={strategy}")
    summary = await run_v4_for_strategy(
        listing_id=listing_id,
        strategy_name=strategy,
        db=db,
        call_gemini=call_gemini,
        call_gemini_json=call_gemini_json,
        fetch_images_batch=fetch_images_batch,
        embed_texts_fn=embed_texts,
        clear_existing_v4=bool(args.force),
    )

    # Pull saved intermediates for audit report
    dims = list((summary.get("dimensions") or {}).keys())
    worklists = {}
    plans = {}
    matches = {}
    for d in dims:
        worklists[d] = await db.get_unified_estimate(listing_id, f"v4_worklist_{strategy}_{d}")
        plans[d] = await db.get_unified_estimate(listing_id, f"v4_quant_plan_{strategy}_{d}")
        matches[d] = await db.get_unified_estimate(listing_id, f"v4_bcca_matches_{strategy}_{d}")

    # Write markdown report
    out_dir = Path(__file__).resolve().parents[1] / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"listing_{listing_id}_v4_smoke_{strategy}_{stamp}.md"

    md = []
    md.append(f"# V4 Smoke Test | listing={listing_id} | strategy={strategy}\n")
    md.append("## Summary\n")
    md.append("```json\n" + json.dumps(summary, indent=2, ensure_ascii=False) + "\n```\n")
    md.append("## Inputs\n")
    md.append("- Strategy spec: `v3_strategy_spec_{strategy}`\n")
    md.append("- PIR: `target`\n")
    md.append("- Smart M2: `smart_m2`\n")
    md.append("- Clusters: `photo_clusters` (floorplan cluster appended to each room when present)\n")

    md.append("\n## Per-dimension artifacts\n")
    for d in dims:
        md.append(f"\n### {d}\n")
        md.append("#### Worklist\n")
        md.append("```json\n" + json.dumps(worklists.get(d), indent=2, ensure_ascii=False) + "\n```\n")
        md.append("#### BCCA matches\n")
        md.append("```json\n" + json.dumps(matches.get(d), indent=2, ensure_ascii=False) + "\n```\n")
        md.append("#### Quantification plan\n")
        md.append("```json\n" + json.dumps(plans.get(d), indent=2, ensure_ascii=False) + "\n```\n")

    out_path.write_text("".join(md), encoding="utf-8")
    logger.info(f"smoke_v4: wrote report | path={out_path}")
    logger.info("smoke_v4: complete")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

