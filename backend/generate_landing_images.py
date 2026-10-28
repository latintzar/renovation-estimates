#!/usr/bin/env python3
"""
Generate copyright-free images for the landing page "No es magia" section.
Uses listing 12 and comparable photos as inspiration to generate original images.
"""

import asyncio
import os
import sys
import base64
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load env
from dotenv import load_dotenv
pass  # Recipient runtime supplies its explicit private environment.

OUTPUT_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/no-es-magia"

# Source images (downloaded from listing 12 and comparables)
SOURCE_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/listing-12"

BRACKETS = [
    {
        "name": "fast_sell",
        "label": "Venta Rápida",
        "target_price": "€628k–€663k",
        "source_file": "comp-fast-sell.jpg",
        "prompt": """Generate a photorealistic interior photo of a beautifully renovated Barcelona apartment living room.

STYLE:
- Light, bright, airy Mediterranean feel
- High ceilings with restored original moldings
- Warm wood herringbone parquet flooring
- White walls with subtle texture
- Large windows with natural light streaming in
- Modern minimalist furniture in neutral tones
- A few green plants for life

QUALITY:
- Professional real estate photography style
- Natural daylight, no harsh shadows
- 4:3 aspect ratio
- Photorealistic, could be from a real listing

This is for a "Venta Rápida" (quick sale) tier renovation - clean, fresh, attractive but not luxury."""
    },
    {
        "name": "fair_market",
        "label": "Mercado Justo",
        "target_price": "€698k–€713k",
        "source_file": "comp-fair-market.jpg",
        "prompt": """Generate a photorealistic interior photo of a beautifully renovated Barcelona apartment living room.

STYLE:
- Elegant Barcelona modernista aesthetic
- Restored original hydraulic tile floors in geometric patterns
- High ceilings with ornate plaster moldings and ceiling rose
- Large French windows opening to a small balcony
- Mix of vintage and contemporary furniture
- Exposed brick accent wall
- Designer lighting fixtures
- Tasteful art on walls

QUALITY:
- Professional architectural photography style
- Golden hour natural light
- 4:3 aspect ratio
- Photorealistic, magazine-quality

This is for a "Mercado Justo" (fair market) tier renovation - refined taste, quality finishes, character."""
    },
    {
        "name": "out_of_market",
        "label": "Premium",
        "target_price": "€750k–€895k",
        "source_file": "comp-out-of-market.jpg",
        "prompt": """Generate a photorealistic interior photo of a luxury renovated Barcelona apartment living room.

STYLE:
- High-end contemporary Barcelona design
- Double-height ceilings or dramatic ceiling details
- Premium materials: marble, natural stone, hardwood
- Designer furniture pieces (B&B Italia, Cassina style)
- Integrated smart home elements
- Statement lighting (sculptural pendant)
- Floor-to-ceiling windows with city views
- Curated art collection on walls
- Premium textiles and materials

QUALITY:
- Luxury real estate photography style
- Perfect lighting, architectural digest quality
- 4:3 aspect ratio
- Photorealistic, ultra-premium feel

This is for "Premium" tier renovation - no expense spared, showcase property."""
    }
]

# Also generate a "before" image
BEFORE_PROMPT = """Generate a photorealistic interior photo of an unrenovated Barcelona apartment needing work.

STYLE:
- 1970s-80s tired interior
- Old terrazzo or worn parquet floors
- Yellowed walls with cracks
- Outdated electrical fixtures
- Old aluminum windows
- Dated built-in furniture
- Slightly dark due to small windows
- General feel of "needs updating"

QUALITY:
- Real estate listing photo style
- Natural daylight but not bright
- 4:3 aspect ratio
- Photorealistic, authentic feel

This should look like a real Barcelona apartment that needs renovation - not destroyed, just tired and dated."""


async def generate_image(prompt: str, output_name: str, reference_image_path: Path = None):
    """Generate a single image using Gemini."""
    from pipeline.gemini_client import call_gemini_image, fetch_image_as_base64
    
    print(f"\n🎨 Generating: {output_name}")
    print(f"   Prompt: {prompt[:100]}...")
    
    # If we have a reference image, include it
    image_data = None
    image_mime_type = "image/jpeg"
    
    if reference_image_path and reference_image_path.exists():
        print(f"   📷 Using reference: {reference_image_path.name}")
        with open(reference_image_path, "rb") as f:
            image_bytes = f.read()
            image_data = base64.b64encode(image_bytes).decode("utf-8")
        
        # Modify prompt to reference the image
        prompt = f"""Look at this reference image for style and composition inspiration.

{prompt}

Generate a NEW, ORIGINAL image inspired by the reference but distinctly different - 
different room layout, different furniture arrangement, different specific details.
The goal is an original image that captures a similar feel but is not a copy."""
    
    try:
        if image_data:
            result = await call_gemini_image(
                prompt=prompt,
                image_data=image_data,
                image_mime_type=image_mime_type,
                model="pro-image",
                temperature=1.0,
            )
        else:
            # For text-only, we need a different approach
            # Generate with a placeholder image (white)
            placeholder = base64.b64encode(bytes([255] * 100)).decode("utf-8")
            result = await call_gemini_image(
                prompt=prompt,
                image_data=placeholder,
                image_mime_type="image/jpeg",
                model="pro-image",
                temperature=1.0,
            )
        
        if result.get("success"):
            output_path = OUTPUT_DIR / f"{output_name}.png"
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result["image_data"]))
            print(f"   ✅ Saved: {output_path}")
            return True
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


async def main():
    print("=" * 60)
    print("GENERATING LANDING PAGE IMAGES")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    # Generate "before" image
    print("\n" + "-" * 40)
    print("GENERATING 'BEFORE' IMAGE")
    print("-" * 40)
    
    before_ref = SOURCE_DIR / "before-listing12.jpg"
    await generate_image(
        prompt=BEFORE_PROMPT,
        output_name="before",
        reference_image_path=before_ref if before_ref.exists() else None
    )
    
    # Generate each bracket's "after" image
    for bracket in BRACKETS:
        print("\n" + "-" * 40)
        print(f"GENERATING '{bracket['label'].upper()}' IMAGE")
        print(f"Target: {bracket['target_price']}")
        print("-" * 40)
        
        ref_path = SOURCE_DIR / bracket["source_file"]
        await generate_image(
            prompt=bracket["prompt"],
            output_name=f"after-{bracket['name']}",
            reference_image_path=ref_path if ref_path.exists() else None
        )
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    
    # List generated files
    print("\n📂 Generated files:")
    for f in sorted(OUTPUT_DIR.glob("*.png")):
        size_kb = f.stat().st_size / 1024
        print(f"   - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
