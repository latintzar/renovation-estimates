#!/usr/bin/env python3
"""
Export V4 artifacts (and v3 strategy specs) to a Markdown file.

Includes, per strategy:
- v3_strategy_spec_{strategy}
- (if present) v2_delta_{strategy}
- v4_worklist_{strategy}_{dim}
- v4_bcca_matches_{strategy}_{dim}
- v4_quant_plan_{strategy}_{dim}
- (if present) v4_signals_{strategy}, v4_run_summary_{strategy}, v4_pricing_summary_{strategy}
- (if present) v4_signals_shared

Usage:
  PYTHONPATH=... .venv/bin/python -u scripts/export_v4_artifacts_md.py --listing-id 12
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import Database  # noqa: E402
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS


def _json_block(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument(
        "--out",
        default=None,
        help="Output markdown path (default: backend/reports/v4_export_listing_<id>_all.md)",
    )
    parser.add_argument(
        "--strategies",
        nargs="*",
        default=["conservative", "market_standard", "top_of_market"],
        help="Strategies to export (default: conservative market_standard top_of_market)",
    )
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    strategies: List[str] = [str(s).strip() for s in (args.strategies or []) if str(s).strip()]
    if not strategies:
        raise RuntimeError("No strategies provided")

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(backend_root, "reports", f"v4_export_listing_{listing_id}_all.md")
    out_path = args.out or default_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    db = Database()

    now = datetime.now(timezone.utc).isoformat()
    md: List[str] = []
    md.append("# V4 Export (Artifacts)\n")
    md.append(f"- Listing ID: {listing_id}\n")
    md.append(f"- Exported at (UTC): {now}\n")
    md.append(f"- Strategies: {', '.join(strategies)}\n\n")

    # Optional V2 artifacts (useful for grounding strategy scope / deltas)
    for pkg in ("v2_strategy_selection",):
        payload = await db.get_unified_estimate(listing_id, pkg)
        if payload is not None:
            md.append(f"## {pkg}\n\n")
            md.append(_json_block(payload))

    # Shared signals if present
    shared = await db.get_unified_estimate(listing_id, "v4_signals_shared")
    if shared is not None:
        md.append("## v4_signals_shared\n\n")
        md.append(_json_block(shared))

    for strat in strategies:
        md.append(f"\n## Strategy: {strat}\n\n")

        spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strat}")
        md.append(f"### v3_strategy_spec_{strat}\n\n")
        md.append(_json_block(spec))

        delta = await db.get_unified_estimate(listing_id, f"v2_delta_{strat}")
        if delta is not None:
            md.append(f"\n### v2_delta_{strat}\n\n")
            md.append(_json_block(delta))

        # Optional per-strategy artifacts
        for pkg in (f"v4_signals_{strat}", f"v4_run_summary_{strat}", f"v4_pricing_summary_{strat}"):
            payload = await db.get_unified_estimate(listing_id, pkg)
            if payload is not None:
                md.append(f"\n### {pkg}\n\n")
                md.append(_json_block(payload))

        for dim in V2_DIMENSIONS:
            md.append(f"\n### Dimension: {dim}\n\n")
            for prefix in ("v4_worklist", "v4_bcca_matches", "v4_quant_plan"):
                pkg = f"{prefix}_{strat}_{dim}"
                payload = await db.get_unified_estimate(listing_id, pkg)
                md.append(f"#### {pkg}\n\n")
                md.append(_json_block(payload))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(out_path)
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))

