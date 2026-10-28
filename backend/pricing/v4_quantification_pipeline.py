"""
V4 Quantification Pipeline (Full Implementation)
================================================

Implements the V4 flow described in `pricing/V4_QUANTIFICATION_ARCHITECTURE.md`.

High-level:
- Generate a room-level V4 worklist (per dimension)
- Match each work item to BCCA (embeddings → code/unit/price)
- Run Quantification Planner (LLM) to produce measurement_requests + deterministic formula_ast
- Forage signals per room (LLM, photos + floorplan appended)
- Deterministically evaluate quantities and write BOQ line items

Design rules:
- Fail loud and fast (no silent defaults).
- Floorplan-first when present. Floorplan images (if any) are appended to EACH room forage prompt.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pricing.bcca_embedding_matcher import BccaEmbeddingMatcher
from functools import lru_cache
from pricing.measurement_catalog_v4 import (
    as_public_catalog_json,
    get_measurement_signal_spec,
    validate_catalog,
)
from pricing.quantity_formula_v4 import (
    FormulaEvaluationContext,
    FormulaValidationError,
    evaluate_formula,
    validate_formula_ast,
)
from pricing.schemas.gemini_schemas_v2 import V2_DIMENSIONS
from pricing.schemas.gemini_schemas_v4 import (
    V4_QUANTIFICATION_PLAN_SCHEMA,
    V4_SMART_M2_FORAGE_SCHEMA,
    V4_WORKLIST_DIMENSION_SCHEMA,
)

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def _load_bcca_whole_dwelling_denylist_v1() -> Dict[str, Dict[str, Any]]:
    """
    Load denylist of BCCA codes that represent whole-dwelling bundles/allowances.

    WHY THIS MATTERS:
    - V5/V4 tail is room-level. Allowing whole-dwelling items in matching duplicates costs across rooms.
    """
    p = Path(__file__).parent / "data" / "bcca_whole_dwelling_denylist_v1.json"
    if not p.exists():
        return {}
    import json

    raw = json.loads(p.read_text(encoding="utf-8"))
    deny = raw.get("denylist") if isinstance(raw, dict) else None
    if not isinstance(deny, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in deny.items():
        kk = str(k).strip()
        if not kk:
            continue
        out[kk] = v if isinstance(v, dict) else {"reason": "unknown"}
    return out
def _is_whole_dwelling_bcca_item(*, bcca_code: str | None, bcca_desc_100: str | None) -> bool:
    """
    Heuristic to exclude "whole-dwelling" priced primitives from a ROOM-LEVEL pipeline.

    WHY THIS MATTERS:
    - V5 work items are produced per-room. If matching selects a "1 vivienda" / whole-home allowance,
      it will be duplicated across rooms and massively overcount.

    Scope:
    - Conservative: we target obvious whole-home wording seen in the BCCA dataset ("1 vivienda",
      "inst. eléctrica vivienda (<=...)", etc).
    - We do NOT try to solve all scoping. This is a stopgap to keep room-level pricing sane.
    """
    d = str(bcca_desc_100 or "").strip().lower()
    if not d:
        return False

    # Primary gate: deterministic denylist from the full BCCA price_book.
    code = str(bcca_code or "").strip()
    if code and code in _load_bcca_whole_dwelling_denylist_v1():
        return True

    # Obvious whole-home / allowance wording patterns.
    deny = (
        " 1 vivienda",  # "ACO. ELECTRICIDAD 1 VIVIENDA ..."
        "inst. eléctrica vivienda",  # "Desmontaje inst. eléctrica vivienda ..."
        "instalación eléctrica vivienda",
        "electricidad 1 vivienda",
        "vivienda hasta c.g.p",  # "HASTA C.G.P."
        "redes int. agua",  # often priced per dwelling in this dataset
    )
    if any(s in d for s in deny):
        return True

    # Generic "vivienda (<=...)" / "vivienda (>...)" style sizing indicates whole-dwelling work.
    # Keep this narrow to avoid nuking unrelated door/window items that mention "vivienda".
    if "vivienda (" in d or "vivienda (<= " in d or "vivienda (> " in d or "vivienda (>= " in d:
        return True

    return False


def _require(cond: bool, msg: str) -> None:
    if cond:
        return
    raise RuntimeError(msg)


def _extract_floorplan_urls(clusters: List[Dict[str, Any]]) -> List[str]:
    urls: List[str] = []
    for c in clusters or []:
        if not isinstance(c, dict):
            continue
        if str(c.get("room_type") or "").strip().lower() != "floorplan":
            continue
        for u in (c.get("photo_urls") or []):
            if isinstance(u, str) and u.strip():
                urls.append(u.strip())
    # dedupe preserve order
    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _room_photo_urls_by_id(clusters: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for c in clusters or []:
        if not isinstance(c, dict):
            continue
        room_type = str(c.get("room_type") or "").strip().lower()
        if room_type in ("floorplan", "exterior", "common_area"):
            continue
        room_id = str(c.get("cluster_id") or "").strip()
        if not room_id:
            continue
        urls = [u for u in (c.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        if urls:
            out[room_id] = urls
    return out


def _unit_family(unit: str) -> str:
    u = str(unit or "").strip().lower()
    u = u.replace(" ", "")
    u = u.replace(".", "")
    # Common BCCA unit normalizations
    if u in ("m", "ml", "mln", "mls"):
        u = "ml"
    if u in ("u", "ud", "uds", "unidad", "unidades"):
        u = "ud"
    if u in ("m2", "m²"):
        u = "m2"
    if u in ("m3", "m³"):
        u = "m3"
    if u in ("m2", "ml", "ud", "m3"):
        return u
    raise RuntimeError(f"v4: unsupported unit family | unit={unit}")


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except Exception:
        return None
    if v <= 0:
        return None
    return v


def _extract_listing_sqm(listing: Optional[Dict[str, Any]]) -> Optional[float]:
    """
    Extract total property area (sqm) from a listing record.

    WHY THIS MATTERS:
    - Smart M2 uses total property m² to distribute room sizes.
    - For V4 foraging/quant planning, knowing total m² enables proportional inference when some signals aren't visible.
    """
    if not isinstance(listing, dict):
        return None

    # Primary column used in this codebase.
    v = _safe_float(listing.get("sqm"))
    if v:
        return v

    # Common scraped_data fields (sometimes merged into listing by get_listing_with_photos).
    for k in ("m2_built", "m2_useful", "sqm_built", "sqm_useful", "area_m2"):
        v2 = _safe_float(listing.get(k))
        if v2:
            return v2

    scraped = listing.get("scraped_data")
    if isinstance(scraped, dict):
        for k in ("sqm", "m2_built", "m2_useful"):
            v3 = _safe_float(scraped.get(k))
            if v3:
                return v3

    return None


def _extract_room_estimated_m2_from_smart_m2(*, smart_m2: Dict[str, Any], room_id: str) -> Optional[float]:
    if not isinstance(smart_m2, dict) or not room_id:
        return None
    rooms = smart_m2.get("rooms") or []
    if not isinstance(rooms, list):
        return None
    for r in rooms:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("room_id") or r.get("cluster_id") or "").strip()
        if rid != str(room_id).strip():
            continue
        return _safe_float(r.get("estimated_m2"))
    return None


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _get_default_bcca_matcher() -> BccaEmbeddingMatcher:
    repo_root = _get_repo_root()
    full_embeddings_path = repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_full_f32.npy"
    full_metadata_path = repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_full_metadata.json"
    embeddings_path = full_embeddings_path if full_embeddings_path.exists() else (repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_f32.npy")
    metadata_path = full_metadata_path if full_metadata_path.exists() else (repo_root / "backend" / "pricing" / "data" / "bcca_embeddings_metadata.json")
    matcher = BccaEmbeddingMatcher(embeddings_path=embeddings_path, metadata_path=metadata_path)
    matcher.load()
    return matcher


def _get_repo_root_data_dir() -> Path:
    repo_root = _get_repo_root()
    return repo_root / "backend" / "pricing" / "data"


@lru_cache(maxsize=16)
def _load_bcca_codes_by_dimension_v1() -> Dict[str, List[str]]:
    data_dir = _get_repo_root_data_dir()
    p = data_dir / "bcca_by_dimension_v1" / "bcca_codes_by_dimension_v1.json"
    if not p.exists():
        raise RuntimeError(f"v4: missing bcca_by_dimension_v1 artifacts | path={p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("v4: invalid bcca_codes_by_dimension_v1.json")
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if not isinstance(v, list):
            continue
        out[k] = [str(x).strip() for x in v if str(x).strip()]
    return out


_DIM_MATCHER_CACHE: Dict[str, BccaEmbeddingMatcher] = {}


def _dimension_scoped_matcher(*, full_matcher: BccaEmbeddingMatcher, dimension: str) -> BccaEmbeddingMatcher:
    dim = str(dimension or "").strip()
    if not dim:
        raise RuntimeError("v4: empty dimension for matcher")
    if dim in _DIM_MATCHER_CACHE:
        return _DIM_MATCHER_CACHE[dim]
    codes_by_dim = _load_bcca_codes_by_dimension_v1()
    allowed = set(codes_by_dim.get(dim) or [])
    if not allowed:
        raise RuntimeError(f"v4: no allowed codes for dimension | dimension={dim}")
    subset = full_matcher.make_subset_matcher(allowed_codes=allowed)
    _DIM_MATCHER_CACHE[dim] = subset
    return subset


def _safe_get(d: Dict[str, Any], path: str) -> Any:
    """
    Minimal dot-path accessor for dicts.
    Path example: "takeoff_primitives.ceiling_finish_m2.value"
    """
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        if part not in cur:
            return None
        cur = cur.get(part)
    return cur


def _prefill_signals_from_smart_m2(
    *,
    smart_m2: Dict[str, Any],
    room_id: str,
    required_signals: List[str],
    allow_missing_room: bool = False,
) -> Dict[str, Dict[str, Any]]:
    rooms = smart_m2.get("rooms") or []
    if not isinstance(rooms, list):
        rooms = []
    room = None
    for r in rooms:
        if isinstance(r, dict) and str(r.get("room_id") or r.get("cluster_id") or "").strip() == room_id:
            room = r
            break
    if not room:
        if allow_missing_room:
            # V5 room ids may not always match Smart M2 room ids; Smart M2 is an optimization/prefill,
            # not a hard requirement for foraging. Missing values will be handled by the forage LLM calls.
            return {}
        raise RuntimeError(f"v4: smart_m2 missing room | room_id={room_id}")

    out: Dict[str, Dict[str, Any]] = {}
    for sid in required_signals:
        # Catalog is optional guidance/prefill. Custom signals may not exist in catalog.
        try:
            spec = get_measurement_signal_spec(sid)
        except Exception:
            continue
        if not spec.smart_m2_path:
            continue
        # Strip leading "rooms[]."
        p = spec.smart_m2_path
        p = p.replace("rooms[].", "")
        val = _safe_get(room, p)
        if val is None:
            continue
        try:
            num = float(val)
        except Exception:
            continue
        out[sid] = {
            "signal_id": sid,
            "unit_family": spec.unit_family,
            "value": num,
            "confidence": "high",
            "defaulted": False,
            "evidence": {"source": "smart_m2", "refs": [spec.smart_m2_path]},
            "notes": "Prefilled from Smart M2 primitives (deterministic).",
        }
    return out


def build_v4_worklist_prompt(
    *,
    strategy_name: str,
    dimension: str,
    strategy_spec_dim: Dict[str, Any],
    target_pir: Dict[str, Any],
    room_ids: List[str],
) -> str:
    """
    Prompt for V4 Worklist.

    Output: V4_WORKLIST_DIMENSION_SCHEMA (room-level scope packages).
    """
    rooms_context = [{"room_id": rid} for rid in room_ids]

    # Keep this small and deterministic. Goal: nudge wording toward the pricebook without dumping the whole BCCA.
    bcca_lexicon_by_dim: Dict[str, Dict[str, List[str]]] = {
        "shell_preparation": {
            "nouns": ["demolición", "retirada", "desmontaje", "carga", "transporte", "vertedero", "protección", "tapiado", "cegado", "apertura de hueco"],
            "verbs": ["demoler", "retirar", "desmontar", "cargar", "transportar", "proteger", "tapiar", "cegar"],
        },
        "apertures_enclosure": {
            "nouns": ["ventana", "balconera", "corredera", "abatible", "carpintería", "aluminio", "madera", "persiana", "cajón", "vidrio", "doble acristalamiento", "RPT", "sellado", "premarco"],
            "verbs": ["sustituir", "instalar", "colocar", "sellar", "anclar"],
        },
        "systems_services": {
            "nouns": ["punto de luz", "mecanismo", "interruptor", "toma de corriente", "enchufe", "cuadro", "circuito", "toma de agua", "desagüe", "radiador", "rejilla", "difusor", "conducto", "termostato"],
            "verbs": ["instalar", "sustituir", "anular", "conectar", "probar"],
        },
        "surface_finishes": {
            "nouns": ["alicatado", "solado", "pavimento", "revestimiento", "rodapié", "pintura", "enlucido", "yeso", "junta", "lechada", "impermeabilización"],
            "verbs": ["alicatar", "solar", "pavimentar", "revestir", "pintar", "enlucir", "impermeabilizar"],
        },
        "fixed_joinery_equipment": {
            "nouns": ["mobiliario de cocina", "mueble de lavabo", "encimera", "zócalo", "armario", "frente de armario", "estantería", "baldas", "mueble columna"],
            "verbs": ["suministrar", "montar", "instalar", "integrar"],
        },
        "details_fittings": {
            "nouns": ["sanitario", "lavabo", "inodoro", "plato de ducha", "mampara", "grifería", "espejo", "accesorio", "barra asidero", "toallero", "herrajes"],
            "verbs": ["instalar", "sustituir", "colocar"],
        },
    }
    lex = bcca_lexicon_by_dim.get(str(dimension), {"nouns": [], "verbs": []})
    return f"""
You are a senior architect with strong renovation PM experience, trained under a quantity surveyor.

GOAL:
Produce a ROOM-LEVEL set of scope packages for the renovation work in this dimension.

WHY THIS MATTERS:
This output is consumed by downstream systems:
1) BCCA matching: needs concise, construction-native Spanish descriptions of WHAT is being worked on.
2) Quantification planning: needs unambiguous "what" so it can decide measurement method later.

CONSTRAINTS (non-negotiable):
- Output ROOM-LEVEL work items only (each work item belongs to exactly one room_id).
- Do NOT output any quantity refs, formulas, or measurements.
- Do NOT include pricing.
- Be SPECIFIC about the physical target (e.g., "puntos de luz", "tomas de corriente", "puertas interiores", "alicatado pared", "solado", "rodapié").
- Use Spanish trade vocabulary close to BCCA wording (construction nouns), not marketing prose.

