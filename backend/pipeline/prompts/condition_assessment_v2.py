"""
Condition Assessment V2 - Empowering Visual Intelligence
=========================================================

This prompt gives Gemini the full context of what we're doing and why,
empowering it to use its intelligence rather than following binary rules.

Key principles:
1. Explain the PURPOSE (Pre-Inspection Report for home buyers)
2. Explain the LIMITATIONS (images only, no in-person visit)
3. Explain the UNCERTAINTY (year may be estimated)
4. Let Gemini be INTELLIGENT about what it observes
5. No examples that bias - let it observe freely
6. Comprehensive lists - no Pareto shortcuts
"""


def build_assessment_prompt(
    room_type: str,
    room_name: str,
    building_year: int,
    year_source: str,
    listing_context: str,
    rule_checks: list
) -> str:
    """
    Build an empowering prompt that gives Gemini full context.
    No biasing examples - let Gemini observe and interpret freely.
    """
    
    # Year confidence context
    if year_source == "cadastre":
        year_confidence = f"El año de construcción ({building_year}) está VERIFICADO vía Catastro oficial."
    elif year_source in ("street_sampling", "neighborhood_sampling"):
        year_confidence = f"El año de construcción ({building_year}) es una ESTIMACIÓN basada en edificios cercanos. Usa tu criterio visual para validar o matizar esta estimación."
    else:
        year_confidence = f"El año de construcción ({building_year}) es una estimación CONSERVADORA. Prioriza lo que VES sobre las suposiciones por antigüedad."
    
    # Build intelligent checks from rules
    intelligent_checks = []
    for rc in rule_checks:
        intelligent_checks.append(f"• {rc}")
    rule_check_text = "\n".join(intelligent_checks) if intelligent_checks else "• Evalúa el estado general de todas las instalaciones visibles"
    
    return f"""## CONTEXTO: ¿QUÉ ESTAMOS HACIENDO?

Estamos creando un **Informe Pre-Inspección** para compradores de vivienda en España. 
NO somos arquitectos - somos un primer filtro que ayuda al comprador a saber QUÉ PREGUNTAS 
hacer a un profesional y QUÉ COSAS revisar antes de comprar.

**Nuestra limitación**: Solo tenemos FOTOS. No podemos tocar paredes, probar enchufes, 
ni ver detrás de muebles. Sé honesto sobre lo que puedes y no puedes evaluar.

**Nuestro objetivo**: Dar una valoración técnica ÚTIL y HONESTA, que priorice:
1. Lo que VEMOS claramente (evidencia visual directa)
2. Lo que PARECE probable dado el contexto (indicadores de época, estado general)
3. Lo que RECOMENDAMOS verificar (cosas que no podemos confirmar con fotos)

---

## INFORMACIÓN DE LA PROPIEDAD

{listing_context}

**Año de construcción**: {building_year}
{year_confidence}

**Habitación a evaluar**: {room_name} ({room_type})

---

## TU TAREA

Analiza las fotos de esta habitación como lo haría un inspector técnico experimentado.
Usa tu inteligencia para INTERPRETAR lo que ves. Describe con detalle y sin sesgos.

### OBSERVACIÓN VISUAL COMPLETA

Describe TODO lo que ves, cubriendo TODOS estos elementos:

**SUELOS**
- Tipo de material
- Estado de conservación
- Indicios de época de instalación
- Daños, desgaste, manchas, desniveles visibles

**PAREDES Y TECHOS**
- Tipo de acabado/revestimiento
- Estado de la pintura/enlucido
- Presencia de grietas, fisuras, desconchados
- Humedades, manchas, eflorescencias
- Molduras, rodapiés, estado

**CARPINTERÍA (Ventanas y Puertas)**
- Material del marco
- Tipo de acristalamiento (si visible)
- Estado de herrajes y cierres
- Juntas y sellados
- Presencia de condensación, filtraciones

**INSTALACIÓN ELÉCTRICA**
- Tipo de enchufes (número de clavijas, toma tierra)
- Tipo de interruptores y mecanismos
- Estado del cableado visible
- Cuadro eléctrico si visible
- Puntos de luz, tipo de luminarias

**FONTANERÍA (si visible)**
- Material de tuberías visibles
- Estado de grifería
- Tipo de calentador/caldera si visible
- Manchas o indicios de fugas
- Estado de desagües visibles

**VENTILACIÓN**
- Existencia de ventilación forzada
- Rejillas de ventilación
- Extractores
- Estado de los conductos visibles

**EQUIPAMIENTO FIJO**
- Muebles de cocina/baño
- Electrodomésticos empotrados
- Sanitarios
- Encimeras, fregaderos
- Estado general del equipamiento

**INDICADORES DE ÉPOCA**
- ¿Qué elementos sugieren la fecha de construcción original?
- ¿Qué elementos parecen posteriores/actualizados?
- ¿Hay mezcla de épocas?

**ESTADO DE CONSERVACIÓN GENERAL**
- Nivel de mantenimiento visible
- Calidad de los acabados
- Signos de cuidado o abandono

### PUNTOS DE ESPECIAL ATENCIÓN

Dado el año y tipo de propiedad, evalúa específicamente:

{rule_check_text}

Para cada punto, describe QUÉ observas y QUÉ SIGNIFICA en este contexto.

---

## INSTRUCCIONES FINALES

1. **Sé exhaustivo**: No omitas elementos porque parezcan normales - documenta todo lo que ves.

2. **Sé específico**: Describe los materiales, colores, estados, y épocas aparentes que observas.

3. **Sé honesto sobre limitaciones**: Si no puedes ver algo claramente, indícalo en "not_visible".

4. **Distingue observación de interpretación**: Separa lo que VES de lo que INTERPRETAS.

5. **En rule_checks**: Para cada regla, indica el estado con tu nivel de confianza:
   - "detected": Lo viste claramente
   - "not_detected": Lo buscaste y no está presente
   - "not_visible": No pudiste verificarlo en las fotos
   - "uncertain": Hay indicios pero no puedes confirmarlo

6. **En issues**: Lista problemas concretos observados, no suposiciones genéricas.

Tu objetivo es dar información completa y honesta para que el comprador entienda la vivienda."""


