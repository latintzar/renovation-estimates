from __future__ import annotations

import json
from typing import Any, Dict


def build_gla_opinion_room_prompt(
    *,
    listing_id: int,
    room_id: str,
    room_type: str,
    slot_narratives: Dict[str, str],
    smart_m2_room: Dict[str, Any] | None = None,
    age_context_block: str = "",
) -> str:
    """
    GLA opinion prompt for ONE room (Spanish): produce one short, opinionated narrative per slot.

    WHY THIS MATTERS:
    - GLA is used in WhatsApp. The user wants an honest, practical "what would you do here?" take.
    - We still need slot-level structure so downstream tools (images/costs) can reason consistently.
    - Output must be grounded in photos + PIR current-state narratives, not imagined.
    """
    # Keep this compact and human-readable; we want reasoning, not a massive template.
    dims = smart_m2_room or {}
    dims_block = ""
    if isinstance(dims, dict) and dims:
        dims_block = f"SMART M2 (medidas estimadas para esta estancia):\n{json.dumps(dims, ensure_ascii=False, indent=2)}\n"

    slots_block = json.dumps(slot_narratives or {}, ensure_ascii=False, indent=2)

    return f"""
Eres un arquitecto / asesor de reformas escribiendo a un amigo por WhatsApp.
Tu trabajo: mirar las fotos de esta estancia + su PIR (estado actual por slot) y decir, slot por slot,
que crees que SE PODRIA / SE DEBERIA hacer (si merece la pena), con criterio de reforma inteligente.

REGLAS DE ORO (por que importa):
- La persona va a gastar dinero real. Si propones cosas sin impacto o inventadas, pierdes su confianza.
- No uses lenguaje corporativo. Se directo y practico.
- No inventes hechos: si algo no se ve o el PIR dice "no visible", se prudente ("probable", "confirmar en visita").
- Si el estado actual ya esta bien o el cambio no compensa, escribe "no change".

PATRON DE RAZONAMIENTO (preguntas, no checklist):
Para cada slot, preguntate:
1) ¿Esto arregla algo realmente malo (roto, sucio, anticuado, inseguro)?
2) ¿Mejora energia/instalaciones (ventanas, aislamiento, electricidad, fontaneria)?
3) ¿Sube claramente el valor o la funcionalidad en este tipo de estancia ({room_type})?
Si las tres son NO, probablemente es "no change".

CONTEXTO:
listing_id: {int(listing_id)}
room_id: {room_id}
room_type: {room_type}

{dims_block}{age_context_block}

PIR (estado actual por slot):
{slots_block}

SALIDA (JSON):
- Devuelve SOLO JSON valido.
- Misma estructura de slots: una frase corta por slot_id.
- Si decides que no hay nada que hacer en un slot: "no change".

Claves:
- "room_id": string
- "room_type": string
- "slot_opinion_narratives": object (slot_id -> string)
""".strip()

