"""
Age-context intelligence block for V5 PIR prompts.

Loads the two rules-engine JSONs ONCE and builds a compact text block
that tells the PIR model:
  1. Which construction era the building belongs to.
  2. What visual cues are typical for that era.
  3. Which regulatory / condition rules are triggered for the specific room type.

The block is purely INFORMATIONAL - it must not make the PIR prescriptive.
It helps the model infer likely hidden conditions behind "No visible en fotos" slots.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

_RULES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pipeline")


@lru_cache(maxsize=1)
def _load_rules_v1() -> Dict[str, Any]:
    path = os.path.join(_RULES_DIR, "rules_engine.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_rules_v2() -> Dict[str, Any]:
    path = os.path.join(_RULES_DIR, "rules_engine_v2.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_ERA_RANGES: List[Tuple[str, int, int]] = [
    ("pre_1960",   0,    1959),
    ("1960_1979",  1960, 1979),
    ("1980_1999",  1980, 1999),
    ("2000_2010",  2000, 2010),
    ("post_2010",  2011, 9999),
]


def _era_for_year(year: int) -> str:
    for label, lo, hi in _ERA_RANGES:
        if lo <= year <= hi:
            return label
    return "post_2010"


def _era_label_spanish(era: str) -> str:
    mapping = {
        "pre_1960":  "anterior a 1960",
        "1960_1979": "1960-1979",
        "1980_1999": "1980-1999",
        "2000_2010": "2000-2010",
        "post_2010": "posterior a 2010",
    }
    return mapping.get(era, era)


_RT_MAP = {
    "kitchen": "cocina",
    "bathroom": "bano",
    "bedroom": "dormitorio",
    "living": "salon",
    "hallway": "pasillo",
    "corridor": "pasillo",
    "exterior": "general",
    "terrace": "general",
    "balcony": "general",
    "laundry": "general",
    "utility": "general",
}


def _normalize_text(value: str) -> str:
    return (
        (value or "")
        .lower()
        .replace("\u00e1", "a")
        .replace("\u00e9", "e")
        .replace("\u00ed", "i")
        .replace("\u00f3", "o")
        .replace("\u00fa", "u")
        .replace("\u00fc", "u")
        .replace("\u00f1", "n")
    )


def build_age_context_block(
    *,
    construction_year: int,
    room_type: str,
) -> str:
    """
    Return a compact text block (Spanish) with age intelligence for a PIR prompt.

    Returns empty string if construction_year is missing/invalid so the caller
    can safely inject it without conditionals.
    """
    if not construction_year or construction_year < 1800:
        return ""

    era = _era_for_year(construction_year)
    era_label = _era_label_spanish(era)

    v1 = _load_rules_v1()
    indicators = (v1.get("age_estimation") or {}).get("indicators") or {}
    era_cues: List[str] = []
    era_data = indicators.get(era)
    if isinstance(era_data, dict):
        era_cues = era_data.get("visual_cues") or []

    v2 = _load_rules_v2()
    all_rules: List[Dict[str, Any]] = v2.get("rules") or []

    rt_lower = _normalize_text(room_type or "").strip()
    rt_key = _RT_MAP.get(rt_lower, rt_lower)

    triggered: List[Dict[str, Any]] = []
    for rule in all_rules:
        year_trigger = rule.get("year_trigger") or 9999
        rule_room_types = [_normalize_text(r) for r in (rule.get("room_types") or [])]
        if construction_year < year_trigger and (
            rt_key in rule_room_types or "general" in rule_room_types
        ):
            triggered.append(rule)

    lines: List[str] = []
    lines.append("CONTEXTO DE ANTIGUEDAD DEL EDIFICIO:")
    lines.append(f"- Ano de construccion: {construction_year} (era: {era_label})")

    if era_cues:
        cues_str = ", ".join(era_cues[:8])
        lines.append(f"- Indicadores visuales tipicos de esta era: {cues_str}")

    if triggered:
        lines.append(f"- Alertas normativas relevantes para este tipo de habitacion ({rt_key}):")
        for rule in triggered:
            rid = rule.get("id", "?")
            ca = rule.get("condition_assessment") or {}
            risk_label = ca.get("risk_label", "")
            prompt_instr = ca.get("prompt_instruction", "")
            visual_triggers = ", ".join((rule.get("visual_triggers") or [])[:5])
            lines.append(f"  * {rid}: {risk_label}. Buscar: {visual_triggers}. {prompt_instr}")

    lines.append("")
    lines.append(
        'POR QUE IMPORTA: Usa este contexto de antiguedad para INFORMAR tu inferencia '
        'en slots no visibles. Por ejemplo, si el edificio es de 1975 y no ves la instalacion '
        'electrica, es razonable describir: "Dado el ano de construccion (1975), es probable que '
        'la instalacion electrica sea anterior al REBT 2002, con posibles mecanismos antiguos. '
        'Confirmar en visita." Esto es INTELIGENCIA descriptiva, no prescripcion -- describe lo '
        'que esperas encontrar, no lo que se deberia hacer.'
    )

    return "\n".join(lines)
