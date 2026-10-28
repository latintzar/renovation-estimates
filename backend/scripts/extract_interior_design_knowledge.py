#!/usr/bin/env python3
"""
Interior Design Knowledge Extraction Script
PETER AGENTIC V0.3.2 - Design Module

APPROACH: Gemini synthesizes from its training knowledge
- Current design trends (2024-2026)
- Spanish brands and retailers
- How to achieve specific looks
- Sourcing guidance (where to buy)
- Indicative FF&E price ranges (not exact - BCCA handles construction)

NOTE: Unlike energy/process KBs, there are no official source documents.
This is synthesized from Gemini's knowledge of interior design, Spanish market.
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
OUTPUT_PATH = STANDARDS_DIR / "interior_design_knowledge.json"

# Import Gemini client
try:
    from pipeline.gemini_client import call_gemini
    GEMINI_AVAILABLE = True
    logger.info("✅ Gemini client loaded")
except ImportError as e:
    logger.error(f"❌ Cannot import Gemini client: {e}")
    sys.exit(1)


async def extract_design_trends() -> dict:
    """Extract current interior design trends."""
    logger.info("\n🎨 Extracting current design trends...")
    
    prompt = """You are a Spanish interior designer working in Madrid and Barcelona, with deep knowledge of current European and international design trends and how they apply to the Spanish market.

Create a comprehensive guide to CURRENT interior design trends (2024-2026). For each trend:

1. **Description** - What defines this style
2. **Key elements** - Specific visual and material indicators
3. **How to achieve** - Practical guidance for each element (walls, flooring, furniture, lighting)
4. **Spain context** - How this works in Spanish homes, climate considerations
5. **Inspiration reference** - What to show clients (hotels, magazines, Instagram accounts)

Cover these trends:
- Warm Minimalism
- Japandi
- Mediterranean Modern (updated, not cliché)
- Quiet Luxury
- Biophilic Design
- New Traditional (modern take on classic)
- Industrial Refined
- Coastal Contemporary

Return JSON:
{
  "trends": {
    "warm_minimalism": {
      "description": "...",
      "key_elements": ["..."],
      "color_palette": ["..."],
      "materials": ["..."],
      "how_to_achieve": {
        "walls": "...",
        "flooring": "...",
        "furniture": "...",
        "lighting": "...",
        "textiles": "...",
        "accessories": "..."
      },
      "spain_context": "...",
      "inspiration": {
        "hotels": ["..."],
        "magazines": ["..."],
        "instagram": ["..."]
      }
    },
    ...
  }
}

Be SPECIFIC - mention actual techniques, materials, and approaches. Not generic advice."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.3,
        max_tokens=30000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse trends: {e}")
            return {}
    return {}


async def extract_spanish_sources() -> dict:
    """Extract Spanish brands and retailers by category."""
    logger.info("\n🏪 Extracting Spanish brands and retailers...")
    
    prompt = """You are a Spanish interior designer with extensive knowledge of where to source furniture, lighting, kitchens, bathrooms, and materials in Spain.

Create a comprehensive sourcing guide for the SPANISH MARKET. Include:

## Categories to cover:
1. **Furniture** (sofas, tables, chairs, beds, storage)
2. **Lighting** (pendants, floor lamps, table lamps, architectural)
3. **Kitchens** (cabinet brands, countertop suppliers)
4. **Bathrooms** (fixtures, tiles, furniture)
5. **Flooring** (tile suppliers, wood suppliers)
6. **Textiles** (rugs, curtains, bedding)
7. **Decor & Accessories**

## For each category, organize by price tier:
- Budget (accessible, IKEA-level)
- Mid-range (quality, reasonable)
- High-end (designer, premium)
- Luxury (top-tier, bespoke)

## For each brand/store include:
- Name
- Origin (Spanish or international)
- Where to buy in Spain (stores, cities, online)
- What they're best for
- Notable product lines or signatures
- Price positioning

## IMPORTANT: Focus on what's actually available in Spain
- Spanish brands (Roca, Porcelanosa, Santos, Marset, Vibia, etc.)
- International brands with good Spain presence
- Online retailers that ship to Spain

Return JSON:
{
  "categories": {
    "furniture": {
      "budget": [
        {
          "name": "IKEA",
          "origin": "International",
          "spain_presence": "12 stores + online",
          "best_for": ["..."],
          "notable_lines": ["..."],
          "website": "..."
        }
      ],
      "mid_range": [...],
      "high_end": [...],
      "luxury": [...]
    },
    "lighting": { ... },
    "kitchens": { ... },
    "bathrooms": { ... },
    "flooring": { ... },
    "textiles": { ... },
    "decor": { ... }
  },
  
  "spanish_brands_spotlight": {
    "furniture": ["Sancal", "Expormim", "Kettal", "Kave Home"],
    "lighting": ["Marset", "Vibia", "Santa & Cole", "LZF"],
    "kitchens": ["Santos", "Dica", "Logos"],
    "bathrooms": ["Roca", "Noken", "Inbani"],
    "tiles": ["Porcelanosa", "Vives", "Equipe", "Grespania"],
    "outdoor": ["Kettal", "Gandia Blasco", "Point"]
  }
}

Be COMPREHENSIVE and ACCURATE about what's available in Spain."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=40000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse sources: {e}")
            return {}
    return {}


async def extract_how_to_achieve() -> dict:
    """Extract detailed guides on how to achieve specific looks."""
    logger.info("\n🛠️ Extracting 'how to achieve' guides...")
    
    prompt = """You are a Spanish interior designer creating practical guides for achieving specific design aesthetics.

