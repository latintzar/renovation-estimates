from __future__ import annotations

import json
from typing import List, Optional


def build_v5_pir_target_room_prompt(
    *,
    room_id: str,
    room_type: str,
    slot_ids: List[str],
    age_context_block: Optional[str] = None,
) -> str:
    """
    V5 target PIR prompt (Spanish): produce exactly one narrative sentence per required slot.
    Output must be valid JSON matching the provided response_schema (enforced by caller).
    """
    slots = [{"slot_id": s} for s in slot_ids]
    age_block = (age_context_block or "").strip()
    age_section = f"\n{age_block}\n" if age_block else ""
    return f"""
Eres un especialista en reformas elaborando un Informe de Inteligencia del Inmueble (PIR) para UNA habitacion.

HABITACION:
- room_id: {room_id}
- room_type: {room_type}
{age_section}
TAREA:
Para cada slot de la lista, escribe EXACTAMENTE UNA frase concisa en espanol describiendo el ESTADO ACTUAL
y las evidencias visibles en las fotos de esta habitacion.
Si el slot no es visible, infiere el estado mas probable basandote en otras pistas visibles de esta misma
habitacion y en la calidad general de lo que SI se ve.

COMO ESCRIBIR:
- Una frase por slot. Sin vinetas, sin listas.
- Mantén cada frase MUY corta (ideal <= 20 palabras y <= 200 caracteres). Evita frases compuestas largas.
- No menciones precios.
- Cuando un slot no se puede evaluar directamente desde las fotos, usa esta forma:
  "No visible en fotos; pero dado <evidencia_concreta>, asumimos <estado_probable>. Confirmar en visita."
  La <evidencia_concreta> DEBE referirse a algo realmente visible en las fotos de esta habitacion
  (o una pista directamente relacionada de otro slot en esta misma estancia).
  No uses suposiciones genericas como "estandar medio del mercado", "estandar moderno" o "promedio".
- Este PIR es DESCRIPTIVO: describe lo que hay, no lo que deberia hacerse.
  Usa verbos de observacion: "se observa", "presenta", "hay", "no hay", "parece", "sugiere".
  Evita verbos de prescripcion: "es necesario", "se requiere", "habria que", "deberia", "se preve",
  "replace", "install", "upgrade".
- Todo el texto debe estar en espanol.
- No anadas claves extra. Devuelve SOLO JSON valido.

SLOTS (obligatorios):
{json.dumps(slots, ensure_ascii=False, indent=2)}
""".strip()
