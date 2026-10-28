"""
V5 Architect Report — professional renovation brief for the frontend modal
=========================================================================

Produces the full `analysis` object that ArchitectReportModal.tsx expects.
The data splits into two halves:

1. COMPUTED — assembled from existing V5 artifacts with zero LLM cost:
   - target_pir_summary (from listing metadata + target PIR)
   - line_items (from BOQ)
   - cost_breakdown (from BOQ aggregation: PEM + 13% overhead + 6% profit + 21% IVA)
   - comparables (from listing_comparables)
   - core financials (asking_price, renovation_cost, etc.)

2. LLM-GENERATED — one Gemini Pro call with KB context:
   - design_concept (overall vision, room concepts, why-not, preserved elements)
   - timeline_breakdown (phased construction plan)
   - energy_compliance (target from comparable rating, grounded in energy_knowledge.json)
   - risk_flags — THE STAR: grounded in rules_engine.json year-triggered rules +
     energy_knowledge.json climate zones + renovation_process_knowledge.json
   - recommendations, compliance_notes, confidence_score

Knowledge bases injected into prompt:
   - rules_engine.json: year-triggered rules (electrical, plumbing, windows, etc.)
   - energy_knowledge.json: rating scale, climate zones, U-values
   - renovation_process_knowledge.json: CSCAE process steps

Input:  BOQ aggregation, listing, target PIR, comparables, delta slots
Output: v5_architect_report_market_standard (saved to unified_estimates)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Knowledge base paths ──────────────────────────────────────────────────────
_STANDARDS_DIR = Path(__file__).parent.parent.parent / "standards"
_RULES_ENGINE_PATH = _STANDARDS_DIR / "rules_engine.json"
_ENERGY_KB_PATH = _STANDARDS_DIR / "energy_knowledge.json"
_PROCESS_KB_PATH = _STANDARDS_DIR / "renovation_process_knowledge.json"

# Also check backend/pipeline for rules_engine
_RULES_ENGINE_FALLBACK = Path(__file__).parent.parent / "pipeline" / "rules_engine.json"


def _load_json_safe(path: Path) -> Dict[str, Any]:
    """Load a JSON file, return {} on any error."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load KB %s: %s", path, e)
    return {}


def _filter_rules_by_year(rules_engine: Dict[str, Any], year_built: int) -> str:
    """
    Pre-filter rules_engine.json rules that apply to this year of construction.
    Returns a human-readable text block for the prompt.

    A rule applies if: year_built < rule.year_trigger (the property predates the standard).
    Handles both dict-of-lists (pipeline format) and flat-list (standards format).
    """
    if not rules_engine or not year_built:
        return ""

    rules_section = rules_engine.get("rules", {})
    applicable: List[tuple] = []

    # Normalize to iterable of (category, rule) pairs
    rule_pairs: List[tuple] = []
    if isinstance(rules_section, dict):
        # Pipeline format: {"electrical": [...], "plumbing": [...], ...}
        for category, rules_list in rules_section.items():
            if isinstance(rules_list, list):
                for rule in rules_list:
                    if isinstance(rule, dict):
                        rule_pairs.append((category, rule))
    elif isinstance(rules_section, list):
        # Standards format: flat list of rule dicts
        for rule in rules_section:
            if isinstance(rule, dict):
                cat = str(rule.get("category") or rule.get("trade") or "general").lower()
                rule_pairs.append((cat, rule))

    for category, rule in rule_pairs:
        trigger = rule.get("year_trigger")
        if trigger is None:
            applicable.append((category, rule))
        elif isinstance(trigger, (int, float)) and year_built < int(trigger):
            applicable.append((category, rule))

    if not applicable:
        return ""

    lines = [f"REGLAS DE CONSTRUCCIÓN APLICABLES (año construcción: {year_built}):"]
    lines.append("Cada regla tiene un ID, normativa de referencia y aviso para el comprador.\n")
    for cat, rule in applicable:
        rid = rule.get("id", "?")
        name = rule.get("name", "?")
        urgency = rule.get("urgency", "?")
        regulation = rule.get("regulation") or "—"
        warning = rule.get("buyer_warning", "")
        remedial = rule.get("remedial_action", {})
        desc = remedial.get("description", "")
        lines.append(
            f"  [{rid}] {name} | urgencia: {urgency} | normativa: {regulation}\n"
            f"    Aviso: {warning}\n"
            f"    Acción: {desc}"
        )
    return "\n".join(lines)


