#!/usr/bin/env python3
"""
Process Knowledge Extraction Script
PETER AGENTIC V0.3 - Process Module

APPROACH: Extract renovation PROCESS knowledge (not technical specs)
- The 10-step rehabilitation journey
- Community decision-making (Comunidad de Propietarios)
- Subsidy navigation
- What triggers rehabilitation
- Homeowner FAQs and expectations
- Professional roles (architect, administrator, constructor)

SOURCE: CSCAE Guía Vecinal de Rehabilitación (4th Edition 2023)
- Published by Spanish Architects' Council + Neighborhood Associations
- Written FOR homeowners, not professionals
- ~30K tokens

OUTPUT: renovation_process_knowledge.json
- Used in onboarding, timeline explanations, "what to expect"
- Complements energy_knowledge.json (technical) with process (practical)
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
OUTPUT_PATH = STANDARDS_DIR / "renovation_process_knowledge.json"

# Source document
SOURCE_DOCUMENT = {
    "id": "CSCAE-GuiaVecinal",
    "file": "CSCAE_Guia_Vecinal_2023.txt",
    "title": "Guía Vecinal de Rehabilitación",
    "short_title": "Guía Vecinal CSCAE (4ª Ed.)",
    "url": "https://portal.coag.es/wp-content/uploads/2023/10/Guia-Vecinal-CSCAE_4aEdicion_Paginas.pdf",
    "authority": "Consejo Superior de los Colegios de Arquitectos de España (CSCAE) + Confederación Estatal de Asociaciones Vecinales (CEAV)",
    "year": 2023,
    "edition": "4th",
    "type": "practical_guide",
    "audience": "Homeowners (vecinos)",
    "use_for": [
        "10-step rehabilitation process",
        "Community decision-making",
        "Subsidy navigation",
        "Homeowner communication",
        "Setting expectations"
    ]
}

# Import Gemini client
try:
    from pipeline.gemini_client import call_gemini
    GEMINI_AVAILABLE = True
    logger.info("✅ Gemini client loaded")
except ImportError as e:
    logger.error(f"❌ Cannot import Gemini client: {e}")
    sys.exit(1)


def load_source() -> tuple[str, dict]:
    """Load the CSCAE guide."""
    logger.info("📚 Loading CSCAE Guía Vecinal...")
    
    filepath = STANDARDS_DIR / SOURCE_DOCUMENT["file"]
    if not filepath.exists():
        logger.error(f"   ❌ Not found: {filepath}")
        sys.exit(1)
    
    content = filepath.read_text(encoding='utf-8', errors='ignore')
    chars = len(content)
    tokens = chars // 4
    
    logger.info(f"   ✅ {SOURCE_DOCUMENT['short_title']}: {chars:,} chars (~{tokens:,} tokens)")
    
    SOURCE_DOCUMENT["chars"] = chars
    SOURCE_DOCUMENT["tokens_approx"] = tokens
    
    return content, SOURCE_DOCUMENT


async def synthesize_process_knowledge(source_content: str, source_meta: dict) -> dict:
    """Extract process knowledge from CSCAE guide."""
    logger.info("\n🤖 Extracting process knowledge with Gemini...")
    
    prompt = f"""You are extracting practical renovation process knowledge from the official Spanish architects' guide for homeowners.

# ============================================================
# SOURCE DOCUMENT
# ============================================================
Title: {source_meta['title']}
Authority: {source_meta['authority']}
Audience: {source_meta['audience']}
Year: {source_meta['year']} (4th Edition)

# ============================================================
# FULL CONTENT
# ============================================================

{source_content}

# ============================================================
# YOUR TASK: EXTRACT PROCESS KNOWLEDGE
# ============================================================

This guide is written FOR HOMEOWNERS, not professionals. Extract the practical process knowledge that helps people understand:
- What to expect during rehabilitation
- How to make decisions as a community
- How to navigate subsidies
- What professionals to involve and when

## 1. THE 10-STEP PROCESS
Extract the complete "Rehabilitar en 10 Pasos" with:
- Step number and name (in Spanish)
- What happens in this step
- Who is involved
- Key decisions/documents
- Tips for homeowners

## 2. REHABILITATION TRIGGERS
What makes people start rehabilitation:
- ITE failures
- High energy bills
- Accessibility needs
- Building problems (humidity, cracks)
- Regulatory requirements

## 3. COMMUNITY DECISION-MAKING
How comunidades de propietarios decide:
- Voting requirements (quorum, majorities)
- Ley de Propiedad Horizontal basics
- How to propose works
- Dealing with disagreements

## 4. SUBSIDY NAVIGATION
From the guide's perspective:
- Types of subsidies mentioned
- Application process
- Timing considerations
- Documentation needed

## 5. PROFESSIONAL ROLES
Who does what:
- Arquitecto/a - when and why
- Administrador de fincas - role
- Constructora - selection process
- Oficinas de Apoyo a la Rehabilitación

## 6. HOMEOWNER FAQs
Common concerns addressed in the guide:
- Cost expectations
- Timeline expectations
- What happens during works
- After the works (maintenance)

## 7. COMMUNICATION TEMPLATES
Useful phrases/explanations from the guide that we can reuse to communicate with homeowners.

