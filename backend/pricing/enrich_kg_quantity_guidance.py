#!/usr/bin/env python3
"""
KG Quantity Guidance Enrichment Script (Schema-Enforced)
=========================================================

Enriches ALL canonical tasks in the Knowledge Graph with `quantity_guidance`,
using Gemini with response_schema to GUARANTEE completeness.

NO hardcoded keyword matching - Gemini reasons from construction principles.

Each task gets:
- quantity_type: How to measure (area_m2, linear_m, count, volume_m3, fixed)
- scope: per_room, per_property, per_opening, fixed
- reasoning_factors: What affects quantity calculation
- typical_rules: Spanish construction rules of thumb
- constraints: Hard min/max limits to prevent hallucination
- unit: Measurement unit (m², ml, ud, m³)

Usage:
    python enrich_kg_quantity_guidance.py
    
Output:
    Updates hybrid_renovation_graph.json with quantity_guidance for ALL tasks
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
KG_PATH = SCRIPT_DIR.parent.parent.parent / "experiments" / "renovation_costing" / "hybrid_renovation_graph.json"
OUTPUT_PATH = KG_PATH  # Update in place

# Gemini setup
from google import genai
from google.genai import types

# API key handling
HELLO_KEY = ""
api_key = os.getenv("GEMINI_API_KEY") or HELLO_KEY
client = genai.Client(api_key=api_key)


def build_response_schema(task_ids: List[str]) -> Dict:
    """
    Build a response schema that FORCES Gemini to cover every task_id.
    
    This uses JSON schema with `required` fields so the model cannot skip any task.
    """
    # Schema for a single task's quantity_guidance
    quantity_guidance_schema = {
        "type": "object",
        "properties": {
            "quantity_type": {
                "type": "string",
                "enum": ["area_m2", "linear_m", "count", "volume_m3", "fixed"],
                "description": "How this task is measured"
            },
            "scope": {
                "type": "string",
                "enum": ["per_room", "per_property", "per_opening", "fixed"],
                "description": "Calculation scope"
            },
            "reasoning_factors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Factors that affect quantity"
            },
            "typical_rules": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Spanish construction rules of thumb"
            },
            "constraints": {
                "type": "object",
                "properties": {
                    "min": {"type": "number"},
                    "max_per_room": {"type": "number"},
                    "max_per_m2": {"type": "number"}
                }
            },
            "unit": {
                "type": "string",
                "enum": ["m²", "ml", "ud", "m³", "kg"],
                "description": "Measurement unit"
            }
        },
        "required": ["quantity_type", "scope", "unit", "typical_rules", "constraints"]
    }
    
    # Build properties for each task_id
    properties = {}
    for task_id in task_ids:
        properties[task_id] = quantity_guidance_schema
    
    # The full schema requires ALL task_ids
    return {
        "type": "object",
        "properties": properties,
        "required": task_ids  # EVERY task MUST appear in output
    }


async def enrich_batch(tasks: List[Dict]) -> Dict[str, Dict]:
    """
    Enrich a batch of tasks with quantity_guidance.
    
    Uses response_schema to FORCE completeness - Gemini cannot skip any task.
    """
    
    # Build task list for prompt
    task_list = []
    task_ids = []
    for task in tasks:
        task_ids.append(task["id"])
        task_list.append({
            "id": task["id"],
            "name": task["name"],
            "layer": task.get("layer", "unknown"),
            "primary_trade": task.get("primary_trade", "unknown"),
            "bcca_chapter": task.get("bcca_chapter", "unknown")
        })
    
    # Build schema that requires ALL task IDs
    response_schema = build_response_schema(task_ids)
    
    prompt = f"""Eres un Aparejador español senior con 30 años de experiencia en mediciones de obra.

Tu tarea: definir EXACTAMENTE cómo calcular la CANTIDAD para cada partida de construcción.

== TAREAS A ANALIZAR ({len(tasks)} total) ==
{json.dumps(task_list, ensure_ascii=False, indent=2)}

== INSTRUCCIONES CRÍTICAS ==

Para CADA tarea, razona desde PRINCIPIOS DE CONSTRUCCIÓN:

1. **quantity_type** - ¿Cómo se mide físicamente?
   - "area_m2": Superficies (suelos, paredes, techos, impermeabilizaciones)
   - "linear_m": Líneas (rodapiés, tuberías, molduras, vigas)
   - "count": Unidades discretas (enchufes, sanitarios, puertas, splits)
   - "volume_m3": Volúmenes (escombros, hormigón, áridos)
   - "fixed": Siempre 1 (cuadro eléctrico principal, caldera, proyecto, licencia)

2. **scope** - ¿A qué nivel se calcula?
   - "per_room": Calcular para cada habitación (la mayoría de acabados)
   - "per_property": Calcular para toda la vivienda (instalaciones generales, escombros)
   - "per_opening": Calcular por hueco (vigas, puertas, ventanas)
   - "fixed": Independiente del tamaño (siempre 1)

3. **reasoning_factors** - ¿Qué información necesita Gemini para calcular?
   Ejemplos: room_m2, room_perimeter, room_height, wall_count, window_count, 
   door_count, wet_zone_type, property_total_m2, opening_width, opening_height

4. **typical_rules** - Reglas prácticas españolas (REBT, CTE, práctica profesional)
   - Sé ESPECÍFICO: "1 punto luz cada 2.5m² según REBT" no "varios puntos"
   - Incluye factores de desperdicio si aplican

5. **constraints** - Límites de seguridad
   - min: Mínimo razonable (normalmente 1)
   - max_per_room: Máximo por habitación para detectar errores
   - max_per_m2: Máximo por m² si es proporcional

