#!/usr/bin/env python3
"""
Energy Knowledge Extraction Script
PETER AGENTIC V0.3 - Energy Module Phase 0

APPROACH: FEED FULL SOURCE DOCUMENTS TO GEMINI → SYNTHESIZE
- Full CTE-DB-HE.txt (Spanish Energy Code)
- Full CTE-DB-HS.txt (Ventilation requirements)
- Full IDAE CE3X Manual (professional rating software methodology)
- Full IDAE Rehabilitation Guide (homeowner-friendly language)
- Full IDAE Subsidy Guide (practical renovation pathways)
- Full Decreto 10/2019 (Habitability requirements)

Total: ~292K tokens (29% of 1M limit)

SOURCE TRACKING: Each synthesized item references back to source documents
for UI disclaimers and professional verification.
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Paths
STANDARDS_DIR = BACKEND_DIR.parent / "standards"
OUTPUT_PATH = STANDARDS_DIR / "energy_knowledge.json"

# =============================================================================
# SOURCE DOCUMENTS - FULL TEXTS (with metadata for UI references)
# =============================================================================

SOURCE_DOCUMENTS = {
    # Primary regulatory sources
    "CTE-DB-HE": {
        "file": "CTE-DB-HE.txt",
        "title": "Código Técnico de la Edificación - Documento Básico HE (Ahorro de Energía)",
        "short_title": "CTE DB-HE 2022",
        "url": "https://www.codigotecnico.org/pdf/Documentos/HE/DBHE.pdf",
        "authority": "Ministerio de Transportes, Movilidad y Agenda Urbana",
        "year": 2022,
        "type": "regulatory",
        "use_for": ["U-value limits", "energy consumption limits", "climate zones", "renewable requirements"]
    },
    "CTE-DB-HS": {
        "file": "CTE-DB-HS.txt",
        "title": "Código Técnico de la Edificación - Documento Básico HS (Salubridad)",
        "short_title": "CTE DB-HS",
        "url": "https://www.codigotecnico.org/pdf/Documentos/HS/DBHS.pdf",
        "authority": "Ministerio de Transportes, Movilidad y Agenda Urbana",
        "year": 2022,
        "type": "regulatory",
        "use_for": ["ventilation requirements", "air quality", "humidity control"]
    },
    
    # IDAE practical guides
    "IDAE-CE3X": {
        "file": "IDAE_CE3X_Manual_Mejoras.txt",
        "title": "Guía de recomendaciones de eficiencia energética - CE³X",
        "short_title": "Manual CE3X (IDAE)",
        "url": "https://www.certificadosenergeticos.com/wp-content/uploads/2015/04/Manual_medidas_mejora_CE3X_03.pdf",
        "authority": "Instituto para la Diversificación y Ahorro de la Energía (IDAE)",
        "year": 2012,
        "type": "technical_guide",
        "use_for": ["improvement measures", "rating methodology", "professional certification process"]
    },
    "IDAE-Rehabilitacion": {
        "file": "IDAE_Guia_Rehabilitacion_Aislamiento.txt",
        "title": "Guía práctica de la energía para la rehabilitación de edificios",
        "short_title": "Guía Rehabilitación (IDAE)",
        "url": "https://www.idae.es/uploads/documentos/documentos_10501_Guia_practica_rehabilitacion_edificios_aislamiento_5266ec2a.pdf",
        "authority": "IDAE",
        "year": 2008,
        "type": "practical_guide",
        "use_for": ["homeowner-friendly explanations", "insulation benefits", "practical advice"]
    },
    "IDAE-Ayudas": {
        "file": "IDAE_Guia_Ayudas_Rehabilitacion_2021.txt",
        "title": "Guía Práctica para la Gestión de Ayudas a la Rehabilitación Energética de Edificios",
        "short_title": "Guía Ayudas 2021 (IDAE)",
        "url": "https://www.idae.es/sites/default/files/documentos/ayudas_y_financiacion/GUIA_PRACTICA_PARA_LA_GESTION_DE_AYUDAS_A_LA_REHABILITACION_ENERGETICA_EDIFICIOS_2021.pdf",
        "authority": "IDAE / Plan de Recuperación",
        "year": 2021,
        "type": "subsidy_guide",
        "use_for": ["subsidy requirements", "eligible improvements", "cost-effectiveness"]
    },
    
    # Regional regulations
    "Decreto-Extremadura": {
        "file": "decreto-10-2019-extremadura.txt",
        "title": "Decreto 10/2019 - Condiciones de Habitabilidad de Extremadura",
        "short_title": "Decreto Habitabilidad Extremadura",
        "url": "https://doe.juntaex.es/pdfs/doe/2019/340o/19040032.pdf",
        "authority": "Junta de Extremadura",
        "year": 2019,
        "type": "regulatory",
        "use_for": ["habitability requirements", "minimum dimensions", "building standards"]
    }
}

# Import Gemini client from pipeline
try:
    from pipeline.gemini_client import call_gemini
    GEMINI_AVAILABLE = True
    logger.info("✅ Gemini client loaded")
except ImportError as e:
    logger.error(f"❌ Cannot import Gemini client: {e}")
    sys.exit(1)


def load_all_sources() -> tuple[str, dict]:
    """Load all source documents and build context."""
    logger.info("📚 Loading FULL source documents...")
    
    context_parts = []
    loaded_sources = {}
    total_chars = 0
    
    for source_id, source_meta in SOURCE_DOCUMENTS.items():
        filepath = STANDARDS_DIR / source_meta["file"]
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            total_chars += len(content)
            
            context_parts.append(f"""