Return JSON with this structure:
{{
    "ten_steps": [
        {{
            "step": 1,
            "name_es": "<Spanish name>",
            "name_en": "<English translation>",
            "description": "<what happens>",
            "participants": ["<who is involved>"],
            "key_documents": ["<documents if any>"],
            "homeowner_tip": "<practical advice>",
            "typical_duration": "<if mentioned>"
        }},
        ...
    ],
    "triggers": {{
        "regulatory": ["<ITE, etc>"],
        "economic": ["<high bills, etc>"],
        "comfort": ["<accessibility, etc>"],
        "building_problems": ["<humidity, cracks, etc>"]
    }},
    "community_decisions": {{
        "voting_requirements": {{
            "simple_majority": "<when>",
            "qualified_majority": "<when>",
            "unanimity": "<when>"
        }},
        "how_to_propose": "<process>",
        "key_meetings": ["<types of meetings>"],
        "tips": ["<advice>"]
    }},
    "subsidies": {{
        "types_mentioned": ["<subsidy types>"],
        "application_process": "<summary>",
        "timing_advice": "<when to apply>",
        "documentation": ["<what's needed>"]
    }},
    "professionals": {{
        "arquitecto": {{
            "role": "<what they do>",
            "when_needed": "<stages>",
            "how_to_find": "<advice from guide>"
        }},
        "administrador_fincas": {{
            "role": "<what they do>",
            "coordination": "<how they help>"
        }},
        "constructora": {{
            "selection": "<how to choose>",
            "minimum_quotes": <number>,
            "evaluation_criteria": ["<what to look for>"]
        }},
        "oficinas_apoyo": {{
            "what_are_they": "<description>",
            "services": ["<what they offer>"]
        }}
    }},
    "homeowner_faqs": [
        {{
            "question_es": "<in Spanish>",
            "question_en": "<in English>",
            "answer": "<from the guide>"
        }},
        ...
    ],
    "communication_phrases": {{
        "explaining_benefits": ["<useful phrases>"],
        "setting_expectations": ["<useful phrases>"],
        "addressing_concerns": ["<useful phrases>"]
    }},
    "key_quotes": [
        {{
            "quote_es": "<memorable quote from guide>",
            "context": "<when to use>"
        }},
        ...
    ]
}}

IMPORTANT:
- Keep Spanish terminology where it's standard (ITE, comunidad de propietarios, etc.)
- Include both Spanish and English where helpful
- Focus on PRACTICAL knowledge, not technical specs
- Use the guide's friendly, accessible tone"""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=65000,
    )
    
    if response.success:
        text = response.text
        logger.info("   ✅ Gemini extraction complete")
        
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


def build_ui_references(source_meta: dict) -> dict:
    """Build reference section for UI."""
    return {
        "disclaimer_es": "Esta información proviene de la Guía Vecinal de Rehabilitación del CSCAE. Para asesoramiento específico, consulte a un arquitecto o las Oficinas de Apoyo a la Rehabilitación.",
        "disclaimer_en": "This information comes from the CSCAE Neighborhood Rehabilitation Guide. For specific advice, consult an architect or the Rehabilitation Support Offices.",
        "source": {
            "title": source_meta["title"],
            "short_title": source_meta["short_title"],
            "url": source_meta["url"],
            "authority": source_meta["authority"],
            "year": source_meta["year"],
            "edition": source_meta["edition"]
        },
        "support_resources": [
            {
                "name": "Oficinas de Apoyo a la Rehabilitación",
                "description": "Red de oficinas de los Colegios de Arquitectos que asesoran gratuitamente a comunidades de propietarios",
                "url": "https://www.cscae.com/index.php/conoce-cscae/red-oficinas",
                "note": "Free advice for property communities"
            },
            {
                "name": "CSCAE",
                "full_name": "Consejo Superior de los Colegios de Arquitectos de España",
                "url": "https://www.cscae.com/",
                "role": "Spanish Architects' Council - publishes official guides"
            }
        ]
    }


async def main():
    print("=" * 70)
    print("PETER AGENTIC V0.3 - Process Knowledge Extraction")
    print("Source: CSCAE Guía Vecinal de Rehabilitación")
    print("=" * 70)
    print()
    
    # Step 1: Load source
    source_content, source_meta = load_source()
    
    # Step 2: Extract with Gemini
    knowledge = await synthesize_process_knowledge(source_content, source_meta)
    
    if not knowledge:
        logger.error("\n❌ Extraction failed. Cannot proceed.")
        sys.exit(1)
    
    # Step 3: Build UI references
    logger.info("\n📋 Building UI reference section...")
    ui_references = build_ui_references(source_meta)
    
    # Step 4: Package output
    logger.info("\n📦 Packaging process knowledge...")
    
    output = {
        "$schema": "process_knowledge_v1",
        "$version": "1.0.0",
        "$created": datetime.now().isoformat(),
        "$approach": "CSCAE Guía Vecinal → Gemini synthesis → Practical process knowledge",
        "$source_tokens": source_meta.get("tokens_approx", 0),
        
        # Source tracking
        "references": ui_references,
        
        # Extracted knowledge
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
    logger.info(f"   10 Steps: {len(output.get('ten_steps', []))}")
    logger.info(f"   Triggers: {sum(len(v) for v in output.get('triggers', {}).values())} items")
    logger.info(f"   Professionals: {len(output.get('professionals', {}))}")
    logger.info(f"   FAQs: {len(output.get('homeowner_faqs', []))}")
    logger.info(f"   Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())

