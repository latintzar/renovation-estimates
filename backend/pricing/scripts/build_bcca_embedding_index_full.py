import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import vertexai
from vertexai.language_models import TextEmbeddingModel

logger = logging.getLogger(__name__)


def _load_allowed_codes(source_path: Path) -> List[Dict[str, Any]]:
    """
    Load the same curated BCCA subset we already use for embeddings (provable units).
    WHY: Full price_book has non-reno/industrial items; we want richer text, not larger scope.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"bcca source not found: {source_path}")
    data = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"bcca source invalid/empty: {source_path}")
    return data


def _load_from_construction_db(db_path: Path, allowed_codes: set[str]) -> List[Dict[str, Any]]:
    if not db_path.exists():
        raise FileNotFoundError(f"construction db not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # Only pull rows we plan to embed.
    # Note: SQLite parameter limit; query in chunks.
    codes = sorted([c for c in allowed_codes if c])
    out_rows: List[Tuple[Any, ...]] = []
    for i in range(0, len(codes), 900):
        chunk = codes[i : i + 900]
        placeholders = ",".join(["?"] * len(chunk))
        cur.execute(
            f"SELECT id, unit, price, chapter, desc_100, full_desc, description FROM price_book WHERE id IN ({placeholders})",
            chunk,
        )
        out_rows.extend(cur.fetchall())
    conn.close()

    out: List[Dict[str, Any]] = []
    for code, unit, price, chapter, desc_100, full_desc, description in out_rows:
        code = str(code or "").strip()
        if not code:
            continue
        unit_norm = str(unit or "").strip().lower() or None
        price_val = float(price) if price is not None else None
        chapter_norm = str(chapter or "").strip() or None
        d100 = str(desc_100 or "").strip()
        fdesc = str(full_desc or "").strip()
        dlong = str(description or "").strip()

        # Build a richer “box” for embeddings:
        # - desc_100 is a strong short anchor used in other parts of the system
        # - full_desc / description adds detailed semantics (what is included, how it's measured)
        # - unit/chapter help separate similarly-named things that should not cross-match
        text_parts = []
        if d100:
            text_parts.append(d100)
        # Prefer full_desc, fallback to long description.
        if fdesc:
            text_parts.append(fdesc)
        elif dlong:
            text_parts.append(dlong)
        if unit_norm:
            text_parts.append(f"Unidad: {unit_norm}")
        if chapter_norm:
            text_parts.append(f"Capítulo: {chapter_norm}")

        text = "\n".join(text_parts).strip()
        if not text:
            continue

        out.append(
            {
                "code": code,
                "unit": unit_norm,
                "price": price_val,
                "chapter": chapter_norm,
                "desc_100": d100 or None,
                "full_desc": fdesc or None,
                "description": text,
            }
        )

    if not out:
        raise RuntimeError("No BCCA rows loaded from construction db")
    return out


def build_index(
    *,
    embeddings_path: Path,
    metadata_path: Path,
    model_name: str = "text-multilingual-embedding-002",
    batch_size: int = 64,
) -> None:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT_ID not set for embedding build")
    vertexai.init(project=project_id, location=location)

    if embeddings_path.exists() and metadata_path.exists():
        logger.info(f"Embeddings already exist, skipping build | {embeddings_path}")
        return

    repo_root = Path(__file__).resolve().parents[3]
    db_path = repo_root / "backend" / "pricing" / "construction.db"
    source_path = repo_root / "backend" / "pricing" / "data" / "bcca_optimized_index_provable_units.json"

    allowed = _load_allowed_codes(source_path)
    allowed_codes = {str(r.get("code") or r.get("id") or "").strip() for r in allowed if isinstance(r, dict)}
    allowed_codes = {c for c in allowed_codes if c}

    logger.info(f"Loading BCCA subset from construction.db | codes={len(allowed_codes)} | db={db_path}")
    metadata = _load_from_construction_db(db_path, allowed_codes)
    metadata.sort(key=lambda x: x.get("code") or "")

    model = TextEmbeddingModel.from_pretrained(model_name)
    logger.info(f"Embedding {len(metadata)} items with {model_name} | batch_size={batch_size}")

    vectors: List[List[float]] = []
    for i in range(0, len(metadata), batch_size):
        batch = metadata[i : i + batch_size]
        texts = [m.get("description") or "" for m in batch]
        if any(not t for t in texts):
            raise RuntimeError(f"Empty description in batch starting at {i}")
        embeddings = model.get_embeddings(texts)
        vectors.extend([e.values for e in embeddings])
        logger.info(f"  embedded {min(i + batch_size, len(metadata))}/{len(metadata)}")

    emb = np.array(vectors, dtype=np.float32)
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(embeddings_path, emb)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")  # type: ignore[name-defined]
    logger.info(f"Saved embeddings to {embeddings_path} and metadata to {metadata_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = Path(__file__).resolve().parents[3]
    out_dir = repo_root / "backend" / "pricing" / "data"
    build_index(
        embeddings_path=out_dir / "bcca_embeddings_full_f32.npy",
        metadata_path=out_dir / "bcca_embeddings_full_metadata.json",
    )


if __name__ == "__main__":
    main()