# ============================================================
# SOURCE: {source_meta['short_title']}
# Authority: {source_meta['authority']}
# Use for: {', '.join(source_meta['use_for'])}
# ============================================================

{content}
""")
            loaded_sources[source_id] = {
                **source_meta,
                "chars": len(content),
                "tokens_approx": len(content) // 4
            }
            logger.info(f"   ✅ {source_meta['short_title']}: {len(content):,} chars (~{len(content)//4:,} tokens)")
        else:
            logger.warning(f"   ⚠️ Not found: {source_meta['file']}")
    
    full_context = "\n".join(context_parts)
    estimated_tokens = len(full_context) // 4
    
    logger.info(f"\n   📊 Total context: {total_chars:,} chars (~{estimated_tokens:,} tokens)")
    logger.info(f"   📊 Context window usage: {estimated_tokens * 100 // 1000000}% of 1M limit")
    
    return full_context, loaded_sources


async def synthesize_energy_knowledge(standards_context: str, sources: dict) -> dict:
    """Feed all source documents to Gemini and synthesize energy knowledge."""
    logger.info("\n🤖 Feeding FULL source documents to Gemini for synthesis...")
    
    # Build source reference list for the prompt
    source_list = "\n".join([
        f"- [{sid}] {s['short_title']} ({s['year']}) - {s['authority']}"
        for sid, s in sources.items()
    ])
    
    prompt = f"""You are a Spanish building energy expert. I'm providing you with COMPLETE official Spanish building and energy standards documentation. Your task is to synthesize comprehensive energy knowledge for a renovation intelligence system.

# ============================================================
# AVAILABLE SOURCE DOCUMENTS (cite these in your responses)
# ============================================================

{source_list}

# ============================================================
# FULL SOURCE CONTENT
# ============================================================

{standards_context}

# ============================================================
# YOUR TASK: SYNTHESIZE ENERGY KNOWLEDGE WITH SOURCE CITATIONS
# ============================================================

Based on the ACTUAL content above, create a comprehensive energy knowledge base. 
For each piece of information, cite the source document using [SOURCE_ID].

