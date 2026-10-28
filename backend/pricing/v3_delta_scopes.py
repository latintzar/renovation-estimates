import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas.gemini_schemas_v2 import V2_DIMENSIONS
from .schemas.gemini_schemas_v3 import V3_BCCA_WORKLIST_SCHEMA, V3_STRATEGY_SPEC_SCHEMA
from .takeoff_menu import build_takeoff_menu

try:
    from ..pipeline.gemini_client import call_gemini
except ImportError:
    import sys
    from pathlib import Path as _Path
    backend_dir = _Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from pipeline.gemini_client import call_gemini

logger = logging.getLogger(__name__)

_CONTEXT_CACHE: Dict[str, str] | None = None


def _load_text(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"v3_delta_scopes: missing {label} | path={path}")
    return path.read_text(encoding="utf-8")


def _get_context_bundle() -> Dict[str, str]:
    global _CONTEXT_CACHE
    if _CONTEXT_CACHE is not None:
        return _CONTEXT_CACHE

    # NOTE: This module lives in `backend/pricing/`. Context files live in `backend/pricing/data/`.
    backend_dir = Path(__file__).resolve().parents[1]
    pricing_dir = backend_dir / "pricing"
    vocab_path = pricing_dir / "data" / "bcca_vocabulary.yaml"

    # kg_context.yaml currently lives at `backend/pricing/kg_context.yaml` (not under data/).
    kg_path = pricing_dir / "kg_context.yaml"

    _CONTEXT_CACHE = {
        "bcca_vocab": _load_text(vocab_path, "bcca_vocabulary.yaml"),
        "knowledge_graph": _load_text(kg_path, "kg_context.yaml"),
    }
    logger.info(f"v3_delta_scopes: loaded context bundle | keys={list(_CONTEXT_CACHE.keys())}")
    return _CONTEXT_CACHE


def _format_room_ledger(room: Dict[str, Any]) -> str:
    room_id = room.get("room_id") or room.get("cluster_id") or "unknown"
    wall_segments = [ws.get("wall_id") for ws in room.get("wall_segments") or [] if isinstance(ws, dict)]
    openings = [
        f"{o.get('opening_id')}:{o.get('opening_type')}"
        for o in room.get("openings") or []
        if isinstance(o, dict) and o.get("opening_id")
    ]
    features = [
        f"{f.get('feature_id')}:{f.get('feature_type')}"
        for f in room.get("features") or []
        if isinstance(f, dict) and f.get("feature_id")
    ]

    return "\n".join(
        [
            f"- room_id: {room_id}",
            f"  wall_segments: {', '.join([w for w in wall_segments if w]) or 'none'}",
            f"  openings: {', '.join(openings) or 'none'}",
            f"  features: {', '.join(features) or 'none'}",
        ]
    )


def _format_dimension_rooms(rooms: List[Dict[str, Any]], dimension: str) -> str:
    lines: List[str] = []
    for room in rooms:
        room_id = room.get("room_id") or room.get("cluster_id") or "unknown"
        room_name = room.get("room_name") or room_id
        dim_data = (room.get("dimensions") or {}).get(dimension) or {}
        narrative = dim_data.get("narrative") or ""
        lines.append(f"[{room_name}] room_id={room_id}")
        if narrative:
            lines.append(f"  narrative: {narrative}")
        for key, value in dim_data.items():
            if key == "narrative" or value in (None, "", [], {}):
                continue
            lines.append(f"  {key}: {value}")
        lines.append("")
    return "\n".join(lines).strip()


