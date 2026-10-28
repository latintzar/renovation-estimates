import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from pipeline.steps.smart_m2 import run_m1_smart_m2_single_room
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


async def _run(listing_id: int, cluster_id: str, model: str) -> None:
    repo_root = _repo_root()

    viewer_path = repo_root / "docs/demos/indoorgml_lite_listing_12_smartm2_viewer.html"
    export_json_path = repo_root / "docs/demos/generated/listing_12_smart_m2_single_room_export.json"

    logger.info(
        f"Gate 0 (single-room): starting Smart M2 export | listing_id={listing_id} cluster_id={cluster_id}"
    )

    db = Database()
    orchestrator = _Orchestrator(db=db)

    result = await run_m1_smart_m2_single_room(
        orchestrator, listing_id, focus_cluster_id=cluster_id, model=model
    )
    room = result.get("room") or {}
    if not isinstance(room, dict):
        raise RuntimeError(f"Smart M2 single-room returned no room | listing_id={listing_id}")

    export_payload: Dict[str, Any] = {
        "listing_id": listing_id,
        "schema": "gate0_smart_m2_single_room_export@0.1",
        "rooms_by_cluster": {cluster_id: room},
        "summary": {"rooms_count": 1},
    }

    _write_json(export_json_path, export_payload)
    logger.info(f"Gate 0 (single-room): wrote export JSON | path={export_json_path}")

    html = _load_text(viewer_path)
    embedded = json.dumps(export_payload, indent=2, ensure_ascii=False)
    html2 = _replace_between_markers(
        html,
        start="<!-- SMART_M2_EXPORT:BEGIN -->",
        end="<!-- SMART_M2_EXPORT:END -->",
        replacement=embedded,
    )
    _write_text(viewer_path, html2)
    logger.info(f"Gate 0 (single-room): embedded export JSON into viewer | path={viewer_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run(listing_id=12, cluster_id="salon_comedor", model="flash"))


if __name__ == "__main__":
    main()
