"""
Rule Verification Prompt - Visual Confirmation of Age-Based Rules
=================================================================

This prompt focuses ONLY on verifying/rejecting rules from rules_engine_v2.json.
It does NOT do free-form visual description - that's for assess_uniclass.py.

Purpose:
- Given a building's year, certain compliance concerns may apply
- Ask Gemini: "Can you SEE evidence that confirms or rejects this concern?"
- Output: confirmed / rejected / not_visible per rule

This is about BEHIND THE WALLS - things you typically can't see but sometimes
can get visual confirmation of (old fuse boxes, lead pipes, etc.)
"""

from typing import List, Dict, Any


def build_rule_verification_prompt(
    room_type: str,
    room_name: str,
    building_year: int,
    year_source: str,
    rules_to_verify: List[Dict[str, Any]]
) -> str:
    """
    Build a focused prompt for rule verification only.
    
    Args:
        room_type: Type of room (cocina, baño, etc.)
        room_name: Display name
        building_year: Year of construction
        year_source: Where the year came from (cadastre, estimate, etc.)
        rules_to_verify: List of rules applicable to this room/year
    
    Returns:
        Prompt string for Gemini
    """
    
    # Year confidence context
    if year_source == "cadastre":
        year_confidence = "El año está VERIFICADO vía Catastro oficial."
    else:
        year_confidence = "El año es una ESTIMACIÓN. Prioriza evidencia visual."
    
    # Build rule verification section
    rule_sections = []
    for i, rule in enumerate(rules_to_verify, 1):
        rule_id = rule.get("id", f"RULE_{i}")
        system = rule.get("system", "unknown")
        visual_triggers = rule.get("visual_triggers", [])
        assessment = rule.get("condition_assessment", {})
        
        instruction = assessment.get("prompt_instruction", "Verificar estado")
        risk_label = assessment.get("risk_label", "Riesgo desconocido")
        
        # What confirms this concern
        confirm_triggers = ", ".join(visual_triggers[:4]) if visual_triggers else "evidencia visual directa"
        
        rule_sections.append(f"""
### {i}. {rule_id} ({system})
**Preocupación**: {risk_label}
**Buscar para CONFIRMAR**: {confirm_triggers}
**Instrucción**: {instruction}
""")
    
    rules_text = "\n".join(rule_sections) if rule_sections else "No hay reglas específicas para verificar."
    
    return f"""## TAREA: VERIFICACIÓN DE REGLAS POR ANTIGÜEDAD

Eres un inspector técnico. Este edificio es de **{building_year}**. {year_confidence}

Dado el año, ciertas preocupaciones técnicas podrían aplicar (instalación eléctrica antigua, 
tuberías de plomo, falta de aislamiento, etc.). Tu trabajo es mirar las fotos y determinar 
si puedes **CONFIRMAR** o **RECHAZAR** cada preocupación basándote en lo que VES.

**IMPORTANTE**: Estas son cosas "detrás de las paredes" - normalmente no se ven, pero a veces 
hay evidencia visible (cuadro eléctrico antiguo, tuberías visibles bajo el fregadero, etc.).

---

## HABITACIÓN: {room_name} ({room_type})

---

## REGLAS A VERIFICAR

{rules_text}

---

## INSTRUCCIONES

Para CADA regla listada arriba:

1. **CONFIRMED**: Si ves evidencia clara de que la preocupación ES real
   - Ejemplo: "Veo un cuadro eléctrico con fusibles cerámicos antiguos"
   
2. **REJECTED**: Si ves evidencia clara de que la preocupación NO aplica
   - Ejemplo: "Veo un cuadro moderno con diferenciales y magnetotérmicos"
   
3. **NOT_VISIBLE**: Si no puedes ver nada relacionado con esta regla
   - Ejemplo: "No hay cuadro eléctrico visible en estas fotos"

**NUNCA inventes**. Si no lo ves, es NOT_VISIBLE. 
Solo usa CONFIRMED o REJECTED si tienes evidencia visual clara.

---

## FORMATO DE RESPUESTA

Responde SOLO en el formato JSON estructurado especificado."""


def get_applicable_rules(
    rules: List[Dict[str, Any]], 
    room_type: str, 
    year_built: int
) -> List[Dict[str, Any]]:
    """
    Filter rules that apply to this room type and building year.
    
    Args:
        rules: All rules from rules_engine_v2.json
        room_type: Type of room (cocina, baño, etc.)
        year_built: Year of construction
    
    Returns:
        List of applicable rules
    """
    applicable = []
    room_type_lower = room_type.lower()
    
    for rule in rules:
        rule_room_types = [rt.lower() for rt in rule.get("room_types", [])]
        year_trigger = rule.get("year_trigger", 9999)
        
        # Check if rule applies to this room
        room_matches = "general" in rule_room_types or room_type_lower in rule_room_types
        
        # Check if building is old enough for this rule to apply
        year_matches = year_built < year_trigger
        
        if room_matches and year_matches:
            applicable.append(rule)
    
    return applicable


# Simplified response schema - ONLY rule verifications
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "rule_verifications": {
            "type": "array",
            "description": "Verification status for each rule",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "ID of the rule being verified"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["confirmed", "rejected", "not_visible"],
                        "description": "confirmed=saw evidence of problem, rejected=saw evidence problem doesn't exist, not_visible=couldn't see relevant elements"
                    },
                    "visual_evidence": {
                        "type": "string",
                        "description": "What exactly you saw that led to this determination (or why you couldn't see it)"
                    }
                },
                "required": ["rule_id", "status", "visual_evidence"]
            }
        }
    },
    "required": ["rule_verifications"]
}