## 1. ENERGY RATING SCALE (ALL 7 LEVELS: A, B, C, D, E, F, G)
Extract from CTE-DB-HE - provide EACH letter separately with:
- Primary energy consumption limits (kWh/m²·año) per climate zone
- CO2 emissions limits
- What buildings typically achieve this rating
- Market/financial implications
- Comfort level description

## 2. SPANISH CLIMATE ZONES (A, B, C, D, E)
Extract from CTE-DB-HE tables:
- Representative cities for each zone
- U-value limits for walls, roofs, floors, windows
- Heating Degree Days (HDD)
- Solar radiation characteristics

## 3. BUILDING AGE → EXPECTED RATING
Based on regulatory timeline (6 periods):
- Pre-1940 (no regulations)
- 1940-1979 (minimal requirements)
- 1980-2006 (NBE-CT-79)
- 2007-2013 (CTE 2006)
- 2014-2019 (CTE updates)
- Post-2020 (nZEB requirements)
Include: regulations applied, typical rating, construction methods, common deficiencies

## 4. INTERVENTION ENERGY IMPACTS (ALL interventions from CE3X)
Extract from IDAE CE3X Manual and CTE limits. For EACH intervention provide:
- Technical description
- U-value improvement (before → after)
- Typical letter improvement
- Climate zone sensitivity
- Homeowner benefit (in simple IDAE language)
- Cost-effectiveness notes
- Subsidy eligibility

Interventions to cover:
- window_replacement (vidrios y marcos)
- wall_insulation_sate (sistema exterior)
- wall_insulation_trasdosado (sistema interior)
- roof_insulation (cubierta)
- floor_insulation (solera/forjado)
- heat_pump_aerothermal (aerotermia)
- heat_pump_geothermal (geotermia)
- solar_thermal_acs (solar térmica ACS)
- photovoltaic (fotovoltaica)
- condensing_boiler (caldera condensación)
- mechanical_ventilation (ventilación mecánica con recuperador)
- led_lighting (iluminación LED)
- hvac_controls (termostatos y control)

## 5. UPGRADE PATHWAYS (subsidy-aligned from IDAE Ayudas)
From IDAE Subsidy Guide 2021:
- G→E pathway (30% improvement minimum)
- E→C pathway (45% improvement)
- C→A pathway (60% improvement, nZEB)
- Complete rehabilitation pathway
Include: required interventions, % energy reduction, subsidy brackets, typical costs

## 6. HOMEOWNER-FRIENDLY EXPLANATIONS
From IDAE Rehabilitation Guide - use their actual language!
- Comfort benefits for each intervention
- Bill savings estimates
- Health benefits (humidity, air quality)
- Property value impact
- "Efecto termo" concept
- Acoustic benefits

## 7. PROFESSIONAL CONTEXT
From CE3X Manual:
- How energy ratings are calculated (methodology)
- Input data requirements
- Common improvement recommendations by building type
- Certification process steps
- Validity period and renewal

## 8. REGULATORY REQUIREMENTS
From CTE-DB-HE and Decreto:
- When certification is mandatory
- Minimum requirements for renovations
- Protected building exceptions
- Local variations

