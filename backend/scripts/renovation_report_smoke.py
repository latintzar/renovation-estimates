#!/usr/bin/env python3
"""
Smoke script for the Renovation Report generator.

WHY THIS EXISTS:
- It is useful for manual debugging.
- It should NOT be collected by pytest (so `python -m pytest` stays non-interactive).
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import httpx


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    repo_root = Path(__file__).resolve().parents[3]  # /root/puedo_casa
    lean_root = repo_root / "lean-mvp"
    pass  # Recipient runtime supplies its explicit private environment.
    pass  # Recipient runtime supplies its explicit private environment.


async def main() -> None:
    _load_env()

    listing_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6

    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL and/or SUPABASE_* key in env/.env.local")

    logger.info("Fetching photos | listing_id=%s", listing_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/listing_photos",
            params={"listing_id": f"eq.{listing_id}", "select": "url"},
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
        )
        resp.raise_for_status()
        photos_data = resp.json() or []

    all_photos = [p["url"] for p in photos_data if p.get("url")]
    logger.info("Found photos | count=%s", len(all_photos))
    if not all_photos:
        raise RuntimeError("No photos found for listing")

    # Distribute photos into rooms (simple heuristic; just for smoke testing).
    photos_by_room: dict[str, list[str]] = {}
    room_names = ["living_room", "kitchen", "bathroom", "bedroom", "general"]
    for i, url in enumerate(all_photos[:15]):
        room = room_names[i % len(room_names)]
        photos_by_room.setdefault(room, []).append(url)

    logger.info("Distributed photos | rooms=%s", len(photos_by_room))

    # Lazy import to keep script runnable even if generator moves.
    from pipeline.steps.renovation_report import RenovationReportGenerator  # type: ignore

    generator = RenovationReportGenerator()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{supabase_url}/rest/v1/listings",
                params={"id": f"eq.{listing_id}", "select": "sqm"},
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
            )
            resp.raise_for_status()
            listing_data = resp.json() or []

        m2 = 100
        if listing_data and isinstance(listing_data, list) and listing_data[0]:
            m2 = int(listing_data[0].get("sqm") or 100)
        logger.info("Property size | sqm=%s", m2)

        report = await generator.generate_report(listing_id=listing_id, photos_by_room=photos_by_room, m2=m2)
        report_dict = generator.to_dict(report)

        out_path = Path("/tmp/renovation_report_smoke.json")
        out_path.write_text(json.dumps(report_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved report | path=%s", out_path)
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())