def _summarize_prior_dimensions_for_prompt(prior_by_dim: Dict[str, Dict[str, Any]]) -> str:
    """
    Build a compact, deterministic "commitments" summary from already-generated dimensions.
    WHY THIS MATTERS: Later dimensions must not contradict earlier demolition/keep decisions.
    """
    if not prior_by_dim:
        return ""

    # Summarize per room, per dimension with short bullets derived from the already-written paragraphs.
    by_room: Dict[str, List[str]] = {}
    for dim, payload in prior_by_dim.items():
        for rb in (payload.get("room_blocks") or []):
            if not isinstance(rb, dict):
                continue
            room_id = str(rb.get("room_id") or "").strip()
            if not room_id:
                continue
            ss = (rb.get("specification_strategy") or {}) if isinstance(rb.get("specification_strategy"), dict) else {}
            t = str(ss.get("transformation") or "").strip()
            h = str(ss.get("hygiene_baseline") or "").strip()

            # Extract the first sentence-ish chunk as a commitment headline.
            def _head(text: str) -> str:
                if not text:
                    return ""
                for sep in (". ", ".\n", "\n"):
                    if sep in text:
                        return text.split(sep, 1)[0].strip() + "."
                return (text[:180].rstrip() + "...") if len(text) > 180 else text

            head = _head(t) or _head(h)
            if not head:
                continue

            by_room.setdefault(room_id, []).append(f"- [{dim}] {head}")

    # Render stable order
    lines: List[str] = []
    for room_id in sorted(by_room.keys()):
        lines.append(f"[{room_id}]")
        lines.extend(by_room[room_id][:6])  # cap to keep prompt bounded
        lines.append("")
    return "\n".join(lines).strip()