Return COMPREHENSIVE JSON with this structure (include source citations in each section):
{{
    "rating_scale": {{
        "A": {{ 
            "primary_energy_kwh_m2": {{ "zone_A": <num>, "zone_B": <num>, "zone_C": <num>, "zone_D": <num>, "zone_E": <num> }},
            "co2_kg_m2": {{ ... }},
            "description": "<str>", 
            "typical_building": "<str>", 
            "comfort_level": "<str>",
            "market_value_impact": "<str>",
            "sources": ["CTE-DB-HE"] 
        }},
        "B": {{ ... }},
        "C": {{ ... }},
        "D": {{ ... }},
        "E": {{ ... }},
        "F": {{ ... }},
        "G": {{ ... }}
    }},
    "climate_zones": {{
        "zone_A": {{ "cities": ["<str>"], "u_wall": <num>, "u_roof": <num>, "u_window": <num>, "hdd": <num>, "sources": ["CTE-DB-HE"] }},
        "zone_B": {{ ... }},
        "zone_C": {{ ... }},
        "zone_D": {{ ... }},
        "zone_E": {{ ... }}
    }},
    "age_correlation": {{
        "pre_1940": {{ "typical_rating": "<letter>", "regulation": "<str>", "construction_methods": ["<str>"], "common_issues": ["<str>"], "sources": ["<source_id>"] }},
        "1940_1979": {{ ... }},
        "1980_2006": {{ ... }},
        "2007_2013": {{ ... }},
        "2014_2019": {{ ... }},
        "post_2020": {{ ... }}
    }},
    "interventions": {{
        "window_replacement": {{
            "description_technical": "<str>",
            "description_homeowner": "<simple explanation from IDAE>",
            "u_value_typical_old": <num>,
            "u_value_achievable": <num>,
            "typical_improvement_letters": <num>,
            "climate_sensitivity": "<which zones benefit most>",
            "comfort_benefits": ["<str>"],
            "cost_effectiveness": "<str>",
            "subsidy_eligible": <bool>,
            "sources": ["CTE-DB-HE", "IDAE-CE3X", "IDAE-Rehabilitacion"]
        }},
        "wall_insulation_sate": {{ ... }},
        "wall_insulation_trasdosado": {{ ... }},
        "roof_insulation": {{ ... }},
        "floor_insulation": {{ ... }},
        "heat_pump_aerothermal": {{ ... }},
        "heat_pump_geothermal": {{ ... }},
        "solar_thermal_acs": {{ ... }},
        "photovoltaic": {{ ... }},
        "condensing_boiler": {{ ... }},
        "mechanical_ventilation": {{ ... }},
        "led_lighting": {{ ... }},
        "hvac_controls": {{ ... }}
    }},
    "upgrade_pathways": {{
        "G_to_E": {{ 
            "min_improvement_percent": 30,
            "typical_interventions": ["<str>"],
            "subsidy_bracket": "<str>",
            "typical_cost_range_eur_m2": "<str>",
            "sources": ["IDAE-Ayudas"] 
        }},
        "E_to_C": {{ ... }},
        "C_to_A": {{ ... }},
        "complete_rehabilitation": {{ ... }}
    }},
    "homeowner_tips": {{
        "comfort": "<explanation from IDAE>",
        "savings": "<explanation with %% estimates>",
        "health": "<air quality, humidity benefits>",
        "property_value": "<explanation>",
        "efecto_termo": "<IDAE's termo analogy>",
        "acoustic": "<noise reduction benefits>",
        "sources": ["IDAE-Rehabilitacion"]
    }},
    "professional_context": {{
        "ce3x_methodology": "<how ratings are calculated>",
        "required_inputs": ["<str>"],
        "certification_validity_years": <num>,
        "common_recommendations_residential": ["<str>"],
        "common_recommendations_tertiary": ["<str>"],
        "sources": ["IDAE-CE3X"]
    }},
    "regulatory_requirements": {{
        "mandatory_certification": ["<when required>"],
        "renovation_thresholds": "<when CTE applies to renovations>",
        "protected_buildings": "<exceptions>",
        "sources": ["CTE-DB-HE", "Decreto-Extremadura"]
    }}
}}

