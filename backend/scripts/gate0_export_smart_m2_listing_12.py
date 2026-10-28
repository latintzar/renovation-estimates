import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from pipeline.steps.smart_m2 import run_m1_smart_m2

from database import Database


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Orchestrator:
    db: Any


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


def _build_rooms_by_cluster(rooms: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    cluster_ids = set()
    name_to_id: Dict[str, str] = {}
    for cluster in clusters:
        cid = cluster.get("cluster_id") or cluster.get("id")
        if not cid:
            continue
        cid = str(cid)
        cluster_ids.add(cid)
        name = cluster.get("cluster_name") or cluster.get("room_name")
        if name:
            name_to_id[str(name).strip().lower()] = cid

    by_cluster: Dict[str, Any] = {}
    for room in rooms:
        cluster_id = room.get("cluster_id") or room.get("room_id")
        if cluster_id and str(cluster_id) not in cluster_ids:
            cluster_id = None
        if not cluster_id:
            cluster_name = room.get("cluster_name") or room.get("room_name")
            if cluster_name:
                cluster_id = name_to_id.get(str(cluster_name).strip().lower())

        if not cluster_id:
            raise RuntimeError(f"Smart M2 room missing cluster_id/room_id/cluster_name | room={room}")

        cluster_id = str(cluster_id)
        if cluster_id in by_cluster:
            raise RuntimeError(f"Duplicate cluster_id in Smart M2 rooms | cluster_id={cluster_id}")

        # Normalize identifiers so viewer selection works.
        room["cluster_id"] = cluster_id
        room["room_id"] = cluster_id
        by_cluster[cluster_id] = room
    return by_cluster


async def _run(listing_id: int) -> None:
    repo_root = _repo_root()

    viewer_path = repo_root / "docs/demos/indoorgml_lite_listing_12_smartm2_viewer.html"
    export_json_path = repo_root / "docs/demos/generated/listing_12_smart_m2_export.json"

    logger.info(f"Gate 0: starting Smart M2 export | listing_id={listing_id}")

    db = Database()
    orchestrator = _Orchestrator(db=db)

    # Run Smart M2 but do not persist to DB yet (Gate 0 rule).
    result = await run_m1_smart_m2(orchestrator, listing_id, persist_to_db=False)
    rooms = result.get("rooms") or []
    if not isinstance(rooms, list) or not rooms:
        raise RuntimeError(f"Smart M2 returned no rooms | listing_id={listing_id}")

    clusters = await db.get_photo_clusters(listing_id)
    if not clusters:
        raise RuntimeError(f"Gate 0: missing clusters for listing {listing_id}")

    rooms_by_cluster = _build_rooms_by_cluster(rooms, clusters)
    export_payload = {
        "listing_id": listing_id,
        "schema": "gate0_smart_m2_export@0.1",
        "rooms_by_cluster": rooms_by_cluster,
        "summary": {
            "rooms_count": len(rooms),
            "total_m2": result.get("total_m2"),
            "circulation_m2": result.get("circulation_m2"),
            "methodology": result.get("methodology"),
        },
    }

    _write_json(export_json_path, export_payload)
    logger.info(f"Gate 0: wrote export JSON | path={export_json_path}")

    # Embed the export JSON directly into the viewer (so opening the HTML “just works” without file:// fetch issues).
    html = _load_text(viewer_path)
    embedded = json.dumps(export_payload, indent=2, ensure_ascii=False)
    html2 = _replace_between_markers(
        html,
        start="<!-- SMART_M2_EXPORT:BEGIN -->",
        end="<!-- SMART_M2_EXPORT:END -->",
        replacement=embedded,
    )
    _write_text(viewer_path, html2)
    logger.info(f"Gate 0: embedded export JSON into viewer | path={viewer_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run(listing_id=12))


if __name__ == "__main__":
    main()

