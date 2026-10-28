#!/usr/bin/env python3
"""
Clear V4 artifacts for a listing (worklists and downstream) from Supabase.

WHY:
- We changed the V4 worklist prompt; cached v4_worklist_* is now stale.
- All downstream artifacts (matches/plans/signals/summaries/BOQ) depend on that worklist.

This script deletes ONLY V4-related unified_estimates packages plus V4 BOQ rows.
It does NOT delete v3_strategy_spec_* or other non-V4 artifacts.

Usage:
  .venv/bin/python -u scripts/clear_v4_artifacts.py --listing-id 12
  .venv/bin/python -u scripts/clear_v4_artifacts.py --listing-id 12 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import List, Tuple

# Allow running as a script: ensure backend/ is on sys.path so `import database` works.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database import get_client, _get_base_url, _get_headers  # noqa: E402


V4_PACKAGE_LIKE_PATTERNS: List[str] = [
    "v4_worklist_%",         # per strategy + dim
    "v4_bcca_matches_%",     # per strategy + dim
    "v4_quant_plan_%",       # per strategy + dim
    "v4_signals_%",          # per strategy
    "v4_run_summary_%",      # per strategy
    "v4_pricing_summary_%",  # per strategy
    "v4_signals_shared",     # shared listing-level signals
]


async def _delete_unified_estimates(*, listing_id: int, package_filter: str, dry_run: bool) -> Tuple[str, int]:
    """
    Delete unified_estimates rows for listing_id with package_type filter.
    package_filter is either:
      - "eq.<package_type>"
      - "like.<pattern>"
    """
    client = await get_client()
    base = _get_base_url()
    url = f"{base}/unified_estimates"
    params = {
        "listing_id": f"eq.{listing_id}",
        "package_type": package_filter,
    }
    if dry_run:
        print(f"DRY_RUN delete unified_estimates where listing_id=eq.{listing_id} package_type={package_filter}")
        return package_filter, 0
    resp = await client.delete(url, params=params, headers=_get_headers())
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"delete unified_estimates failed | status={resp.status_code} body={resp.text[:500]}")
    # PostgREST doesn't reliably return deleted count; return 0.
    return package_filter, 0


async def _delete_boq_v4(*, listing_id: int, dry_run: bool) -> None:
    client = await get_client()
    base = _get_base_url()
    url = f"{base}/boq_line_items"
    params = {
        "listing_id": f"eq.{listing_id}",
        "dimension": "eq.v4",
    }
    if dry_run:
        print(f"DRY_RUN delete boq_line_items where listing_id=eq.{listing_id} dimension=eq.v4")
        return
    resp = await client.delete(url, params=params, headers=_get_headers())
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"delete boq_line_items failed | status={resp.status_code} body={resp.text[:500]}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    listing_id = int(args.listing_id)
    dry_run = bool(args.dry_run)

    # Delete unified_estimates V4 artifacts
    for pat in V4_PACKAGE_LIKE_PATTERNS:
        if "%" in pat:
            filt = f"like.{pat}"
        else:
            filt = f"eq.{pat}"
        await _delete_unified_estimates(listing_id=listing_id, package_filter=filt, dry_run=dry_run)

    # Delete V4 BOQ line items
    await _delete_boq_v4(listing_id=listing_id, dry_run=dry_run)

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