For each of these common renovation scenarios, provide DETAILED guidance on how to achieve the look:

## Scenarios:
1. **dated_to_contemporary** - Transform 1970s-80s Spanish apartment to modern
2. **traditional_to_mediterranean_modern** - Update traditional Spanish to fresh Mediterranean
3. **basic_to_warm_minimal** - Elevate builder-grade to warm minimalism
4. **dark_to_bright** - Transform dark, compartmentalized to light and airy
5. **rental_refresh** - Impactful changes without major construction
6. **luxury_minimal** - High-end quiet luxury aesthetic

## For each scenario, provide:
- **Starting point** - What we're typically working with
- **Target aesthetic** - What we're trying to achieve
- **Key transformations** - Priority changes that have most impact
- **Detailed guidance** for:
  - Walls (finishes, colors, techniques)
  - Flooring (materials, colors, patterns)
  - Kitchen approach
  - Bathroom approach
  - Lighting strategy
  - Furniture direction
  - Color palette
  - Materials palette
- **Budget allocation** - Where to spend vs save (%)
- **Common mistakes** - What to avoid
- **Spain-specific tips** - Local considerations

Return JSON:
{
  "transformations": {
    "dated_to_contemporary": {
      "starting_point": "1970s-80s Spanish apartment with gotelé, terrazzo, dark wood",
      "target": "Clean, contemporary, light-filled",
      "priority_changes": [
        {"change": "Remove gotelé", "impact": "high", "effort": "medium"},
        {"change": "Replace flooring", "impact": "high", "effort": "high"},
        ...
      ],
      "walls": {
        "remove": "Gotelé texture",
        "finish": "Smooth plaster, matte paint",
        "colors": ["White", "Warm white", "Light grey"],
        "technique": "Skim coat or full replaster",
        "accent_options": ["Microcement feature wall", "Wood slat wall"]
      },
      "flooring": { ... },
      "kitchen": { ... },
      "bathroom": { ... },
      "lighting": { ... },
      "furniture_direction": { ... },
      "color_palette": { ... },
      "materials_palette": { ... },
      "budget_allocation": {
        "flooring": "25%",
        "kitchen": "30%",
        "bathroom": "20%",
        "walls_paint": "10%",
        "lighting": "10%",
        "furniture_ffe": "5%"
      },
      "common_mistakes": ["..."],
      "spain_specific": ["..."]
    },
    ...
  }
}

Be PRACTICAL and SPECIFIC - this is for real renovation projects."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.3,
        max_tokens=40000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse transformations: {e}")
            return {}
    return {}


