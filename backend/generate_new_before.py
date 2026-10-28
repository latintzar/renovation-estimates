#!/usr/bin/env python3
"""
Generate landing page images with consistent two-window composition.
"""

import asyncio
import os
import sys
import base64
import io
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load env
from dotenv import load_dotenv
pass  # Recipient runtime supplies its explicit private environment.

OUTPUT_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/no-es-magia"

# Which image to generate - change this to generate different images
GENERATE_MODE = "fast_sell"  # Options: "before", "fast_sell", "fair_market", "premium"

NEW_BEFORE_PROMPT = """Transform this placeholder into a photorealistic interior photo of a neglected Barcelona apartment living room that desperately needs renovation.

CRITICAL REQUIREMENTS:
- TWO LARGE WINDOWS side by side on one wall (like French windows or balcony doors)
- Living room space that looks like elderly occupants recently passed away
- Cluttered, neglected, but not destroyed

ATMOSPHERE - "INHERITED APARTMENT FROM DECEASED ELDERLY RELATIVES":
- Feels stuck in time from the 1970s
- Cluttered with decades of accumulated belongings
- Dark, gloomy despite the windows (dirty glass, heavy old curtains)
- Musty, neglected feeling

VISIBLE PROBLEMS:
- MOLD or humidity stains on walls/ceiling corners (dark patches)
- Peeling or bubbling paint on walls
- Water damage marks near windows
- Yellowed, cracked walls
- Old worn terrazzo or damaged parquet floors
- Cobwebs in corners
- Dust visible on surfaces

CLUTTER & DATED ITEMS:
- Old heavy dark wood furniture everywhere
- Massive outdated wall unit/shelving crammed with old books, ornaments, photos
- Old CRT television
- Dated patterned upholstery on worn sofas (floral or brown)
- Old magazines/newspapers stacked
- Religious items, old family photos on walls
- Heavy dark curtains, yellowed lace
- Old chandelier with missing bulbs
- Random accumulated items (old clock, vases, figurines)

QUALITY:
- Real estate listing photo style (like from an inheritance sale)
- Dim natural daylight, realistic gloomy lighting
- 4:3 aspect ratio, landscape orientation
- Photorealistic, authentic feel
- The kind of apartment you'd see listed "needs complete renovation" or "to reform"

This should look like a real inherited apartment in Barcelona - the kind where an elderly couple lived for 50 years and now it needs to be completely gutted. Sad but full of potential. The TWO WINDOWS are essential."""

FAST_SELL_PROMPT = """Transform this placeholder into a photorealistic interior photo of a nicely renovated Barcelona apartment living room - a "quick flip" quality renovation.

CRITICAL REQUIREMENTS:
- TWO LARGE WINDOWS side by side on one wall (like French windows or balcony doors)
- Same room/composition as the before image but completely transformed
- Light, bright, clean, modern

RENOVATION LEVEL - "VENTA RÁPIDA" (Quick Sale):
- Fresh, clean, inviting but not luxury
- Good quality but budget-conscious choices
- The kind of flip that looks great in photos

FINISHES & STYLE:
- Fresh white or light gray walls (perfectly smooth)
- New light wood laminate flooring (oak tone)
- Simple modern baseboards
- New electrical outlets and switches (white)
- Simple but stylish lighting (basic pendant or ceiling lamp)
- Large windows letting in lots of natural light
- Simple white curtains or blinds
- Minimal furniture staging: modern IKEA-style sofa, simple coffee table
- A few plants for freshness
- Clean, uncluttered space

QUALITY:
- Real estate listing photo style
- Bright natural daylight flooding in
- 4:3 aspect ratio, landscape orientation  
- Photorealistic, professional staging feel
- The kind of renovation that costs €45k and adds €90k in value

This is "Venta Rápida" tier - clean, fresh, attractive, move-in ready. Not luxury but definitely desirable. The TWO WINDOWS matching the before image are essential."""


def create_placeholder_image():
    """Create a simple placeholder image to seed the generation."""
    try:
        from PIL import Image
        # Create a simple gradient that suggests a room with windows
        img = Image.new('RGB', (800, 600), color=(200, 190, 180))
        
        # Draw some basic shapes to suggest windows
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Two window shapes
        draw.rectangle([200, 100, 350, 400], fill=(220, 230, 240))  # Left window
        draw.rectangle([450, 100, 600, 400], fill=(220, 230, 240))  # Right window
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=80)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        # Fallback: minimal JPEG placeholder
        print("   ⚠️ PIL not available, using minimal placeholder")
        # A minimal valid JPEG (1x1 pixel)
        minimal_jpeg = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5,
            0xFF, 0xD9
        ])
        return base64.b64encode(minimal_jpeg).decode('utf-8')


IMAGE_CONFIGS = {
    "before": {
        "prompt": NEW_BEFORE_PROMPT,
        "output_name": "before",
        "description": "Neglected apartment with mold and clutter",
    },
    "fast_sell": {
        "prompt": FAST_SELL_PROMPT,
        "output_name": "after-fast_sell",
        "description": "Quick flip renovation - €340k tier",
    },
}


async def generate_image(mode: str = "before"):
    """Generate an image using Gemini."""
    from pipeline.gemini_client import call_gemini_image
    
    config = IMAGE_CONFIGS.get(mode)
    if not config:
        print(f"❌ Unknown mode: {mode}")
        print(f"   Available modes: {list(IMAGE_CONFIGS.keys())}")
        return False
    
    print("=" * 60)
    print(f"GENERATING '{mode.upper()}' IMAGE")
    print(f"Description: {config['description']}")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    print(f"\n🎨 Generating {config['output_name']}...")
    
    # Create placeholder image
    print(f"   📷 Creating placeholder image...")
    placeholder_data = create_placeholder_image()
    
    try:
        result = await call_gemini_image(
            prompt=config["prompt"],
            image_data=placeholder_data,
            image_mime_type="image/jpeg",
            model="pro-image",
            temperature=1.0,
        )
        
        if result.get("success") and result.get("image_data"):
            # Save as PNG first
            output_path = OUTPUT_DIR / f"{config['output_name']}-new.png"
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result["image_data"]))
            print(f"\n   ✅ Saved: {output_path}")
            print(f"   📏 Size: {output_path.stat().st_size / 1024:.1f} KB")
            
            # Backup and replace
            import shutil
            backup_path = OUTPUT_DIR / f"{config['output_name']}-old-backup.webp"
            original_path = OUTPUT_DIR / f"{config['output_name']}.webp"
            if original_path.exists():
                shutil.copy(original_path, backup_path)
                print(f"   📦 Backed up original to: {backup_path.name}")
            
            # Convert to webp
            try:
                from PIL import Image
                img = Image.open(output_path)
                img.save(original_path, 'WEBP', quality=85)
                print(f"   🔄 Converted and saved as: {original_path.name}")
            except:
                shutil.copy(output_path, original_path.with_suffix('.png'))
                print(f"   🔄 Saved as PNG (PIL not available for webp conversion)")
            
            return True
        else:
            print(f"\n   ❌ Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await generate_image(GENERATE_MODE)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ GENERATION COMPLETE")
        print("\n📋 Next steps:")
        print("   1. Check the generated image in:")
        print(f"      {OUTPUT_DIR}")
        print(f"   2. Image saved as: {IMAGE_CONFIGS[GENERATE_MODE]['output_name']}.webp")
        print("   3. Refresh your browser to see the new image")
    else:
        print("❌ GENERATION FAILED")
        print("\n💡 Try running manually or check API credentials")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