BCCA VOCABULARY RULE (ABSOLUTE / NON-NEGOTIABLE):
You MUST use ONLY the BCCA vocabulary provided below for this dimension.
Use ONLY the vocabulary provided below.
Use ONLY the vocabulary list below.
Use ONLY the BCCA nouns/verbs provided below.
Only use the BCCA terms below.
Only use the BCCA word list below.
Use the BCCA vocabulary below and nothing else.
Use the vocabulary provided below; do not invent wording.
Use exactly the provided BCCA vocabulary (below).
Use the BCCA vocabulary below; do not add bespoke design wording.
Use the BCCA vocabulary below; do not add extra adjectives/specs.
Use the BCCA vocabulary below; do not use narrative/prose.
Use the BCCA vocabulary below; do not use synonyms unless they are in the list.
Use the BCCA vocabulary below; if you need a word and it is not in the list, rewrite the sentence using only the words that are in the list.

BCCA VOCABULARY PROVIDED (FOR THIS DIMENSION):
- nouns: {json.dumps(lex.get("nouns") or [], ensure_ascii=False)}
- verbs: {json.dumps(lex.get("verbs") or [], ensure_ascii=False)}
- Each room should have at least 1 item if the strategy spec indicates any work is needed there.
- Create stable work_item_id values that are unique within this dimension: "{dimension}:{{room_id}}:{{i}}" (i starting at 1).

DIMENSION:
{dimension}

ROOMS (canonical ids):
{json.dumps(rooms_context, ensure_ascii=False, indent=2)}

STRATEGY SPEC CONTEXT (this dimension, already written as narrative):
{json.dumps(strategy_spec_dim, ensure_ascii=False, indent=2)}

TARGET PIR CONTEXT (for grounding / constraints):
{json.dumps(target_pir, ensure_ascii=False, indent=2)}

Return ONLY valid JSON matching the schema.
""".strip()


def build_v4_quant_planner_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    worklist_dim: Dict[str, Any],
    bcca_matches: List[Dict[str, Any]],
    floorplan_available: bool,
    room_has_photos: Dict[str, bool],
    listing_sqm: Optional[float] = None,
) -> str:
    """
    Prompt for the Quantification Planner.

Output: V4_QUANTIFICATION_PLAN_SCHEMA
    """
    # Catalog is guidance + prefill optimization, NOT a hard constraint.
    # IMPORTANT: Do NOT dump large catalogs into the prompt; it bloats tokens and increases truncation risk.
    validate_catalog()

    def _compact_match(m: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "bcca_code": m.get("bcca_code"),
            "unit": m.get("unit"),
            "unit_price": m.get("unit_price"),
            "bcca_desc_100": m.get("bcca_desc_100"),
            "embedding_similarity": m.get("embedding_similarity"),
        }

    matches_by_item = {
        m.get("work_item_id"): _compact_match(m)
        for m in bcca_matches
        if isinstance(m, dict) and m.get("work_item_id")
    }
    # Attach match info into the prompt for each scope package
    work_blocks = []
    for rb in (worklist_dim.get("room_blocks") or []):
        if not isinstance(rb, dict):
            continue
        room_id = rb.get("room_id")
        pkgs = []
        for pkg in rb.get("scope_packages") or []:
            if not isinstance(pkg, dict):
                continue
            wid = pkg.get("work_item_id")
            pkgs.append(
                {
                    **pkg,
                    "bcca_match": matches_by_item.get(wid),
                }
            )
        work_blocks.append(
            {
                "room_id": room_id,
                "has_photos": bool(room_has_photos.get(str(room_id))),
                "scope_packages": pkgs,
            }
        )

    return f"""
You are a senior quantity surveyor.

GOAL:
For each work item, decide the ONE measurable number we need from that room in order to cost the item using its provided pricing primitive.

WHY THIS MATTERS:
We price deterministically as (quantity × unit_price). If you choose the wrong measurement basis (m2 vs ml vs ud vs m3), the cost is wrong.

CONTEXT:
- listing_id={listing_id}
- strategy={strategy_name}
- dimension={dimension}
- floorplan_available={str(bool(floorplan_available)).lower()}
- listing_total_sqm={listing_sqm if listing_sqm is not None else "unknown"}

WHAT YOU ARE GIVEN (per work item):
- room_id
- work_description (what needs doing)
- bcca_match (the pricing primitive): bcca_code + unit + unit_price (+ labor_hours_per_unit when available)

YOUR TASK (for each work item):
- Output a single variable-like signal_id in snake_case that describes exactly what to measure in that room.
  For instance, a signal might describe an area, a length, or a count — but do NOT include any numbers.
- MEASURABILITY FIRST (CRITICAL):
  You are choosing WHAT we will measure later from evidence (room photos; and floorplan images only if floorplan_available=true).
  Your job is not to invent a nice variable name — your job is to choose a signal that a surveyor could actually extract.

  Rules:
  - PHYSICAL MEASUREMENT (CRITICAL):
    Choose a signal that describes a *physical quantity in the room*, not an action or a construction method.
    - GOOD: "area_suelo_m2", "area_techo_m2", "area_paredes_m2", "perimetro_suelo_ml", "cantidad_puertas_ud"
    - BAD (do NOT request): action/outcome signals like "area_demolicion_*", "area_picado_*", "area_canalizacion_*",
      or any signal that implies hidden demolition / chases / runs inside walls.
    WHY: “Action” signals are rarely visible, and they force the foraging step into 0s or arbitrary guesses.
  - Prefer signals that are directly observable from photos:
    - Counts (ud): sockets, switches, light points, visible fixtures, visible openings/doors/windows.
    - Areas (m2): visible tiling, visible floor finish, visible ceiling finish, visible paintable surfaces (when boundaries are clear).
    - Lengths (ml): when traceable (visible skirting/rodapié). If not traceable, choose a perimeter proxy rather than a hidden run.
  - NO-HIDDEN-RUN SIGNALS (avoid unless truly visible):
    Avoid names like "longitud_cable_*_ml" / "longitud_tuberia_*_ml" unless the run is clearly visible/traceable in evidence.
    If the primitive is ml but the real-world run is hidden, choose a robust proxy such as "perimetro_suelo_ml" / "perimetro_rodapie_ml".
    WHY: The BOQ needs plausible quantities even when photos don't show inside-wall routes.
  - REUSE CANONICAL SIGNALS (IMPORTANT):
    If multiple work items in a room can share the same measurement, reuse the SAME signal_id.
    Prefer canonical room geometry signals wherever they make sense:
    - m2: "area_suelo_m2", "area_techo_m2", "area_paredes_m2"
    - ml: "perimetro_suelo_ml" or "perimetro_rodapie_ml"
    - ud: "cantidad_*_ud" (only for countable, visible objects)
    WHY: Reuse increases consistency and gives foraging better anchors for inference.
  - It is OK that foraging returns 0 ONLY when absence is visually verifiable from photos.
    If absence is NOT verifiable, choose a more evidence-grounded *proxy* signal instead of steering the pipeline into “0 by default”.
  - IMPORTANT: We often know the total property size (listing_total_sqm). You can use this to select signals that can be
    *inferred proportionally* from photos when direct measurement is impossible (e.g., room floor area share, perimeter proxies).
    WHY: This lets downstream foraging make a conservative estimate instead of defaulting to 0.
- SIGNAL PREFIX RULE (STRICT):
  Use these prefixes based on the unit family:
  - unit m2 → signal_id must start with "area_" and end with "_m2"
  - unit ml → signal_id must start with "longitud_" OR "perimetro_" and end with "_ml"
  - unit ud → signal_id must start with "cantidad_" and end with "_ud"
  - unit m3 → signal_id must start with "volumen_" and end with "_m3"
- The signal_id MUST end with a unit suffix matching the primitive unit:
  - unit m2 → *_m2
  - unit ml → *_ml
  - unit ud → *_ud
  - unit m3 → *_m3
- Treat the provided bcca_match as FIXED. Do not invent alternative BCCA items or reinterpret the unit.

OUTPUT FORMAT (schema requirement):
- For each work item, return:
  - work_item_id
  - formula_ast = SIGNAL(signal_id)
  WHY: downstream we automatically turn SIGNALs into a simple checklist for the foraging step.

WORK ITEMS (room-level) with attached bcca_match:
{json.dumps(work_blocks, ensure_ascii=False, indent=2)}

Return ONLY valid JSON matching the schema.
""".strip()


def build_v4_forage_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    measurement_requests: List[Dict[str, Any]],
    floorplan_available: bool,
    listing_sqm: Optional[float] = None,
    room_estimated_m2: Optional[float] = None,
    known_signals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    _require(isinstance(measurement_requests, list) and measurement_requests, "v4_forage_prompt: empty measurement_requests")

    return f"""
You are a senior quantity surveyor extracting measurable signals from evidence.

WHY THIS MATTERS:
These signals will be used in deterministic formulas to compute BOQ quantities.
If you guess wildly, you will create wrong costs. If you miss a required signal, the pipeline fails.
If you return 0 when absence is NOT visually verifiable, you will create misleading “zero-quantity BOQ” items.

EVIDENCE:
- You will receive room photos (always).
- If a floorplan exists, you will also receive floorplan image(s), appended for this room.

FLOORPLAN POLICY:
- floorplan_available={str(bool(floorplan_available)).lower()}
- If floorplan is available, use it for count/layout signals (sockets, switches, light points, openings) where applicable.

TASK:
For room_id={room_id}, output ALL required signals below, with:
- value (number)
- unit_family (m2/ml/ud/m3)
- confidence (low/medium/high/unknown)
- defaulted:
  - defaulted=false ONLY when directly measured/observed from evidence
  - defaulted=true ONLY when you are making an educated estimate from other known signals/context (see INFERENCE POLICY)
- evidence: source + refs
  - measured: source in ("photo","floorplan") and refs like "photo:idx" / "floorplan:idx"
  - inferred (STRICT): source="imputed" and refs must cite ONLY proxy *signal_id* values you used
    (and/or the literal token "listing_total_sqm"). NEVER put "photo:*" or "floorplan:*" inside refs for imputed signals.

CONTEXT YOU CAN USE:
- listing_total_sqm={listing_sqm if listing_sqm is not None else "unknown"}
- room_estimated_m2_hint={room_estimated_m2 if room_estimated_m2 is not None else "unknown"}
- known_signals_in_room (already available; use these as proxies instead of guessing blindly):
{json.dumps(known_signals or [], ensure_ascii=False, indent=2)}

INFERENCE POLICY (PIR-STYLE, BUT AUDITABLE):
- If a requested signal is not visible/traceable in the provided photos, you SHOULD still produce a reasonable estimate
  instead of defaulting to 0, as long as the estimate can be anchored to:
  - listing_total_sqm and/or room_estimated_m2_hint (if available), AND/OR
  - other known_signals_in_room that you are also returning.
  WHY: The BOQ needs plausible quantities even when a photo doesn't capture every corner.
- When you infer (educated estimate):
  - set defaulted=true
  - set confidence="low" (or "medium" only if the proxy is extremely strong and direct)
  - set evidence.source="imputed"
  - set evidence.refs to the proxy signal_id(s) you relied on (and/or "listing_total_sqm").
  - NEVER cite photos/floorplans in refs for imputed signals (refs are for proxies only).
  - IMPORTANT HARD RULE: if evidence.source="imputed", value MUST be > 0 (never output an imputed zero).
- VALUE=0 POLICY (STRICT):
  - Output value=0 ONLY when you can visually verify ABSENCE from the evidence (e.g., “there are clearly 0 radiators”).
  - If absence is NOT visually verifiable, do NOT output 0 by default — produce a conservative estimate using proxies and mark it imputed.
- If you truly cannot anchor an estimate to any proxy/context, THEN (and only then) return value=0 with:
  - confidence="unknown"
  - defaulted=false
  - evidence.source="unknown"

WORKING STYLE (helps reduce zeros):
- You are returning ALL requested signals together. You MAY use other signals you are also returning as proxies.
  If you do, cite their signal_id(s) in evidence.refs (imputed only).

MEASUREMENT REQUESTS (custom; you must return each signal_id):
{json.dumps(measurement_requests, ensure_ascii=False, indent=2)}

Return ONLY valid JSON matching the schema.
""".strip()


async def generate_v4_worklist_for_dimension(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    strategy_spec: Dict[str, Any],
    target_pir: Dict[str, Any],
    room_ids: List[str],
    call_gemini: Any,
) -> Dict[str, Any]:
    spec_dim = (strategy_spec.get("dimensions") or {}).get(dimension) or {}
    prompt = build_v4_worklist_prompt(
        strategy_name=strategy_name,
        dimension=dimension,
        strategy_spec_dim=spec_dim,
        target_pir=target_pir,
        room_ids=[str(r) for r in room_ids if str(r).strip()],
    )
    resp = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.2,
        max_tokens=65536,
        response_schema=V4_WORKLIST_DIMENSION_SCHEMA,
        use_spanish=True,
    )
    if not resp.success:
        raise RuntimeError(f"v4_worklist: gemini failed | listing_id={listing_id} strategy={strategy_name} dim={dimension} err={resp.error}")
    out = json.loads(resp.text)
    out["dimension"] = dimension
    return out


async def _rerank_bcca_candidates_flash_lite(
    *,
    work_description: str,
    room_id: str,
    dimension: str,
    target_element: str | None,
    candidates: List[Tuple[float, Dict[str, Any]]],
) -> int:
    """
    Use Gemini Flash Lite to re-rank BCCA embedding candidates for a work item.

    WHY THIS MATTERS:
    Embeddings measure word similarity, not construction-domain correctness.
    "Pintura de muro" (wall paint) embeds close to "chapa Al lacado" (aluminum cladding)
    because both involve walls + "lacado". A cheap LLM call can reason about physical
    appropriateness and pick the right code from the top-10 embedding candidates.

    Returns: index (0-based) into `candidates` list of the best match.
    """
    from pipeline.gemini_client import call_gemini

    # Build compact candidate list for the prompt
    cand_lines = []
    for i, (sim, m) in enumerate(candidates):
        desc = str(m.get("desc_100") or m.get("description") or "")[:120]
        unit = m.get("unit") or "?"
        price = m.get("price") or "?"
        cand_lines.append(f"{i}: [{m.get('code')}] {desc} | {unit} | EUR{price} | sim={sim:.3f}")

    prompt = f"""Eres un aparejador (quantity surveyor) que verifica la correspondencia entre un trabajo
de reforma residencial y un código del cuadro de precios BCCA.