IMPORTANT: 
- Use ACTUAL numbers from CTE tables (e.g., "U-value limit 0.49 W/m²K for Zone C")
- Quote homeowner-friendly language from IDAE guides where possible
- Cite sources for each section using the [SOURCE_ID] format"""

    response = await call_gemini(
        prompt=prompt,
        model="pro",  # Use pro for complex synthesis with large context
        temperature=0.2,
        max_tokens=65000,  # MAXED OUT - extract everything from 287K source tokens
    )
    
    if response.success:
        text = response.text
        logger.info("   ✅ Gemini synthesis complete")
        
        try:
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse JSON: {e}")
            logger.error(f"   Response preview: {text[:1000]}")
            return None
    else:
        logger.error(f"   ❌ Gemini call failed: {response.error}")
        return None


def build_ui_references(sources: dict) -> dict:
    """Build reference section for UI disclaimers."""
    return {
        "disclaimer": "La información de eficiencia energética se basa en normativa española oficial. Para certificación profesional, consulte a un técnico certificador.",
        "disclaimer_en": "Energy efficiency information is based on official Spanish regulations. For professional certification, consult a certified technician.",
        "primary_sources": {
            sid: {
                "title": s["title"],
                "short_title": s["short_title"],
                "url": s["url"],
                "authority": s["authority"],
                "year": s["year"],
                "type": s["type"]
            }
            for sid, s in sources.items()
        },
        "certification_bodies": [
            {
                "name": "IDAE",
                "full_name": "Instituto para la Diversificación y Ahorro de la Energía",
                "url": "https://www.idae.es/",
                "role": "National energy efficiency authority, maintains CE3X software"
            },
            {
                "name": "Ministerio de Transportes",
                "full_name": "Ministerio de Transportes, Movilidad y Agenda Urbana",
                "url": "https://www.mitma.gob.es/",
                "role": "Maintains CTE building code"
            }
        ],
        "professional_tools": [
            {
                "name": "CE3X",
                "description": "Software oficial de certificación energética de edificios existentes",
                "url": "https://www.idae.es/informacion-y-publicaciones/publicaciones-de-ahorro-y-eficiencia-energetica",
                "note": "Used by certified technicians for official energy ratings"
            }
        ]
    }


async def main():
    print("=" * 70)
    print("PETER AGENTIC V0.3 - Energy Knowledge Extraction")
    print("FULL SOURCE DOCUMENTS + SOURCE TRACKING")
    print("=" * 70)
    print()
    
    # Step 1: Load all source documents
    standards_context, loaded_sources = load_all_sources()
    
    # Step 2: Synthesize with Gemini
    knowledge = await synthesize_energy_knowledge(standards_context, loaded_sources)
    
    if not knowledge:
        logger.error("\n❌ Synthesis failed. Cannot proceed.")
        sys.exit(1)
    
    # Step 3: Build UI references
    logger.info("\n📋 Building UI reference section...")
    ui_references = build_ui_references(loaded_sources)
    
    # Step 4: Package output
    logger.info("\n📦 Packaging energy knowledge...")
    
    # Handle nested structure if Gemini wrapped it
    if 'energy_knowledge_base' in knowledge:
        knowledge = knowledge['energy_knowledge_base']
    
    output = {
        "$schema": "energy_knowledge_v1",
        "$version": "1.0.0",
        "$created": datetime.now().isoformat(),
        "$approach": "FULL SOURCE DOCUMENTS fed to Gemini for synthesis",
        "$total_tokens": sum(s.get("tokens_approx", 0) for s in loaded_sources.values()),
        
        # Source tracking for UI
        "references": ui_references,
        
        # Synthesized knowledge
        **knowledge
    }
    
    # Save
    logger.info(f"\n💾 Writing to {OUTPUT_PATH}...")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Stats
    file_size = OUTPUT_PATH.stat().st_size
    
    logger.info(f"\n✅ Done!")
    logger.info(f"   File size: {file_size:,} bytes")
    logger.info(f"   Sources loaded: {len(loaded_sources)}")
    logger.info(f"   Rating scale levels: {len(output.get('rating_scale', {}))}")
    logger.info(f"   Age correlations: {len(output.get('age_correlation', {}))}")
    logger.info(f"   Interventions: {len(output.get('interventions', {}))}")
    logger.info(f"   Output: {OUTPUT_PATH}")
    
    # Print reference section for verification
    logger.info("\n📚 UI References:")
    for sid, src in loaded_sources.items():
        logger.info(f"   [{sid}] {src['short_title']} - {src['url'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
