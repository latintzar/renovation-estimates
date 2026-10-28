import logging
from functools import lru_cache
import inspect
from typing import List

import numpy as np
from vertexai.language_models import TextEmbeddingModel

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbeddingModel:
    model_name = "text-multilingual-embedding-002"
    logger.info(f"embedding_runtime: loading model | {model_name}")
    return TextEmbeddingModel.from_pretrained(model_name)


def embed_texts(texts: List[str]) -> List[np.ndarray]:
    if not texts:
        raise RuntimeError("embedding_runtime: empty texts")
    model = get_embedding_model()
    # Vertex AI SDK API compatibility:
    # Some versions of TextEmbeddingModel.get_embeddings() do NOT accept `task_type`.
    # We feature-detect support to avoid runtime failures while keeping behavior consistent.
    try:
        sig = inspect.signature(model.get_embeddings)
        if "task_type" in sig.parameters:
            embeddings = model.get_embeddings(texts, task_type="RETRIEVAL_QUERY")
        else:
            embeddings = model.get_embeddings(texts)
    except TypeError:
        # Fallback: older SDKs may not expose a stable signature; try without task_type.
        embeddings = model.get_embeddings(texts)
    return [np.array(e.values, dtype=np.float32) for e in embeddings]


def embed_text(text: str) -> np.ndarray:
    if not text or not isinstance(text, str):
        raise RuntimeError("embedding_runtime: empty text")
    return embed_texts([text])[0]