TRABAJO:
  Estancia: {room_id}
  Dimensión: {dimension}
  Elemento: {target_element or '(ninguno)'}
  Descripción: {work_description}

CANDIDATOS (del mejor embedding al peor):
{chr(10).join(cand_lines)}

REGLAS para elegir:
- Es una reforma RESIDENCIAL INTERIOR (no industrial, no comercial, no exterior salvo fachada/balcón).
- El código debe describir el MISMO tipo de trabajo (pintura→pintura, no pintura→revestimiento aluminio).
- Preferir códigos con unidad coherente (m2 para superficies, ud para piezas, ml para lineales).
- Si hay duda entre interior y exterior, elegir interior.
- Si hay duda entre residencial y comercial/público, elegir residencial.
- No elegir ensayos, inspecciones, mantenimiento ni partidas provisionales de obra.

Responde SOLO con el número del candidato elegido (0-{len(candidates)-1}). Nada más."""

    resp = await call_gemini(
        prompt=prompt,
        model="flash-lite",
        temperature=0.0,
        max_tokens=16,
        use_spanish=True,
    )

    if not resp.success or not resp.text:
        logger.warning(f"rerank_bcca: flash-lite failed, using embedding rank | err={resp.error}")
        return 0  # Fall back to embedding top pick

    # Parse the integer from the response
    raw = resp.text.strip()
    # Extract first integer from the response
    import re as _re
    nums = _re.findall(r"\d+", raw)
    if nums:
        idx = int(nums[0])
        if 0 <= idx < len(candidates):
            return idx
    logger.warning(f"rerank_bcca: could not parse index from response | raw={raw!r}")
    return 0


async def match_v4_bcca(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    worklist_dim: Dict[str, Any],
    matcher: BccaEmbeddingMatcher,
    embed_texts_fn: Any,
    query_mode: str = "rich",
    use_llm_rerank: bool = True,
) -> List[Dict[str, Any]]:
    def _build_bcca_query_packet(
        *,
        strategy_name: str,
        dimension: str,
        room_id: str,
        work_description: str,
        target_element: str | None,
        source_scope_refs: List[str] | None,
    ) -> str:
        lines: List[str] = []
        lines.append("Contexto: reforma vivienda (residencial).")
        lines.append(f"Estrategia: {strategy_name}.")
        lines.append(f"Dimensión: {dimension}.")
        lines.append(f"Estancia: {room_id}.")
        if target_element and str(target_element).strip():
            lines.append(f"Elemento objetivo: {str(target_element).strip()}.")
        lines.append(f"Trabajo: {work_description}.")
        refs = [str(r).strip() for r in (source_scope_refs or []) if isinstance(r, str) and str(r).strip()]
        if refs:
            lines.append("Referencias de alcance: " + "; ".join(refs[:6]) + ("; …" if len(refs) > 6 else "") + ".")
        # Tiny negative hint for generic text: helps avoid absurd non-reno equipment.
        lines.append("Excluir: informática/oficina, mobiliario urbano, equipamiento público.")
        return "\n".join(lines).strip()

    # Flatten room scope packages
    items: List[Tuple[str, str, str, str | None, List[str] | None]] = []  # (work_item_id, room_id, work_description, target_element, refs)
    for rb in worklist_dim.get("room_blocks") or []:
        if not isinstance(rb, dict):
            continue
        room_id = str(rb.get("room_id") or "").strip()
        for pkg in rb.get("scope_packages") or []:
            if not isinstance(pkg, dict):
                continue
            wid = str(pkg.get("work_item_id") or "").strip()
            work_desc = str(pkg.get("work_description") or "").strip()
            target_element = str(pkg.get("target_element") or "").strip() or None
            refs = pkg.get("source_scope_refs")
            refs_list: List[str] | None = refs if isinstance(refs, list) else None
            if not wid or not room_id or not work_desc:
                continue
            items.append((wid, room_id, work_desc, target_element, refs_list))
    _require(items, f"v4_bcca_match: no items | listing_id={listing_id} strategy={strategy_name} dim={dimension}")

    qmode = str(query_mode or "").strip().lower()
    _require(qmode in ("plain", "rich"), f"v4_bcca_match: invalid query_mode | query_mode={query_mode}")

    query_texts: List[str] = []
    for _, room_id, work_desc, target_element, refs in items:
        if qmode == "plain":
            query_texts.append(work_desc)
        else:
            query_texts.append(
                _build_bcca_query_packet(
                    strategy_name=strategy_name,
                    dimension=dimension,
                    room_id=room_id,
                    work_description=work_desc,
                    target_element=target_element,
                    source_scope_refs=refs,
                )
            )

    embeddings = embed_texts_fn(query_texts)
    _require(len(embeddings) == len(query_texts), "v4_bcca_match: embeddings length mismatch")

    # Build a COMPLETE dimension-scoped matcher (no runtime widening/fallback).
    scoped_matcher = _dimension_scoped_matcher(full_matcher=matcher, dimension=dimension)

    import asyncio as _aio

    # --- Phase 1: Embedding retrieval (top-10) + deterministic filtering ---
    pre_rerank: List[Dict[str, Any]] = []  # One entry per work item
    for (wid, room_id, work_desc, target_element, refs), emb, qtext in zip(items, embeddings, query_texts):
        matches = scoped_matcher.match(
            emb,
            unit=None,
            top_k=10,
            min_similarity=0.40,
        )
        slot_id = str(target_element or "").strip()

        def _desc_low(m: Dict[str, Any]) -> str:
            return str(m.get("desc_100") or m.get("description") or "").strip().lower()

        def _is_entry_door_item(m: Dict[str, Any]) -> bool:
            return "puerta entrada vivienda" in _desc_low(m)

        # Deterministic filters: whole-dwelling, entry-door
        filtered = []
        for s, m in matches:
            if _is_whole_dwelling_bcca_item(bcca_code=m.get("code"), bcca_desc_100=m.get("desc_100") or m.get("description")):
                continue
            if slot_id and slot_id != "enclosure.entrance_door" and _is_entry_door_item(m):
                continue
            filtered.append((s, m))
        candidates = filtered if filtered else matches

        pre_rerank.append({
            "wid": wid,
            "room_id": room_id,
            "work_desc": work_desc,
            "target_element": target_element,
            "refs": refs,
            "slot_id": slot_id,
            "qtext": qtext,
            "candidates": candidates,  # List[(sim, meta)]
            "all_matches": matches,    # Original top-10 for provenance
        })

    # --- Phase 2: LLM re-ranking (Flash Lite) ---
    if use_llm_rerank and pre_rerank:
        rerank_sem = _aio.Semaphore(20)  # Cap concurrency

        async def _rerank_one(entry: Dict[str, Any]) -> int:
            async with rerank_sem:
                return await _rerank_bcca_candidates_flash_lite(
                    work_description=entry["work_desc"],
                    room_id=entry["room_id"],
                    dimension=dimension,
                    target_element=entry["target_element"],
                    candidates=entry["candidates"],
                )

        rerank_indices = await _aio.gather(*[_rerank_one(e) for e in pre_rerank])
    else:
        rerank_indices = [0] * len(pre_rerank)

    # --- Phase 3: Build output with picked match ---
    out: List[Dict[str, Any]] = []
    for entry, rerank_idx in zip(pre_rerank, rerank_indices):
        candidates = entry["candidates"]
        all_matches = entry["all_matches"]

        # Embedding pick (index 0 = highest sim after filtering)
        emb_score, emb_best = candidates[0]
        # LLM pick
        llm_score, llm_best = candidates[rerank_idx]

        # Final pick = LLM choice if reranking enabled, else embedding top
        best_score, best = llm_score, llm_best
        unit = _unit_family(best.get("unit"))

        out.append(
            {
                "work_item_id": entry["wid"],
                "room_id": entry["room_id"],
                "dimension": dimension,
                "query_mode": qmode,
                "query_text": entry["qtext"],
                "work_description": entry["work_desc"],
                "target_element": entry["target_element"],
                "source_scope_refs": entry["refs"],
                "bcca_code": best.get("code"),
                "unit": unit,
                "unit_price": float(best.get("price") or 0),
                "labor_hours_per_unit": best.get("labor_hours_per_unit"),
                "bcca_desc_100": best.get("desc_100") or best.get("description"),
                "bcca_full_desc": best.get("full_desc"),
                "embedding_similarity": float(best_score),
                "llm_reranked": use_llm_rerank,
                "llm_rerank_index": rerank_idx,
                "embedding_top_code": emb_best.get("code"),
                "embedding_top_price": float(emb_best.get("price") or 0),
                "whole_dwelling_filtered": bool(candidates != all_matches),
                "slot_gate": {"slot_id": entry["slot_id"], "entry_door_excluded": bool(entry["slot_id"] and entry["slot_id"] != "enclosure.entrance_door")},
                "top_k": [
                    {
                        "score": float(s),
                        "code": m.get("code"),
                        "unit": m.get("unit"),
                        "price": m.get("price"),
                        "desc_100": m.get("desc_100") or m.get("description"),
                    }
                    for s, m in all_matches
                ],
            }
        )
    return out


def _plans_validate_or_raise(
    *,
    plan: Dict[str, Any],
    bcca_matches_by_item: Dict[str, Dict[str, Any]],
    bcca_meta_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    import re

    plans = plan.get("plans") or []
    if not isinstance(plans, list) or not plans:
        raise RuntimeError("v4_quant_plan: empty plans")

    # Fail loud if planner didn't return a plan for every work item we asked it to plan.
    expected_ids = {str(k) for k in bcca_matches_by_item.keys() if str(k).strip()}
    actual_ids = {
        str(p.get("work_item_id"))
        for p in plans
        if isinstance(p, dict) and str(p.get("work_item_id") or "").strip()
    }
    missing = sorted(expected_ids - actual_ids)
    if missing:
        raise RuntimeError(
            f"v4_quant_plan: missing plans for work items | missing_count={len(missing)} sample={missing[:12]}"
        )

    def _normalize_formula_ast(
        *,
        formula_ast: Dict[str, Any],
        work_item_id: str,
        signal_units: Dict[str, str],
    ) -> Dict[str, Any]:
        _require(isinstance(formula_ast, dict), f"v4_quant_plan: formula_ast must be object | work_item_id={work_item_id}")
        op = str(formula_ast.get("op") or "").strip()
        _require(op, f"v4_quant_plan: formula_ast missing op | work_item_id={work_item_id}")

        def _infer_family(node: Dict[str, Any]) -> str:
            node_op = str(node.get("op") or "").strip()
            if node_op == "CONST":
                return "unitless"
            if node_op == "CONST_UNIT":
                return str(node.get("unit_family") or "").strip() or "unitless"
            if node_op == "SIGNAL":
                sid = str(node.get("signal_id") or "").strip()
                return signal_units.get(sid) or "unitless"
            if node_op in ("CEIL", "FLOOR"):
                arg_node = node.get("arg")
                if isinstance(arg_node, dict):
                    return _infer_family(arg_node)
                return "unitless"
            if node_op in ("ADD", "SUB", "MIN", "MAX"):
                args_nodes = node.get("args")
                if not isinstance(args_nodes, list) or not args_nodes:
                    return "unitless"
                families = [_infer_family(a) for a in args_nodes if isinstance(a, dict)]
                unit_families = [f for f in families if f not in ("unitless", "mixed")]
                if not unit_families:
                    return "unitless"
                if len(set(unit_families)) == 1:
                    return unit_families[0]
                return "mixed"
            if node_op in ("MUL", "DIV"):
                return "mixed"
            return "mixed"

        if op in ("ADD", "SUB", "MUL", "DIV", "MIN", "MAX"):
            args = formula_ast.get("args")
            arg = formula_ast.get("arg")
            _require(
                args is None or isinstance(args, list),
                f"v4_quant_plan: formula_ast args must be list | work_item_id={work_item_id}",
            )
            _require(
                arg is None or isinstance(arg, dict),
                f"v4_quant_plan: formula_ast arg must be object | work_item_id={work_item_id}",
            )
            merged: List[Dict[str, Any]] = []
            if isinstance(arg, dict):
                merged.append(arg)
            if isinstance(args, list):
                for a in args:
                    _require(isinstance(a, dict), f"v4_quant_plan: formula_ast args must be objects | work_item_id={work_item_id}")
                    merged.append(a)
            _require(merged, f"v4_quant_plan: formula_ast missing args | work_item_id={work_item_id}")
            normalized_args = [
                _normalize_formula_ast(formula_ast=a, work_item_id=work_item_id, signal_units=signal_units)
                for a in merged
            ]
            if op in ("ADD", "SUB", "MIN", "MAX"):
                families = [_infer_family(a) for a in normalized_args]
                unit_families = [f for f in families if f not in ("unitless", "mixed")]
                if unit_families and len(set(unit_families)) == 1:
                    target_family = unit_families[0]
                    for a in normalized_args:
                        if str(a.get("op") or "").strip() == "CONST":
                            a["op"] = "CONST_UNIT"
                            a["unit_family"] = target_family
            formula_ast["args"] = normalized_args
            if "arg" in formula_ast:
                formula_ast.pop("arg", None)
            return formula_ast
        if op in ("CEIL", "FLOOR"):
            arg = formula_ast.get("arg")
            args = formula_ast.get("args")
            if arg is None and isinstance(args, list) and args:
                arg = args[0]
            _require(isinstance(arg, dict), f"v4_quant_plan: formula_ast arg must be object | work_item_id={work_item_id}")
            formula_ast["arg"] = _normalize_formula_ast(
                formula_ast=arg,
                work_item_id=work_item_id,
                signal_units=signal_units,
            )
            if "args" in formula_ast:
                formula_ast.pop("args", None)
            return formula_ast
        if op in ("CONST", "CONST_UNIT", "SIGNAL"):
            return formula_ast
        raise RuntimeError(f"v4_quant_plan: unsupported op={op} | work_item_id={work_item_id}")

    def _infer_formula_unit_family(
        *,
        formula_ast: Dict[str, Any],
        signal_units: Dict[str, str],
    ) -> Optional[str]:
        for family in ("m2", "ml", "ud", "m3"):
            try:
                validate_formula_ast(
                    formula_ast=formula_ast,
                    unit_family=family,
                    signal_units=signal_units,
                )
                return family
            except FormulaValidationError:
                continue
        return None

    for p in plans:
        if not isinstance(p, dict):
            continue
        wid = p.get("work_item_id")
        _require(wid in bcca_matches_by_item, f"v4_quant_plan: missing bcca match | work_item_id={wid}")
        match = bcca_matches_by_item[wid]
        unit = _unit_family(match.get("unit"))

        formula = p.get("formula_ast")
        _require(isinstance(formula, dict), f"v4_quant_plan: missing formula_ast | work_item_id={wid}")
        # We intentionally keep V4 plans dead-simple: one measurable number per work item.
        # The planner must output formula_ast = SIGNAL(signal_id).
        _require(
            str(formula.get("op") or "").strip() == "SIGNAL",
            "v4_quant_plan: formula_ast must be a single SIGNAL() for this pipeline "
            f"| work_item_id={wid} op={formula.get('op')}",
        )

        def _collect_signal_ids(node: Dict[str, Any]) -> List[str]:
            out: List[str] = []
            op = node.get("op")
            if op == "SIGNAL":
                sid = str(node.get("signal_id") or "").strip()
                if sid:
                    out.append(sid)
                return out
            arg = node.get("arg")
            if isinstance(arg, dict):
                out.extend(_collect_signal_ids(arg))
            args = node.get("args")
            if isinstance(args, list):
                for a in args:
                    if isinstance(a, dict):
                        out.extend(_collect_signal_ids(a))
            return out

        signal_ids = sorted(set(_collect_signal_ids(formula)))
        _require(signal_ids, f"v4_quant_plan: formula has no SIGNAL() | work_item_id={wid}")
        _require(
            len(signal_ids) == 1,
            f"v4_quant_plan: expected exactly one SIGNAL() | work_item_id={wid} signal_ids={signal_ids}",
        )
        # Ensure signal_id is variable-like and self-describing.
        _require(
            re.fullmatch(r"[a-z][a-z0-9_]*", signal_ids[0]) is not None,
            f"v4_quant_plan: signal_id must be snake_case [a-z0-9_] | work_item_id={wid} signal_id={signal_ids[0]}",
        )
        # Strict prefix naming by unit family to keep signals consistent and QA-able.
        sid0 = str(signal_ids[0])
        prefix_ok = False
        if unit == "m2":
            prefix_ok = sid0.startswith("area_")
        elif unit == "ml":
            prefix_ok = sid0.startswith("longitud_") or sid0.startswith("perimetro_")
        elif unit == "ud":
            prefix_ok = sid0.startswith("cantidad_")
        elif unit == "m3":
            prefix_ok = sid0.startswith("volumen_")
        _require(
            prefix_ok,
            "v4_quant_plan: signal_id must follow strict prefix rule for unit family "
            f"| work_item_id={wid} bcca_unit={unit} signal_id={sid0}",
        )

        def _infer_unit_family_from_signal_id(signal_id: str) -> str:
            sid = signal_id.strip().lower()
            for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
                if sid.endswith(suf):
                    return uf
            raise RuntimeError(f"v4_quant_plan: signal_id missing unit suffix | work_item_id={wid} signal_id={signal_id}")

        signal_units: Dict[str, str] = {sid: _infer_unit_family_from_signal_id(sid) for sid in signal_ids}
        formula = _normalize_formula_ast(formula_ast=formula, work_item_id=str(wid), signal_units=signal_units)
        p["formula_ast"] = formula
        inferred_family = _infer_formula_unit_family(formula_ast=formula, signal_units=signal_units)
        _require(
            inferred_family is not None,
            f"v4_quant_plan: unable to infer formula unit family | work_item_id={wid} formula_ast={formula}",
        )
        _require(
            inferred_family == unit,
            "v4_quant_plan: formula unit family mismatch with BCCA match "
            f"| work_item_id={wid} bcca_code={match.get('bcca_code')} bcca_unit={unit} inferred_family={inferred_family}",
        )
        try:
            validate_formula_ast(
                formula_ast=formula,
                unit_family=unit,
                signal_units=signal_units,
            )  # type: ignore[arg-type]
        except FormulaValidationError as exc:
            raise FormulaValidationError(
                "v4_quant_plan: formula unit validation failed "
                f"| work_item_id={wid} bcca_unit={unit} signal_units={signal_units} formula_ast={formula}"
            ) from exc


async def generate_v4_quant_plan(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    worklist_dim: Dict[str, Any],
    bcca_matches: List[Dict[str, Any]],
    floorplan_available: bool,
    room_has_photos: Dict[str, bool],
    call_gemini: Any,
    bcca_meta_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
    plan_granularity: str = "dimension",
    room_concurrency: int = 5,
    listing_sqm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate a quantification plan for a dimension.

    IMPORTANT: We chunk to avoid JSON truncation (finish_reason=MAX_TOKENS) on large dimensions.
    This is not a functional compromise; it's a reliability strategy that still produces plans for every item.
    """
    import asyncio

    gran = str(plan_granularity or "").strip().lower()
    _require(gran in ("dimension", "room"), f"v4_quant_plan: invalid plan_granularity={plan_granularity}")
    if room_concurrency < 1:
        raise ValueError(f"v4_quant_plan: room_concurrency must be >= 1 (got {room_concurrency})")

    async def _run_once(
        *,
        worklist_dim_in: Dict[str, Any],
        bcca_matches_in: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = build_v4_quant_planner_prompt(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=dimension,
            worklist_dim=worklist_dim_in,
            bcca_matches=bcca_matches_in,
            floorplan_available=floorplan_available,
            room_has_photos=room_has_photos,
            listing_sqm=listing_sqm,
        )

        matches_by_item_local = {
            m.get("work_item_id"): m
            for m in bcca_matches_in
            if isinstance(m, dict) and m.get("work_item_id")
        }

        def _collect_plan_issues(*, plan: Dict[str, Any]) -> Dict[str, Any]:
            """
            Collect ALL plan issues in one pass so we can do a single targeted repair call.
            This does NOT mutate bcca matches; it only evaluates plan completeness + signal naming rules.
            """
            import re

            issues: List[Dict[str, Any]] = []
            plans = plan.get("plans") or []
            expected_ids = {str(k) for k in matches_by_item_local.keys() if str(k).strip()}
            actual_ids = {
                str(p.get("work_item_id"))
                for p in plans
                if isinstance(p, dict) and str(p.get("work_item_id") or "").strip()
            }
            missing_ids = sorted(expected_ids - actual_ids)
            for wid in missing_ids:
                issues.append({"work_item_id": wid, "issue": "missing_plan"})

            for p in plans if isinstance(plans, list) else []:
                if not isinstance(p, dict):
                    continue
                wid = str(p.get("work_item_id") or "").strip()
                if not wid or wid not in matches_by_item_local:
                    continue
                match = matches_by_item_local[wid]
                unit = _unit_family(match.get("unit"))

                f = p.get("formula_ast")
                if not isinstance(f, dict):
                    issues.append({"work_item_id": wid, "issue": "missing_formula_ast"})
                    continue
                op = str(f.get("op") or "").strip()
                if op != "SIGNAL":
                    issues.append({"work_item_id": wid, "issue": "op_not_SIGNAL", "op": op})
                    continue
                sid = str(f.get("signal_id") or "").strip()
                if not sid:
                    issues.append({"work_item_id": wid, "issue": "missing_signal_id"})
                    continue
                if re.fullmatch(r"[a-z][a-z0-9_]*", sid) is None:
                    issues.append({"work_item_id": wid, "issue": "bad_signal_id", "signal_id": sid})
                    continue

                # NOTE:
                # We intentionally do NOT hard-ban "hidden infrastructure" signals when floorplan is missing.
                # WHY: The foraging step can still produce a reasonable, conservative estimate from photos + context.
                # suffix
                suf = None
                for s, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
                    if sid.lower().endswith(s):
                        suf = uf
                        break
                if suf is None:
                    issues.append({"work_item_id": wid, "issue": "missing_unit_suffix", "signal_id": sid})
                    continue
                if suf != unit:
                    issues.append({"work_item_id": wid, "issue": "unit_mismatch", "bcca_unit": unit, "signal_unit": suf, "signal_id": sid})
                    continue
                # strict prefix
                prefix_ok = False
                if unit == "m2":
                    prefix_ok = sid.startswith("area_")
                elif unit == "ml":
                    prefix_ok = sid.startswith("longitud_") or sid.startswith("perimetro_")
                elif unit == "ud":
                    prefix_ok = sid.startswith("cantidad_")
                elif unit == "m3":
                    prefix_ok = sid.startswith("volumen_")
                if not prefix_ok:
                    issues.append({"work_item_id": wid, "issue": "bad_prefix_for_unit", "bcca_unit": unit, "signal_id": sid})

            return {"issues": issues}

        def _filter_worklist_dim(*, worklist: Dict[str, Any], keep_ids: set[str]) -> Dict[str, Any]:
            out = {**worklist}
            blocks = []
            for rb in worklist.get("room_blocks") or []:
                if not isinstance(rb, dict):
                    continue
                pkgs = []
                for pkg in rb.get("scope_packages") or []:
                    if not isinstance(pkg, dict):
                        continue
                    wid = str(pkg.get("work_item_id") or "").strip()
                    if wid in keep_ids:
                        pkgs.append(pkg)
                if pkgs:
                    blocks.append({**rb, "scope_packages": pkgs})
            out["room_blocks"] = blocks
            return out

        resp = await call_gemini(
            prompt=prompt,
            model="pro",
            temperature=0.0,
            max_tokens=65536,
            response_schema=V4_QUANTIFICATION_PLAN_SCHEMA,
            use_spanish=True,
        )
        if not resp.success:
            raise RuntimeError(f"v4_quant_plan: gemini failed | listing_id={listing_id} strategy={strategy_name} dim={dimension} err={resp.error}")
        out = json.loads(resp.text)
        out["strategy_name"] = strategy_name
        out["dimension"] = dimension

        issues_payload = _collect_plan_issues(plan=out)
        issues = issues_payload.get("issues") or []
        if issues:
            # Single repair call: regenerate plans ONLY for failing work_item_ids.
            repair_ids = sorted({str(i.get("work_item_id") or "").strip() for i in issues if str(i.get("work_item_id") or "").strip()})
            logger.warning(
                "v4_quant_plan: plan failed validation; attempting single targeted repair "
                f"| listing_id={listing_id} strategy={strategy_name} dim={dimension} repair_count={len(repair_ids)}"
            )
            filtered_worklist = _filter_worklist_dim(worklist=worklist_dim_in, keep_ids=set(repair_ids))
            filtered_matches = [m for m in bcca_matches_in if isinstance(m, dict) and str(m.get("work_item_id") or "").strip() in set(repair_ids)]
            repair_prompt = build_v4_quant_planner_prompt(
                listing_id=listing_id,
                strategy_name=strategy_name,
                dimension=dimension,
                worklist_dim=filtered_worklist,
                bcca_matches=filtered_matches,
                floorplan_available=floorplan_available,
                room_has_photos=room_has_photos,
            )
            repair_prompt += (
                "\n\nREPAIR MODE (STRICT):\n"
                "- Return plans ONLY for the following work_item_id values (no extras):\n"
                + json.dumps(repair_ids, ensure_ascii=False, indent=2)
                + "\n- Every formula_ast MUST be exactly SIGNAL(signal_id)\n"
                "- The signal_id must follow BOTH:\n"
                "  - suffix rule: *_m2/*_ml/*_ud/*_m3 matches bcca_match.unit\n"
                "  - prefix rule: area_/longitud_|perimetro_/cantidad_/volumen_ for m2/ml/ud/m3\n"
            )
            repair_resp = await call_gemini(
                prompt=repair_prompt,
                model="pro",
                temperature=0.0,
                max_tokens=65536,
                response_schema=V4_QUANTIFICATION_PLAN_SCHEMA,
                use_spanish=True,
            )
            if not repair_resp.success:
                raise RuntimeError(
                    "v4_quant_plan: targeted repair call failed "
                    f"| listing_id={listing_id} strategy={strategy_name} dim={dimension} err={repair_resp.error}"
                )
            repair_out = json.loads(repair_resp.text)
            repair_plans = (repair_out or {}).get("plans") if isinstance(repair_out, dict) else None
            _require(isinstance(repair_plans, list), "v4_quant_plan: repair response missing plans[]")

            # Merge repaired plans into original out (replace by work_item_id).
            by_id: Dict[str, Dict[str, Any]] = {}
            for p in (out.get("plans") or []):
                if isinstance(p, dict) and str(p.get("work_item_id") or "").strip():
                    by_id[str(p.get("work_item_id"))] = p
            for p in repair_plans:
                if isinstance(p, dict) and str(p.get("work_item_id") or "").strip():
                    by_id[str(p.get("work_item_id"))] = p
            out["plans"] = list(by_id.values())

            # Re-collect issues; if still failing, raise with full list (fail loud).
            issues2 = (_collect_plan_issues(plan=out).get("issues") or [])
            if issues2:
                raise RuntimeError(
                    "v4_quant_plan: validation failed after single repair "
                    f"| listing_id={listing_id} strategy={strategy_name} dim={dimension} "
                    f"initial_issues={issues[:25]} remaining_issues={issues2[:25]}"
                )

        # Final strict validation (also checks formula/unit family deterministically).
        _plans_validate_or_raise(plan=out, bcca_matches_by_item=matches_by_item_local, bcca_meta_by_code=bcca_meta_by_code)
        return out

    if gran == "dimension":
        return await _run_once(worklist_dim_in=worklist_dim, bcca_matches_in=bcca_matches)

    # gran == "room": plan per room block, then merge (still validated across all work items).
    by_room_blocks: Dict[str, Dict[str, Any]] = {}
    for rb in worklist_dim.get("room_blocks") or []:
        if not isinstance(rb, dict):
            continue
        rid = str(rb.get("room_id") or "").strip()
        if rid:
            by_room_blocks[rid] = rb

    matches_by_room: Dict[str, List[Dict[str, Any]]] = {}
    for m in bcca_matches:
        if not isinstance(m, dict):
            continue
        rid = str(m.get("room_id") or "").strip()
        if not rid:
            continue
        matches_by_room.setdefault(rid, []).append(m)

    sem = asyncio.Semaphore(room_concurrency)

    async def _run_room(rid: str) -> Dict[str, Any]:
        rb = by_room_blocks.get(rid)
        local_matches = matches_by_room.get(rid) or []
        if not rb or not local_matches:
            return {"rid": rid, "plans": []}
        local_worklist = {**worklist_dim, "room_blocks": [rb]}
        async with sem:
            out_room = await _run_once(worklist_dim_in=local_worklist, bcca_matches_in=local_matches)
        return {"rid": rid, "plans": out_room.get("plans") or []}

    tasks = [asyncio.create_task(_run_room(rid)) for rid in sorted(matches_by_room.keys())]
    results: List[Dict[str, Any]] = []
    try:
        for t in asyncio.as_completed(tasks):
            results.append(await t)
    except Exception:
        for t in tasks:
            if not t.done():
                t.cancel()
        raise

    merged_by_id: Dict[str, Dict[str, Any]] = {}
    for r in results:
        for p in (r.get("plans") or []):
            if isinstance(p, dict) and str(p.get("work_item_id") or "").strip():
                merged_by_id[str(p.get("work_item_id"))] = p

    merged = {
        "strategy_name": strategy_name,
        "dimension": dimension,
        "plan_granularity": "room",
        "room_concurrency": int(room_concurrency),
        "plans": list(merged_by_id.values()),
    }
    matches_by_item_full = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
    _plans_validate_or_raise(plan=merged, bcca_matches_by_item=matches_by_item_full, bcca_meta_by_code=bcca_meta_by_code)
    return merged


async def forage_v4_signals_for_room(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    measurement_requests: List[Dict[str, Any]],
    floorplan_available: bool,
    listing_sqm: Optional[float] = None,
    room_photo_urls: List[str],
    floorplan_urls: List[str],
    smart_m2: Dict[str, Any],
    call_gemini_json: Any,
    fetch_images_batch: Any,
    allow_missing_smart_m2_room: bool = False,
) -> Dict[str, Dict[str, Any]]:
    _require(isinstance(measurement_requests, list) and measurement_requests, f"v4_forage: empty measurement_requests | room_id={room_id}")
    required_signal_ids = [
        str(r.get("signal_id")).strip()
        for r in measurement_requests
        if isinstance(r, dict) and str(r.get("signal_id") or "").strip()
    ]
    _require(required_signal_ids, f"v4_forage: no signal_id in measurement_requests | room_id={room_id}")
    # Prefill from Smart M2
    prefilled = _prefill_signals_from_smart_m2(
        smart_m2=smart_m2,
        room_id=room_id,
        required_signals=required_signal_ids,
        allow_missing_room=bool(allow_missing_smart_m2_room),
    )
    missing = [sid for sid in required_signal_ids if sid not in prefilled]
    if not missing:
        return prefilled

    _require(room_photo_urls, f"v4_forage: room has no photos | room_id={room_id}")
    # Append floorplan images to each room forage call (per user requirement)
    evidence_urls = [*room_photo_urls, *floorplan_urls]
    images = [img for img in (await fetch_images_batch(evidence_urls)) if img is not None]
    _require(images, f"v4_forage: failed to fetch any evidence images | room_id={room_id}")

    prompt = build_v4_forage_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        measurement_requests=[r for r in measurement_requests if isinstance(r, dict) and str(r.get("signal_id") or "").strip() in set(missing)],
        floorplan_available=floorplan_available,
        listing_sqm=listing_sqm,
        room_estimated_m2=_extract_room_estimated_m2_from_smart_m2(smart_m2=smart_m2, room_id=room_id),
        known_signals=[
            {
                "signal_id": s.get("signal_id"),
                "unit_family": s.get("unit_family"),
                "value": s.get("value"),
                "confidence": s.get("confidence"),
                "defaulted": s.get("defaulted"),
                "evidence": s.get("evidence"),
            }
            for s in prefilled.values()
            if isinstance(s, dict)
        ],
    )
    # Provide an index map so evidence refs can be "photo:idx" / "floorplan:idx"
    mapping = []
    for i, u in enumerate(room_photo_urls, start=1):
        mapping.append(f"{i}. photo:{i} {u}")
    offset = len(room_photo_urls)
    for j, u in enumerate(floorplan_urls, start=1):
        mapping.append(f"{offset + j}. floorplan:{j} {u}")
    prompt += "\n\nEVIDENCE INDEX MAP (same order as provided images):\n" + "\n".join(mapping) + "\n"

    result = await call_gemini_json(
        prompt=prompt,
        model="pro",
        temperature=0.1,
        images=images,
        response_schema=V4_SMART_M2_FORAGE_SCHEMA,
        use_spanish=True,
    )
    if not result or not isinstance(result, dict):
        raise RuntimeError(f"v4_forage: invalid model response | room_id={room_id}")

    rooms = result.get("rooms") or []
    _require(isinstance(rooms, list) and rooms, "v4_forage: missing rooms[]")
    # Expect single room response
    room_payload = None
    for r in rooms:
        if isinstance(r, dict) and str(r.get("room_id") or "").strip() == room_id:
            room_payload = r
            break
    if not room_payload:
        room_payload = rooms[0] if isinstance(rooms[0], dict) else None
    _require(isinstance(room_payload, dict), "v4_forage: invalid room payload")

    found: Dict[str, Dict[str, Any]] = {}
    for s in room_payload.get("signals") or []:
        if not isinstance(s, dict):
            continue
        sid = s.get("signal_id")
        if sid in missing:
            found[str(sid)] = s

    # Fail loud if any remain missing
    still_missing = [sid for sid in missing if sid not in found]
    _require(not still_missing, f"v4_forage: missing signals after forage | room_id={room_id} missing={still_missing}")

    return {**prefilled, **found}