def _build_strategy_spec_prompt(
    *,
    target_pir: Dict[str, Any],
    reference_pir: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
    strategy_rationale: str,
    dimension: str,
    prior_dimension_summaries: str = "",
) -> str:
    context = _get_context_bundle()
    target_rooms = target_pir.get("rooms") or []
    reference_rooms = reference_pir.get("rooms") or []
    # IMPORTANT: For downstream worklist generation we can only price rooms present in Smart M2 / TAKEOFF_MENU.
    # So the StrategySpec must use Smart M2 room_ids as the canonical list to avoid un-priceable rooms.
    smart_m2_rooms = [r for r in (smart_m2.get("rooms") or []) if isinstance(r, dict)]
    room_ids = [r.get("room_id") or r.get("cluster_id") for r in smart_m2_rooms if isinstance(r, dict)]
    room_ids = [str(rid).strip() for rid in room_ids if rid]
    canonical_room_ids = "\n".join([f"- {rid}" for rid in room_ids])

    ledger_lines = [_format_room_ledger(r) for r in smart_m2.get("rooms") or [] if isinstance(r, dict)]
    ledger_text = "\n".join(ledger_lines)

    target_dim = _format_dimension_rooms(target_rooms, dimension)
    reference_dim = _format_dimension_rooms(reference_rooms, dimension)

    return f"""
You are a senior architect with project management experience and a strong background in residential renovation. You trained under a quantity surveyor early in your career, so you understand how scope narratives translate into priced line items.

OUTPUT LENGTH REQUIREMENT (critical):
- Each room's TRANSFORMATION field must be 400–800 words (a full page of sequential instructions).
- Each room's HYGIENE_BASELINE field must be 100–200 words.
- Short summaries fail this task. Write exhaustively.

WHY THIS MATTERS for this task:
- The buyer will judge credibility based on how concrete, comprehensive, and well-sequenced your narrative is.
- Generic “paint + tidy” summaries destroy trust. We need a believable story of the work.
- Your narrative must be auditable: anchor concrete mentions to IndoorGML-lite IDs.

YOUR TASK (StrategySpec — comprehensive narrator + anchored):
For the STRATEGY × DIMENSION below, output room_blocks[] for every room in Smart M2 (these are the only rooms we can price downstream).

CANONICAL ROOM IDS (use ONLY these exact strings, and include ALL of them):
{canonical_room_ids}

Hard rules:
- Use the exact room_id values provided.
- Use IndoorGML-lite references: ROOM(room_id), WALL(room_id, wall_id), OPENING(opening_id), FEATURE(feature_id).
- Provide TWO paragraphs per room: TRANSFORMATION and HYGIENE_BASELINE.
- Write as pure narrative. Do not create identifiers like TASK_* or any other artificial IDs.

OUTPUT REQUIREMENT (tone + structure):
- Start with a short, human-friendly dimension preface field: dimension_intro (2–4 sentences).
  It should read like: “Here’s what we’re doing for X and why it matters…”
  WHY THIS MATTERS: This is what a buyer reads first; it must be clear and non-robotic.

Narrative expectations (this is the core of the task):
- Write like a narrator briefing a contractor + a skeptical buyer: concrete, specific, and complete.
- For each room, tell the *story of the work* in a plausible sequence:
  - protection/prep → (selective) demolition/removals (if any) → rough-in/repairs → finishes → fittings → cleanup → final snagging.
- Include “invisible” but necessary process work where it would realistically occur (masking, dust control, rubbish handling, making-good).
- Tie actions to what you observe or infer from TARGET/REFERENCE narratives. If something is uncertain, say what you’d check onsite.
- Avoid invented quantities/costs; this is scope/story, not pricing.
- Ensure your story covers the full lifecycle phases for each room, when relevant:
  - Inspection & assumptions (what you'd verify onsite)
  - Pre-construction (protections, access, isolation, setup)
  - Demolition & removals (only if justified; include waste handling)
  - Construction/repairs/installs (the actual works, dependencies)
  - Finishes (making good, paint/tiling/trim)
  - Post-construction / closeout (cleanup, snagging, tests, handover)
- Cross-dimension consistency is critical:
  - If earlier dimensions committed to “keep existing tiles”, do NOT later propose “full demolition of tiles”.
  - If earlier dimensions require demolition, later finishes must reflect the new substrate, not “clean existing”.

CHAIN OF EXECUTION (the heart of this task):
Your narrative is a method statement. It describes the sequence of physical actions a contractor performs, in chronological order, from arrival to handover.

A good transformation paragraph:
- Reads like instructions to a junior site manager who will execute exactly what you write
- Follows strict chronological order: protection → demolition → substrate prep → installation → making-good → cleanup → snagging
- Names every distinct trade operation (each sentence becomes a priced line item downstream)
- References specific elements using IndoorGML-lite IDs (WALL, OPENING, FEATURE)
- Mentions material choices, fixing methods, curing/drying times, and sequencing dependencies
- Includes the invisible work that gets forgotten: dust sheets, masking tape, waste bagging, skip disposal, final vacuum

WHY THIS LEVEL OF DETAIL MATTERS:
The next step in the pipeline is a worklist generator that will price every operation you mention. Operations you omit will be missing from the final quote. A buyer who later discovers unpriced prep work loses trust. Your job is to leave nothing out.

LENGTH GUIDANCE:
- TRANSFORMATION: 400–800 words per room (a full paragraph of sequential instructions)
- HYGIENE_BASELINE: 100–200 words per room (lighter touch, still sequential)

STRATEGY:
- name: {strategy_name}
- rationale: {strategy_rationale}

DIMENSION: {dimension}

PRIOR DIMENSION COMMITMENTS (for consistency; do not contradict):
{prior_dimension_summaries or "(none yet)"}

TARGET ROOMS (dimension narrative):
{target_dim or "(no dimension narrative provided)"}

REFERENCE ROOMS (dimension narrative):
{reference_dim or "(no reference dimension narrative provided)"}

INDOORGML-LITE LEDGER (IDs you must reference):
{ledger_text or "(no ledger entries found)"}

WHY THIS MATTERS for context:
- The BCCA worklist will select quantities ONLY from Smart M2 references; do not invent numbers.
- When you mention a wall/opening/feature, the worklist must map it to those IDs.

RENOVATION KNOWLEDGE GRAPH (use for reasoning; do not copy verbatim):
WHY YOU HAVE THIS:
- It’s a completeness and sequencing guide. It hints at what usually accompanies what.
- It prevents “context drift” and missing obvious dependencies (e.g., if you touch electrics, what making-good follows?).

How to use it (think like a senior):
- For each room, ask: what has to happen first, and what must be protected?
- For each intervention you propose, ask: what prep/demolition/cleanup does it imply?
- For each visible condition (age, damp risk, cracked finishes), ask: what’s the minimum credible scope to reach the strategy goal?

{context["knowledge_graph"]}

Output room_blocks for all rooms: {", ".join([str(r) for r in room_ids if r])}
""".strip()


