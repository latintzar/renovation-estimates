import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import sqlite3
import re

logger = logging.getLogger(__name__)

# This is NOT “keyword must-haves”. It's a data curation denylist to remove clearly non-residential /
# non-renovation items from the searchable pricebook, so embeddings can't drift into absurd matches.
_DENY_SUBSTRINGS = [
    # ── Medical / institutional ──
    "quiróf",                       # medical / OR
    "quirof",
    "esclusa",
    "transfer",
    # ── Vertical transport (commercial) ──
    "ascensor",
    "elevador",
    "montacargas",
    # ── Commercial doors ──
    "puerta corredera automát",     # auto sliding doors (commercial)
    "puerta corredera curva",       # curved auto doors (commercial)
    # ── Safety / industrial ──
    "protección dorsal",            # PPE ladders etc.
    "radar",
    # ── Testing / inspection services (not construction work) ──
    "blower door",                  # air tightness test (ch.18) — 18UDA00040 etc.
    "ensayo rellenos cámara",       # insulation fill test (ch.18)
    "ensayo estanqueidad",          # watertightness test
    "func. inst. bt",              # functional inspection of low-voltage (ch.18)
    "localización avería",          # fault-finding maintenance visit — not construction
    # ── Public / urban infrastructure ──
    "alumbrado público",            # public street / park lighting — 15EPP* codes
    "mobiliario urbano",            # street furniture
    # ── Provisional site facilities (not final construction) ──
    "prov. local aseos",            # temporary construction-site toilets — 19LAA/19LIA
    "prov. local comedor",          # temporary construction-site canteen
    "prov. local vestuario",        # temporary construction-site changing rooms
    # NOTE: "armario cuadro mando" is NOT denied globally because small 9-element boards
    # (EUR 22-38) are legitimate residential items. Large cabinets are caught by
    # _is_obviously_overspecified_resi_item() below instead.
    # ── Aluminium panel cladding (industrial facade, not interior finish) ──
    "chapa al lacado",              # aluminium sheet cladding — 10LAM90002
    "chapa al anodizado",           # aluminium sheet cladding — 10LAM90001
    # ── Commercial / office flooring (not residential) ──
    "suelo elevado registrable",    # raised access floor — 10SWW90008 etc. (office/data-centre)
    # ── Ventilated / marble facade cladding (exterior commercial, not interior) ──
    "fachada vent",                 # ventilated facade systems — 06EVP* codes
    # ── Building-block-level electrical supply (block, not dwelling) ──
    "acometida eléctrica bloque",   # block-level electrical supply — 21IEAS00020
    # ── Large-scale structural opening (commercial scale) ──
    "apertura hueco >1m en muro",   # opening >1m in load-bearing wall — 06RLA00500 (overscoped for resi)
]


def _load_labor_hours_from_bcca_full_index(path: Path) -> Dict[str, float]:
    """
    Load labor hours per unit from the canonical BCCA full index file.
    Format per line:
      CODE|UNIT|PRICE|DESC|LABOR_HOURS|BREAKDOWN
    """
    if not path.exists():
        return {}
    out: Dict[str, float] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("|")
        if len(parts) < 6:
            continue
        code = parts[0].strip()
        labor_raw = parts[4].strip()
        if not code or not labor_raw:
            continue
        try:
            out[code] = float(labor_raw)
        except Exception:
            continue
    return out


def _is_obviously_overspecified_resi_item(code: str, desc_100: str) -> bool:
    """
    Filter oversized or commercial-grade variants that explode costs for residential estimates.
    Keep this conservative and explainable.

    WHY THIS MATTERS:
    The BCCA pricebook covers everything from single-dwelling to commercial/industrial.
    If an item is clearly oversized for residential renovation (e.g., 120kW boiler, 100kW
    A/C, industrial ductwork), it will massively inflate per-room BOQ if matched.
    """
    d = (desc_100 or "").lower()
    # Boilers: exclude very large kW ratings (e.g., 120kW) — not typical for a single dwelling.
    if "caldera" in d and "kw" in d:
        nums = re.findall(r"(\d+(?:\.\d+)?)\s*kw", d)
        try:
            for n in nums:
                if float(n) >= 50.0:
                    return True
        except Exception:
            pass
    # A/C splits: exclude semi-industrial (>5kW). Residential splits are typically 2-5kW.
    if "split" in d and "kw" in d:
        nums = re.findall(r"(\d+(?:[.,]\d+)?)\s*kw", d)
        try:
            for n in nums:
                if float(n.replace(",", ".")) > 5.5:
                    return True
        except Exception:
            pass
    # Electrical/HVAC cabinets: large industrial cabinets (>=1200mm dimension) are not residential.
    # Small 9-element boards (EUR 22-38) are residential and kept.
    if "armario cuadro mando" in d:
        if any(dim in d for dim in ("1500", "1200", "1900", "2000")):
            return True
    return False