# =============================================================================
# V4 ZERO RESCUE — Pro + Photos reasoning pass for zero-valued signals
# =============================================================================


def build_v4_zero_rescue_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    zero_signals_with_context: List[Dict[str, Any]],
    nonzero_signals: List[Dict[str, Any]],
    floorplan_available: bool,
    listing_sqm: Optional[float] = None,
    room_estimated_m2: Optional[float] = None,
) -> str:
    """
    Prompt for the zero-rescue call.

    Each entry in zero_signals_with_context has:
      - signal_id, unit_family
      - work_items: list of {work_item_id, work_description, bcca_desc_100}
    """
    _require(
        isinstance(zero_signals_with_context, list) and zero_signals_with_context,
        "v4_zero_rescue_prompt: empty zero_signals_with_context",
    )

    return f"""
You are a senior quantity surveyor doing a careful SECOND PASS on room measurements.

SITUATION:
A first-pass survey of this room returned value=0 for several signals. Your job is to look at the photos again
and decide, for each zero signal, what a realistic nonzero quantity should be.

WHY THIS MATTERS:
Every signal below is attached to a real renovation work item that the buyer needs priced.
A zero quantity means the work item costs €0 in the BOQ — which is misleading if the work is actually needed.
Your goal is to produce the best possible estimate so the buyer gets an honest cost picture.

ROOM: {room_id}
LISTING: {listing_id}
STRATEGY: {strategy_name}
EVIDENCE: Room photos (provided). {"Floorplan images also provided." if floorplan_available else "No floorplan available."}
LISTING TOTAL M²: {listing_sqm if listing_sqm is not None else "unknown"}
ROOM ESTIMATED M² (from prior survey): {room_estimated_m2 if room_estimated_m2 is not None else "unknown"}

ALREADY-MEASURED SIGNALS IN THIS ROOM (nonzero — use as anchors/proxies):
{json.dumps(nonzero_signals, ensure_ascii=False, indent=2)}

ZERO SIGNALS THAT NEED YOUR JUDGMENT:
Each entry below shows the signal_id, its unit, AND the renovation work item(s) that depend on it.
Read the work_description to understand WHY this measurement is needed — that context helps you reason
about what a sensible quantity would be.

{json.dumps(zero_signals_with_context, ensure_ascii=False, indent=2)}

YOUR TASK (for each zero signal):
Look at the room photos and the context above, then decide a plausible quantity.

RULES:
- value MUST be > 0 for every signal. Zero is not acceptable — that's why you're here.
- For counts (ud):
  - If the renovation calls for installing something new (e.g., AC split, wardrobe, vanity) and none exists
    currently, the quantity is how many the renovation plan implies — typically 1 per room unless the
    work description says otherwise.
  - If the item already exists but wasn't counted in the first pass, estimate the count from photos.
- For areas (m2):
  - Use room_estimated_m2 and the already-measured signals as anchors.
  - Wall area ≈ perimeter × ceiling_height (assume 2.5m if not known).
  - Floor area and ceiling area ≈ room_estimated_m2.
  - Wardrobe/furniture fronts: estimate from typical dimensions for this room type and size.
- For lengths (ml):
  - Perimeter ≈ 2 × (sqrt(room_estimated_m2) × 2) as a rough proxy, or use area_suelo if available.
- confidence: "low" or "medium" — never "high" for a rescue estimate.
- defaulted: true (these are all educated estimates).
- evidence:
  - source: "imputed"
  - refs: cite the proxy signal_id(s) and/or "listing_total_sqm" / "room_estimated_m2" you relied on.
  - If you can see something relevant in the photos that helps your estimate, mention it in "notes"
    but keep evidence.source as "imputed" (since the first pass already tried photo-based measurement).

OUTPUT: Return ALL {len(zero_signals_with_context)} signals with nonzero values.
Return ONLY valid JSON matching the schema.
""".strip()


