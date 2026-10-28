#!/usr/bin/env python3
"""
=============================================================================
research_ffe_expansion.py - Use Gemini with Google Search Grounding 
                            to research FFE items and prices
=============================================================================

PURPOSE: Generate a comprehensive list of FFE items for the database expansion.
         Uses Gemini 2.0 Flash with Google Search grounding to research:
         - Current product categories from Spanish retailers
         - Price ranges by tier
         - Brand references
         
USAGE:
    python research_ffe_expansion.py

OUTPUT:
    Prints structured FFE items ready to add to build_ffe_database.py
    
AUTHOR: Reformia Team
DATE: 2026-01-11
=============================================================================
"""

import os
import json
import time

# =============================================================================
# SETUP
# =============================================================================

# Use the same API key as the current pipeline (from gemini_client.py)
HELLO_KEY = ""

print(f"Using API key: {HELLO_KEY[:15]}...")

# Use google.generativeai SDK (same as pipeline)
import google.generativeai as genai_sdk
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

genai_sdk.configure(api_key=HELLO_KEY)

# Model - using gemini-3-pro-preview for better quality
MODEL_ID = "gemini-3-pro-preview"

# Categories to research
CATEGORIES_TO_EXPAND = {
    "LIGHTING": {
        "subcategories": [
            "Pendant lights (by size, style: industrial, nordic, bohemian, minimalist, organic)",
            "Wall sconces (reading, ambient, decorative, outdoor)",
            "Floor lamps (arc, tripod, torchiere, reading)",
            "Table lamps (bedside, desk, accent)",
            "Ceiling lights (flush mount, semi-flush, track, spots)",
            "Chandeliers (modern, classic, crystal, sputnik, linear)",
            "Strip/LED lights (under cabinet, cove, accent)",
            "Outdoor lights (wall, post, path, string)"
        ]
    },
    "BATHROOM_FFE": {
        "subcategories": [
            "Shower systems (rain head, handheld, thermostatic, digital)",
            "Shower enclosures (walk-in, sliding, pivot, quadrant, wet room)",
            "Bathtubs (freestanding, built-in, corner, clawfoot, Japanese soaking)",
            "Vanity units (floating, freestanding, double, with integrated basin)",
            "Mirrors (LED backlit, magnifying, smart, round, framed)",
            "Taps/faucets (waterfall, wall-mounted, basin mixer, freestanding)",
            "Towel storage (heated rails, racks, rings, hooks)",
            "WC accessories (soft close seats, bidet attachments, brush holders)"
        ]
    },
    "LIVING_FURNITURE": {
        "subcategories": [
            "Sofas (by size: 2P, 3P, 4P, modular, corner, chaise)",
            "Sofas (by style: mid-century, scandinavian, industrial, bouclé, velvet)",
            "Armchairs (lounge, accent, swivel, rocking, papasan)",
            "Coffee tables (round, oval, rectangular, nesting, lift-top)",
            "Side tables (C-shape, tripod, drum, glass)",
            "TV units (wall-mounted, floating, lowboard, with fireplace)",
            "Bookshelves (ladder, modular, built-in style, room divider)",
            "Room dividers (screens, shelving, hanging)",
            "Pouffes and ottomans (storage, footstool, accent)"
        ]
    },
    "DINING_FURNITURE": {
        "subcategories": [
            "Dining tables (by size: 2-4P, 6P, 8P, extendable)",
            "Dining tables (by material: wood, marble, ceramic, glass)",
            "Dining chairs (upholstered, wood, metal, rattan)",
            "Bar stools (counter height 65cm, bar height 75cm)",
            "Banquette seating (corner, straight, with storage)",
            "Sideboards and buffets (by style)",
            "Display cabinets (glass front, china cabinet)",
            "Bar carts and drinks cabinets"
        ]
    },
    "BEDROOM_FURNITURE": {
        "subcategories": [
            "Bed frames (platform, upholstered, wooden, metal, four poster)",
            "Headboards (upholstered, wooden, rattan, floating)",
            "Mattresses (foam, spring, hybrid, organic)",
            "Nightstands (floating, drawer, open, smart with charging)",
            "Dressers and chests (tall, wide, vintage style)",
            "Wardrobes (sliding, hinged, walk-in systems, open)",
            "Vanity tables (with mirror, with lights)",
            "Bedroom seating (bench, chair, chaise)"
        ]
    },
    "KITCHEN_SMALL_APPLIANCES": {
        "subcategories": [
            "Coffee machines (espresso, bean-to-cup, filter, capsule)",
            "Cooking robots (Thermomix style, Monsieur Cuisine)",
            "Air fryers (standard, dual zone, oven style)",
            "Stand mixers (KitchenAid style, bowl-lift)",
            "Blenders (high-speed, personal, immersion)",
            "Toasters (2-slice, 4-slice, smart)",
            "Kettles (electric, smart, gooseneck)",
            "Food processors and choppers"
        ]
    },
    "TEXTILES_EXPANDED": {
        "subcategories": [
            "Curtains (blackout, sheer, linen, velvet, printed)",
            "Blinds (roller, roman, venetian, vertical, smart)",
            "Rugs (by size: small, medium, large, runner)",
            "Rugs (by material: wool, cotton, jute, synthetic, silk)",
            "Bedding (duvet sets, sheets, throws, quilts)",
            "Cushions and pillows (decorative, floor, outdoor)",
            "Throws and blankets (wool, fleece, knitted)",
            "Towels (bath, hand, beach, kitchen)"
        ]
    },
    "HOME_TECH": {
        "subcategories": [
            "Smart home hubs and speakers",
            "Smart lighting systems",
            "Smart thermostats",
            "Robot vacuums and mops",
            "Air purifiers",
            "Humidifiers/dehumidifiers",
            "Smart locks and doorbells",
            "Home security cameras"
        ]
    },
    "OUTDOOR_EXPANDED": {
        "subcategories": [
            "Outdoor dining (tables, chairs, sets)",
            "Outdoor lounge (sofas, daybeds, hanging chairs)",
            "Sun loungers and deck chairs",
            "Parasols and shade sails",
            "Outdoor storage (deck boxes, cushion storage)",
            "Planters (ceramic, concrete, metal, self-watering)",
            "BBQs and outdoor cooking (gas, charcoal, kamado)",
            "Outdoor lighting and heating"
        ]
    },
    "KIDS_ROOM": {
        "subcategories": [
            "Kids beds (single, bunk, loft, themed)",
            "Kids storage (toy boxes, bookshelves, wardrobes)",
            "Kids desks and chairs",
            "Play furniture (teepees, play kitchens, play tables)",
            "Baby furniture (cribs, changing tables, gliders)"
        ]
    }
}