async def extract_finish_quality_indicators() -> dict:
    """Extract detailed indicators for identifying finish quality tiers."""
    logger.info("\n🔍 Extracting finish quality indicators...")
    
    prompt = """You are a Spanish real estate appraiser and interior designer who needs to quickly assess the quality tier of finishes in a property from photos.

Create a comprehensive guide for IDENTIFYING finish quality tiers based on OBSERVABLE indicators.

## Quality Tiers:
1. **builder_grade** - Minimum spec, developer standard
2. **mid_range** - Upgraded, quality but not luxury
3. **high_end** - Premium materials, designer elements
4. **luxury** - Top-tier, bespoke, exceptional

## For each tier, provide indicators for:
- Kitchen (cabinets, counters, appliances, hardware)
- Bathroom (fixtures, tiles, vanity, shower)
- Flooring (type, size, pattern, quality indicators)
- Doors (interior, entry)
- Windows (frames, glass)
- Walls (finish, texture)
- Lighting (fixtures, layout)
- Hardware (handles, switches, outlets)

## Include:
- Visual indicators (what to look for in photos)
- Material indicators (specific materials per tier)
- Brand indicators (typical brands per tier in Spain)
- Age indicators (when these finishes were common)
- Red flags (signs of cheap despite appearing expensive)

Return JSON:
{
  "quality_tiers": {
    "builder_grade": {
      "description": "Minimum specification, cost-driven choices",
      "typical_context": "New construction entry-level, unrenovated properties",
      "indicators": {
        "kitchen": {
          "cabinets": {
            "materials": ["Melamine", "Basic MDF"],
            "visual_indicators": ["Visible hinges", "No soft-close", "Basic handles"],
            "brands_spain": ["IKEA basic", "Leroy Merlin entry"]
          },
          "countertops": {
            "materials": ["Laminate", "Basic ceramic tile"],
            "visual_indicators": ["Visible seams", "Thin edge", "Limited colors"]
          },
          "appliances": {
            "type": ["White", "Black basic"],
            "visual_indicators": ["Visible brand badges", "Standard sizes"],
            "brands_spain": ["Balay entry", "Teka basic"]
          },
          "hardware": {
            "visual_indicators": ["Chrome plastic", "Basic shapes"]
          }
        },
        "bathroom": { ... },
        "flooring": { ... },
        "doors": { ... },
        "lighting": { ... },
        "hardware_general": { ... }
      },
      "red_flags": ["..."],
      "age_context": "Standard in 2000s-2010s new builds"
    },
    "mid_range": { ... },
    "high_end": { ... },
    "luxury": { ... }
  },
  
  "quick_assessment_checklist": [
    {"element": "Kitchen cabinets", "builder": "Melamine, visible hinges", "mid": "Lacquer, soft-close", "high": "Custom, handleless", "luxury": "Bespoke, premium wood"},
    ...
  ]
}

This is for QUICK VISUAL ASSESSMENT from property photos."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=30000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse quality indicators: {e}")
            return {}
    return {}


async def extract_ffe_guidance() -> dict:
    """Extract FF&E (Furniture, Fixtures, Equipment) guidance - NOT pricing, just sourcing."""
    logger.info("\n🛋️ Extracting FF&E guidance...")
    
    prompt = """You are a Spanish interior designer helping clients understand FF&E (Furniture, Fixtures & Equipment) - the things NOT included in construction budgets.

Create a comprehensive FF&E guide for the SPANISH MARKET.

## What is FF&E (vs construction)?
- Loose furniture (sofas, beds, tables, chairs)
- Appliances (ovens, fridges, washers, dishwashers)
- Soft furnishings (rugs, curtains, cushions, bedding)
- Lighting fixtures (pendants, floor lamps, table lamps)
- Decor and accessories
- Electronics (TVs, sound systems)
- Outdoor furniture

## For each FF&E category, provide:
1. **What's typically needed** (per room type)
2. **Quality tiers** - What distinguishes budget from luxury
3. **Where to source in Spain** - Specific stores/brands per tier
4. **Indicative budget ranges** - Not exact prices, but guidance like:
   - "Budget sofa: €500-1,000"
   - "Mid-range sofa: €1,500-3,000"
   - "High-end sofa: €3,000-8,000"
5. **How to prioritize** - What to invest in vs save on
6. **Common mistakes**

## Important notes:
- This is SEPARATE from construction costs (BCCA)
- Focus on what you can BUY, not what you BUILD
- Spain-specific sourcing
- Current market (2024-2026)