def _get_bcca_examples_for_dimension(dimension: str) -> str:
    """
    Return 5 representative BCCA item descriptions for the given dimension.
    WHY THIS MATTERS: These examples teach the LLM the right level of granularity.
    BCCA items are composite (include transport, cleanup, etc.) - not micro-tasks.
    """
    examples = {
        "shell_preparation": """
- Demolición de partición interior de tabique, con medios manuales, incluso revestimientos, desmontado de cerco, p.p. de instalaciones, alicatados, carga y transporte a vertedero.
- Picado de paramentos alicatados incluso carga y transporte de material sobrante a vertedero.
- Enfoscado sin maestrear, fratasado, con mortero de cemento M10 (1:4), en paramentos verticales.
- Guarnecido maestreado con yeso negro y enlucido con yeso blanco en paramentos verticales.
- Reparación de fisuras en paramentos de yeso mediante sellado con masilla acrílica flexible.""",

        "apertures_enclosure": """
- Ventana de aluminio lacado de hojas correderas, incluso precerco, herrajes de colgar y seguridad, y sellado de juntas con masilla elástica.
- Puerta de paso ciega de tablero aglomerado, incluso precerco de pino, galces, tapajuntas, herrajes de colgar y cierre.
- Persiana enrollable de PVC con cajón monoblock, incluso accesorios, cinta y recogedor.
- Sustitución de acristalamiento simple por doble acristalamiento 4/12/4 con cámara de aire.
- Sellado perimetral de carpintería con silicona neutra, previa limpieza del soporte.""",

        "systems_services": """
- Punto de luz sencillo instalado con cable de cobre de 1,5 mm2, incluso mecanismo, caja y parte proporcional de línea.
- Toma de corriente de 16A instalada con cable de cobre de 2,5 mm2, incluso mecanismo, caja empotrada y p.p. de línea.
- Canalización eléctrica de superficie con tubo rígido de PVC, incluso cajas de derivación y p.p. de accesorios.
- Tubería de polibutileno para agua fría/caliente, incluso p.p. de accesorios, pruebas y ayudas de albañilería.
- Instalación de termo eléctrico, incluso conexiones hidráulicas y eléctricas, válvulas y p.p. de pequeño material.""",

        "surface_finishes": """
- Solado de baldosa cerámica de gres porcelánico, recibido con mortero de cemento, incluso rejuntado y limpieza.
- Alicatado con azulejo cerámico recibido con mortero de cemento, incluso cortes, ingletes, rejuntado y limpieza.
- Pintura plástica lisa mate, dos manos, sobre paramentos verticales y horizontales interiores previamente preparados.
- Rodapié de gres porcelánico, recibido con mortero de cemento, incluso rejuntado y limpieza.
- Pulido y abrillantado de pavimento de terrazo, incluso tratamiento hidrofugante de acabado.""",

        "fixed_joinery_equipment": """
- Mueble bajo de cocina de tablero melamínico, incluso herrajes, tiradores, zócalo y p.p. de remates.
- Mueble alto de cocina de tablero melamínico, incluso herrajes, tiradores y p.p. de remates.
- Encimera de piedra natural o artificial, incluso corte de hueco para fregadero y pulido de cantos.
- Frente de armario empotrado de hojas correderas, incluso guías, herrajes y tiradores.
- Plato de ducha acrílico con válvula de desagüe, incluso sellado perimetral con silicona.""",

        "details_fittings": """
- Inodoro de tanque bajo de porcelana vitrificada, incluso asiento, tapa, mecanismos, llave de paso y conexión.
- Lavabo de porcelana vitrificada con pedestal, incluso grifería monomando, válvula, sifón y conexiones.
- Grifería monomando para fregadero, incluso llaves de paso, latiguillos flexibles y conexión.
- Interruptor o conmutador de superficie, incluso caja, bornas de conexión y pequeño material.
- Aplique de pared con lámpara LED, incluso elementos de fijación y conexión.""",
    }
    return examples.get(dimension, "")


