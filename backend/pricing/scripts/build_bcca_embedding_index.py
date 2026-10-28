import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import vertexai
from vertexai.language_models import TextEmbeddingModel

logger = logging.getLogger(__name__)


def _load_bcca_codes(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"bcca index not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"bcca index invalid/empty: {path}")
    return data


def _normalize_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "code": row.get("code") or row.get("id"),
        "description": row.get("description") or row.get("desc"),
        "unit": row.get("unit"),
        "price": row.get("price") or row.get("unit_price"),
        "category": row.get("category"),
    }


def build_index(
    *,
    source_path: Path,
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

    logger.info(f"Loading BCCA codes | path={source_path}")
    codes = _load_bcca_codes(source_path)
    metadata = [_normalize_metadata(row) for row in codes]

    model = TextEmbeddingModel.from_pretrained(model_name)
    logger.info(f"Embedding {len(metadata)} items with {model_name}")

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
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved embeddings to {embeddings_path} and metadata to {metadata_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = Path(__file__).resolve().parents[3]
    source = repo_root / "backend" / "pricing" / "data" / "bcca_optimized_index_provable_units.json"
    out_dir = repo_root / "backend" / "pricing" / "data"
    build_index(
        source_path=source,
        embeddings_path=out_dir / "bcca_embeddings_f32.npy",
        metadata_path=out_dir / "bcca_embeddings_metadata.json",
    )


if __name__ == "__main__":
    main()
