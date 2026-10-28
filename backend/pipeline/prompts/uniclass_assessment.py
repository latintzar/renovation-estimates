"""
Room Fingerprinting via Uniclass Taxonomy
==========================================

This creates a COMPREHENSIVE VISUAL CATALOGUE of a room, using Uniclass 2015
as the organizing framework for consistency across properties.

The goal is FULL FINGERPRINTING - not a sparse inventory, but a rich,
detailed description of EVERYTHING visible, organized by Uniclass code.

For each element we capture:
- What it is (Uniclass code + title)
- Visual condition (excellent → critical)
- CHARACTERISTICS: Material, color, style, age estimate, brand tier, dimensions
- OBSERVATIONS: Wear patterns, damage, quality indicators
- REPLACEMENT NOTES: Urgency, what would be appropriate replacement

This enables:
1. Detailed gap analysis (quality comparison, not just presence)
2. Accurate scope building (knowing exactly what to specify)
3. Client presentation (showing them what they're buying)
4. Portfolio comparison (fingerprinting across properties)
"""

import os
import json
from typing import List, Dict, Any


def load_uniclass_residential() -> tuple[List[Dict], List[Dict]]:
    """Load the Gemini-filtered residential Uniclass codes."""
    # Go up from prompts -> pipeline -> backend -> Lean MVP
    standards_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "standards"
    )
    
    ss_path = os.path.join(standards_dir, "uniclass_ss_residential.json")
    pr_path = os.path.join(standards_dir, "uniclass_pr_residential.json")
    
    with open(ss_path, 'r', encoding='utf-8') as f:
        ss_data = json.load(f)
    
    with open(pr_path, 'r', encoding='utf-8') as f:
        pr_data = json.load(f)
    
    return ss_data.get("codes", []), pr_data.get("codes", [])


def format_codes_for_prompt(codes: List[Dict], prefix: str) -> str:
    """
    Format codes hierarchically for the prompt.
    Groups codes by their group/subgroup for readability.
    """
    # Group by group number
    by_group = {}
    for code in codes:
        group = code.get("group", "")
        if group not in by_group:
            by_group[group] = []
        by_group[group].append(code)
    
    lines = []
    for group in sorted(by_group.keys()):
        group_codes = by_group[group]
        # Get group title (first entry usually)
        group_title = next((c["title"] for c in group_codes if not c.get("sub_group")), "")
        lines.append(f"\n### {prefix}_{group}: {group_title}")
        
        # Add codes (limit to most specific ones for brevity)
        for code in group_codes[:50]:  # Limit per group for prompt size
            lines.append(f"- {code['code']}: {code['title']}")
        
        if len(group_codes) > 50:
            lines.append(f"  ... and {len(group_codes) - 50} more codes in this group")
    
    return "\n".join(lines)