def _build_bcca_worklist_prompt(
    *,
    strategy_spec: Dict[str, Any],
    takeoff_menu: Dict[str, Any],
    strategy_name: str,
    dimension: str,
) -> str:
    menu_rooms = takeoff_menu.get("rooms") or {}

    menu_lines = []
    for room_id, room_menu in menu_rooms.items():
        menu_lines.append(f"[{room_id}]")
        for key in ("surfaces", "details", "openings", "features", "waste"):
            refs = room_menu.get(key) or []
            if refs:
                menu_lines.append(f"  {key}: {', '.join(refs)}")
        menu_lines.append("")
    menu_text = "\n".join(menu_lines).strip()

    valid_room_ids = ", ".join([str(rid) for rid in sorted(menu_rooms.keys())])
    # NOTE: For worklist generation, we intentionally do NOT include the huge renovation knowledge graph.
    # The StrategySpec step already used it to decide WHAT work is needed. Here we only "unpack" into
    # BCCA descriptions + deterministic quantity_ref selections.
    context = _get_context_bundle()
    bcca_examples = _get_bcca_examples_for_dimension(dimension)

    return f"""
You are a senior quantity surveyor unpacking a StrategySpec into BCCA worklist items.

WHY THIS MATTERS for this task:
- Downstream BOQ generation is deterministic. If you invent quantities, the run fails.
- Your output must be pure selection from TAKEOFF_MENU — no arithmetic, no new strings.

WHAT “GOOD” LOOKS LIKE (systematic translation, not summarization):
- Treat the StrategySpec as the authoritative scope narrative.
- Your job is to translate that narrative into a complete set of BCCA-style work packages measured with TAKEOFF_MENU refs.
- Work in a methodical sweep:
  - For each room_id in the StrategySpec, read transformation + hygiene_baseline and identify distinct scopes by trade:
    demolition/removal, substrate prep, install/replace, finish/paint/tile, seals, MEP, disposal.
  - For each scope you identify, emit at least one worklist_item with:
    - a short BCCA noun phrase (bcca_description)
    - a unit (m2/ml/ud/m3)
    - one or more rooms[] entries with exact room_id + an exact quantity_ref from that room’s TAKEOFF_MENU.
- Group rooms when the SAME work applies across them, but never “drop” a room’s scope: grouping should preserve completeness.

INPUT: StrategySpec (already decided the scope; you must implement it without adding/removing work)
{json.dumps(strategy_spec, ensure_ascii=False, indent=2)}

TAKEOFF_MENU (per room; choose exact quantity_ref strings ONLY):
{menu_text or "(empty TAKEOFF_MENU)"}

RULES:
- Output worklist_items[] (item-centric), where each worklist_item can cover ONE or MANY rooms.
- CRITICAL: room_id MUST be EXACTLY one of these IDs (no renaming, no slashes, no accents): {valid_room_ids}
- Each worklist_item MUST include:
  bcca_description, unit, rooms[]
- Each rooms[] entry MUST include:
  room_id, quantity_ref
- quantity_ref MUST be an EXACT string from TAKEOFF_MENU for that room.
- Units must match the quantity_ref family (m2/ml/ud/m3).
- If you need disposal and the menu has WASTE_M3(...), pick one rule_id; otherwise omit disposal items.
- BCCA VOCABULARY ADHERENCE (HARD REQUIREMENT):
  - bcca_description must be written in a constrained BCCA lexicon:
    - Use only terms that appear in BCCA VOCABULARY below, plus Spanish glue words needed for grammar:
      "de", "del", "y", "en", "con", "para", "por", "al", "a".
    - Choose the closest BCCA phrasing even if the StrategySpec wording is more colorful.
    - The output should read like the BCCA index: compact work packages that already “include” accessories, transporte, limpieza, etc.
  - Do NOT invent synonyms. If a concept isn't covered, choose the closest BCCA VOCABULARY phrasing instead.
  - Avoid vague words (e.g., "tratamiento", "revisión", "ajuste") unless they are present in BCCA VOCABULARY.
  - Return ONLY the JSON object (no commentary, no markdown, no extra keys).
- GROUPING:
  - If the SAME work applies to multiple rooms, make ONE worklist_item and list all affected rooms in rooms[].
  - A good example is painting walls: one item, rooms=[{{room_id, WALL_NET_M2(room)}}...]
- IMPORTANT: It is OK for TWO DIFFERENT works in the SAME room to use the SAME quantity_ref
  (e.g., "preparación de paramento" and "pintura" can both use WALL_NET_M2(room)).
  This is NOT duplication; it's pricing multiple trades measured off the same geometry.
- KEEP OUTPUT SMALL:
  - bcca_description must be short (Spanish noun phrase, no explanations, ~<80 chars).
  - Prefer fewer, higher-quality items over many micro-items. Each item should be a BCCA-style work package.

BCCA ITEM EXAMPLES FOR THIS DIMENSION ({dimension}):
These show the right level of granularity. Notice how each item is a complete work package
(includes transport, cleanup, accessories, etc.) — never micro-tasks like "grease cleaning" or "vacuum floor".
{bcca_examples}

BCCA VOCABULARY (use Spanish BCCA terms):
{context["bcca_vocab"]}
""".strip()


