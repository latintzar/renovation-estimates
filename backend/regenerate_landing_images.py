#!/usr/bin/env python3
"""
Regenerate specific landing page images with fixed prompts.
"""

import asyncio
import os
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
pass  # Recipient runtime supplies its explicit private environment.

OUTPUT_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/no-es-magia"

IMAGES_TO_REGENERATE = [
    {
        "name": "fair_market",
        "output": "after-fair_market",
        "prompt": """Generate a photorealistic interior photo of a beautifully renovated Barcelona apartment living room.

CRITICAL REQUIREMENTS:
- Standard ceiling height (2.7-3m) - NOT double height
- Normal residential windows - NOT floor-to-ceiling glass walls
- Realistic Barcelona Eixample apartment proportions

STYLE:
- Elegant Barcelona modernista aesthetic
- Restored original hydraulic tile floors in geometric blue/cream patterns
- High but normal ceilings with ornate plaster moldings
- Traditional French windows with wooden shutters, opening to small iron balcony
- Exposed brick accent wall on one side
- Mix of mid-century modern and contemporary furniture
- Warm wood tones, earth colors, some greenery
- Pendant lighting with warm glow
- Tasteful art, books on shelves

QUALITY:
- Professional real estate photography style
- Natural daylight from windows
- 4:3 aspect ratio
- Photorealistic, could be from an Idealista listing

NO watermarks, NO text, NO logos. This is for "Mercado Justo" tier - quality renovation, not ultra-luxury."""
    },
    {
        "name": "out_of_market", 
        "output": "after-out_of_market",
        "prompt": """Generate a photorealistic interior photo of a premium renovated Barcelona apartment living room.

CRITICAL REQUIREMENTS:
- Standard ceiling height (2.7-3.2m maximum) - NOT double height lofts
- Normal residential windows - NOT warehouse-style floor-to-ceiling glass
- Realistic Barcelona apartment proportions - this is still a FLAT, not a penthouse

STYLE:
- High-end contemporary Barcelona design
- Beautiful restored parquet or premium wide-plank oak flooring
- Elegant ceiling with restored moldings, perhaps coffered
- Large traditional windows with premium curtains/blinds
- Premium furniture - clean lines, quality materials (leather, marble, brass accents)
- Statement lighting - elegant chandelier or designer pendant
- Built-in bookshelves or media unit
- Curated art pieces
- Some greenery, quality textiles
- Neutral palette with sophisticated accents

QUALITY:
- Luxury real estate photography style
- Perfect natural lighting
- 4:3 aspect ratio  
- Photorealistic, could be from a premium Barcelona agency listing

NO watermarks, NO text, NO logos. This is "Premium" tier - expensive renovation but still a realistic Barcelona apartment, NOT a Manhattan loft."""
    }
]


async def generate_image(prompt: str, output_name: str):
    """Generate a single image using Gemini - no reference image to avoid watermarks."""
    from pipeline.gemini_client import call_gemini_image
    
    print(f"\n🎨 Generating: {output_name}")
    print(f"   Prompt: {prompt[:100]}...")
    
    # Create a simple placeholder - Gemini needs an image input
    # Using a simple gray image as neutral starting point
    import io
    from PIL import Image
    
    # Create a neutral gray image
    img = Image.new('RGB', (800, 600), color=(200, 200, 200))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    try:
        result = await call_gemini_image(
            prompt=prompt,
            image_data=image_data,
            image_mime_type="image/jpeg",
            model="pro-image",
            temperature=1.0,
        )
        
        if result.get("success"):
            output_path = OUTPUT_DIR / f"{output_name}.png"
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result["image_data"]))
            print(f"   ✅ Saved: {output_path}")
            
            # Also save as webp
            webp_path = OUTPUT_DIR / f"{output_name}.webp"
            from PIL import Image
            img = Image.open(output_path)
            img.save(webp_path, 'WEBP', quality=85)
            print(f"   ✅ Converted to webp: {webp_path}")
            
            return True
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("REGENERATING LANDING PAGE IMAGES")
    print("=" * 60)
    
    for img_config in IMAGES_TO_REGENERATE:
        print("\n" + "-" * 40)
        print(f"REGENERATING '{img_config['name'].upper()}'")
        print("-" * 40)
        
        await generate_image(
            prompt=img_config["prompt"],
            output_name=img_config["output"]
        )
    
    print("\n" + "=" * 60)
    print("REGENERATION COMPLETE")
    print("=" * 60)
    
    # List files
    print("\n📂 Current files:")
    for f in sorted(OUTPUT_DIR.glob("*.webp")):
        size_kb = f.stat().st_size / 1024
        print(f"   - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