6. **unit** - Unidad de medida exacta

== PRINCIPIOS FUNDAMENTALES ==

NO uses reglas anecdóticas. Razona desde:
- Normativa española vigente (REBT, CTE, ordenanzas)
- Principios físicos (área = largo × ancho, perímetro = 2(l+a))
- Práctica profesional común en España
- Seguridad (nunca menos de los mínimos legales)

== RESPUESTA ==

Responde con un objeto JSON donde cada clave es el task_id:

{{
  "TASK_XXX": {{
    "quantity_type": "...",
    "scope": "...",
    "reasoning_factors": [...],
    "typical_rules": [...],
    "constraints": {{"min": N, "max_per_room": N}},
    "unit": "..."
  }},
  ...
}}

DEBES incluir las {len(tasks)} tareas. La schema lo requiere.
"""
    
    config = types.GenerateContentConfig(
        temperature=0.1,  # Low temperature for consistency
        max_output_tokens=65000,
        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        response_mime_type="application/json",
        response_schema=response_schema,
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[types.Content(role='user', parts=[types.Part.from_text(text=prompt)])],
                config=config
            )
            
            if response.text:
                # Schema enforces JSON format, so this should parse cleanly
                try:
                    result = json.loads(response.text)
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error despite schema: {e}")
                    logger.debug(f"Response: {response.text[:500]}...")
            else:
                logger.warning(f"Empty response on attempt {attempt + 1}")
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini error on attempt {attempt + 1}: {e}")
            
            if "429" in error_str:
                wait = 60 * (attempt + 1)
                logger.info(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            elif "INVALID_ARGUMENT" in error_str:
                # Schema might be too complex, try without
                logger.warning("Schema rejected, trying without response_schema...")
                config_fallback = types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=65000,
                    thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                )
                try:
                    response = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=[types.Content(role='user', parts=[types.Part.from_text(text=prompt)])],
                        config=config_fallback
                    )
                    if response.text:
                        # Parse manually
                        text = response.text
                        if '```json' in text:
                            text = text.split('```json')[1].split('```')[0]
                        elif '```' in text:
                            text = text.split('```')[1].split('```')[0]
                        return json.loads(text.strip())
                except Exception as fallback_e:
                    logger.error(f"Fallback also failed: {fallback_e}")
            else:
                time.sleep(5)
    
    return {}


async def main():
    """Main enrichment process."""
    
    logger.info("=" * 70)
    logger.info("🔧 ENRICHING KG WITH QUANTITY GUIDANCE (Schema-Enforced)")
    logger.info("=" * 70)
    logger.info("Model: gemini-3-flash-preview")
    logger.info("Thinking: HIGH")
    logger.info("Response Schema: ENABLED (forces completeness)")
    logger.info("=" * 70)
    
    # Load KG
    logger.info(f"\nLoading KG from {KG_PATH}...")
    with open(KG_PATH, 'r', encoding='utf-8') as f:
        kg = json.load(f)
    
    tasks = list(kg['canonical_tasks'].values())
    logger.info(f"Total tasks: {len(tasks)}")
    
    # Check how many already have quantity_guidance
    already_enriched = sum(1 for t in tasks if t.get('quantity_guidance'))
    logger.info(f"Already enriched: {already_enriched}")
    
    tasks_to_enrich = [t for t in tasks if not t.get('quantity_guidance')]
    logger.info(f"Tasks to enrich: {len(tasks_to_enrich)}")
    
    if not tasks_to_enrich:
        logger.info("✅ All tasks already have quantity_guidance!")
        return
    
    # Process in batches
    # Smaller batches = more reliable schema enforcement
    batch_size = 20
    total_batches = (len(tasks_to_enrich) + batch_size - 1) // batch_size
    total_enriched = 0
    missing_tasks = []
    
    for i in range(0, len(tasks_to_enrich), batch_size):
        batch = tasks_to_enrich[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        logger.info(f"\n📦 Batch {batch_num}/{total_batches}: {len(batch)} tasks")
        batch_task_ids = [t["id"] for t in batch]
        
        results = await enrich_batch(batch)
        
        if not results:
            logger.error(f"  ❌ Batch {batch_num} failed completely")
            missing_tasks.extend(batch_task_ids)
            continue
        
        # Merge results into KG
        batch_success = 0
        for task_id in batch_task_ids:
            if task_id in results:
                kg['canonical_tasks'][task_id]['quantity_guidance'] = results[task_id]
                total_enriched += 1
                batch_success += 1
            else:
                logger.warning(f"  ⚠️ Missing: {task_id}")
                missing_tasks.append(task_id)
        
        logger.info(f"  ✓ Enriched {batch_success}/{len(batch)} tasks")
        
        # Save progress after each batch
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(kg, f, ensure_ascii=False, indent=2)
        
        # Rate limiting
        if i + batch_size < len(tasks_to_enrich):
            logger.info("  Waiting 2s for rate limits...")
            time.sleep(2)
    
    # Final save
    logger.info(f"\n💾 Saving updated KG...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)
    
    # Verify
    with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
        kg_verify = json.load(f)
    
    final_count = sum(1 for t in kg_verify['canonical_tasks'].values() if t.get('quantity_guidance'))
    
    logger.info("\n" + "=" * 70)
    logger.info(f"✅ ENRICHMENT COMPLETE")
    logger.info(f"  Tasks with quantity_guidance: {final_count}/{len(kg_verify['canonical_tasks'])}")
    if missing_tasks:
        logger.warning(f"  ⚠️ Missing tasks ({len(missing_tasks)}): {missing_tasks[:10]}...")
    logger.info("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
