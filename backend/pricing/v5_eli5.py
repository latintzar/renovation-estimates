"""
V5 ELI5 — Buyer-friendly renovation summary
============================================

Takes the raw BOQ line items (BCCA codes, construction jargon) and transforms
them into a "product configurator" view that a first-time buyer can understand.

WHY THIS MATTERS:
A buyer looking at "01ADS00003 Demolición partición int. tabique L/hueco sencillo
manual, carga mecánica" learns nothing. But "Paredes y suelo — Retirada del
alicatado antiguo, nuevo azulejo blanco hasta el techo, solado cerámico.
Incluye la preparación de superficies. ~€5.100" tells them exactly what they're
getting and what it costs.

The LLM (Gemini Pro) reads ALL line items for a room and regroups them into 2-5
buyer-friendly "packages" — surfaces, fixtures, installations, carpentry, etc.
It's doing the job a good architect does when they explain the budget to a client.

Input:  v2_market_standard (aggregated BOQ), listing metadata
Output: v5_eli5_market_standard (saved to unified_estimates)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def generate_v5_eli5(
    *,
    listing_id: int,
    strategy_name: str,
    boq_aggregation: Dict[str, Any],
    listing: Dict[str, Any],
    db: Any,
    call_gemini_json: Any,
    target_pir: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a buyer-friendly ELI5 summary from the priced BOQ.

    Uses Gemini Pro to regroup raw BCCA line items into understandable
    "product packages" per room (surfaces, fixtures, installations, etc.).

    If target_pir is provided, the LLM also receives the current-condition
    narratives so it can produce a "before → after" intro pair.

    Returns the ELI5 dict and saves it to unified_estimates.
    """
    line_items = boq_aggregation.get("line_items") or []
    if not line_items:
        raise RuntimeError(f"v5_eli5: no line items | listing_id={listing_id}")

    total_pem = float(boq_aggregation.get("total_pem") or 0)
    grand_total = float(boq_aggregation.get("grand_total_with_iva") or 0)
    total_hours = float(boq_aggregation.get("total_labor_hours") or 0)
    estimated_weeks = int(boq_aggregation.get("estimated_weeks") or 0)
    sqm = float(listing.get("sqm") or listing.get("m2_built") or 0)

    # Group line items by room
    rooms_data: Dict[str, List[Dict[str, Any]]] = {}
    for item in line_items:
        rid = str(item.get("room_id") or item.get("room_name") or "general").strip()
        rooms_data.setdefault(rid, []).append(item)

    # Build the room-by-room BOQ block for the prompt
    room_blocks = []
    for rid in sorted(rooms_data.keys()):
        items = rooms_data[rid]
        room_total = sum(float(i.get("line_total") or 0) for i in items)
        room_hours = sum(float(i.get("labor_hours") or 0) for i in items)

        lines_text = []
        for i in items:
            desc = str(i.get("description") or "")[:100]
            qty = float(i.get("quantity") or 0)
            unit = str(i.get("unit") or "")
            lt = float(i.get("line_total") or 0)
            lines_text.append(f"  - {desc} | {qty:.1f} {unit} | EUR {lt:,.0f}")

        room_blocks.append(
            f"ROOM: {rid} | {len(items)} items | EUR {room_total:,.0f} | {room_hours:.0f}h labor\n"
            + "\n".join(lines_text)
        )

    all_rooms_text = "\n\n".join(room_blocks)

    # ── Build PIR context block (current condition per room) ──────────────────
    pir_block = ""
    if target_pir and isinstance(target_pir, dict):
        pir_rooms = target_pir.get("rooms") or []
        pir_lines = []
        for pr in pir_rooms:
            rid = str(pr.get("room_id") or "").strip()
            rt = str(pr.get("room_type") or "").strip()
            narratives = pr.get("slot_narratives") or {}
            if not narratives:
                continue
            sentences = [f"  - {slot}: {txt}" for slot, txt in narratives.items() if isinstance(txt, str) and txt.strip()]
            if sentences:
                pir_lines.append(f"ROOM {rid} ({rt}):\n" + "\n".join(sentences))
        if pir_lines:
            pir_block = "\n\n".join(pir_lines)

    # ── Prompt ────────────────────────────────────────────────────────────────
    prompt = f"""Eres un arquitecto explicando el presupuesto de reforma a un comprador de primera vivienda.
El comprador NO entiende de construcción. Tu trabajo es traducir las partidas técnicas (códigos BCCA,
demoliciones, albañilería, etc.) en un lenguaje que cualquier persona entienda — como si fuera
un configurador de producto online.

PROPIEDAD:
- Ciudad: {listing.get("city", "?")}
- Superficie: {sqm:.0f} m²
- Habitaciones: {listing.get("bedrooms", "?")} | Baños: {listing.get("bathrooms", "?")}
- Precio venta: EUR {float(listing.get("price") or 0):,.0f}

PRESUPUESTO TOTAL:
- PEM (sin IVA): EUR {total_pem:,.0f}
- Con IVA (21%): EUR {grand_total:,.0f}
- Horas de trabajo: {total_hours:,.0f}
- Semanas estimadas: {estimated_weeks}
"""

    if pir_block:
        prompt += f"""
ESTADO ACTUAL DE LA PROPIEDAD (inspección visual por estancia):
Debajo tienes las observaciones del estado actual de cada estancia. Usa esta información para
escribir la frase "intro_before" — cómo está la vivienda AHORA, el estado real.
{pir_block}

"""

    prompt += f"""PARTIDAS COMPLETAS POR ESTANCIA (líneas del presupuesto):
{all_rooms_text}

TU TAREA:
Primero, escribe DOS frases de introducción:

1. "intro_before" — UNA sola frase que describe el estado ACTUAL de la vivienda. Sé honesto y concreto
   sobre lo que se ha visto: antigüedad de los acabados, estado de baños/cocina, instalaciones obsoletas,
   etc. Piensa en cómo un amigo describiría el piso después de visitarlo. Sin dramatizar, sin marketing.
   Ejemplo: "Piso de los años 80 con suelos de terrazo, baños con azulejo marrón original, cocina sin
   reformar y ventanas de aluminio simple."

2. "intro_after" — UNA sola frase que describe en qué se convierte tras la reforma. Concreta y visual:
   qué acabados, qué cambios se notan. No menciones plazos ni precios.
   Ejemplo: "Suelos de porcelánico, baños con azulejo blanco hasta el techo, cocina nueva con encimera
   de cuarzo, y ventanas de aluminio con rotura de puente térmico."

Después, para cada estancia, haz dos cosas:
1. Escribe un "tagline" — UNA frase descriptiva que explique claramente qué se hace en esa estancia.
   Debe ser concreta y útil, no marketing. Por ejemplo: "Azulejo nuevo en paredes y suelo, mueble
   bajo fregadero, y puntos de luz y agua actualizados."
2. Reagrupa las partidas técnicas en 2-5 "paquetes" con nombre corto y coste. SIN descripción extra
   por paquete — el tagline ya lo explica todo. Los paquetes son solo etiquetas de coste.

Por ejemplo, si una cocina tiene estas partidas:
- Demolición tabique hueco sencillo manual | 15 m² | EUR 1.200
- Alicatado azulejo blanco 20x20 adhesivo | 30 m² | EUR 1.560  
- Solado cerámico rectificado | 7 m² | EUR 490
- Mueble bajo fregadero aglomerado 1,20m | 1 ud | EUR 151

El resultado sería:
- tagline: "Azulejo blanco nuevo en paredes y suelo cerámico, mueble bajo fregadero. Incluye retirar revestimiento antiguo."
- Paquetes: "Paredes y suelo" → EUR 3.250 | "Muebles de cocina" → EUR 151

REGLAS:
- "intro_before" e "intro_after" son UNA frase cada una. Claras, concretas, sin jerga técnica.
  El lector las ve una encima de la otra con una flecha, así que deben funcionar como un "antes → después".
- El tagline es la parte importante: debe ser una frase que un comprador entienda sin contexto extra.
  No uses jerga técnica, no copies códigos BCCA. Habla como un arquitecto explicaría a un amigo.
- Los paquetes son SOLO nombre + coste. Nada más. Sin frases explicativas.
- Los costes de los paquetes de una estancia DEBEN sumar el total de esa estancia (no inventes costes).
- Si una estancia tiene pocas partidas (1-3), un solo paquete es suficiente.
- Al final, incluye un resumen de timeline: cuántas semanas y qué va primero.
- No incluyas "value_story" ni frases de marketing. Solo claridad.

IMPORTANTE — formato de respuesta JSON:
"""

    schema = {
        "type": "object",
        "properties": {
            "intro_before": {
                "type": "string",
                "description": "UNA frase: estado actual de la vivienda — acabados, instalaciones, antigüedad. Honesto y concreto."
            },
            "intro_after": {
                "type": "string",
                "description": "UNA frase: en qué se convierte tras la reforma — acabados nuevos, cambios visibles. Sin precios ni plazos."
            },
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "room_name": {"type": "string", "description": "Nombre legible: Cocina, Salón-Comedor, Baño, etc."},
                        "tagline": {"type": "string", "description": "UNA frase descriptiva y concreta que explica toda la reforma de esta estancia en lenguaje normal"},
                        "cost": {"type": "number", "description": "Coste total de la estancia (PEM sin IVA)"},
                        "packages": {
                            "type": "array",
                            "description": "2-5 paquetes — solo nombre y coste, sin descripción",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Nombre corto: Paredes y suelo, Muebles, Instalaciones, etc."},
                                    "cost": {"type": "number", "description": "Coste del paquete (suma de partidas incluidas)"}
                                },
                                "required": ["name", "cost"]
                            }
                        }
                    },
                    "required": ["room_id", "room_name", "tagline", "cost", "packages"]
                }
            },
            "timeline": {
                "type": "object",
                "properties": {
                    "total_weeks": {"type": "integer"},
                    "summary": {"type": "string", "description": "1-2 frases: cuánto dura y qué va primero"}
                },
                "required": ["total_weeks", "summary"]
            }
        },
        "required": ["intro_before", "intro_after", "rooms", "timeline"]
    }

    result = await call_gemini_json(
        prompt,
        model="pro",
        temperature=0.2,
        response_schema=schema,
    )

    if not result or not isinstance(result, dict) or not result.get("rooms"):
        raise RuntimeError(f"v5_eli5: LLM returned empty/invalid result | listing_id={listing_id}")

    # ── Adapt to frontend ELI5Summary shape ──────────────────────────────────
    # The frontend expects: concept, property_summary, rooms (with key_changes), general_items, timeline
    eli5_rooms = []
    for room in result.get("rooms", []):
        # Build key_changes from package names + costs (no description — tagline covers it)
        key_changes = []
        for pkg in room.get("packages", []):
            cost_str = f"EUR {float(pkg.get('cost') or 0):,.0f}"
            key_changes.append(f"{pkg['name']} ({cost_str})")

        eli5_rooms.append({
            "room_id": room.get("room_id", ""),
            "room_name": room.get("room_name", ""),
            "tagline": room.get("tagline", ""),
            "key_changes": key_changes,
            "cost": float(room.get("cost") or 0),
            "packages": room.get("packages", []),  # Keep raw packages for richer frontend rendering
        })

    eli5 = {
        "concept": {
            "vision_statement": "",  # Replaced by intro_before / intro_after
            "intro_before": result.get("intro_before", ""),
            "intro_after": result.get("intro_after", ""),
            "design_style": "",
            "key_upgrades": [],
            "value_story": "",
        },
        "property_summary": {
            "address": listing.get("title") or listing.get("address") or f"Listing {listing_id}",
            "total_cost": grand_total,
            "total_weeks": estimated_weeks,
        },
        "rooms": eli5_rooms,
        "timeline": result.get("timeline", {"total_weeks": estimated_weeks, "summary": ""}),
        "schema_version": "v5_eli5_v1",
    }

    # Save
    eli5_key = f"v5_eli5_{strategy_name}"
    ok = await db.save_unified_estimate(listing_id, eli5_key, eli5)
    if not ok:
        raise RuntimeError(f"v5_eli5: save failed | key={eli5_key} listing_id={listing_id}")

    logger.info(
        "v5_eli5: generated | listing_id=%s | rooms=%d | total=%.0f",
        listing_id, len(eli5_rooms), grand_total,
    )
    return eli5