async def _call_strategy_spec(
    *,
    target_pir: Dict[str, Any],
    reference_pir: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
    strategy_rationale: str,
    dimension: str,
    prior_dimension_summaries: str = "",
) -> Dict[str, Any]:
    prompt = _build_strategy_spec_prompt(
        target_pir=target_pir,
        reference_pir=reference_pir,
        smart_m2=smart_m2,
        strategy_name=strategy_name,
        strategy_rationale=strategy_rationale,
        dimension=dimension,
        prior_dimension_summaries=prior_dimension_summaries,
    )
    response = await call_gemini(
        prompt=prompt,
        model="flash",
        temperature=0.4,
        max_tokens=65536,
        response_schema=V3_STRATEGY_SPEC_SCHEMA,
        use_spanish=True,
    )
    if not response.success:
        raise RuntimeError(f"v3_strategy_spec failed | strategy={strategy_name} dimension={dimension} | {response.error}")
    data = json.loads(response.text)
    data["dimension"] = dimension

    # Fail loud & fast if the model used non-canonical room_ids (breaks TAKEOFF_MENU mapping downstream).
    smart_rooms = [r for r in (smart_m2.get("rooms") or []) if isinstance(r, dict)]
    allowed_room_ids = {
        str(r.get("room_id") or r.get("cluster_id")).strip()
        for r in smart_rooms
        if (r.get("room_id") or r.get("cluster_id"))
    }
    if not allowed_room_ids:
        raise RuntimeError("v3_strategy_spec: Smart M2 has no rooms; cannot validate room_ids")

    seen_room_ids: List[str] = []
    bad_room_ids: List[str] = []
    for rb in (data.get("room_blocks") or []):
        if not isinstance(rb, dict):
            continue
        rid = str(rb.get("room_id") or "").strip()
        if not rid:
            continue
        seen_room_ids.append(rid)
        if rid not in allowed_room_ids:
            bad_room_ids.append(rid)

    missing_room_ids = sorted([rid for rid in allowed_room_ids if rid not in set(seen_room_ids)])
    if bad_room_ids or missing_room_ids:
        raise RuntimeError(
            "v3_strategy_spec: invalid room_ids in model output (must match Smart M2 exactly) "
            f"| strategy={strategy_name} | dim={dimension} | bad_room_ids={sorted(set(bad_room_ids))} "
            f"| missing_room_ids={missing_room_ids} | allowed_room_ids={sorted(allowed_room_ids)}"
        )

    return data


