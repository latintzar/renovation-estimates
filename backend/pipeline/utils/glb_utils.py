import json
import logging
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GlbInfo:
    path: Path
    json_data: Dict
    bin_chunk: bytes


def load_glb(path: Path) -> GlbInfo:
    if not path.exists():
        raise FileNotFoundError(f"GLB not found: {path}")

    with path.open("rb") as f:
        header = f.read(12)
        if len(header) != 12:
            raise RuntimeError("GLB header too short")
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise RuntimeError(f"Invalid GLB magic: {magic!r}")
        if version != 2:
            raise RuntimeError(f"Unsupported GLB version: {version}")

        json_chunk = None
        bin_chunk = None
        while f.tell() < length:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_length, chunk_type = struct.unpack("<I4s", chunk_header)
            chunk_data = f.read(chunk_length)
            if chunk_type == b"JSON":
                json_chunk = chunk_data
            elif chunk_type == b"BIN\x00":
                bin_chunk = chunk_data

    if json_chunk is None or bin_chunk is None:
        raise RuntimeError("GLB missing JSON or BIN chunk")

    json_data = json.loads(json_chunk.decode("utf-8"))
    return GlbInfo(path=path, json_data=json_data, bin_chunk=bin_chunk)


def extract_positions(info: GlbInfo) -> np.ndarray:
    accessors = info.json_data.get("accessors") or []
    buffer_views = info.json_data.get("bufferViews") or []
    meshes = info.json_data.get("meshes") or []

    if not accessors or not buffer_views or not meshes:
        raise RuntimeError("GLB missing accessors/bufferViews/meshes")

    positions = []
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            pos_accessor_idx = (primitive.get("attributes") or {}).get("POSITION")
            if pos_accessor_idx is None:
                continue
            accessor = accessors[pos_accessor_idx]
            if accessor.get("componentType") != 5126 or accessor.get("type") != "VEC3":
                raise RuntimeError(
                    f"Unsupported POSITION accessor type: {accessor.get('componentType')} {accessor.get('type')}"
                )
            count = int(accessor["count"])
            buffer_view = buffer_views[accessor["bufferView"]]
            byte_offset = int(buffer_view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
            byte_stride = int(buffer_view.get("byteStride", 12))

            if byte_stride < 12:
                raise RuntimeError(f"Invalid byteStride for POSITION: {byte_stride}")

            if byte_stride == 12:
                data = np.frombuffer(
                    info.bin_chunk,
                    dtype="<f4",
                    count=count * 3,
                    offset=byte_offset,
                ).reshape((count, 3))
                positions.append(data)
                continue

            raw = np.frombuffer(
                info.bin_chunk,
                dtype=np.uint8,
                count=count * byte_stride,
                offset=byte_offset,
            )
            raw = raw.reshape((count, byte_stride))
            data = raw[:, :12].view("<f4").reshape((count, 3))
            positions.append(data)

    if not positions:
        raise RuntimeError("No POSITION accessors found in GLB")

    return np.vstack(positions)


def _read_accessor_array(info: GlbInfo, accessor_idx: int) -> np.ndarray:
    accessors = info.json_data.get("accessors") or []
    buffer_views = info.json_data.get("bufferViews") or []
    if accessor_idx < 0 or accessor_idx >= len(accessors):
        raise RuntimeError(f"Accessor index out of range: {accessor_idx}")

    accessor = accessors[accessor_idx]
    buffer_view = buffer_views[accessor["bufferView"]]

    component_type = int(accessor.get("componentType"))
    accessor_type = str(accessor.get("type"))
    count = int(accessor.get("count"))

    component_map = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    type_map = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

    if component_type not in component_map:
        raise RuntimeError(f"Unsupported componentType: {component_type}")
    if accessor_type not in type_map:
        raise RuntimeError(f"Unsupported accessor type: {accessor_type}")

    dtype = component_map[component_type]
    components = type_map[accessor_type]

    byte_offset = int(buffer_view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    byte_stride = buffer_view.get("byteStride")

    item_bytes = np.dtype(dtype).itemsize * components
    if byte_stride is None or int(byte_stride) == item_bytes:
        data = np.frombuffer(
            info.bin_chunk,
            dtype=dtype,
            count=count * components,
            offset=byte_offset,
        )
        if components == 1:
            return data
        return data.reshape((count, components))

    stride = int(byte_stride)
    raw = np.frombuffer(info.bin_chunk, dtype=np.uint8, count=count * stride, offset=byte_offset).reshape((count, stride))
    data = raw[:, :item_bytes].view(dtype)
    if components == 1:
        return data.reshape((count,))
    return data.reshape((count, components))


def compute_mesh_triangle_metrics(info: GlbInfo, *, max_triangles: int = 2_000_000) -> Dict[str, float | int | Dict[str, int]]:
    """
    Compute simple, deterministic mesh metrics from triangles:
    - triangle_count
    - surface_area
    - normal_bin_counts (coarse orientation bins)
    """
    meshes = info.json_data.get("meshes") or []
    accessors = info.json_data.get("accessors") or []
    if not meshes or not accessors:
        raise RuntimeError("GLB missing meshes/accessors for triangle metrics")

    total_triangles = 0
    total_area = 0.0
    # Coarse bins by dominant axis of normal (abs)
    normal_bins = {"x": 0, "y": 0, "z": 0}

    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            attrs = primitive.get("attributes") or {}
            pos_acc = attrs.get("POSITION")
            if pos_acc is None:
                continue
            positions = _read_accessor_array(info, int(pos_acc)).astype(np.float32)
            if positions.ndim != 2 or positions.shape[1] != 3:
                raise RuntimeError("POSITION accessor must be VEC3")

            indices_acc = primitive.get("indices")
            if indices_acc is None:
                # Non-indexed triangles are rare; skip to avoid guessing topology.
                continue
            indices = _read_accessor_array(info, int(indices_acc)).astype(np.int64)
            if indices.ndim != 1:
                raise RuntimeError("indices accessor must be SCALAR")
            if indices.size % 3 != 0:
                raise RuntimeError("indices count is not divisible by 3 (not triangles)")

            tri_count = indices.size // 3
            if total_triangles + tri_count > max_triangles:
                raise RuntimeError(
                    f"Too many triangles for metric computation | total={total_triangles + tri_count:,} max={max_triangles:,}"
                )

            tris = indices.reshape((-1, 3))
            v0 = positions[tris[:, 0]]
            v1 = positions[tris[:, 1]]
            v2 = positions[tris[:, 2]]
            e1 = v1 - v0
            e2 = v2 - v0
            n = np.cross(e1, e2)
            area = 0.5 * np.linalg.norm(n, axis=1)
            total_area += float(area.sum())
            total_triangles += int(tri_count)

            # Normal bins
            n_norm = np.linalg.norm(n, axis=1)
            valid = n_norm > 1e-9
            nn = n[valid] / n_norm[valid][:, None]
            dominant = np.argmax(np.abs(nn), axis=1)
            normal_bins["x"] += int((dominant == 0).sum())
            normal_bins["y"] += int((dominant == 1).sum())
            normal_bins["z"] += int((dominant == 2).sum())

    return {
        "triangle_count": total_triangles,
        "surface_area": round(total_area, 6),
        "normal_bin_counts": normal_bins,
    }


def compute_bbox(points: np.ndarray) -> Dict[str, list]:
    if points.size == 0:
        raise RuntimeError("Cannot compute bbox from empty points")
    min_xyz = points.min(axis=0)
    max_xyz = points.max(axis=0)
    size_xyz = max_xyz - min_xyz
    return {
        "min_xyz": min_xyz.tolist(),
        "max_xyz": max_xyz.tolist(),
        "size_xyz": size_xyz.tolist(),
    }


def infer_axes_from_bbox(bbox: Dict[str, list]) -> Dict[str, int]:
    size = bbox.get("size_xyz") or []
    if len(size) != 3:
        raise RuntimeError("bbox size_xyz must have 3 elements")

    size_with_idx = list(enumerate(size))
    size_sorted = sorted(size_with_idx, key=lambda item: item[1])

    height_axis = size_sorted[0][0]
    floor_axes = [idx for idx, _ in size_sorted[1:]]
    return {
        "height_axis": height_axis,
        "floor_axis_a": floor_axes[0],
        "floor_axis_b": floor_axes[1],
    }


def write_glb_with_extras(info: GlbInfo, extras: Dict, output_path: Path) -> None:
    json_data = dict(info.json_data)
    json_data["extras"] = extras

    json_bytes = json.dumps(json_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_padding = (4 - (len(json_bytes) % 4)) % 4
    json_bytes_padded = json_bytes + (b" " * json_padding)

    bin_bytes = info.bin_chunk
    bin_padding = (4 - (len(bin_bytes) % 4)) % 4
    bin_bytes_padded = bin_bytes + (b"\x00" * bin_padding)

    total_length = 12 + 8 + len(json_bytes_padded) + 8 + len(bin_bytes_padded)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_length))
        f.write(struct.pack("<I4s", len(json_bytes_padded), b"JSON"))
        f.write(json_bytes_padded)
        f.write(struct.pack("<I4s", len(bin_bytes_padded), b"BIN\x00"))
        f.write(bin_bytes_padded)

    logger.info(f"Wrote GLB with extras | path={output_path}")