def _build_energy_context(energy_kb: Dict[str, Any], city: str, comparable_energy: str) -> str:
    """
    Build energy context from the energy KB, including:
    - Climate zone for the city
    - Rating scale descriptions
    - Comparable's energy rating as the target reference
    """
    if not energy_kb:
        return ""

    # Find climate zone
    climate_zone = ""
    zones = energy_kb.get("climate_zones", {})
    city_lower = (city or "").lower()
    for zone_name, zone_data in zones.items():
        if not isinstance(zone_data, dict):
            continue
        cities = zone_data.get("cities", [])
        for c in cities:
            if city_lower in str(c).lower():
                climate_zone = zone_name
                break
        if climate_zone:
            break

    # Rating descriptions
    rating_scale = energy_kb.get("rating_scale", {})
    rating_lines = []
    for letter in ["A", "B", "C", "D", "E", "F", "G"]:
        info = rating_scale.get(letter, {})
        if info:
            rating_lines.append(f"  {letter}: {info.get('description', '')} | Típico: {info.get('typical_building', '')}")

    lines = ["CONOCIMIENTO ENERGÉTICO (energy_knowledge.json):"]
    if climate_zone:
        zone_info = zones.get(climate_zone, {})
        lines.append(f"  Zona climática: {climate_zone} (U-muro: {zone_info.get('u_wall', '?')}, U-ventana: {zone_info.get('u_window', '?')})")
    if comparable_energy:
        lines.append(f"  Rating energético del COMPARABLE vendido (referencia-objetivo): {comparable_energy}")
        lines.append(f"  NOTA: Este rating es del comparable, no de la propiedad actual. Úsalo como objetivo orientativo.")
    lines.append("\nEscala de ratings:")
    lines.extend(rating_lines)

    return "\n".join(lines)


def _get_comparable_energy_rating(comparables: List[Dict[str, Any]]) -> str:
    """Get the most common energy rating from comparables (mode)."""
    ratings: Dict[str, int] = {}
    for c in (comparables or []):
        if not isinstance(c, dict):
            continue
        rating = c.get("energy_rating") or c.get("energy_certificate")
        if rating and isinstance(rating, str) and rating.strip():
            r = rating.strip().upper()
            ratings[r] = ratings.get(r, 0) + 1
    if not ratings:
        return ""
    # Return the most common rating
    return max(ratings, key=ratings.get)  # type: ignore[arg-type]


