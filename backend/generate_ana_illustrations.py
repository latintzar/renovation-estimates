#!/usr/bin/env python3
"""
Generate "Ana" illustrations for landing page problem cards.
Thin-line, calm, approachable style illustrations.
"""

import asyncio
import os
import sys
import base64
import io
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load env
from dotenv import load_dotenv
pass  # Recipient runtime supplies its explicit private environment.

# ---------------------------------------------------------------------------
# Standalone script mode: relax strict Gemini accounting requirements.
# WHY THIS MATTERS:
# - call_gemini_image() can be configured to require usageMetadata and DB writes
#   for pipeline runs. This script is a standalone asset generator, so we don't
#   have a DB job context. If strict flags are enabled, image generation can
#   fail with "missing usage metadata" / "cannot persist call log" errors.
# - We still log and fail loud on real HTTP/model errors.
# ---------------------------------------------------------------------------
os.environ.setdefault("PIPELINE_STRICT_GEMINI_USAGE_METADATA", "false")
os.environ.setdefault("PIPELINE_STRICT_GEMINI_COST_DB_WRITE", "false")

OUTPUT_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/illustrations"

# Style guide for all illustrations
STYLE_GUIDE = """
ILLUSTRATION STYLE (CRITICAL - FOLLOW EXACTLY):
- FLAT VECTOR illustration style, clean and modern
- MEDIUM line weight (not too thin, not too thick) - confident strokes
- Color palette: warm terracotta/coral (#D4846A) as main color, soft warm gray (#9A918A) for secondary elements, light peach (#F5E6E0) for subtle fills
- WHITE BACKGROUND (pure white #FFFFFF)
- Minimalist, clean, horizontal composition
- Friendly, approachable, calm feeling
- NOT cartoon/childish - sophisticated, like Stripe or Notion marketing
- Character: Same woman in all illustrations - professional, early 30s, dark hair in a bun or ponytail
- Simple clothing: white/cream top (same in all)
- Expression: subtle, relatable emotions
- NO heavy shadows, NO gradients, NO complex textures
- WIDE FORMAT - landscape orientation (wider than tall)
- Character positioned to one side, with conceptual elements on the other
"""

ILLUSTRATIONS = {
    "ana-confused": {
        "prompt": f"""Create a flat vector illustration of a woman confused by numbers and costs.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Woman on the LEFT side, looking slightly confused (hand on chin)
- On the RIGHT side: floating € symbols, percentages, question marks
- Simple, clean composition
- She's a professional in her 30s with dark hair in a neat bun
- Wearing a simple cream/white blouse
- Warm terracotta (#D4846A) for her skin/clothing accents
- Gray (#9A918A) for the floating symbols
- Expression: slight frown, puzzled but not distressed

Keep it simple, clean, wide format. Like a Stripe or Linear illustration.
""",
        "output_name": "ana-confused",
        "description": "Ana confused by renovation costs",
    },
    
    "ana-waiting": {
        "prompt": f"""Create a flat vector illustration of a woman stuck in a waiting loop.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Woman in the CENTER, arms slightly crossed, patient expression
- Circular arrows or a subtle loop symbol around her
- Small clock icon nearby
- She's the SAME woman: professional, 30s, dark hair in a neat bun
- Wearing the SAME simple cream/white blouse
- Warm terracotta (#D4846A) for her skin/clothing accents
- Gray (#9A918A) for the loop/clock symbols
- Expression: patient but slightly frustrated, waiting

Keep it simple, clean, wide format. Matches the other illustrations in the series.
""",
        "output_name": "ana-waiting",
        "description": "Ana stuck in decision loop",
    },
    
    "ana-lost": {
        "prompt": f"""Create a flat vector illustration of a woman looking lost during a property visit.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Woman on the RIGHT side, looking around uncertainly
- On the LEFT side: simple door outlines, directional arrows pointing different ways
- She's the SAME woman: professional, 30s, dark hair in a neat bun
- Wearing the SAME simple cream/white blouse
- Warm terracotta (#D4846A) for her skin/clothing accents
- Gray (#9A918A) for the door/arrow symbols
- Expression: curious, looking around, needs guidance

Keep it simple, clean, wide format. Matches the other illustrations in the series.
""",
        "output_name": "ana-lost",
        "description": "Ana lost during property viewing",
    },

    # ---------------------------------------------------------------------
    # Investor / flipper variants (same illustration style, new audience)
    # ---------------------------------------------------------------------
    "investor-bad-visit": {
        "prompt": f"""Create a flat vector illustration of a real estate investor who wasted a morning on a deal that doesn't pencil.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Character on the LEFT: a professional investor in their 30s-40s (gender-neutral), casual-smart outfit (light shirt), calm but annoyed expression
- They are holding a phone with a listing thumbnail on it (simple rectangle, no real brand logos)
- On the RIGHT side: a simple calendar icon + a car icon + a red X mark (concept: wasted trip / wasted time)
- Also include a small simple "margin" bar that goes negative (a small chart line dipping below 0)
- Warm terracotta (#D4846A) accents, gray (#9A918A) for icons/symbols, light peach (#F5E6E0) fills
- No text in the image (no words), only icons and shapes

Keep it simple, clean, wide format. Matches the existing illustration set.
""",
        "output_name": "investor-bad-visit",
        "description": "Investor wasted visit (deal doesn't pencil)",
    },

    "investor-waiting": {
        "prompt": f"""Create a flat vector illustration of a real estate investor waiting for a contractor estimate.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Character centered or slightly to the LEFT: same investor character as other investor illustrations
- They are looking at a phone showing a chat bubble icon (no WhatsApp logo)
- On the RIGHT side: a clock icon, a loading spinner icon, and a simple document/quote icon
- Expression: patient but slightly frustrated (waiting)
- Warm terracotta (#D4846A) accents, gray (#9A918A) for icons/symbols, light peach (#F5E6E0) fills
- No text in the image

Keep it simple, clean, wide format. Matches the existing illustration set.
""",
        "output_name": "investor-waiting",
        "description": "Investor waiting for estimate",
    },

    "investor-negotiating": {
        "prompt": f"""Create a flat vector illustration of a real estate investor negotiating without concrete evidence.

{STYLE_GUIDE}

SCENE SPECIFICS:
- WIDE LANDSCAPE FORMAT (3:2 ratio, much wider than tall)
- Character on the LEFT: same investor character, in a seated posture at a simple table
- On the RIGHT side: two speech bubbles (concept: negotiation), but with missing "proof"
- Include simple photo-thumbnail icons + a price tag icon + a checklist icon, all faded out / semi-transparent (concept: lacking evidence)
- Expression: confident but constrained, like they need better ammunition
- Warm terracotta (#D4846A) accents, gray (#9A918A) for icons/symbols, light peach (#F5E6E0) fills
- No text in the image

Keep it simple, clean, wide format. Matches the existing illustration set.
""",
        "output_name": "investor-negotiating",
        "description": "Investor negotiating without evidence",
    },
}

