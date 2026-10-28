import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from pipeline.gemini_client import call_gemini_json, fetch_image_as_base64
from pipeline.steps.smart_m2 import (
    get_smart_m2_single_room_prompt,
    _compute_opening_derived_fields,
    _compute_wall_segment_derived_fields,
    _compute_room_level_primitives,
    _compute_opening_aggregates,
    _compute_feature_aggregates,
    _compute_takeoff_primitives,
    _compute_room_waste_m3_menu,
    _load_waste_rules,
)

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    # .../lean-mvp/backend/scripts -> repo root
    return Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _replace_between_markers(text: str, *, start: str, end: str, replacement: str) -> str:
    start_idx = text.find(start)
    end_idx = text.find(end)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise RuntimeError(f"Failed to find marker block | start={start!r} end={end!r}")
    before = text[: start_idx + len(start)]
    after = text[end_idx:]
    return before + "\n" + replacement + "\n" + after


def _normalize_wall_ids(room: Dict[str, Any]) -> None:
    wall_segments = room.get("wall_segments") or []
    if not isinstance(wall_segments, list) or not wall_segments:
        raise RuntimeError("smart_m2_panorama: missing wall_segments")
    wall_id_map: Dict[str, str] = {}
    for idx, segment in enumerate(wall_segments, start=1):
        if not isinstance(segment, dict):
            continue
        old_id = str(segment.get("wall_id") or f"w{idx}")
        new_id = f"w{idx}"
        wall_id_map[old_id] = new_id
        segment["wall_id"] = new_id
    room["wall_segments"] = wall_segments

    def _remap_wall_id(item: Dict[str, Any]) -> None:
        wall_id = item.get("wall_id")
        if wall_id and wall_id in wall_id_map:
            item["wall_id"] = wall_id_map[wall_id]

    openings = room.get("openings") or []
    if not isinstance(openings, list):
        openings = []
    for opening in openings:
        if isinstance(opening, dict):
            _remap_wall_id(opening)
            _compute_opening_derived_fields(opening)
    room["openings"] = openings

    features = room.get("features") or []
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, dict):
                _remap_wall_id(feature)
    room["features"] = features


async def _run(args: argparse.Namespace) -> None:
    repo_root = _repo_root()
    pano_url = args.image_url.strip()

    cluster_id = args.cluster_id.strip()
    cluster_name = args.cluster_name.strip() or cluster_id
    room_type = args.room_type.strip() or "room"

    viewer_path = repo_root / "docs/demos/indoorgml_lite_panorama_room_viewer.html"
    export_json_path = repo_root / "docs/demos/generated/panorama_smart_m2_single_room_export.json"

    logger.info("Gate 0 (panorama single-room): starting export")
    logger.info(f"  → image_url={pano_url}")
    logger.info(f"  → cluster_id={cluster_id} room_type={room_type}")

    cluster = {
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "room_type": room_type,
        "photo_urls": [pano_url],
    }

    listing_context = "PROPERTY CONTEXT:\n- Title: Panorama test (single room)\n- Bedrooms: N/A\n- Bathrooms: N/A\n- City: N/A"
    prompt = get_smart_m2_single_room_prompt(cluster=cluster, listing_context=listing_context)
    prompt += (
        "\n\nIMPORTANT CONTEXT:\n"
        "- The provided image is a SINGLE-ROOM PANORAMA (equirectangular projection).\n"
        "- Straight lines may appear curved; rely on semantic cues and relative proportions.\n"
        "- Do not assume multiple rooms; treat it as one enclosed space.\n"
        "- OPENINGS include doors, windows, and floor-to-ceiling glazing/doors.\n"
        "- If a door is open, the opening is still the door frame (treat it as a door opening).\n"
        "- Floor-to-ceiling windows/doors should be treated as openings even if the sill is at floor level."
    )
    prompt += f"\n\nPHOTO INDEX MAP:\n1. [{cluster_name}] {pano_url}\n"

    logger.info("  → Fetching panorama image")
    image = await fetch_image_as_base64(pano_url)
    if not image:
        raise RuntimeError("Failed to fetch panorama image")

    logger.info(f"  → Calling Gemini | model={args.model}")
    result = await call_gemini_json(
        prompt=prompt,
        model=args.model,
        temperature=0.1,
        images=[image],
        use_spanish=True,
    )
    if not result or not isinstance(result, dict) or "room" not in result:
        raise RuntimeError(f"Invalid Gemini response | keys={list((result or {}).keys())}")

    room = result.get("room") or {}
    if not isinstance(room, dict):
        raise RuntimeError("Gemini response missing room object")

    room["cluster_id"] = cluster_id
    room["room_id"] = cluster_id
    room["cluster_name"] = cluster_name
    room["room_type"] = room_type

    _normalize_wall_ids(room)
    _compute_wall_segment_derived_fields(room)
    _compute_room_level_primitives(room)
    _compute_opening_aggregates(room)
    _compute_feature_aggregates(room)
    _compute_takeoff_primitives(room)

    waste_rules = _load_waste_rules()
    room["waste_m3_by_rule"] = _compute_room_waste_m3_menu(room, waste_rules)

    export_payload: Dict[str, Any] = {
        "schema": "gate0_smart_m2_panorama_export@0.1",
        "source": {"image_url": pano_url, "note": "single panorama input"},
        "rooms_by_cluster": {cluster_id: room},
        "summary": {"rooms_count": 1},
    }

    _write_json(export_json_path, export_payload)
    logger.info(f"  → Wrote export JSON | path={export_json_path}")

    html = _load_text(viewer_path)
    embedded = json.dumps(export_payload, indent=2, ensure_ascii=False)
    html2 = _replace_between_markers(
        html,
        start="<!-- SMART_M2_EXPORT:BEGIN -->",
        end="<!-- SMART_M2_EXPORT:END -->",
        replacement=embedded,
    )
    _write_text(viewer_path, html2)
    logger.info(f"  → Embedded export JSON into viewer | path={viewer_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Gate0: Smart M2 single-room from panorama URL.")
    parser.add_argument("--image-url", required=True, help="Panorama image URL")
    parser.add_argument("--cluster-id", default="panorama_room", help="Cluster id for the room")
    parser.add_argument("--cluster-name", default="Panorama Room", help="Cluster name for the room")
    parser.add_argument("--room-type", default="room", help="Room type (e.g., living_room)")
    parser.add_argument("--model", default="pro", help="Gemini model alias (pro|flash|flash-lite)")
    args = parser.parse_args()

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