def build_uniclass_assessment_prompt(
    room_type: str,
    room_name: str,
    ss_codes: List[Dict],
    pr_codes: List[Dict]
) -> str:
    """
    Build the prompt for FULL ROOM FINGERPRINTING.
    
    No room-specific filtering - the model looks at the photos and
    catalogues everything it sees using Uniclass codes.
    """
    
    # Provide full code reference - model decides what's relevant based on photos
    ss_summary = format_codes_for_prompt(ss_codes, "Ss")
    pr_summary = format_codes_for_prompt(pr_codes, "Pr")
    
    return f"""## TASK: FULL ROOM FINGERPRINTING

You are a property surveyor creating a COMPREHENSIVE VISUAL CATALOGUE of this space: **{room_name}**.

Look at the photos and catalogue EVERYTHING visible using Uniclass 2015 codes. The photos tell you what this space is - could be a kitchen, bathroom, bedroom, exterior, utility room, or anything else.

**FULL FINGERPRINTING** - capture everything with RICH DETAIL.

---

## UNICLASS REFERENCE - Systems (Ss)

{ss_summary}

---

## UNICLASS REFERENCE - Products (Pr)

{pr_summary}

---

## FINGERPRINTING CHECKLIST - DON'T MISS ANYTHING

**SURFACES & FINISHES:**
□ Floor - material, tile size, pattern, grout condition, levelness
□ Walls - finish type, paint/tile/plaster, color, texture, damage
□ Ceiling - height, finish, any cracks/stains, lighting integration
□ Skirting/baseboards - material, profile, condition

**OPENINGS:**
□ Windows - frame material (PVC/aluminum/wood), glazing (single/double), handles, seals
□ Doors - material, style, handle, hinges, frame condition
□ Built-in storage - material, hardware, interior finish

**ELECTRICAL:**
□ ALL outlets - count them, style, condition, placement
□ Light switches - type, style, condition
□ Light fixtures - ceiling, wall, type, style
□ Electrical panel if visible

**PLUMBING (if applicable):**
□ Taps/faucets - material, style, brand tier, condition
□ Sinks/basins - material, mounting style, condition
□ Toilet - style, flush mechanism, seat condition
□ Shower/bath - type, enclosure, fixtures
□ Visible pipes - material, condition

**CLIMATE:**
□ Radiators/heating - type, style, condition
□ Air conditioning - type, condition
□ Ventilation - extractors, vents

**APPLIANCES (if visible):**
□ Each appliance - brand tier, age estimate, condition

---

## HOW TO DESCRIBE EACH ELEMENT

For EACH item, provide RICH characteristics:

**Material:** Chrome, ceramic, porcelain, stainless steel, melamine, solid wood, laminate, PVC, aluminum, etc.

**Style/Era:** Modern minimalist, traditional Spanish, 80s/90s dated, rustic, industrial, etc.

**Quality Tier:** Budget/basic, mid-range, premium/designer, luxury

**Age Estimate:** New (<2 years), recent (2-5), moderate (5-10), dated (10-20), vintage (20+)

**Condition Details:** Specific wear - scratches, limescale, discoloration, chips, cracks, stains, rust

**Dimensions (if estimable):** Tile sizes, fixture dimensions, heights

---

## VISUAL CONDITION SCALE

- **excellent**: Like new, showroom quality, no visible wear
- **good**: Minor wear, well maintained, presentable
- **fair**: Noticeable wear/aging, functional but dated (MOST COMMON in older properties)
- **poor**: Significant wear, staining, damage - replacement advisable
- **critical**: Broken, hazardous, non-functional - immediate attention needed

---

## OUTPUT FORMAT

Return a comprehensive fingerprint:

{{
  "systems": [
    {{
      "code": "Ss_35_20",
      "title": "Wall finish systems",
      "visual_condition": "fair",
      "characteristics": {{
        "material": "Painted plaster",
        "color": "Off-white, yellowing",
        "style": "Plain smooth finish",
        "age_estimate": "15-20 years since last paint",
        "observations": "Hairline cracks near window, some scuff marks at chair height, paint peeling slightly in corner"
      }}
    }},
    {{
      "code": "Ss_70_30_80",
      "title": "Small power systems",
      "visual_condition": "fair",
      "characteristics": {{
        "material": "White plastic",
        "style": "Square Spanish standard, Simón 27 series or similar",
        "quantity": "4 double outlets visible",
        "age_estimate": "10-15 years",
        "observations": "Yellowed plastic, one outlet has cracked faceplate"
      }}
    }}
  ],
  "products": [
    {{
      "code": "Pr_35_57_22_14",
      "title": "Ceramic floor tiles",
      "visual_condition": "fair",
      "characteristics": {{
        "material": "Glazed ceramic",
        "dimensions": "Approximately 45x45cm",
        "color": "Beige/cream with terracotta undertone",
        "pattern": "Plain, slight texture",
        "style": "Classic Spanish, late 90s/early 2000s",
        "quality_tier": "Mid-range",
        "observations": "Grout darkened, 2-3 tiles with visible chips at edges, slight hollow sound when walking (possible debonding)"
      }}
    }},
    {{
      "code": "Pr_40_20_87_55",
      "title": "Mixer taps",
      "visual_condition": "poor",
      "characteristics": {{
        "material": "Chrome-plated brass",
        "style": "Single lever, dated curved design",
        "brand_tier": "Budget (Roca basic or similar)",
        "age_estimate": "15+ years",
        "observations": "Heavy limescale buildup, chrome flaking near base, drip when closed, aerator calcified"
      }}
    }}
  ],
  "room_summary": {{
    "overall_condition": "fair",
    "style_era": "Late 1990s Spanish standard",
    "quality_tier": "Mid-range originally, now dated",
    "key_issues": ["Dated finishes throughout", "Electrical outlets need updating", "Plumbing fixtures at end of life"],
    "notable_features": ["Good natural light", "Spacious layout", "Original terracotta-style flooring"]
  }},
  "not_assessable": ["Cabinet interiors", "Behind appliances", "Under-sink plumbing"]
}}

**TARGET: 15-30+ items for a full room fingerprint. Miss nothing visible.**"""