Return JSON:
{
  "ffe_categories": {
    "living_room": {
      "essential_items": ["Sofa", "Coffee table", "TV unit or wall mount", "Rug", "Curtains", "Main lighting"],
      "optional_items": ["Armchairs", "Side tables", "Floor lamp", "Art"],
      "items": {
        "sofa": {
          "what_to_look_for": ["Frame quality", "Cushion density", "Fabric durability"],
          "budget_indicators": ["Particle board frame", "Foam-only cushions"],
          "quality_indicators": ["Solid wood frame", "Spring + foam", "Removable covers"],
          "where_to_buy_spain": {
            "budget": ["IKEA", "Conforama", "Kave Home"],
            "mid": ["Kenay Home", "El Corte Inglés", "BoConcept"],
            "high": ["Roche Bobois", "Sancal", "Living Divani"],
            "luxury": ["B&B Italia", "Flexform", "Minotti"]
          },
          "indicative_ranges_eur": {
            "budget": "500-1,200",
            "mid": "1,500-3,500",
            "high": "4,000-10,000",
            "luxury": "10,000+"
          },
          "investment_priority": "high",
          "reasoning": "Used daily, visible centerpiece, affects comfort"
        },
        "coffee_table": { ... },
        ...
      },
      "total_indicative_budget": {
        "budget": "2,000-4,000",
        "mid": "5,000-12,000",
        "high": "15,000-35,000",
        "luxury": "40,000+"
      }
    },
    "bedroom_main": { ... },
    "kitchen_appliances": { ... },
    "bathroom_accessories": { ... },
    "outdoor": { ... }
  },
  
  "investment_priorities": {
    "high_priority_items": ["Sofa", "Mattress", "Dining table", "Main lighting"],
    "reasoning": "Used daily, long-lasting, define the space",
    "low_priority_items": ["Accessories", "Seasonal decor", "Trend pieces"],
    "reasoning": "Easy to change, less impact"
  },
  
  "common_mistakes": [
    "Buying everything at once from same store (looks catalog)",
    "Skipping proper lighting budget",
    "Oversized furniture for Spanish apartment scale",
    "Ignoring outdoor space (important in Spanish climate)"
  ]
}

Focus on PRACTICAL GUIDANCE for homeowners planning a renovation budget."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=40000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse FF&E: {e}")
            return {}
    return {}


async def extract_spanish_construction_eras() -> dict:
    """Extract Spanish construction eras with typical original finishes."""
    logger.info("\n🏗️ Extracting Spanish construction eras...")
    
    prompt = """You are a Spanish architect and historian with deep knowledge of Spanish residential construction across the 20th and 21st centuries.

Create a comprehensive guide to SPANISH CONSTRUCTION ERAS and their typical original finishes.

## Eras to cover:
1. Pre-1940 (Pre-Civil War, early Franco)
2. 1940-1960 (Post-war autarky)
3. 1960-1980 (Desarrollo/Development boom)
4. 1980-2000 (Democracy, EU entry)
5. 2000-2008 (Construction boom)
6. 2008-2015 (Crisis period)
7. 2015-present (Post-crisis recovery)

## For each era, provide:
- **Historical context** - What was happening in Spain
- **Construction characteristics** - Structure, layout, typical sizes
- **Typical original finishes** - What was standard when built
- **Common issues today** - What problems these properties have
- **Renovation approach** - How to approach updating
- **What to preserve vs replace** - Character elements worth keeping
- **Regional variations** - Differences in Cataluña, Andalucía, etc.

Return JSON:
{
  "eras": {
    "pre_1940": {
      "period": "Pre-Civil War / Early Franco",
      "historical_context": "...",
      "construction": {
        "structure": "Load-bearing walls, brick or stone",
        "layout": "High ceilings, large rooms, gallery",
        "typical_size": "Variable, often large",
        "quality": "Generally good, solid construction"
      },
      "typical_finishes": {
        "floors": "Baldosa hidráulica (hydraulic tiles), wood parquet",
        "walls": "High-quality plaster, sometimes painted murals",
        "ceilings": "High, often decorative moldings",
        "doors": "Solid wood, ornate",
        "windows": "Large, wood frames",
        "kitchens": "Separate, utilitarian",
        "bathrooms": "Often added later or minimal"
      },
      "common_issues_today": ["..."],
      "renovation_approach": "...",
      "preserve": ["Hydraulic tiles", "Ceiling moldings", "Original doors"],
      "replace": ["Plumbing", "Electrical", "Kitchen"],
      "regional_variations": {
        "barcelona": "Modernisme influence, more ornate",
        "madrid": "More classical, simpler",
        "andalucia": "Moorish influences, patios"
      }
    },
    "1940_1960": { ... },
    "1960_1980": { ... },  // This is the MOST COMMON renovation target
    "1980_2000": { ... },
    "2000_2008": { ... },
    "2008_2015": { ... },
    "2015_present": { ... }
  },
  
  "renovation_priorities_by_era": {
    "pre_1940": ["Preserve character", "Update systems", "Careful modernization"],
    "1960_1980": ["Full renovation usually needed", "Improve layout", "Add insulation"],
    ...
  }
}

Be SPECIFIC about typical finishes - this helps identify era from photos."""

    response = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=30000,
    )
    
    if response.success:
        try:
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"   ❌ Failed to parse eras: {e}")
            return {}
    return {}


