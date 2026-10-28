import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from pipeline.steps.smart_m2 import (
    _compute_opening_aggregates,
    _compute_room_level_primitives,
    _compute_takeoff_primitives,
)
from pipeline.utils.glb_utils import (
    compute_bbox,
    extract_positions,
    infer_axes_from_bbox,
    load_glb,
    write_glb_with_extras,
)


logger = logging.getLogger(__name__)


def _aspect_ratio_label(length_m: float, width_m: float) -> str:
    if width_m <= 0:
        return "unknown"
    ratio = length_m / width_m
    if ratio < 1.2:
        return "square"
    if ratio < 1.8:
        return "rectangular"
    return "elongated"


def _build_room_from_bbox(
    bbox: Dict[str, List[float]],
    axes: Dict[str, int],
    room_id: str,
) -> Dict[str, Any]:
    size = bbox.get("size_xyz") or []
    if len(size) != 3:
        raise RuntimeError("bbox size_xyz must have 3 elements")

    height_axis = axes["height_axis"]
    floor_axis_a = axes["floor_axis_a"]
    floor_axis_b = axes["floor_axis_b"]

    floor_a = float(size[floor_axis_a])
    floor_b = float(size[floor_axis_b])
    height_m = float(size[height_axis])

    length_m = max(floor_a, floor_b)
    width_m = min(floor_a, floor_b)
    estimated_m2 = length_m * width_m
    perimeter_m = 2 * (length_m + width_m)

    wall_segments = [
        {"wall_id": "w1", "length_m": round(length_m, 3), "height_m": round(height_m, 3), "features": [], "photo_indices": []},
        {"wall_id": "w2", "length_m": round(width_m, 3), "height_m": round(height_m, 3), "features": [], "photo_indices": []},
        {"wall_id": "w3", "length_m": round(length_m, 3), "height_m": round(height_m, 3), "features": [], "photo_indices": []},
        {"wall_id": "w4", "length_m": round(width_m, 3), "height_m": round(height_m, 3), "features": [], "photo_indices": []},
    ]

    room = {
        "room_id": room_id,
        "cluster_id": room_id,
        "cluster_name": "GLB Room",
        "estimated_m2": round(estimated_m2, 3),
        "estimated_dimensions": {
            "length_m": round(length_m, 3),
            "width_m": round(width_m, 3),
            "aspect_ratio": _aspect_ratio_label(length_m, width_m),
            "dimension_confidence": "low",
        },
        "estimated_height_m": round(height_m, 3),
        "perimeter_m": round(perimeter_m, 3),
        "wall_area_m2": round(perimeter_m * height_m, 3),
        "wall_segments": wall_segments,
        "openings": [],
        "features": [],
        "confidence": "low",
        "reasoning": "Single-room envelope inferred from GLB mesh bounding box; no semantic partitioning detected.",
        "assumptions": [
            "Smallest bbox axis treated as height axis.",
            "No openings inferred from geometry without explicit segmentation.",
            "Single-room layout used as conservative default.",
        ],
    }

    return room


def _build_pir_payload(
    glb_path: Path,
    bbox: Dict[str, List[float]],
    axes: Dict[str, int],
    room: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "schema": "glb_pir@0.1",
        "source": {"glb_path": str(glb_path)},
        "bbox": bbox,
        "axis_inference": axes,
        "rooms": [room],
        "global_confidence": "low",
        "scale_assumptions": {
            "unit_guess": "meters",
            "rationale": "GLB from trimesh with typical metric scale; no explicit unit metadata found.",
        },
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _replace_between_markers(text: str, *, start: str, end: str, replacement: str) -> str:
    start_idx = text.find(start)
    end_idx = text.find(end)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise RuntimeError(f"Failed to find marker block | start={start!r} end={end!r}")
    before = text[: start_idx + len(start)]
    after = text[end_idx:]
    return before + "\n" + replacement + "\n" + after


def _embed_in_viewer(viewer_path: Path, output_path: Path, payload: Dict[str, Any]) -> None:
    html = viewer_path.read_text(encoding="utf-8")
    embedded = json.dumps(payload, indent=2, ensure_ascii=False)
    html2 = _replace_between_markers(
        html,
        start="<!-- PIR_EXPORT:BEGIN -->",
        end="<!-- PIR_EXPORT:END -->",
        replacement=embedded,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html2, encoding="utf-8")
    logger.info(f"Embedded PIR payload into viewer | path={output_path}")


def _run(args: argparse.Namespace) -> None:
    glb_path = Path(args.glb).resolve()
    out_dir = Path(args.out_dir).resolve()

    logger.info(f"Loading GLB | path={glb_path}")
    info = load_glb(glb_path)
    points = extract_positions(info)
    logger.info(f"Loaded positions | count={points.shape[0]:,}")

    bbox = compute_bbox(points)
    axes = infer_axes_from_bbox(bbox)
    room = _build_room_from_bbox(bbox, axes, room_id=args.room_id)

    _compute_room_level_primitives(room)
    _compute_opening_aggregates(room)
    _compute_takeoff_primitives(room)

    payload = _build_pir_payload(glb_path, bbox, axes, room)

    pir_path = out_dir / "glb_pir.json"
    meta_path = out_dir / "glb_pir_meta.json"
    _write_json(pir_path, payload)
    _write_json(
        meta_path,
        {
            "glb_path": str(glb_path),
            "bbox": bbox,
            "axis_inference": axes,
            "notes": [
                "Single-room PIR inferred from bbox; low confidence.",
                "Openings and room partitions not inferred.",
            ],
        },
    )
    logger.info(f"Wrote PIR payload | path={pir_path}")
    logger.info(f"Wrote PIR metadata | path={meta_path}")

    if args.embed_glb:
        output_glb = out_dir / "scene_with_pir.glb"
        write_glb_with_extras(info, extras={"pir": payload}, output_path=output_glb)

    if args.embed_viewer:
        viewer_path = Path(args.viewer_template).resolve()
        viewer_out = out_dir / "glb_pir_viewer.html"
        _embed_in_viewer(viewer_path, viewer_out, payload)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build a PIR-style IndoorGML-lite payload from a GLB mesh.")
    parser.add_argument("--glb", required=True, help="Path to GLB file")
    parser.add_argument(
        "--out-dir",
        default=str(repo_root / "docs/reference/glb_pir"),
        help="Output directory",
    )
    parser.add_argument("--room-id", default="room_1", help="Room id for the single-room PIR")
    parser.add_argument("--embed-glb", action="store_true", help="Embed PIR into GLB extras")
    parser.add_argument(
        "--embed-viewer",
        action="store_true",
        help="Embed PIR into the viewer template HTML",
    )
    parser.add_argument(
        "--viewer-template",
        default=str(repo_root / "docs/demos/indoorgml_lite_glb_viewer.html"),
        help="Viewer template HTML path",
    )
    args = parser.parse_args()

    try:
        _run(args)
    except Exception:
        logger.exception("GLB PIR build failed")
        raise


if __name__ == "__main__":
    main()