async def _call_bcca_worklist(
    *,
    strategy_spec: Dict[str, Any],
    takeoff_menu: Dict[str, Any],
    strategy_name: str,
    dimension: str,
) -> Dict[str, Any]:
    prompt = _build_bcca_worklist_prompt(
        strategy_spec=strategy_spec,
        takeoff_menu=takeoff_menu,
        strategy_name=strategy_name,
        dimension=dimension,
    )
    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=65536,
        response_schema=V3_BCCA_WORKLIST_SCHEMA,
        use_spanish=True,
    )
    if not response.success:
        raise RuntimeError(f"v3_bcca_worklist failed | strategy={strategy_name} dimension={dimension} | {response.error}")
    data = json.loads(response.text)
    data["dimension"] = dimension
    return data


async def generate_bcca_worklist_for_strategy_incremental(
    *,
    strategy_spec: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
    on_dimension: Any = None,
) -> Dict[str, Any]:
    """
    Incremental worklist generator.

    WHY THIS MATTERS:
    - `validate_pipeline_listing.py` is often run in foreground timeout slices.
    - If we only save at the very end, the run never converges and we repeatedly pay for the same LLM calls.

    `on_dimension` (optional) is called after each dimension completes:
      await on_dimension(dimension: str, payload: Dict[str, Any], takeoff_menu: Dict[str, Any])
    """
    if not strategy_spec:
        raise RuntimeError("v3_bcca_worklist: missing strategy_spec")
    if not smart_m2:
        raise RuntimeError("v3_bcca_worklist: missing smart_m2")

    takeoff_menu = build_takeoff_menu(smart_m2)
    dimensions = strategy_spec.get("dimensions") or {}
    if not dimensions:
        raise RuntimeError(f"v3_bcca_worklist: strategy_spec missing dimensions | strategy={strategy_name}")

    # Fail loud if StrategySpec includes room_ids that cannot be priced (not present in TAKEOFF_MENU)
    menu_room_ids = set((takeoff_menu.get("rooms") or {}).keys())
    if not menu_room_ids:
        raise RuntimeError("v3_bcca_worklist: TAKEOFF_MENU has no rooms")

    out: Dict[str, Dict[str, Any]] = {}
    for dim in V2_DIMENSIONS:
        if dim not in dimensions:
            raise RuntimeError(f"v3_bcca_worklist: missing dimension {dim} in strategy_spec | strategy={strategy_name}")
        spec_room_ids = {
            str(rb.get("room_id")).strip()
            for rb in (dimensions[dim].get("room_blocks") or [])
            if isinstance(rb, dict) and rb.get("room_id")
        }
        unknown = sorted([rid for rid in spec_room_ids if rid not in menu_room_ids])
        if unknown:
            raise RuntimeError(
                "v3_bcca_worklist: StrategySpec contains un-priceable room_ids not in TAKEOFF_MENU "
                f"| strategy={strategy_name} | dim={dim} | unknown_room_ids={unknown} | menu_room_ids={sorted(menu_room_ids)}"
            )
        payload = await _call_bcca_worklist(
            strategy_spec=dimensions[dim],
            takeoff_menu=takeoff_menu,
            strategy_name=strategy_name,
            dimension=dim,
        )
        out[dim] = payload
        if on_dimension is not None:
            await on_dimension(dim, payload, takeoff_menu)

    return {"strategy_name": strategy_name, "dimensions": out, "takeoff_menu": takeoff_menu}