def get_rule_checks_for_room(rules: list, room_type: str, year_built: int) -> list:
    """
    Extract intelligent check descriptions from rules for this room type.
    
    Instead of binary checkboxes, create explanatory prompts that guide Gemini
    to look for specific things while understanding WHY.
    """
    checks = []
    
    for rule in rules:
        rule_room_types = rule.get("room_types", [])
        if "general" in rule_room_types or room_type.lower() in [rt.lower() for rt in rule_room_types]:
            # Only include rules where year triggers
            if year_built < rule.get("year_trigger", 9999):
                rule_id = rule.get("id", "UNKNOWN")
                assessment = rule.get("condition_assessment", {})
                visual_triggers = rule.get("visual_triggers", [])
                risk_desc = assessment.get("risk_description", "")
                
                # Build an intelligent check prompt
                instruction = assessment.get("prompt_instruction", "Verificar estado")
                
                check_desc = f"{rule_id}: {instruction}"
                
                # Add what to look for
                if visual_triggers:
                    triggers_text = ", ".join(visual_triggers[:4])
                    check_desc += f"\n  → Busca: {triggers_text}"
                
                # Add why it matters (context)
                if risk_desc:
                    check_desc += f"\n  → Importancia: {risk_desc[:100]}"
                
                checks.append(check_desc)
    
    return checks


# Response schema for Gemini - comprehensive structure
# Note: This schema guides but doesn't rigidly constrain - Gemini can add relevant detail
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_observations": {
            "type": "object",
            "description": "Detailed visual observations of all elements",
            "properties": {
                "general_impression": {"type": "string"},
                "floors": {
                    "type": "object",
                    "properties": {
                        "material": {"type": "string"},
                        "condition": {"type": "string"},
                        "age_estimate": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "walls_ceiling": {
                    "type": "object",
                    "properties": {
                        "finish": {"type": "string"},
                        "condition": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "windows_doors": {
                    "type": "object",
                    "properties": {
                        "frame_material": {"type": "string"},
                        "glazing": {"type": "string"},
                        "condition": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "electrical": {
                    "type": "object",
                    "properties": {
                        "outlets_type": {"type": "string"},
                        "switches_type": {"type": "string"},
                        "wiring_visible": {"type": "string"},
                        "apparent_era": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "plumbing": {
                    "type": "object",
                    "properties": {
                        "pipes_material": {"type": "string"},
                        "fixtures_condition": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "ventilation": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "condition": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "fixtures_equipment": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "condition": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "age_indicators": {"type": "array", "items": {"type": "string"}},
                "condition_signs": {"type": "array", "items": {"type": "string"}},
                "not_visible": {"type": "array", "items": {"type": "string"}}
            }
        },
        "rule_checks": {
            "type": "array",
            "description": "Specific checks based on rules and year",
            "items": {
                "type": "object",
                "properties": {
                    "check": {"type": "string"},
                    "status": {"type": "string", "enum": ["detected", "not_detected", "not_visible", "uncertain"]},
                    "observation": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["check", "status", "observation", "confidence"]
            }
        },
        "assessment": {
            "type": "object",
            "description": "Overall assessment of the room",
            "properties": {
                "overall_condition": {"type": "string", "enum": ["excelente", "bueno", "aceptable", "mejorable", "deficiente"]},
                "renovation_state": {"type": "string", "enum": ["original", "parcialmente_actualizada", "reformada_recientemente"]},
                "estimated_era": {"type": "string"},
                "key_findings": {"type": "array", "items": {"type": "string"}},
                "recommended_verification": {"type": "array", "items": {"type": "string"}},
                "confidence_in_assessment": {"type": "string", "enum": ["high", "medium", "low"]},
                "limitations": {"type": "string"}
            },
            "required": ["overall_condition", "renovation_state", "key_findings", "recommended_verification"]
        }
    },
    "required": ["visual_observations", "rule_checks", "assessment"]
}