def _build_target_pir_summary(
    listing: Dict[str, Any],
    target_pir: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute Section 1 from listing metadata + V5 target PIR."""
    sqm = float(listing.get("sqm") or listing.get("m2_built") or 0)
    summary: Dict[str, Any] = {
        "address": listing.get("title") or listing.get("address") or "",
        "asking_price": float(listing.get("price") or 0),
        "area_sqm": sqm,
        "bedrooms": listing.get("bedrooms"),
        "bathrooms": listing.get("bathrooms"),
        "year_built": listing.get("construction_year") or listing.get("year_built"),
        "energy_current": listing.get("energy_rating"),
    }

    # Derive condition summary + key observations from target PIR room narratives
    if target_pir and isinstance(target_pir, dict):
        rooms = target_pir.get("rooms") or []
        observations = []
        for room in rooms[:6]:  # Cap to avoid bloat
            if not isinstance(room, dict):
                continue
            narrs = room.get("slot_narratives") or {}
            if isinstance(narrs, dict):
                for _sid, narr in list(narrs.items())[:2]:
                    if isinstance(narr, str) and narr.strip() and len(narr) > 20:
                        observations.append(narr.strip()[:120])
        if observations:
            summary["key_observations"] = observations[:6]
            summary["condition_summary"] = observations[0] if observations else ""

    return {k: v for k, v in summary.items() if v is not None and v != "" and v != 0}


def _build_comparables(comparables_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format comparables for the frontend grid (max 4)."""
    out = []
    for c in (comparables_raw or [])[:4]:
        if not isinstance(c, dict):
            continue
        out.append({
            "id": c.get("casafari_property_id") or c.get("id"),
            "sale_price": float(c.get("sale_price") or 0),
            "price_per_sqm": float(c.get("price_per_sqm") or 0),
            "total_area": float(c.get("total_area") or 0),
            "living_area": float(c.get("living_area") or c.get("total_area") or 0),
            "bedrooms": c.get("bedrooms"),
            "bathrooms": c.get("bathrooms"),
            "condition": c.get("condition") or c.get("property_condition") or "",
            "address": c.get("address") or "",
            "photo_urls": (c.get("photo_urls") or [])[:4],
            "energy_rating": c.get("energy_rating"),
            "construction_year": c.get("construction_year"),
        })
    return out


def _build_cost_breakdown(boq_agg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute standard Spanish construction pricing from PEM."""
    pem = float(boq_agg.get("total_pem") or 0)
    overhead = pem * 0.13
    profit = pem * 0.06
    subtotal = pem + overhead + profit
    iva = subtotal * 0.21
    total = subtotal + iva
    return {
        "pem": round(pem, 2),
        "overhead": round(overhead, 2),
        "profit": round(profit, 2),
        "iva": round(iva, 2),
        "total": round(total, 2),
    }


async def generate_v5_architect_report(
    *,
    listing_id: int,
    strategy_name: str,
    boq_aggregation: Dict[str, Any],
    listing: Dict[str, Any],
    target_pir: Optional[Dict[str, Any]],
    comparables: Optional[List[Dict[str, Any]]],
    delta_slots: Optional[Dict[str, Any]],
    eli5: Optional[Dict[str, Any]],
    db: Any,
    call_gemini_json: Any,
) -> Dict[str, Any]:
    """
    Generate the full architect report matching ArchitectReportModal's `analysis` prop.

    Returns the report dict and saves it to unified_estimates.
    """
    line_items = boq_aggregation.get("line_items") or []
    if not line_items:
        raise RuntimeError(f"v5_architect_report: no line items | listing_id={listing_id}")

    total_pem = float(boq_aggregation.get("total_pem") or 0)
    grand_total = float(boq_aggregation.get("grand_total_with_iva") or 0)
    total_hours = float(boq_aggregation.get("total_labor_hours") or 0)
    estimated_weeks = int(boq_aggregation.get("estimated_weeks") or 0)
    sqm = float(listing.get("sqm") or listing.get("m2_built") or 0)
    asking_price = float(listing.get("price") or 0)

    # ── Computed sections (no LLM) ────────────────────────────────────────────
    target_pir_summary = _build_target_pir_summary(listing, target_pir)
    cost_breakdown = _build_cost_breakdown(boq_aggregation)
    comps = _build_comparables(comparables or [])

    # Room IDs and delta context for the prompt
    rooms_in_boq: Dict[str, List[Dict[str, Any]]] = {}
    for item in line_items:
        rid = str(item.get("room_id") or item.get("room_name") or "general").strip()
        rooms_in_boq.setdefault(rid, []).append(item)

    room_cost_summary = []
    for rid in sorted(rooms_in_boq.keys()):
        items = rooms_in_boq[rid]
        room_total = sum(float(i.get("line_total") or 0) for i in items)
        room_cost_summary.append(f"- {rid}: {len(items)} partidas, EUR {room_total:,.0f}")

    # Build delta context (what changes per room)
    delta_context = ""
    if delta_slots and isinstance(delta_slots, dict):
        delta_lines = []
        for room in delta_slots.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            rid = str(room.get("room_id") or "")
            rt = str(room.get("room_type") or "")
            slots = room.get("slots") or []
            changes = [s for s in slots if isinstance(s, dict) and str(s.get("action") or "").lower() not in ("no_change", "sin_cambio", "")]
            if changes:
                delta_lines.append(f"  {rid} ({rt}): {', '.join(str(s.get('work_sentence') or s.get('action') or '') for s in changes[:5])}")
        if delta_lines:
            delta_context = "DELTA POR ESTANCIA (qué se cambia y por qué):\n" + "\n".join(delta_lines[:15])

    # ELI5 context (buyer-friendly room summaries)
    eli5_context = ""
    if eli5 and isinstance(eli5, dict):
        eli5_lines = []
        for room in eli5.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            name = room.get("room_name") or room.get("room_id") or "?"
            tagline = room.get("tagline") or ""
            cost = float(room.get("cost") or 0)
            eli5_lines.append(f"  {name} (EUR {cost:,.0f}): {tagline}")
        if eli5_lines:
            eli5_context = "RESUMEN ELI5 (perspectiva comprador):\n" + "\n".join(eli5_lines)

    # Comparable context
    comp_context = ""
    if comps:
        comp_lines = []
        for i, c in enumerate(comps):
            comp_lines.append(
                f"  Comp {i+1}: EUR {c.get('sale_price', 0):,.0f} | "
                f"{c.get('living_area', 0)} m² | "
                f"{c.get('bedrooms', '?')} hab | "
                f"{c.get('condition', '?')}"
            )
        comp_context = "COMPARABLES VENDIDOS:\n" + "\n".join(comp_lines)

    # ── Load knowledge bases ─────────────────────────────────────────────────
    rules_path = _RULES_ENGINE_PATH if _RULES_ENGINE_PATH.exists() else _RULES_ENGINE_FALLBACK
    rules_engine = _load_json_safe(rules_path)
    energy_kb = _load_json_safe(_ENERGY_KB_PATH)
    # process_kb loaded but only lightly referenced (timeline guidance)

    year_built_raw = listing.get("construction_year") or listing.get("year_built")
    year_built_int = int(year_built_raw) if isinstance(year_built_raw, (int, float)) else 0
    year_built_str = str(year_built_raw) if year_built_raw else "desconocido"

    # Pre-filter rules that apply to this construction year
    rules_context = _filter_rules_by_year(rules_engine, year_built_int)
    if rules_context:
        logger.info("v5_architect_report: %d applicable rules for year %s", rules_context.count("["), year_built_str)

    # Energy: target from comparable, context from KB
    comparable_energy = _get_comparable_energy_rating(comparables or [])
    energy_context = _build_energy_context(energy_kb, listing.get("city", ""), comparable_energy)

    # ── LLM prompt for intelligent sections ───────────────────────────────────
    prompt = f"""Eres un director de proyectos de rehabilitación preparando un informe técnico para un comprador
de vivienda. El informe combina visión de diseño, planificación de obra, y — lo más importante —
una evaluación honesta de los riesgos y cosas a investigar ANTES de cerrar la compra.

PROPIEDAD:
- Dirección: {listing.get("title") or listing.get("address") or "?"}
- Ciudad: {listing.get("city", "?")}
- Superficie: {sqm:.0f} m²
- Habitaciones: {listing.get("bedrooms", "?")} | Baños: {listing.get("bathrooms", "?")}
- Año construcción: {year_built_str}
- Precio venta: EUR {asking_price:,.0f}
- Certificación energética actual: {listing.get("energy_rating") or "No disponible"}

PRESUPUESTO:
- PEM: EUR {total_pem:,.0f}
- Total con IVA: EUR {grand_total:,.0f}
- Horas de trabajo: {total_hours:,.0f}
- Semanas estimadas: {estimated_weeks}
- Partidas: {len(line_items)}

DESGLOSE POR ESTANCIA:
{chr(10).join(room_cost_summary)}

{delta_context}

{eli5_context}

{comp_context}

═══════════════════════════════════════════════════════════════════════════════
BASE DE CONOCIMIENTO — REGLAS DE CONSTRUCCIÓN POR AÑO
(rules_engine.json — filtradas para año de construcción {year_built_str})
═══════════════════════════════════════════════════════════════════════════════
{rules_context if rules_context else "No se encontraron reglas aplicables o año desconocido."}

═══════════════════════════════════════════════════════════════════════════════
BASE DE CONOCIMIENTO — ENERGÍA Y CLIMA
(energy_knowledge.json — escala oficial, zonas climáticas CTE)
═══════════════════════════════════════════════════════════════════════════════
{energy_context if energy_context else "No disponible."}

TU TAREA — genera las siguientes secciones:

1. **design_concept**: Visión de diseño.
   - overall_vision: Una frase que define el concepto
   - key_features: 4-6 características principales de la reforma
   - preserved_elements: Qué se conserva y por qué
   - why_not: 2-3 cosas que NO se incluyen y por qué (gestión de expectativas)
   - room_concepts: Para cada estancia, una visión breve + key_changes (3-4 cambios)

2. **timeline_breakdown**: Plan de obra por fases. Cada fase con nombre, semana inicio/fin,
   y tareas principales. Sé realista — las fases se solapan en obra real.

3. **energy_compliance**: Certificación energética.
   - current_rating: El rating actual de la propiedad (de la ficha o estimado por año)
   - target_rating: El rating OBJETIVO — basado en el comparable vendido ({comparable_energy or "no disponible"}).
     IMPORTANTE: Este es un objetivo orientativo basado en IA. Necesita verificación profesional
     con CE3X por un técnico certificador. Inclúyelo como "objetivo estimado, pendiente de certificación".
   - measures: Medidas incluidas en el alcance que afectan al rating
   - Usa la escala y zona climática de la base de conocimiento energético.

4. **compliance_notes**: Normativa aplicable — USA las referencias de normativa de las reglas
   de construcción (REBT 2002, CTE DB-HS, etc.). No inventes normativa.

5. **risk_flags** (SECCIÓN MÁS IMPORTANTE):
   USA LAS REGLAS DE CONSTRUCCIÓN de arriba. Cada regla con urgencia "critical" o "high"
   DEBE aparecer como un riesgo. Combina la información de la regla con tu conocimiento
   de construcción para hacer el riesgo concreto y accionable.

   Para cada riesgo:
   - flag: qué puede pasar — ANCLA al ID de la regla si es aplicable (ej: "[ELEC_001] Cableado pre-REBT sin toma de tierra")
   - severity: alta / media / baja — respeta la urgencia de la regla
   - mitigation: qué hacer al respecto — incluye la acción de la regla + tu recomendación
   - cost_impact: estimación de coste adicional si se materializa

   TAMBIÉN añade riesgos propios basados en el año y la ciudad que no estén en las reglas
   (amianto en bajantes, aluminosis, normativa de fachada local, etc.)

6. **recommendations**: 3-5 recomendaciones priorizadas — qué investigar, qué pedir en
   la negociación, qué hacer antes de empezar obra.

7. **confidence_score**: 0-100

IMPORTANTE — formato de respuesta JSON:
"""

    schema = {
        "type": "object",
        "properties": {
            "design_concept": {
                "type": "object",
                "properties": {
                    "overall_vision": {"type": "string"},
                    "design_rationale": {"type": "string"},
                    "key_features": {"type": "array", "items": {"type": "string"}},
                    "preserved_elements": {"type": "array", "items": {"type": "string"}},
                    "why_not": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "feature": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["feature", "reason"],
                        },
                    },
                    "room_concepts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "room_id": {"type": "string"},
                                "room_name": {"type": "string"},
                                "vision": {"type": "string"},
                                "key_changes": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["room_id", "room_name", "vision", "key_changes"],
                        },
                    },
                },
                "required": ["overall_vision", "key_features", "room_concepts"],
            },
            "timeline_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "week_start": {"type": "integer"},
                        "week_end": {"type": "integer"},
                        "tasks": {"type": "array", "items": {"type": "string"}},
                        "description": {"type": "string"},
                    },
                    "required": ["name", "week_start", "week_end", "tasks"],
                },
            },
            "energy_compliance": {
                "type": "object",
                "properties": {
                    "current_rating": {"type": "string"},
                    "target_rating": {"type": "string"},
                    "improvement_letters": {"type": "integer"},
                    "climate_zone": {"type": "string"},
                    "meets_cte_db_he": {"type": "boolean"},
                    "measures": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["current_rating", "target_rating", "measures"],
            },
            "compliance_notes": {
                "type": "object",
                "properties": {
                    "standards": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": "string"},
                },
                "required": ["standards", "note"],
            },
            "risk_flags": {
                "type": "array",
                "description": "5-8 riesgos concretos anclados al año, ubicación y alcance",
                "items": {
                    "type": "object",
                    "properties": {
                        "flag": {"type": "string", "description": "Qué puede pasar — concreto y específico"},
                        "severity": {"type": "string", "description": "alta / media / baja"},
                        "mitigation": {"type": "string", "description": "Qué hacer al respecto"},
                        "cost_impact": {"type": "string", "description": "Estimación de coste adicional si se materializa"},
                    },
                    "required": ["flag", "severity", "mitigation", "cost_impact"],
                },
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "recommendation": {"type": "string"},
                        "priority": {"type": "string"},
                    },
                    "required": ["recommendation", "priority"],
                },
            },
            "confidence_score": {"type": "integer", "description": "0-100"},
        },
        "required": [
            "design_concept", "timeline_breakdown",
            "energy_compliance", "compliance_notes",
            "risk_flags", "recommendations", "confidence_score",
        ],
    }

    result = await call_gemini_json(
        prompt,
        model="pro",
        temperature=0.3,
        response_schema=schema,
    )

    if not result or not isinstance(result, dict):
        raise RuntimeError(f"v5_architect_report: LLM returned empty/invalid | listing_id={listing_id}")

    # ── Assemble full analysis object ─────────────────────────────────────────
    # This matches what ArchitectReportModal.tsx reads from analysis prop.
    weeks_min = max(1, estimated_weeks - 2)
    weeks_max = estimated_weeks + 4

    report: Dict[str, Any] = {
        # Section 1: The Property (computed)
        "target_pir_summary": target_pir_summary,

        # Comparables (computed — no market positioning text, just the grid)
        "comparables": comps,
        "bracket": "market_standard",

        # Design Concept (LLM)
        "design_concept": result.get("design_concept", {}),

        # Scope & BOQ (computed)
        "asking_price": asking_price,
        "renovation_cost": grand_total,
        "total_investment": asking_price + grand_total,
        "target_price": asking_price + grand_total,
        "pem_subtotal": total_pem,
        "view": "market_standard",
        "estimated_weeks_min": weeks_min,
        "estimated_weeks_max": weeks_max,
        "line_items_count": len(line_items),
        "line_items": line_items,
        "cost_breakdown": cost_breakdown,
        "scope_of_work": {
            "total_items": len(line_items),
            "categories": [],
            "pricing": {
                "pem": cost_breakdown["pem"],
                "overhead_13pct": cost_breakdown["overhead"],
                "profit_6pct": cost_breakdown["profit"],
                "iva_21pct": cost_breakdown["iva"],
                "total_with_iva": cost_breakdown["total"],
            },
        },

        # Timeline (LLM)
        "timeline_breakdown": result.get("timeline_breakdown", []),
        "timeline_summary": {
            "total_weeks": estimated_weeks,
            "critical_phases": [p.get("name", "") for p in (result.get("timeline_breakdown") or [])[:3]],
        },

        # Energy (LLM)
        "energy_compliance": result.get("energy_compliance", {}),

        # Compliance (LLM)
        "compliance_notes": result.get("compliance_notes", {}),

        # Risks & Recommendations — the star sections (LLM, year-aware)
        "risk_flags": result.get("risk_flags", []),
        "recommendations": result.get("recommendations", []),

        # Quality
        "confidence_score": (result.get("confidence_score") or 75) / 100,  # Frontend expects 0-1
        "sanity_check_passed": True,

        # Meta
        "gap": 0,
        "schema_version": "v5_architect_report_v1",
    }

    # Save
    report_key = f"v5_architect_report_{strategy_name}"
    ok = await db.save_unified_estimate(listing_id, report_key, report)
    if not ok:
        raise RuntimeError(f"v5_architect_report: save failed | key={report_key} listing_id={listing_id}")

    logger.info(
        "v5_architect_report: generated | listing_id=%s | rooms=%d | confidence=%d%%",
        listing_id,
        len(result.get("design_concept", {}).get("room_concepts", [])),
        result.get("confidence_score", 0),
    )
    return report