async def generate_strategy_spec_for_strategy(
    *,
    target_pir: Dict[str, Any],
    comparable_pir: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
    strategy_rationale: str,
) -> Dict[str, Any]:
    if not target_pir:
        raise RuntimeError("v3_strategy_spec: missing target_pir")
    if not comparable_pir:
        raise RuntimeError("v3_strategy_spec: missing comparable_pir")
    if not smart_m2:
        raise RuntimeError("v3_strategy_spec: missing smart_m2")

    return await generate_strategy_spec_for_strategy_incremental(
        target_pir=target_pir,
        comparable_pir=comparable_pir,
        smart_m2=smart_m2,
        strategy_name=strategy_name,
        strategy_rationale=strategy_rationale,
        on_dimension=None,
    )


async def generate_strategy_spec_for_strategy_incremental(
    *,
    target_pir: Dict[str, Any],
    comparable_pir: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
    strategy_rationale: str,
    existing_dimensions: Optional[Dict[str, Dict[str, Any]]] = None,
    on_dimension: Any = None,
) -> Dict[str, Any]:
    """
    Incremental StrategySpec generator (delta scopes).

    WHY THIS MATTERS:
    - Listing validation is often run in foreground timeout slices.
    - StrategySpec generation is expensive (large knowledge graph context).
    - If we only save at the very end, partial runs lose all progress.

    `on_dimension` (optional) is called after each dimension completes:
      await on_dimension(dimension: str, payload: Dict[str, Any], partial_spec: Dict[str, Any])
    """
    if not target_pir:
        raise RuntimeError("v3_strategy_spec: missing target_pir")
    if not comparable_pir:
        raise RuntimeError("v3_strategy_spec: missing comparable_pir")
    if not smart_m2:
        raise RuntimeError("v3_strategy_spec: missing smart_m2")

    # Generate dimensions sequentially so later dimensions can reference earlier commitments.
    # If we have partial progress saved, resume from it to reduce repeated token spend.
    out: Dict[str, Dict[str, Any]] = {}
    if existing_dimensions:
        if not isinstance(existing_dimensions, dict):
            raise RuntimeError("v3_strategy_spec: existing_dimensions must be a dict")
        for k, v in existing_dimensions.items():
            if isinstance(k, str) and isinstance(v, dict):
                out[k] = v

    for dim in V2_DIMENSIONS:
        if dim in out:
            continue
        prior_summary = _summarize_prior_dimensions_for_prompt(out)
        payload = await _call_strategy_spec(
            target_pir=target_pir,
            reference_pir=comparable_pir,
            smart_m2=smart_m2,
            strategy_name=strategy_name,
            strategy_rationale=strategy_rationale,
            dimension=dim,
            prior_dimension_summaries=prior_summary,
        )
        out[dim] = payload

        if on_dimension is not None:
            partial_spec = {"strategy_name": strategy_name, "strategy_rationale": strategy_rationale, "dimensions": dict(out)}
            await on_dimension(dim, payload, partial_spec)

    return {"strategy_name": strategy_name, "strategy_rationale": strategy_rationale, "dimensions": out}


async def generate_bcca_worklist_for_strategy(
    *,
    strategy_spec: Dict[str, Any],
    smart_m2: Dict[str, Any],
    strategy_name: str,
) -> Dict[str, Any]:
    if not strategy_spec:
        raise RuntimeError("v3_bcca_worklist: missing strategy_spec")
    if not smart_m2:
        raise RuntimeError("v3_bcca_worklist: missing smart_m2")

    # Keep this API, but implement via incremental generator for better checkpointing behavior.
    return await generate_bcca_worklist_for_strategy_incremental(
        strategy_spec=strategy_spec,
        smart_m2=smart_m2,
        strategy_name=strategy_name,
    )