# Response schema - FULL ROOM FINGERPRINT with rich characteristics
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "systems": {
            "type": "array",
            "description": "Building systems - aim for 8-15 items",
            "items": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Uniclass Ss code"
                    },
                    "title": {
                        "type": "string",
                        "description": "System title"
                    },
                    "visual_condition": {
                        "type": "string",
                        "enum": ["excellent", "good", "fair", "poor", "critical"]
                    },
                    "characteristics": {
                        "type": "object",
                        "description": "Rich description of what's visible",
                        "properties": {
                            "material": {"type": "string"},
                            "color": {"type": "string"},
                            "style": {"type": "string"},
                            "quantity": {"type": "string"},
                            "dimensions": {"type": "string"},
                            "age_estimate": {"type": "string"},
                            "quality_tier": {"type": "string", "enum": ["budget", "mid-range", "premium", "luxury"]},
                            "observations": {"type": "string", "description": "Detailed wear, damage, notable features"}
                        }
                    }
                },
                "required": ["code", "title", "visual_condition", "characteristics"]
            }
        },
        "products": {
            "type": "array",
            "description": "Products and fixtures - aim for 15-25 items",
            "items": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Uniclass Pr code"
                    },
                    "title": {
                        "type": "string",
                        "description": "Product title"
                    },
                    "visual_condition": {
                        "type": "string",
                        "enum": ["excellent", "good", "fair", "poor", "critical"]
                    },
                    "characteristics": {
                        "type": "object",
                        "description": "Rich description",
                        "properties": {
                            "material": {"type": "string"},
                            "color": {"type": "string"},
                            "pattern": {"type": "string"},
                            "dimensions": {"type": "string"},
                            "style": {"type": "string"},
                            "brand_tier": {"type": "string"},
                            "age_estimate": {"type": "string"},
                            "quality_tier": {"type": "string", "enum": ["budget", "mid-range", "premium", "luxury"]},
                            "observations": {"type": "string", "description": "Specific wear, damage, notable features"}
                        }
                    }
                },
                "required": ["code", "title", "visual_condition", "characteristics"]
            }
        },
        "room_summary": {
            "type": "object",
            "description": "Overall room assessment",
            "properties": {
                "overall_condition": {
                    "type": "string",
                    "enum": ["excellent", "good", "fair", "poor", "critical"]
                },
                "style_era": {
                    "type": "string",
                    "description": "e.g., 'Late 1990s Spanish standard', '2010s modern', 'Original 1975 unreformed'"
                },
                "quality_tier": {
                    "type": "string",
                    "description": "Original quality level and current state"
                },
                "key_issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main problems to address"
                },
                "notable_features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Positives to preserve or highlight"
                }
            },
            "required": ["overall_condition", "style_era", "key_issues"]
        },
        "not_assessable": {
            "type": "array",
            "items": {"type": "string"},
            "description": "What couldn't be seen"
        }
    },
    "required": ["systems", "products", "room_summary"]
}