async def resolve_zero_signals_for_room(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    zero_signals_with_context: List[Dict[str, Any]],
    nonzero_signals: List[Dict[str, Any]],
    floorplan_available: bool,
    listing_sqm: Optional[float] = None,
    room_estimated_m2: Optional[float] = None,
    room_photo_urls: List[str],
    floorplan_urls: List[str],
    call_gemini_json: Any,
    fetch_images_batch: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Pro + photos reasoning call to resolve zero-valued signals.

    Returns a dict of signal_id -> signal payload (all with value > 0).
    """
    _require(
        isinstance(zero_signals_with_context, list) and zero_signals_with_context,
        f"v4_zero_rescue: no zero signals | room_id={room_id}",
    )
    _require(room_photo_urls, f"v4_zero_rescue: room has no photos | room_id={room_id}")

    evidence_urls = [*room_photo_urls, *floorplan_urls]
    images = [img for img in (await fetch_images_batch(evidence_urls)) if img is not None]
    _require(images, f"v4_zero_rescue: failed to fetch evidence images | room_id={room_id}")

    prompt = build_v4_zero_rescue_prompt(
        listing_id=listing_id,
        strategy_name=strategy_name,
        room_id=room_id,
        zero_signals_with_context=zero_signals_with_context,
        nonzero_signals=nonzero_signals,
        floorplan_available=floorplan_available,
        listing_sqm=listing_sqm,
        room_estimated_m2=room_estimated_m2,
    )

    # Evidence index map (same as forage)
    mapping = []
    for i, u in enumerate(room_photo_urls, start=1):
        mapping.append(f"{i}. photo:{i} {u}")
    offset = len(room_photo_urls)
    for j, u in enumerate(floorplan_urls, start=1):
        mapping.append(f"{offset + j}. floorplan:{j} {u}")
    prompt += "\n\nEVIDENCE INDEX MAP (same order as provided images):\n" + "\n".join(mapping) + "\n"

    result = await call_gemini_json(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        images=images,
        response_schema=V4_SMART_M2_FORAGE_SCHEMA,
        use_spanish=True,
    )

    if not result or not isinstance(result, dict):
        raise RuntimeError(f"v4_zero_rescue: invalid model response | room_id={room_id}")

    rooms = result.get("rooms") or []
    _require(isinstance(rooms, list) and rooms, "v4_zero_rescue: missing rooms[]")
    room_payload = None
    for r in rooms:
        if isinstance(r, dict) and str(r.get("room_id") or "").strip() == room_id:
            room_payload = r
            break
    if not room_payload:
        room_payload = rooms[0] if isinstance(rooms[0], dict) else None
    _require(isinstance(room_payload, dict), "v4_zero_rescue: invalid room payload")

    expected_ids = {str(z.get("signal_id") or "").strip() for z in zero_signals_with_context}
    resolved: Dict[str, Dict[str, Any]] = {}
    still_zero: List[str] = []
    for s in room_payload.get("signals") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("signal_id") or "").strip()
        if sid not in expected_ids:
            continue
        val = _safe_float(s.get("value"))
        if val is not None and val > 0:
            resolved[sid] = s
        else:
            still_zero.append(sid)

    missing_ids = [sid for sid in expected_ids if sid not in resolved and sid not in still_zero]
    if missing_ids:
        logger.warning(
            "v4_zero_rescue: model did not return some signals | room_id=%s missing=%s",
            room_id,
            missing_ids[:20],
        )

    if still_zero:
        logger.warning(
            "v4_zero_rescue: model still returned 0 for some signals (will keep original) | room_id=%s still_zero=%s",
            room_id,
            still_zero[:20],
        )

    return resolved


async def run_v4_for_strategy(
    *,
    listing_id: int,
    strategy_name: str,
    db: Any,
    call_gemini: Any,
    call_gemini_json: Any,
    fetch_images_batch: Any,
    embed_texts_fn: Any,
    clear_existing_v4: bool = True,
) -> Dict[str, Any]:
    """
    Full V4 run for a single strategy across ALL 6 dimensions.
    Writes:
    - unified_estimates: v4_worklist_{strategy}_{dimension}, v4_bcca_matches_{strategy}_{dimension},
      v4_quant_plan_{strategy}_{dimension}, v4_signals_{strategy}, v4_run_summary_{strategy}
    - boq_line_items: dimension="v4"
    """
    validate_catalog()

    # Property-wide context (used as a sanity anchor for proportional inference).
    try:
        listing = await db.get_listing(listing_id)
    except Exception:
        listing = None
    listing_sqm = _extract_listing_sqm(listing)

    clusters = await db.get_photo_clusters(listing_id)
    _require(clusters, f"v4: missing clusters | listing_id={listing_id}")
    smart_m2 = await db.get_smart_m2(listing_id)
    _require(smart_m2, f"v4: missing smart_m2 | listing_id={listing_id}")
    target_pir = await db.get_pir(listing_id, pir_type="target")
    _require(target_pir, f"v4: missing target PIR | listing_id={listing_id}")
    strategy_spec = await db.get_unified_estimate(listing_id, f"v3_strategy_spec_{strategy_name}")
    _require(strategy_spec, f"v4: missing strategy_spec | listing_id={listing_id} strategy={strategy_name}")

    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    _require(room_photos, f"v4: no room photos found | listing_id={listing_id}")
    room_has_photos = {rid: True for rid in room_photos.keys()}

    # Canonical room ids come from Smart M2 (and must have photos)
    room_ids: List[str] = []
    for r in (smart_m2.get("rooms") or []):
        if not isinstance(r, dict):
            continue
        rid = str(r.get("room_id") or r.get("cluster_id") or "").strip()
        if not rid:
            continue
        if rid not in room_photos:
            raise RuntimeError(f"v4: smart_m2 room has no photo cluster | room_id={rid}")
        room_ids.append(rid)
    _require(room_ids, f"v4: no canonical room_ids from smart_m2 | listing_id={listing_id}")

    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    if clear_existing_v4:
        await db.clear_boq_line_items_by_dimension(listing_id, strategy_name=strategy_name, dimension="v4")

    signals_store_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _load_signals_payload_into_store(*, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        for rr in payload.get("rooms") or []:
            if not isinstance(rr, dict):
                continue
            rid = str(rr.get("room_id") or "").strip()
            sigs = rr.get("signals") or []
            if not rid or not isinstance(sigs, list):
                continue
            signals_store_by_room.setdefault(rid, {})
            for s in sigs:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("signal_id") or "").strip()
                if sid:
                    signals_store_by_room[rid][sid] = s

    # Resume: reuse previously saved signals to avoid re-foraging.
    # 1) Shared signals (listing-level) reduce duplicate foraging across strategies.
    try:
        saved_shared_signals = await db.get_unified_estimate(listing_id, "v4_signals_shared")
    except Exception:
        saved_shared_signals = None
    _load_signals_payload_into_store(payload=saved_shared_signals)

    # 2) Strategy-specific signals override/extend shared signals (same structure).
    try:
        saved_strategy_signals = await db.get_unified_estimate(listing_id, f"v4_signals_{strategy_name}")
    except Exception:
        saved_strategy_signals = None
    _load_signals_payload_into_store(payload=saved_strategy_signals)
    # Prevent duplicate foraging work / races when dimensions run concurrently.
    room_locks: Dict[str, Any] = {}
    summary: Dict[str, Any] = {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "floorplan_available": floorplan_available,
        "listing_sqm": listing_sqm,
        "room_count": len(room_ids),
        "dimensions": {},
    }

    total_saved = 0
    # Run dimensions concurrently (bounded) to reduce wall-clock time.
    import asyncio

    semaphore = asyncio.Semaphore(3)
    signals_checkpoint_lock = asyncio.Lock()

    async def _checkpoint_signals(*, reason: str) -> None:
        """
        Persist v4_signals_{strategy} frequently so timeout slices can resume without re-foraging.
        WHY THIS MATTERS: Foraging is the expensive, high-latency step and must be checkpointed immediately.
        """
        async with signals_checkpoint_lock:
            rooms_payload: List[Dict[str, Any]] = []
            signal_count = 0
            for rid in sorted(signals_store_by_room.keys()):
                sigs_by_id = signals_store_by_room.get(rid) or {}
                signals_list = [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]
                signal_count += len(signals_list)
                rooms_payload.append({"room_id": rid, "signals": signals_list})
            payload = {"rooms": rooms_payload}
            logger.info(
                "v4: checkpoint signals start | reason=%s | rooms=%s | signals=%s | listing_id=%s | strategy=%s",
                reason,
                len(rooms_payload),
                signal_count,
                listing_id,
                strategy_name,
            )
            await db.save_unified_estimate(listing_id, f"v4_signals_{strategy_name}", payload)
            # Also persist shared listing-level signals so later strategies can reuse them.
            await db.save_unified_estimate(listing_id, "v4_signals_shared", payload)
            logger.info(
                "v4: checkpoint signals complete | reason=%s | rooms=%s | signals=%s | listing_id=%s | strategy=%s",
                reason,
                len(rooms_payload),
                signal_count,
                listing_id,
                strategy_name,
            )

    async def _prepare_dimension(dim: str) -> Tuple[str, Dict[str, Any]]:
        async with semaphore:
            logger.info(f"v4: start dimension (prepare) | {dim} | listing_id={listing_id} strategy={strategy_name}")

            pkg_worklist = f"v4_worklist_{strategy_name}_{dim}"
            worklist_dim = await db.get_unified_estimate(listing_id, pkg_worklist)
            if not isinstance(worklist_dim, dict):
                worklist_dim = await generate_v4_worklist_for_dimension(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    dimension=dim,
                    strategy_spec=strategy_spec,
                    target_pir=target_pir,
                    room_ids=room_ids,
                    call_gemini=call_gemini,
                )
                await db.save_unified_estimate(listing_id, pkg_worklist, worklist_dim)
            else:
                logger.info(f"v4: reuse worklist | {dim} | listing_id={listing_id} strategy={strategy_name}")

            pkg_matches = f"v4_bcca_matches_{strategy_name}_{dim}"
            matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
            bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
            if not isinstance(bcca_matches, list) or not bcca_matches:
                bcca_matches = await match_v4_bcca(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    dimension=dim,
                    worklist_dim=worklist_dim,
                    matcher=matcher,
                    embed_texts_fn=embed_texts_fn,
                )
                await db.save_unified_estimate(listing_id, pkg_matches, {"matches": bcca_matches})
            else:
                logger.info(f"v4: reuse bcca matches | {dim} | listing_id={listing_id} strategy={strategy_name}")

            pkg_plan = f"v4_quant_plan_{strategy_name}_{dim}"
            quant_plan = await db.get_unified_estimate(listing_id, pkg_plan)
            has_cached_plan = (
                isinstance(quant_plan, dict)
                and isinstance(quant_plan.get("plans"), list)
                and bool(quant_plan.get("plans"))
            )
            if has_cached_plan:
                try:
                    matches_by_item = {
                        m.get("work_item_id"): m
                        for m in bcca_matches
                        if isinstance(m, dict) and m.get("work_item_id")
                    }
                    _plans_validate_or_raise(
                        plan=quant_plan,
                        bcca_matches_by_item=matches_by_item,
                        bcca_meta_by_code=bcca_meta_by_code,
                    )
                    await db.save_unified_estimate(listing_id, pkg_plan, quant_plan)
                    logger.info(f"v4: reuse quant plan | {dim} | listing_id={listing_id} strategy={strategy_name}")
                except Exception as exc:
                    logger.warning(
                        "v4: cached quant plan invalid; regenerating "
                        f"| dim={dim} listing_id={listing_id} strategy={strategy_name} err={exc}"
                    )
                    has_cached_plan = False
            if not has_cached_plan:
                quant_plan = await generate_v4_quant_plan(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    dimension=dim,
                    worklist_dim=worklist_dim,
                    bcca_matches=bcca_matches,
                    floorplan_available=floorplan_available,
                    room_has_photos=room_has_photos,
                    call_gemini=call_gemini,
                    bcca_meta_by_code=bcca_meta_by_code,
                    listing_sqm=listing_sqm,
                )
                await db.save_unified_estimate(listing_id, pkg_plan, quant_plan)

            # Persist any unit-family reconciliation changes to matches (if any).
            await db.save_unified_estimate(listing_id, pkg_matches, {"matches": bcca_matches})

            def _collect_signal_ids(node: Dict[str, Any]) -> List[str]:
                out: List[str] = []
                op = node.get("op")
                if op == "SIGNAL":
                    sid = str(node.get("signal_id") or "").strip()
                    if sid:
                        out.append(sid)
                    return out
                arg = node.get("arg")
                if isinstance(arg, dict):
                    out.extend(_collect_signal_ids(arg))
                args = node.get("args")
                if isinstance(args, list):
                    for a in args:
                        if isinstance(a, dict):
                            out.extend(_collect_signal_ids(a))
                return out

            def _infer_unit_family_from_signal_id(signal_id: str) -> str:
                sid = signal_id.strip().lower()
                for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
                    if sid.endswith(suf):
                        return uf
                raise RuntimeError(f"v4: signal_id missing unit suffix | signal_id={signal_id}")

            requests_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
            for p in quant_plan.get("plans") or []:
                if not isinstance(p, dict):
                    continue
                wid = str(p.get("work_item_id") or "").strip()
                match = next((m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id") == wid), None)
                rid = str((match or {}).get("room_id") or "").strip()
                _require(rid, f"v4: missing room_id for work_item | dim={dim} work_item_id={wid}")
                formula = p.get("formula_ast")
                if not isinstance(formula, dict):
                    continue
                signal_ids = sorted(set(_collect_signal_ids(formula)))
                _require(signal_ids, f"v4: formula has no SIGNAL() | room_id={rid} work_item_id={p.get('work_item_id')}")
                for sid in signal_ids:
                    requests_by_room.setdefault(rid, {})
                    requests_by_room[rid][sid] = {
                        "signal_id": sid,
                        "unit_family": _infer_unit_family_from_signal_id(sid),
                    }

            dim_summary = {
                "work_items": sum(
                    len((rb.get("scope_packages") or []))
                    for rb in (worklist_dim.get("room_blocks") or [])
                    if isinstance(rb, dict)
                ),
                "bcca_matches": len(bcca_matches),
                "plans": len(quant_plan.get("plans") or []),
                "saved_boq_items": 0,
            }
            logger.info(f"v4: complete dimension (prepare) | {dim} | listing_id={listing_id} strategy={strategy_name}")
            return (
                dim,
                {
                    "worklist_dim": worklist_dim,
                    "bcca_matches": bcca_matches,
                    "quant_plan": quant_plan,
                    "requests_by_room": requests_by_room,
                    "dim_summary": dim_summary,
                },
            )

    # Phase 1: prepare ALL dimensions (worklist + bcca + quant_plan) and collect REQUIRED signals per room.
    prepared = await asyncio.gather(*[_prepare_dimension(dim) for dim in V2_DIMENSIONS])
    dim_payload_by_dim: Dict[str, Dict[str, Any]] = {}
    required_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for dim, payload in prepared:
        dim_payload_by_dim[dim] = payload
        summary["dimensions"][dim] = payload.get("dim_summary") or {}
        for rid, reqs_by_id in (payload.get("requests_by_room") or {}).items():
            if rid not in required_by_room:
                required_by_room[rid] = {}
            for sid, req in (reqs_by_id or {}).items():
                required_by_room[rid][sid] = req

    # Phase 2: forage each room ONCE using the union of required signals across ALL dimensions.
    forage_semaphore = asyncio.Semaphore(3)

    async def _forage_room_once(rid: str) -> None:
        async with forage_semaphore:
            reqs_by_id = required_by_room.get(rid) or {}
            if rid not in signals_store_by_room:
                signals_store_by_room[rid] = {}

            existing_ids = set(signals_store_by_room[rid].keys())
            want_ids = [sid for sid in reqs_by_id.keys() if sid not in existing_ids]
            if not want_ids:
                return

            if rid not in room_locks:
                room_locks[rid] = asyncio.Lock()
            async with room_locks[rid]:
                # Recompute after acquiring lock (in case another task updated).
                existing_ids2 = set(signals_store_by_room[rid].keys())
                want_ids2 = [sid for sid in reqs_by_id.keys() if sid not in existing_ids2]
                if not want_ids2:
                    return
                want_requests = [reqs_by_id[sid] for sid in want_ids2 if sid in reqs_by_id]

                measured = await forage_v4_signals_for_room(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    room_id=rid,
                    measurement_requests=want_requests,
                    floorplan_available=floorplan_available,
                    listing_sqm=listing_sqm,
                    room_photo_urls=room_photos.get(rid) or [],
                    floorplan_urls=floorplan_urls,
                    smart_m2=smart_m2,
                    call_gemini_json=call_gemini_json,
                    fetch_images_batch=fetch_images_batch,
                    allow_missing_smart_m2_room=False,
                )
                signals_store_by_room[rid].update(measured)

            await _checkpoint_signals(reason=f"room_forage_update room_id={rid} new_signals={len(measured)}")

    await asyncio.gather(*[_forage_room_once(rid) for rid in sorted(required_by_room.keys())])

    # Phase 3: assemble BOQ per dimension now that signals are complete (deterministic).
    async def _assemble_dimension(dim: str) -> Tuple[str, int]:
        async with semaphore:
            payload = dim_payload_by_dim.get(dim) or {}
            bcca_matches = payload.get("bcca_matches") or []
            quant_plan = payload.get("quant_plan") or {}
            saved = await assemble_v4_boq(
                listing_id=listing_id,
                strategy_name=strategy_name,
                dimension=dim,
                bcca_matches=bcca_matches,
                quant_plan=quant_plan,
                signals_by_room=signals_store_by_room,
                db=db,
                listing_sqm=listing_sqm,
            )
            await _checkpoint_signals(reason=f"dimension_complete dim={dim}")
            logger.info(f"v4: complete dimension (assemble) | {dim} | saved={saved} | listing_id={listing_id} strategy={strategy_name}")
            return dim, int(saved)

    assembled = await asyncio.gather(*[_assemble_dimension(dim) for dim in V2_DIMENSIONS])
    for dim, saved in assembled:
        total_saved += int(saved)
        dim_summary = summary["dimensions"].get(dim) if isinstance(summary.get("dimensions"), dict) else None
        if isinstance(dim_summary, dict):
            dim_summary["saved_boq_items"] = int(saved)

    # Persist signals store (single per strategy)
    await _checkpoint_signals(reason="final")
    summary["saved_boq_items_total"] = total_saved
    await db.save_unified_estimate(listing_id, f"v4_run_summary_{strategy_name}", summary)

    return summary


# ── Quantity sanity caps ──────────────────────────────────────────────────────
# WHY THIS MATTERS: Forage vision signals frequently over-estimate areas
# (e.g. 119 m² tiles for a bathroom, 54 cabinets for a kitchen). These caps
# act as a safety net at the BOQ assembler level. They don't fix the upstream
# signal quality, but prevent the most egregious cost inflation.
#
# Heuristic: for an 81 m² flat with 10 rooms, average room is ~8 m².
# We use listing_sqm / 5 as a generous per-room area cap (assumes the largest
# room could be ~20% of the flat). For unit items, we cap per room.

# Per-room caps by unit family
_QTY_CAPS_PER_ROOM_UD: Dict[str, int] = {
    # HVAC: 1 AC split or radiator per room, not 4
    "08CAF": 1,       # A/C split units
    "08CCE": 2,       # radiator panels (some rooms have 2)
    # Electrical supply: 1 per flat, but we cap per-room to 1 (flat-level handled below)
    "21IEAS": 1,      # electrical supply substitution
    # Doors: max 2 per room (entry + closet or passage)
    "21KPS": 2,       # door replacement
    "11MPW": 2,       # sliding doors
    "11LPC": 2,       # aluminium sliding doors
    "11LPA": 2,       # aluminium hinged doors
    # Kitchen cabinets: max 6 per kitchen (reasonable for a full refit)
    "14MCC": 6,       # sink/base cabinets
    "14MCW": 6,       # wall cabinets
    # Electrical demolition: 1 per room
    "01IEW": 1,       # electrical demo
}

# Flat-level caps (total across all rooms — these items are building/dwelling-wide)
_QTY_CAPS_FLAT_TOTAL: Dict[str, int] = {
    "21IEAS00010": 1,  # electrical supply substitution per dwelling
    "21IEAS00020": 1,  # block electrical supply (shouldn't appear but safety net)
}

# Running totals for flat-level caps (reset per assemble call via closure)
_flat_totals: Dict[str, float] = {}


def _cap_quantity(
    *,
    qty: float,
    unit: str,
    bcca_code: str,
    room_id: str,
    work_item_id: str,
    listing_sqm: float | None,
) -> float:
    """
    Apply sanity caps to prevent absurd quantities from inflated signals.
    Returns the (possibly capped) quantity. Logs when capping occurs.
    """
    if qty <= 0:
        return qty

    original_qty = qty
    code6 = bcca_code[:6] if len(bcca_code) >= 6 else bcca_code

    # Cap 1: per-room unit caps for specific BCCA code families
    if unit in ("ud",):
        cap = _QTY_CAPS_PER_ROOM_UD.get(code6)
        if cap is not None and qty > cap:
            qty = float(cap)

    # Cap 2: flat-level total caps (e.g., 1 electrical supply per dwelling total)
    flat_cap = _QTY_CAPS_FLAT_TOTAL.get(bcca_code)
    if flat_cap is not None:
        used = _flat_totals.get(bcca_code, 0.0)
        remaining = max(0.0, float(flat_cap) - used)
        if qty > remaining:
            qty = remaining
        _flat_totals[bcca_code] = used + qty

    # Cap 3: area-based caps for m² quantities — no single room should exceed
    # a generous fraction of the flat area. For an 81 m² flat, max ~28 m² per room
    # for any single trade item (floor, wall tiles, demo, etc.).
    if unit == "m2" and listing_sqm and listing_sqm > 0:
        room_floor_cap = listing_sqm * 0.35  # largest room ≈ 35% of flat
        # Wall/ceiling items (plaster, paint, tile, demo, repair) can be ~3x floor area
        # (4 walls × ~2.7m height ÷ floor length). 3x is generous.
        # Detect by BCCA chapter prefix: 10CGG (plaster), 10AAL (tiles), 13I/13P (paint),
        # 01ADS/01RAA/01RCE (demo), 21ADS/21PEP/21PEC (repair/paint).
        _WALL_PREFIXES = ("10CGG", "10AAL", "13ITT", "13IPP", "13IPE",
                          "01ADS", "01RAA", "01RCE", "21ADS", "21PEP", "21PEC")
        is_wall_item = any(bcca_code.startswith(pfx) for pfx in _WALL_PREFIXES)
        if is_wall_item:
            max_qty = room_floor_cap * 3.0  # e.g. 81*0.35*3 = 85 m² wall for largest room
        else:
            max_qty = room_floor_cap  # floor/ceiling items capped to room floor area
        if qty > max_qty:
            qty = max_qty

    # Cap 4: ml quantities — max ~perimeter of largest room (~4 × sqrt(area))
    if unit == "ml" and listing_sqm and listing_sqm > 0:
        room_area_cap = listing_sqm * 0.35
        max_ml = 4.0 * (room_area_cap ** 0.5) * 1.5  # perimeter × 1.5 safety margin
        if qty > max_ml:
            qty = max_ml

    if qty != original_qty:
        logger.info(
            "v4_boq: qty capped | %s | room=%s | bcca=%s | %.1f → %.1f %s",
            work_item_id, room_id, bcca_code, original_qty, qty, unit,
        )
    return qty


async def assemble_v4_boq(
    *,
    listing_id: int,
    strategy_name: str,
    dimension: str,
    bcca_matches: List[Dict[str, Any]],
    quant_plan: Dict[str, Any],
    signals_by_room: Dict[str, Dict[str, Dict[str, Any]]],
    db: Any,
    boq_table_dimension: str = "v4",
    match_mode: str | None = None,
    listing_sqm: float | None = None,
) -> int:
    # Reset flat-level quantity caps for this dimension (accumulated per assemble call).
    _flat_totals.clear()

    matches_by_item = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
    rows: List[Dict[str, Any]] = []

    matches_by_id = matches_by_item
    plans_raw = [p for p in (quant_plan.get("plans") or []) if isinstance(p, dict)]

    # Join formula-only plans back to room_id + unit_family deterministically via BCCA matches.
    plans: List[Dict[str, Any]] = []
    for p in plans_raw:
        wid = str(p.get("work_item_id") or "").strip()
        _require(wid in matches_by_id, f"v4_boq: missing bcca match | work_item_id={wid}")
        match = matches_by_id[wid]
        plans.append(
            {
                **p,
                "room_id": match.get("room_id"),
                "dimension": dimension,
                "unit_family": _unit_family(match.get("unit")),
            }
        )

    for p in plans:
        if not isinstance(p, dict):
            continue
        wid = p.get("work_item_id")
        room_id = str(p.get("room_id") or "").strip()
        _require(wid in matches_by_item, f"v4_boq: missing bcca match | work_item_id={wid}")
        match = matches_by_item[wid]
        unit = _unit_family(match.get("unit"))

        room_signals = signals_by_room.get(room_id) or {}
        ctx = FormulaEvaluationContext(
            work_item_id=str(wid),
            room_id=room_id,
            dimension=dimension,
            unit_family=unit,  # type: ignore[arg-type]
        )
        def _collect_signal_ids(node: Dict[str, Any]) -> List[str]:
            out: List[str] = []
            op = node.get("op")
            if op == "SIGNAL":
                sid = str(node.get("signal_id") or "").strip()
                if sid:
                    out.append(sid)
                return out
            arg = node.get("arg")
            if isinstance(arg, dict):
                out.extend(_collect_signal_ids(arg))
            args = node.get("args")
            if isinstance(args, list):
                for a in args:
                    if isinstance(a, dict):
                        out.extend(_collect_signal_ids(a))
            return out

        def _infer_unit_family_from_signal_id(signal_id: str) -> str:
            sid = signal_id.strip().lower()
            for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
                if sid.endswith(suf):
                    return uf
            raise RuntimeError(f"v4_boq: signal_id missing unit suffix | signal_id={signal_id}")

        formula_ast = p.get("formula_ast")
        _require(isinstance(formula_ast, dict), f"v4_boq: missing formula_ast | work_item_id={wid}")
        signal_ids = sorted(set(_collect_signal_ids(formula_ast)))
        signal_units = {sid: _infer_unit_family_from_signal_id(sid) for sid in signal_ids}
        qty, used = evaluate_formula(ctx=ctx, formula_ast=formula_ast, signals=room_signals, signal_units=signal_units)  # type: ignore[arg-type]

        # ── Quantity sanity caps ──────────────────────────────────────────────
        # WHY: Forage signal estimates can be wildly inflated (e.g. 119 m² tiles
        # for a bathroom, 54 cabinets for a kitchen). These caps prevent absurd
        # line totals while we improve forage accuracy upstream.
        qty = _cap_quantity(
            qty=float(qty),
            unit=unit,
            bcca_code=str(match.get("bcca_code") or ""),
            room_id=room_id,
            work_item_id=str(wid),
            listing_sqm=listing_sqm,
        )
        # ─────────────────────────────────────────────────────────────────────

        unit_price = float(match.get("unit_price") or 0)
        line_total = float(qty) * unit_price
        hours_per_unit = match.get("labor_hours_per_unit")
        labor_hours = None
        if hours_per_unit is not None:
            try:
                labor_hours = float(hours_per_unit) * float(qty)
            except Exception:
                labor_hours = None

        rows.append(
            {
                "item_kind": "v4",
                "bcca_code": match.get("bcca_code"),
                "description": match.get("bcca_desc_100") or "",
                "quantity": float(qty),
                "unit": unit,
                "unit_price": unit_price,
                "line_total": line_total,
                "labor_hours": labor_hours,
                # NOTE: we store table dimension="v4" (or "v4_rich") to avoid collisions with v3,
                # but keep the actual dimension in provenance for summaries and audits.
                "room_id": room_id,
                "room_name": room_id,
                "provenance": {
                    "pipeline": "v4",
                    "v4_dimension": dimension,
                    "work_item_id": wid,
                    "signals_used": used,
                    "formula_ast": formula_ast,
                    "match_mode": match_mode,
                },
            }
        )

    # Per-room batch save (preserve granularity)
    rows_by_room: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        rn = str(r.get("room_name") or r.get("room_id") or "unknown").strip() or "unknown"
        rows_by_room.setdefault(rn, []).append(r)

    saved_total = 0
    for room_name, room_rows in rows_by_room.items():
        saved = await db.save_boq_line_items_batch(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension=str(boq_table_dimension),
            room_name=room_name,
            items=room_rows,
        )
        saved_total += int(saved)
    return int(saved_total)


def _worklist_dim_from_flat_items(*, dimension: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a V4_WORKLIST_DIMENSION-like payload from flat items.

    This avoids writing/reading v4_worklist_* artifacts while still reusing
    existing V4 matching + quant planning + forage + BOQ code paths.
    """
    by_room: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        if str(it.get("dimension") or "").strip() != str(dimension):
            continue
        rid = str(it.get("room_id") or "").strip()
        wid = str(it.get("work_item_id") or "").strip()
        desc = str(it.get("work_description") or "").strip()
        if not rid or not wid or not desc:
            continue
        by_room.setdefault(rid, []).append(it)

    room_blocks: List[Dict[str, Any]] = []
    for rid in sorted(by_room.keys()):
        pkgs: List[Dict[str, Any]] = []
        for it in by_room[rid]:
            pkgs.append(
                {
                    "work_item_id": str(it.get("work_item_id") or ""),
                    "work_description": str(it.get("work_description") or ""),
                    "target_element": str(it.get("slot_id") or "") or None,
                    "source_scope_refs": list(it.get("source_refs") or []),
                }
            )
        room_blocks.append({"room_id": rid, "scope_packages": pkgs})
    return {"dimension": str(dimension), "dimension_intro": f"V5-derived worklist for {dimension}", "room_blocks": room_blocks}


async def _ensure_smart_m2(
    *,
    listing_id: int,
    listing: Dict[str, Any] | None,
    listing_sqm: float | None,
    clusters: List[Dict[str, Any]],
    v5_room_ids: List[str],
    db: Any,
) -> Dict[str, Any]:
    """
    Ensure Smart M² data exists for this listing with room IDs matching V5 clusters.

    Strategy:
    1. Load existing Smart M² from DB.
    2. If it exists and room IDs match current V5 clusters (>=70% overlap) → reuse as-is.
    3. Otherwise → run Smart M² generation from scratch, persist, return.

    No semantic remapping — if IDs are stale, we regenerate cleanly.

    Returns a smart_m2 dict with rooms keyed by V5 cluster IDs.
    """
    raw_smart_m2 = await db.get_smart_m2(listing_id)

    if raw_smart_m2 and isinstance(raw_smart_m2, dict) and raw_smart_m2.get("rooms"):
        sm2_room_ids = {
            str(r.get("room_id") or r.get("cluster_id") or "").strip()
            for r in raw_smart_m2.get("rooms", [])
            if isinstance(r, dict)
        }
        v5_set = set(v5_room_ids)
        overlap = sm2_room_ids & v5_set

        if len(overlap) >= len(v5_set) * 0.7:
            # Room IDs already match V5 clusters — reuse as-is
            logger.info(
                "smart_m2: reusing existing data (IDs match) | listing_id=%s | sm2_rooms=%d | v5_rooms=%d | overlap=%d",
                listing_id, len(sm2_room_ids), len(v5_set), len(overlap),
            )
            return raw_smart_m2
        else:
            logger.info(
                "smart_m2: stale IDs (overlap %d/%d), regenerating | listing_id=%s",
                len(overlap), len(v5_set), listing_id,
            )

    # ── Generate Smart M² from scratch using current V5 clusters ──────────
    logger.info("smart_m2: generating from scratch | listing_id=%s | clusters=%d", listing_id, len(clusters))

    total_m2 = listing_sqm
    if not total_m2 and listing:
        total_m2 = _safe_float(listing.get("sqm")) or _safe_float(listing.get("m2_built"))
        if not total_m2:
            scraped = listing.get("scraped_data") or {}
            areas = scraped.get("areas") or {}
            total_m2 = _safe_float(areas.get("constructed")) or _safe_float(areas.get("useful")) or _safe_float(scraped.get("sqm"))
    _require(total_m2 and total_m2 > 0, f"smart_m2: no total m² found | listing_id={listing_id}")

    # Build a minimal orchestrator shim so we can reuse run_m1_smart_m2
    from pipeline.steps.smart_m2 import run_m1_smart_m2

    class _OrchestratorShim:
        """Minimal shim providing only the db interface needed by run_m1_smart_m2."""
        def __init__(self, db_inst: Any):
            self.db = db_inst

    shim = _OrchestratorShim(db)
    result = await run_m1_smart_m2(shim, listing_id, persist_to_db=True)  # type: ignore[arg-type]

    # The generated Smart M² uses the current cluster IDs (V5), so no remapping needed.
    sm2_data = {
        "rooms": result.get("rooms") or [],
        "circulation_and_walls_m2": result.get("circulation_m2") or 0,
        "total_check": result.get("total_m2") or total_m2,
    }

    sm2_room_count = len(sm2_data.get("rooms") or [])
    logger.info(
        "smart_m2: generated and saved | listing_id=%s | rooms=%d | total_m2=%s",
        listing_id, sm2_room_count, total_m2,
    )
    return sm2_data


async def run_v4_tail_from_v5_work_items(
    *,
    listing_id: int,
    strategy_name: str,
    v5_work_items: Dict[str, Any],
    db: Any,
    call_gemini: Any,
    call_gemini_json: Any,
    fetch_images_batch: Any,
    embed_texts_fn: Any,
    clear_existing_v4: bool = True,
    dimension_concurrency: int = 6,
    forage_concurrency: int = 5,
) -> Dict[str, Any]:
    """
    Run the V4 tail (BCCA match → quant plan → forage → BOQ) starting from V5 work items,
    without writing any intermediate v4_worklist_* artifacts.

    This is the preferred V5 integration because it avoids the lossy V4 worklist prompt entirely.

    Concurrency: dimension_concurrency caps parallel prepare/assemble per dimension (default 6);
    forage_concurrency caps parallel room foraging (default 5).
    """
    validate_catalog()

    # Property-wide context (used as a sanity anchor for proportional inference).
    try:
        listing = await db.get_listing(listing_id)
    except Exception:
        listing = None
    listing_sqm = _extract_listing_sqm(listing)

    items = v5_work_items.get("items") or []
    _require(isinstance(items, list) and items, f"v4_tail_from_v5: empty v5 work_items | listing_id={listing_id} strategy={strategy_name}")

    clusters = await db.get_photo_clusters(listing_id)
    _require(clusters, f"v4_tail_from_v5: missing clusters | listing_id={listing_id}")

    # ── Smart M²: run or reuse ───────────────────────────────────────────
    # WHY: Smart M² provides authoritative room dimensions (floor area, wall area,
    # perimeter, openings) that prevent forage from hallucinating inflated quantities.
    # It MUST run before the V4 tail. If the data already exists with matching room IDs
    # we reuse it; otherwise we (re)generate it from the current clusters.
    v5_room_ids = sorted({str(c.get("cluster_id") or "").strip() for c in clusters if isinstance(c, dict) and str(c.get("cluster_id") or "").strip()})
    smart_m2 = await _ensure_smart_m2(
        listing_id=listing_id,
        listing=listing,
        listing_sqm=listing_sqm,
        clusters=clusters,
        v5_room_ids=v5_room_ids,
        db=db,
    )

    floorplan_urls = _extract_floorplan_urls(clusters)
    floorplan_available = bool(floorplan_urls)
    room_photos = _room_photo_urls_by_id(clusters)
    _require(room_photos, f"v4_tail_from_v5: no room photos found | listing_id={listing_id}")
    room_has_photos = {rid: True for rid in room_photos.keys()}

    matcher = _get_default_bcca_matcher()
    bcca_meta_by_code = matcher.get_metadata_by_code_map()

    if clear_existing_v4:
        await db.clear_boq_line_items_by_dimension(listing_id, strategy_name=strategy_name, dimension="v4")

    # Resume signals cache (same approach as V4).
    signals_store_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _load_signals_payload_into_store(*, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        for rr in payload.get("rooms") or []:
            if not isinstance(rr, dict):
                continue
            rid = str(rr.get("room_id") or "").strip()
            sigs = rr.get("signals") or []
            if not rid or not isinstance(sigs, list):
                continue
            signals_store_by_room.setdefault(rid, {})
            for s in sigs:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("signal_id") or "").strip()
                if sid:
                    signals_store_by_room[rid][sid] = s

    try:
        saved_shared_signals = await db.get_unified_estimate(listing_id, "v4_signals_shared")
    except Exception:
        saved_shared_signals = None
    _load_signals_payload_into_store(payload=saved_shared_signals)
    try:
        saved_strategy_signals = await db.get_unified_estimate(listing_id, f"v4_signals_{strategy_name}")
    except Exception:
        saved_strategy_signals = None
    _load_signals_payload_into_store(payload=saved_strategy_signals)

    import asyncio

    if dimension_concurrency < 1:
        dimension_concurrency = 1
    if forage_concurrency < 1:
        forage_concurrency = 1
    semaphore = asyncio.Semaphore(dimension_concurrency)
    signals_checkpoint_lock = asyncio.Lock()

    async def _checkpoint_signals(*, reason: str) -> None:
        async with signals_checkpoint_lock:
            rooms_payload: List[Dict[str, Any]] = []
            signal_count = 0
            for rid in sorted(signals_store_by_room.keys()):
                sigs_by_id = signals_store_by_room.get(rid) or {}
                signals_list = [sigs_by_id[sid] for sid in sorted(sigs_by_id.keys())]
                signal_count += len(signals_list)
                rooms_payload.append({"room_id": rid, "signals": signals_list})
            payload = {"rooms": rooms_payload}
            await db.save_unified_estimate(listing_id, f"v4_signals_{strategy_name}", payload)
            await db.save_unified_estimate(listing_id, "v4_signals_shared", payload)
            logger.info(
                "v4_tail_from_v5: checkpoint signals | reason=%s | rooms=%s | signals=%s | listing_id=%s | strategy=%s",
                reason,
                len(rooms_payload),
                signal_count,
                listing_id,
                strategy_name,
            )

    summary: Dict[str, Any] = {
        "listing_id": listing_id,
        "strategy_name": strategy_name,
        "floorplan_available": floorplan_available,
        "listing_sqm": listing_sqm,
        "dimensions": {},
    }

    async def _prepare_dimension(dim: str) -> Tuple[str, Dict[str, Any]]:
        async with semaphore:
            worklist_dim = _worklist_dim_from_flat_items(dimension=dim, items=items)

            pkg_matches = f"v4_bcca_matches_{strategy_name}_{dim}"
            matches_payload = await db.get_unified_estimate(listing_id, pkg_matches)
            bcca_matches = (matches_payload or {}).get("matches") if isinstance(matches_payload, dict) else None
            if not isinstance(bcca_matches, list) or not bcca_matches:
                bcca_matches = await match_v4_bcca(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    dimension=dim,
                    worklist_dim=worklist_dim,
                    matcher=matcher,
                    embed_texts_fn=embed_texts_fn,
                )
                await db.save_unified_estimate(listing_id, pkg_matches, {"matches": bcca_matches})

            pkg_plan = f"v4_quant_plan_{strategy_name}_{dim}"
            quant_plan = await db.get_unified_estimate(listing_id, pkg_plan)
            has_cached_plan = (
                isinstance(quant_plan, dict)
                and isinstance(quant_plan.get("plans"), list)
                and bool(quant_plan.get("plans"))
            )
            if has_cached_plan:
                try:
                    matches_by_item = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
                    _plans_validate_or_raise(plan=quant_plan, bcca_matches_by_item=matches_by_item, bcca_meta_by_code=bcca_meta_by_code)
                except Exception:
                    has_cached_plan = False
            if not has_cached_plan:
                quant_plan = await generate_v4_quant_plan(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    dimension=dim,
                    worklist_dim=worklist_dim,
                    bcca_matches=bcca_matches,
                    floorplan_available=floorplan_available,
                    room_has_photos=room_has_photos,
                    call_gemini=call_gemini,
                    bcca_meta_by_code=bcca_meta_by_code,
                    listing_sqm=listing_sqm,
                )
                await db.save_unified_estimate(listing_id, pkg_plan, quant_plan)

            # Collect required signals per room.
            requests_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}

            def _collect_signal_ids(node: Dict[str, Any]) -> List[str]:
                out: List[str] = []
                op = node.get("op")
                if op == "SIGNAL":
                    sid = str(node.get("signal_id") or "").strip()
                    if sid:
                        out.append(sid)
                    return out
                arg = node.get("arg")
                if isinstance(arg, dict):
                    out.extend(_collect_signal_ids(arg))
                args = node.get("args")
                if isinstance(args, list):
                    for a in args:
                        if isinstance(a, dict):
                            out.extend(_collect_signal_ids(a))
                return out

            def _infer_unit_family_from_signal_id(signal_id: str) -> str:
                sid = signal_id.strip().lower()
                for suf, uf in (("_m2", "m2"), ("_ml", "ml"), ("_ud", "ud"), ("_m3", "m3")):
                    if sid.endswith(suf):
                        return uf
                raise RuntimeError(f"v4_tail_from_v5: signal_id missing unit suffix | signal_id={signal_id}")

            matches_by_item = {m.get("work_item_id"): m for m in bcca_matches if isinstance(m, dict) and m.get("work_item_id")}
            for p in quant_plan.get("plans") or []:
                if not isinstance(p, dict):
                    continue
                wid = str(p.get("work_item_id") or "").strip()
                match = matches_by_item.get(wid)
                rid = str((match or {}).get("room_id") or "").strip()
                if not rid:
                    continue
                formula = p.get("formula_ast")
                if not isinstance(formula, dict):
                    continue
                for sid in sorted(set(_collect_signal_ids(formula))):
                    requests_by_room.setdefault(rid, {})
                    requests_by_room[rid][sid] = {"signal_id": sid, "unit_family": _infer_unit_family_from_signal_id(sid)}

            return dim, {"bcca_matches": bcca_matches, "quant_plan": quant_plan, "requests_by_room": requests_by_room}

    prepared = await asyncio.gather(*[_prepare_dimension(dim) for dim in V2_DIMENSIONS])
    dim_payload_by_dim: Dict[str, Dict[str, Any]] = {}
    required_by_room: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for dim, payload in prepared:
        dim_payload_by_dim[dim] = payload
        for rid, reqs_by_id in (payload.get("requests_by_room") or {}).items():
            required_by_room.setdefault(rid, {})
            for sid, req in (reqs_by_id or {}).items():
                required_by_room[rid][sid] = req

    forage_semaphore = asyncio.Semaphore(forage_concurrency)
    room_locks: Dict[str, Any] = {}

    async def _forage_room_once(rid: str) -> None:
        async with forage_semaphore:
            if rid not in signals_store_by_room:
                signals_store_by_room[rid] = {}
            reqs_by_id = required_by_room.get(rid) or {}
            existing_ids = set(signals_store_by_room[rid].keys())
            want_ids = [sid for sid in reqs_by_id.keys() if sid not in existing_ids]
            if not want_ids:
                return
            room_locks.setdefault(rid, asyncio.Lock())
            async with room_locks[rid]:
                existing_ids2 = set(signals_store_by_room[rid].keys())
                want_ids2 = [sid for sid in reqs_by_id.keys() if sid not in existing_ids2]
                if not want_ids2:
                    return
                want_requests = [reqs_by_id[sid] for sid in want_ids2 if sid in reqs_by_id]
                measured = await forage_v4_signals_for_room(
                    listing_id=listing_id,
                    strategy_name=strategy_name,
                    room_id=rid,
                    measurement_requests=want_requests,
                    floorplan_available=floorplan_available,
                    listing_sqm=listing_sqm,
                    room_photo_urls=room_photos.get(rid) or [],
                    floorplan_urls=floorplan_urls,
                    smart_m2=smart_m2 or {"rooms": []},
                    call_gemini_json=call_gemini_json,
                    fetch_images_batch=fetch_images_batch,
                    allow_missing_smart_m2_room=True,
                )
                signals_store_by_room[rid].update(measured)
                await _checkpoint_signals(reason=f"room_forage_update room_id={rid} new_signals={len(measured)}")

    await asyncio.gather(*[_forage_room_once(rid) for rid in sorted(required_by_room.keys())])

    # --------------------------------------------------------------------
    # Zero rescue pass (Pro + photos): resolve any remaining value=0 signals
    # --------------------------------------------------------------------
    signal_work_items_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for dim in V2_DIMENSIONS:
        payload = dim_payload_by_dim.get(dim) or {}
        bcca_matches = payload.get("bcca_matches") or []
        quant_plan = payload.get("quant_plan") or {}
        matches_by_item = {
            str(m.get("work_item_id")): m
            for m in (bcca_matches or [])
            if isinstance(m, dict) and str(m.get("work_item_id") or "").strip()
        }
        for p in (quant_plan.get("plans") or []):
            if not isinstance(p, dict):
                continue
            wid = str(p.get("work_item_id") or "").strip()
            match = matches_by_item.get(wid) or {}
            rid = str(match.get("room_id") or "").strip()
            if not rid:
                continue
            f = p.get("formula_ast") or {}
            if not isinstance(f, dict) or str(f.get("op") or "").strip() != "SIGNAL":
                continue
            sid = str(f.get("signal_id") or "").strip()
            if not sid:
                continue
            key = (rid, sid)
            signal_work_items_map.setdefault(key, []).append(
                {
                    "work_item_id": wid,
                    "work_description": str(match.get("work_description") or "").strip(),
                    "bcca_desc_100": str(match.get("bcca_desc_100") or "").strip(),
                }
            )

    async def _zero_rescue_room(rid: str) -> None:
        async with forage_semaphore:
            room_sigs = signals_store_by_room.get(rid) or {}
            reqs_by_id = required_by_room.get(rid) or {}
            if not reqs_by_id:
                return
            zero_sids = []
            for sid in reqs_by_id.keys():
                sig = room_sigs.get(sid)
                try:
                    v = float((sig or {}).get("value") or 0)
                except Exception:
                    v = 0.0
                if v == 0.0:
                    zero_sids.append(sid)
            if not zero_sids:
                return

            room_urls = room_photos.get(rid) or []
            if not room_urls:
                logger.warning("v4_tail_from_v5: zero_rescue skip (no photos) | room_id=%s", rid)
                return

            zero_signals_with_context: List[Dict[str, Any]] = []
            for sid in sorted(set(zero_sids)):
                work_items_ctx = signal_work_items_map.get((rid, sid)) or []
                zero_signals_with_context.append(
                    {
                        "signal_id": sid,
                        "unit_family": (
                            str((reqs_by_id.get(sid) or {}).get("unit_family") or "").strip()
                            or ("m2" if sid.endswith("_m2") else "ml" if sid.endswith("_ml") else "ud" if sid.endswith("_ud") else "m3" if sid.endswith("_m3") else "m2")
                        ),
                        "work_items": work_items_ctx,
                    }
                )

            nonzero_signals = [
                {
                    "signal_id": s.get("signal_id"),
                    "unit_family": s.get("unit_family"),
                    "value": s.get("value"),
                    "confidence": s.get("confidence"),
                }
                for s in room_sigs.values()
                if isinstance(s, dict) and _safe_float(s.get("value")) is not None and float(s.get("value")) > 0
            ]

            resolved = await resolve_zero_signals_for_room(
                listing_id=listing_id,
                strategy_name=strategy_name,
                room_id=rid,
                zero_signals_with_context=zero_signals_with_context,
                nonzero_signals=nonzero_signals,
                floorplan_available=floorplan_available,
                listing_sqm=listing_sqm,
                room_estimated_m2=None,
                room_photo_urls=room_urls,
                floorplan_urls=floorplan_urls,
                call_gemini_json=call_gemini_json,
                fetch_images_batch=fetch_images_batch,
            )
            if not isinstance(resolved, dict) or not resolved:
                return
            updated = 0
            for sid, sig in resolved.items():
                try:
                    v = float((sig or {}).get("value") or 0)
                except Exception:
                    v = 0.0
                if v > 0:
                    signals_store_by_room.setdefault(rid, {})[sid] = sig
                    updated += 1
            if updated:
                await _checkpoint_signals(reason=f"zero_rescue room_id={rid} updated={updated}")

    await asyncio.gather(*[_zero_rescue_room(rid) for rid in sorted(required_by_room.keys())])

    async def _assemble_dimension(dim: str) -> Tuple[str, int]:
        async with semaphore:
            payload = dim_payload_by_dim.get(dim) or {}
            bcca_matches = payload.get("bcca_matches") or []
            quant_plan = payload.get("quant_plan") or {}
            saved = await assemble_v4_boq(
                listing_id=listing_id,
                strategy_name=strategy_name,
                dimension=dim,
                bcca_matches=bcca_matches,
                quant_plan=quant_plan,
                signals_by_room=signals_store_by_room,
                db=db,
                listing_sqm=listing_sqm,
            )
            await _checkpoint_signals(reason=f"dimension_complete dim={dim}")
            return dim, int(saved)

    assembled = await asyncio.gather(*[_assemble_dimension(dim) for dim in V2_DIMENSIONS])
    total_saved = 0
    for dim, saved in assembled:
        total_saved += int(saved)
        summary["dimensions"][dim] = {"saved_boq_items": int(saved)}

    await _checkpoint_signals(reason="final")
    summary["saved_boq_items_total"] = total_saved
    await db.save_unified_estimate(listing_id, f"v4_run_summary_{strategy_name}", summary)
    return summary