def research_category(category_name: str, subcategories: list) -> str:
    """Research a category using Gemini SDK."""
    
    prompt = f"""You are a Spanish interior design and furniture pricing expert. 
Provide current prices in Spain (2024-2025) for the following FFE items.

CATEGORY: {category_name}

For each subcategory below, provide:
1. Specific product types (at least 5-8 items per subcategory)
2. Price tiers for Spain:
   - Budget: IKEA, Amazon, Leroy Merlin level
   - Mid: Kave Home, Kenay Home, Maisons du Monde level  
   - High: Spanish design brands (Treku, Sancal, Marset) level
   - Luxury: International design (Poliform, B&B Italia, Miele) level
3. Reference brands for each tier
4. Typical specs/sizes

SUBCATEGORIES TO RESEARCH:
{json.dumps(subcategories, indent=2)}

OUTPUT FORMAT (for each item):
```
ITEM: [Item Name in Spanish]
CODE: FFE_[CATEGORY]_[ITEM_CODE]
DESCRIPTION_ES: [Quality indicators by tier]
SPECS: [Typical specs]
BUDGET: €[low]-[high], mid=€[typical] | Brands: [list]
MID: €[low]-[high], mid=€[typical] | Brands: [list]  
HIGH: €[low]-[high], mid=€[typical] | Brands: [list]
LUXURY: €[low]+ | Brands: [list]
PRIORITY: [alta/media/baja]
LIFESPAN: [years]
BASIS: [Retailers, specific products used as reference]
```

Use your knowledge of Spanish retailers: MediaMarkt, El Corte Inglés, IKEA España, 
Kave Home, Kenay Home, Leroy Merlin, Porcelanosa, Roca, Marset, Vibia.

Provide at least 20 distinct items for this category."""

    # Use google.generativeai SDK (same as pipeline)
    model = genai_sdk.GenerativeModel(MODEL_ID)
    response = model.generate_content(
        prompt,
        generation_config=genai_sdk.GenerationConfig(
            temperature=0.7,
            max_output_tokens=8192,
        )
    )
    
    return response.text


def main():
    """Research all categories and output structured FFE items."""
    
    print("="*70)
    print("FFE DATABASE EXPANSION RESEARCH")
    print("Using Gemini 2.0 Flash with Google Search Grounding")
    print("="*70)
    
    all_results = {}
    
    for category, data in CATEGORIES_TO_EXPAND.items():
        print(f"\n\n{'='*70}")
        print(f"RESEARCHING: {category}")
        print(f"{'='*70}")
        
        try:
            result = research_category(category, data["subcategories"])
            all_results[category] = result
            print(result)
        except Exception as e:
            print(f"ERROR researching {category}: {e}")
            all_results[category] = f"ERROR: {e}"
    
    # Save results
    output_path = "/root/puedo_casa/Lean MVP/backend/scripts/ffe_research_results.txt"
    with open(output_path, "w") as f:
        for category, result in all_results.items():
            f.write(f"\n\n{'='*70}\n")
            f.write(f"CATEGORY: {category}\n")
            f.write(f"{'='*70}\n\n")
            f.write(result)
    
    print(f"\n\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()