async def main():
    print("=" * 70)
    print("PETER AGENTIC V0.3.2 - Interior Design Knowledge Extraction")
    print("Spain-specific, current trends, detailed sourcing")
    print("=" * 70)
    print()
    
    # Run all extractions
    results = await asyncio.gather(
        extract_design_trends(),
        extract_spanish_sources(),
        extract_how_to_achieve(),
        extract_finish_quality_indicators(),
        extract_ffe_guidance(),
        extract_spanish_construction_eras(),
    )
    
    trends, sources, transformations, quality, ffe, eras = results
    
    # Log results
    logger.info("\n📊 Extraction Results:")
    logger.info(f"   Trends: {len(trends.get('trends', {}))} styles")
    logger.info(f"   Sources: {len(sources.get('categories', {}))} categories")
    logger.info(f"   Transformations: {len(transformations.get('transformations', {}))} scenarios")
    logger.info(f"   Quality tiers: {len(quality.get('quality_tiers', {}))} tiers")
    logger.info(f"   FF&E categories: {len(ffe.get('ffe_categories', {}))} rooms")
    logger.info(f"   Construction eras: {len(eras.get('eras', {}))} eras")
    
    # Package output
    logger.info("\n📦 Packaging interior design knowledge...")
    
    output = {
        "$schema": "interior_design_knowledge_v1",
        "$version": "1.0.0",
        "$created": datetime.now().isoformat(),
        "$approach": "Gemini Pro synthesis - Spain-specific interior design knowledge",
        "$note": "Unlike energy/process KBs, no official source docs - synthesized from Gemini training",
        "$coverage": {
            "market": "Spain",
            "currency": "EUR",
            "year": "2024-2026 trends and pricing",
            "ffe_note": "Indicative ranges only - BCCA handles construction costs"
        },
        
        # Design trends
        "trends": trends.get("trends", {}),
        
        # Spanish sources
        "spanish_sources": sources.get("categories", {}),
        "spanish_brands_spotlight": sources.get("spanish_brands_spotlight", {}),
        
        # How to achieve transformations
        "transformations": transformations.get("transformations", {}),
        
        # Quality tier indicators
        "quality_tiers": quality.get("quality_tiers", {}),
        "quality_checklist": quality.get("quick_assessment_checklist", []),
        
        # FF&E guidance
        "ffe_guidance": ffe.get("ffe_categories", {}),
        "ffe_priorities": ffe.get("investment_priorities", {}),
        "ffe_mistakes": ffe.get("common_mistakes", []),
        
        # Spanish construction eras
        "construction_eras": eras.get("eras", {}),
        "renovation_priorities_by_era": eras.get("renovation_priorities_by_era", {}),
        
        # References (unlike energy/process, these are general)
        "references": {
            "note": "This knowledge base is synthesized from Gemini's training, not official documents.",
            "approach": "Interior design has no regulatory standards like CTE for energy.",
            "validation": "Should be validated against current Spanish market reality.",
            "update_frequency": "Design trends change - recommend annual refresh."
        }
    }
    
    # Save
    logger.info(f"\n💾 Writing to {OUTPUT_PATH}...")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Stats
    file_size = OUTPUT_PATH.stat().st_size
    
    logger.info(f"\n✅ Done!")
    logger.info(f"   File size: {file_size:,} bytes")
    logger.info(f"   Output: {OUTPUT_PATH}")
    
    # Summary
    logger.info("\n📋 Contents Summary:")
    logger.info(f"   • {len(output.get('trends', {}))} design trends with how-to-achieve")
    logger.info(f"   • {len(output.get('spanish_sources', {}))} sourcing categories")
    logger.info(f"   • {len(output.get('transformations', {}))} transformation scenarios")
    logger.info(f"   • {len(output.get('quality_tiers', {}))} quality tier definitions")
    logger.info(f"   • {len(output.get('ffe_guidance', {}))} FF&E room guides")
    logger.info(f"   • {len(output.get('construction_eras', {}))} Spanish construction eras")


if __name__ == "__main__":
    asyncio.run(main())

