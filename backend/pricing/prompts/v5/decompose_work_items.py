from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _slot_id_to_dimension(slot_id: str) -> str:
    s = str(slot_id or "")
    if s.startswith("shell."):
        return "shell_preparation"
    if s.startswith("enclosure."):
        return "apertures_enclosure"
    if s.startswith("mep."):
        return "systems_services"
    if s.startswith("finishes."):
        return "surface_finishes"
    if s.startswith("joinery."):
        return "fixed_joinery_equipment"
    if s.startswith("details."):
        return "details_fittings"
    return "systems_services"


# Minimal, dimension-scoped vocabulary guide (BCCA-ish).
# NOTE: This is intentionally small; it’s a constraint to keep outputs matchable,
# not a full cost catalog dump.
def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


_VOCAB_CACHE: Dict[str, Dict[str, List[str]]] | None = None


def _load_bcca_vocab_by_dimension_v1() -> Dict[str, Dict[str, List[str]]]:
    global _VOCAB_CACHE
    if _VOCAB_CACHE is not None:
        return _VOCAB_CACHE
    repo_root = _get_repo_root()
    p = repo_root / "backend" / "pricing" / "data" / "bcca_by_dimension_v1" / "bcca_vocab_by_dimension_v1.json"
    if not p.exists():
        raise RuntimeError(f"v5 decompose: missing bcca vocab-by-dim artifacts | path={p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("v5 decompose: invalid bcca_vocab_by_dimension_v1.json")
    out: Dict[str, Dict[str, List[str]]] = {}
    for dim, vv in raw.items():
        if not isinstance(dim, str) or not isinstance(vv, dict):
            continue
        nouns = vv.get("nouns") or []
        verbs = vv.get("verbs") or []
        if not isinstance(nouns, list) or not isinstance(verbs, list):
            continue
        out[dim] = {
            "nouns": [str(x) for x in nouns if isinstance(x, str) and x.strip()],
            "verbs": [str(x) for x in verbs if isinstance(x, str) and x.strip()],
        }
    _VOCAB_CACHE = out
    return out


def build_v5_decompose_work_items_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    dimension: str,
    slot_narratives: dict,
) -> str:
    """
    Convert rich per-slot work narratives into BCCA-matchable work item descriptions.

    This prompt is run PER ROOM × DIMENSION to keep the vocabulary menu small and strict.
    Output: JSON { "by_slot": { "<slot_id>": ["desc", ...] } }.
    """
    dim = str(dimension or "").strip()
    vocab_by_dim = _load_bcca_vocab_by_dimension_v1()
    if dim not in vocab_by_dim:
        raise RuntimeError(f"v5 decompose: unknown dimension (no vocab) | dimension={dim}")
    vocab = vocab_by_dim.get(dim, {"nouns": [], "verbs": []})
    return f"""
You are decomposing renovation work narratives into matchable construction work item descriptions.

listing_id: {listing_id}
strategy_name: {strategy_name}
room_id: {room_id}
room_type: {room_type}
dimension: {dim}

INPUT (per-slot work narratives):
{json.dumps(slot_narratives, ensure_ascii=False)[:12000]}

TASK:
Return a JSON object with:
- by_slot: an object mapping each input slot_id to an array of 0-10 short, construction-native descriptions that could be matched to a cost catalog (BCCA-like).

RULES:
- No quantities, no prices, no formulas.
- Keep descriptions short and concrete (nouns + verbs).
- If a slot narrative is exactly "no change", return an empty list for that slot.
- If the narrative implies enabling works (protection, stripout, waste haulage, substrate prep/make-good, sealing, testing/commissioning),
  include those as work items when you can express them with the provided vocabulary; otherwise omit.
- BCCA VOCABULARY RULE (HARD):
  You MUST use ONLY the following BCCA vocabulary nouns/verbs (plus Spanish function words like articles/prepositions).
  Do NOT introduce extra technical adjectives or bespoke design wording.
  If a detail cannot be expressed with the provided vocabulary, omit it (the original narrative is retained elsewhere as evidence).
- Return ONLY valid JSON.

BCCA VOCABULARY PROVIDED (FOR THIS DIMENSION):
- nouns: {json.dumps(vocab.get("nouns") or [], ensure_ascii=False)}
- verbs: {json.dumps(vocab.get("verbs") or [], ensure_ascii=False)}

Example output:
{{"by_slot": {{"finishes.walls": ["pintar paramentos", "enlucir yeso"]}}}}
""".strip()


def build_v5_decompose_work_items_room_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    slot_narratives_by_dim: Dict[str, dict],
) -> str:
    """
    Convert per-slot one-liners into BCCA-matchable work item descriptions in ONE call per room.

    Output: JSON { "by_dim": { "<dimension>": { "<slot_id>": ["desc", ...] } } }.
    """
    if not isinstance(slot_narratives_by_dim, dict) or not slot_narratives_by_dim:
        raise RuntimeError(f"v5 decompose(room): empty slot_narratives_by_dim | room_id={room_id}")

    vocab_by_dim = _load_bcca_vocab_by_dimension_v1()
    dims = [d for d in slot_narratives_by_dim.keys() if isinstance(d, str) and d.strip()]
    for d in dims:
        if d not in vocab_by_dim:
            raise RuntimeError(f"v5 decompose(room): unknown dimension (no vocab) | dimension={d}")

    vocab_payload = {
        d: {
            "nouns": (vocab_by_dim.get(d) or {}).get("nouns") or [],
            "verbs": (vocab_by_dim.get(d) or {}).get("verbs") or [],
        }
        for d in dims
    }

    return f"""
You are decomposing renovation work one-liners into matchable construction work item descriptions.

listing_id: {listing_id}
strategy_name: {strategy_name}
room_id: {room_id}
room_type: {room_type}

INPUT (slot narratives grouped by dimension):
{json.dumps(slot_narratives_by_dim, ensure_ascii=False)[:16000]}

TASK:
Return a JSON object with:
- by_dim: an object mapping each provided dimension to an object that maps each provided slot_id to an array of 0-10 short, construction-native descriptions.

RULES:
- No quantities, no prices, no formulas.
- Keep descriptions short and concrete (nouns + verbs).
- If a slot narrative is exactly "no change", return an empty list for that slot.
- If the narrative implies enabling works (protection, stripout, waste haulage, substrate prep/make-good, sealing, testing/commissioning),
  include those as work items when you can express them with that dimension's vocabulary; otherwise omit.
- BCCA VOCABULARY RULE (HARD):
  For each dimension, you MUST use ONLY that dimension's provided nouns/verbs (plus Spanish function words like articles/prepositions).
  Do NOT introduce extra technical adjectives or bespoke design wording.
  If a detail cannot be expressed with the provided vocabulary, omit it.
- Return ONLY valid JSON.

BCCA VOCABULARY PROVIDED (BY DIMENSION):
{json.dumps(vocab_payload, ensure_ascii=False)[:16000]}
""".strip()