class BccaEmbeddingMatcher:
    """
    Loads a precomputed embedding index and matches BCCA descriptions to codes.

    This module is deterministic (no LLM calls). It expects:
    - embeddings: float32 matrix [N, D]
    - metadata: list of dicts with keys: code, description, unit, price, category (optional)
    """

    def __init__(self, embeddings_path: Path, metadata_path: Path) -> None:
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path
        self._embeddings: np.ndarray | None = None
        self._metadata: List[Dict[str, Any]] | None = None
        self._metadata_by_code: Dict[str, Dict[str, Any]] | None = None

    def load(self) -> None:
        if not self.embeddings_path.exists():
            raise FileNotFoundError(f"bcca_embedding_matcher: embeddings not found | {self.embeddings_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"bcca_embedding_matcher: metadata not found | {self.metadata_path}")

        self._embeddings = np.load(self.embeddings_path)
        with self.metadata_path.open("r", encoding="utf-8") as f:
            self._metadata = json.load(f)
        self._metadata_by_code = None

        if not isinstance(self._metadata, list) or self._embeddings is None:
            raise RuntimeError("bcca_embedding_matcher: invalid embeddings/metadata")
        if len(self._metadata) != self._embeddings.shape[0]:
            raise RuntimeError(
                f"bcca_embedding_matcher: embeddings/metadata length mismatch | emb={self._embeddings.shape[0]} meta={len(self._metadata)}"
            )

        # Backfill missing fields from the local BCCA pricebook DB (pricing/construction.db).
        # WHY: embeddings metadata can be shipped without prices/chapters; BOQ generation needs unit_price + (optional) labor hours.
        try:
            db_path = Path(__file__).parent / "construction.db"
            if db_path.exists():
                # Labor hours come from the canonical full index text file (it contains LABOR_HOURS explicitly).
                labor_path = Path(__file__).parent / "data" / "bcca_full_index.txt"
                labor_by_code = _load_labor_hours_from_bcca_full_index(labor_path)

                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT id, unit, price, chapter, desc_100 FROM price_book")
                by_code = {row[0]: {"unit": row[1], "price": row[2], "chapter": row[3], "desc_100": row[4]} for row in cur.fetchall()}
                conn.close()

                filled = 0
                # Also compute a filtered index to remove non-residential / industrial items.
                keep_indices: List[int] = []
                dropped = 0

                for m in self._metadata:
                    if not isinstance(m, dict):
                        continue
                    code = m.get("code")
                    if not code:
                        continue

                # Pass 1: backfill all metadata dicts in-place (stable ordering).
                for idx, m in enumerate(self._metadata):
                    if not isinstance(m, dict):
                        continue
                    code = m.get("code")
                    if not code:
                        continue
                    rec = by_code.get(code)
                    if rec:
                        if m.get("price") is None and rec.get("price") is not None:
                            m["price"] = float(rec["price"])
                            filled += 1
                        if not m.get("unit") and rec.get("unit"):
                            m["unit"] = rec.get("unit")
                        if rec.get("chapter") is not None and m.get("chapter") is None:
                            m["chapter"] = str(rec.get("chapter"))
                        if rec.get("desc_100") and m.get("desc_100") is None:
                            m["desc_100"] = rec.get("desc_100")
                        if m.get("labor_hours_per_unit") is None:
                            lh = labor_by_code.get(code)
                            if lh is not None:
                                m["labor_hours_per_unit"] = float(lh)

                # Pass 2: build keep mask (drop obviously industrial / overspecified items).
                for idx, m in enumerate(self._metadata):
                    if not isinstance(m, dict):
                        continue
                    code = str(m.get("code") or "")
                    desc_100 = str(m.get("desc_100") or m.get("description") or "")
                    dlow = desc_100.lower()

                    if any(s in dlow for s in _DENY_SUBSTRINGS):
                        dropped += 1
                        continue
                    if _is_obviously_overspecified_resi_item(code, desc_100):
                        dropped += 1
                        continue
                    # Exclude elevator chapter (observed as 'I' in this dataset).
                    ch = str(m.get("chapter") or "")
                    if ch == "I":
                        dropped += 1
                        continue
                    keep_indices.append(idx)

                if dropped > 0:
                    self._metadata = [self._metadata[i] for i in keep_indices]  # type: ignore[index]
                    self._embeddings = self._embeddings[keep_indices, :]
                logger.info(f"bcca_embedding_matcher: backfilled prices | filled={filled} | dropped={dropped} | kept={len(self._metadata)}")
            else:
                logger.warning(f"bcca_embedding_matcher: construction.db not found | path={db_path}")
        except Exception as e:
            logger.exception(f"bcca_embedding_matcher: failed to backfill prices | error={e}")

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._embeddings = self._embeddings / norms
        logger.info(f"✅ BCCA embeddings loaded | count={self._embeddings.shape[0]} dim={self._embeddings.shape[1]}")

    def get_metadata_by_code_map(self) -> Dict[str, Dict[str, Any]]:
        if self._metadata is None:
            raise RuntimeError("bcca_embedding_matcher: call load() first")
        if self._metadata_by_code is None:
            self._metadata_by_code = {
                str(m.get("code")): m for m in self._metadata if isinstance(m, dict) and m.get("code")
            }
        return self._metadata_by_code

    def make_subset_matcher(self, *, allowed_codes: set[str]) -> "BccaEmbeddingMatcher":
        """
        Create an in-memory subset matcher restricted to allowed BCCA codes.

        Notes:
        - Assumes `load()` has been called on the base matcher.
        - Preserves cosine-normalized embeddings already computed by `load()`.
        - Used to build per-dimension matchers without re-loading or re-embedding.
        """
        if self._embeddings is None or self._metadata is None:
            raise RuntimeError("bcca_embedding_matcher: call load() before make_subset_matcher()")
        allowed = {str(c).strip() for c in (allowed_codes or set()) if str(c).strip()}
        if not allowed:
            raise RuntimeError("bcca_embedding_matcher: allowed_codes is empty")

        keep_indices: List[int] = []
        keep_meta: List[Dict[str, Any]] = []
        for i, m in enumerate(self._metadata):
            if not isinstance(m, dict):
                continue
            code = str(m.get("code") or "").strip()
            if code and code in allowed:
                keep_indices.append(i)
                keep_meta.append(m)
        if not keep_indices:
            raise RuntimeError("bcca_embedding_matcher: subset resulted in empty index")

        subset = BccaEmbeddingMatcher(embeddings_path=self.embeddings_path, metadata_path=self.metadata_path)
        subset._embeddings = self._embeddings[keep_indices, :]
        subset._metadata = keep_meta
        subset._metadata_by_code = None
        return subset

    def match(
        self,
        query_embedding: np.ndarray,
        *,
        unit: str | None,
        top_k: int = 5,
        category_hint: str | None = None,
        chapter_prefixes: List[str] | None = None,
        min_similarity: float = 0.45,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Returns top_k matches with similarity scores, enforcing unit gating.
        """
        if self._embeddings is None or self._metadata is None:
            raise RuntimeError("bcca_embedding_matcher: call load() first")
        if query_embedding.ndim != 1:
            raise ValueError("bcca_embedding_matcher: query_embedding must be 1D")

        # Normalize query
        q = query_embedding.astype(np.float32)
        qn = np.linalg.norm(q)
        if qn == 0:
            raise ValueError("bcca_embedding_matcher: query embedding norm is zero")
        q = q / qn

        candidates: List[int] | range = range(len(self._metadata))

        # Optional: filter candidates by a metadata category field (if present).
        if category_hint:
            candidates = [
                i
                for i, m in enumerate(self._metadata)
                if str(m.get("category") or "") == str(category_hint)
            ]

        # Optional: filter candidates by BCCA chapter prefixes (e.g., ["01", "08"]).
        # This is a pragmatic gating heuristic to keep embedding matches within the right trade bucket.
        if chapter_prefixes:
            allowed = [str(c).strip() for c in chapter_prefixes if str(c).strip()]
            if allowed:
                base = list(candidates) if not isinstance(candidates, range) else list(candidates)
                filtered = []
                for i in base:
                    ch = str((self._metadata[i] or {}).get("chapter") or "").strip()
                    if any(ch.startswith(a) for a in allowed):
                        filtered.append(i)
                candidates = filtered

        if not candidates:
            candidates = range(len(self._metadata))

        # Compute similarity for candidates
        emb = self._embeddings[list(candidates)]
        scores = emb @ q

        scored = []
        for idx, sim in zip(candidates, scores):
            meta = self._metadata[idx]
            if unit and meta.get("unit") and str(meta.get("unit")).lower() != str(unit).lower():
                continue
            scored.append((float(sim), meta))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [(s, m) for s, m in scored[:top_k] if s >= min_similarity]
        if not top:
            raise RuntimeError("bcca_embedding_matcher: no matches above threshold")
        return top