# Which illustration to generate
GENERATE_MODE = "all"  # Options: illustration key above, or "all"


def create_white_placeholder():
    """Create a white placeholder image to seed the generation."""
    try:
        from PIL import Image
        # Create pure white image - WIDE format (3:2 ratio)
        img = Image.new('RGB', (1200, 800), color=(255, 255, 255))
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        print("   ⚠️ PIL not available")
        return None


def remove_white_background(input_path: Path, output_path: Path, threshold: int = 250):
    """Convert white background to transparent."""
    try:
        from PIL import Image
        import numpy as np
        
        # Load image
        img = Image.open(input_path).convert('RGBA')
        data = np.array(img)
        
        # Find white pixels (R, G, B all above threshold)
        white_mask = (data[:, :, 0] > threshold) & (data[:, :, 1] > threshold) & (data[:, :, 2] > threshold)
        
        # Set alpha to 0 for white pixels
        data[white_mask, 3] = 0
        
        # Save result
        result = Image.fromarray(data)
        result.save(output_path, 'PNG')
        
        print(f"   ✅ Removed white background: {output_path.name}")
        return True
    except Exception as e:
        print(f"   ⚠️ Could not remove background: {e}")
        return False


async def generate_illustration(mode: str):
    """Generate an illustration using Gemini."""
    from pipeline.gemini_client import call_gemini_image
    
    config = ILLUSTRATIONS.get(mode)
    if not config:
        print(f"❌ Unknown mode: {mode}")
        print(f"   Available modes: {list(ILLUSTRATIONS.keys())}")
        return False
    
    print(f"\n🎨 Generating '{mode}'...")
    print(f"   Description: {config['description']}")
    
    # Create placeholder image
    print(f"   📷 Creating white placeholder...")
    placeholder_data = create_white_placeholder()
    if not placeholder_data:
        print("   ❌ Could not create placeholder")
        return False
    
    try:
        result = await call_gemini_image(
            prompt=config["prompt"],
            image_data=placeholder_data,
            image_mime_type="image/png",
            model="pro-image",
            temperature=1.0,
        )
        
        if result.get("success") and result.get("image_data"):
            # Save original PNG
            original_path = OUTPUT_DIR / f"{config['output_name']}-original.png"
            with open(original_path, "wb") as f:
                f.write(base64.b64decode(result["image_data"]))
            print(f"   ✅ Saved original: {original_path.name}")
            
            # Remove white background
            transparent_path = OUTPUT_DIR / f"{config['output_name']}.png"
            remove_white_background(original_path, transparent_path)
            
            # Also save as WebP for web
            try:
                from PIL import Image
                img = Image.open(transparent_path)
                webp_path = OUTPUT_DIR / f"{config['output_name']}.webp"
                img.save(webp_path, 'WEBP', quality=90)
                print(f"   ✅ Saved WebP: {webp_path.name}")
            except Exception as e:
                print(f"   ⚠️ Could not save WebP: {e}")
            
            return True
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Generate landing page illustrations via Gemini")
    parser.add_argument(
        "--mode",
        default=GENERATE_MODE,
        help="One of: all, investor, or a specific key in ILLUSTRATIONS",
    )
    args = parser.parse_args()
    mode = str(args.mode).strip()

    print("=" * 60)
    print("GENERATING ANA ILLUSTRATIONS")
    print("Thin-line, approachable style for landing page")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    if mode == "investor":
        modes = ["investor-bad-visit", "investor-waiting", "investor-negotiating"]
        results = {}
        for m in modes:
            results[m] = await generate_illustration(m)
        print("\n" + "=" * 60)
        print("RESULTS:")
        for m, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {m}")
    elif mode == "all":
        # Generate all illustrations
        results = {}
        for mode in ILLUSTRATIONS.keys():
            results[mode] = await generate_illustration(mode)
        
        print("\n" + "=" * 60)
        print("RESULTS:")
        for mode, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {mode}")
    else:
        # Generate single illustration
        success = await generate_illustration(mode)
        
        print("\n" + "=" * 60)
        if success:
            print("✅ GENERATION COMPLETE")
            print(f"\n📋 Image saved to: {OUTPUT_DIR / ILLUSTRATIONS[mode]['output_name']}.png")
        else:
            print("❌ GENERATION FAILED")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
