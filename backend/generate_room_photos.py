#!/usr/bin/env python3
"""
Generate room photos for the landing page Guía de Visita section.
Creates thumbnails for: kitchen, bathroom, living room, entry/hallway
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

OUTPUT_DIR = Path(__file__).parent.parent / "frontend/public/images/landing/rooms"

ROOM_PROMPTS = {
    "kitchen": """Generate a photorealistic interior photo of an old Barcelona apartment kitchen needing renovation.

STYLE:
- 1970s-80s dated kitchen
- Old wooden cabinets, possibly dark wood or faded
- Old tile backsplash with dated pattern
- Old gas cooktop or basic appliances
- Worn countertop, possibly marble or old laminate
- Small window with light coming in
- General feel of "functional but very dated"

QUALITY:
- Real estate listing photo style
- Natural daylight
- Landscape orientation, close-up room shot
- Photorealistic, could be from a real listing""",

    "bathroom": """Generate a photorealistic interior photo of an old Barcelona apartment bathroom needing renovation.

STYLE:
- 1970s-80s dated bathroom
- Old tiles on walls and floor (possibly pink, green, or beige)
- Old bathtub or shower with dated fixtures
- Basic vanity or pedestal sink
- Possibly a bidet
- Old mirror cabinet
- Worn grout, possibly some discoloration
- Small frosted window
- General feel of "needs updating"

QUALITY:
- Real estate listing photo style
- Artificial bathroom lighting
- Landscape orientation, room shot
- Photorealistic, could be from a real listing""",

    "living": """Generate a photorealistic interior photo of an old Barcelona apartment living room needing renovation.

STYLE:
- 1970s-80s tired interior
- TWO LARGE WINDOWS (French balcony doors) letting in natural light
- Old parquet or terrazzo floors showing wear
- Yellowed walls, possibly with cracks
- Old built-in shelving or wall unit
- High ceilings typical of Barcelona Eixample
- Some dated furniture (old sofa, coffee table)
- General feel of "good bones but needs renovation"

QUALITY:
- Real estate listing photo style
- Natural daylight from windows
- Landscape orientation
- Photorealistic, could be from a real listing""",

    "entry": """Generate a photorealistic interior photo of an old Barcelona apartment entry/hallway.

STYLE:
- 1970s-80s dated entry area
- Long narrow hallway typical of Barcelona apartments
- Old terrazzo or worn parquet floors
- Yellowed walls
- Old wooden doors leading to rooms
- Electrical panel visible on wall (old style with fuses)
- Maybe an old coat rack or mirror
- Some natural light from end of hallway
- General feel of "needs updating"

QUALITY:
- Real estate listing photo style
- Dim natural or artificial lighting
- Landscape orientation
- Photorealistic, could be from a real listing"""
}


def create_placeholder_image():
    """Create a simple placeholder image to seed the generation."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color=(200, 190, 180))
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=80)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        # Minimal JPEG fallback
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
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xFB, 0xD5, 0xFF, 0xD9
        ])
        return base64.b64encode(minimal_jpeg).decode('utf-8')


async def generate_room_image(room_id: str, prompt: str):
    """Generate a single room image."""
    from pipeline.gemini_client import call_gemini_image
    
    print(f"\n🎨 Generating: {room_id}")
    
    placeholder_data = create_placeholder_image()
    
    try:
        result = await call_gemini_image(
            prompt=f"Transform this placeholder into: {prompt}",
            image_data=placeholder_data,
            image_mime_type="image/jpeg",
            model="pro-image",
            temperature=1.0,
        )
        
        if result.get("success") and result.get("image_data"):
            # Save as PNG
            output_path = OUTPUT_DIR / f"{room_id}.png"
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result["image_data"]))
            print(f"   ✅ Saved: {output_path.name}")
            
            # Also save as webp
            try:
                from PIL import Image
                img = Image.open(output_path)
                webp_path = OUTPUT_DIR / f"{room_id}.webp"
                img.save(webp_path, 'WEBP', quality=85)
                print(f"   ✅ Converted: {webp_path.name}")
            except Exception as e:
                print(f"   ⚠️ WebP conversion failed: {e}")
            
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
    print("GENERATING ROOM PHOTOS FOR GUÍA DE VISITA")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    results = {}
    for room_id, prompt in ROOM_PROMPTS.items():
        results[room_id] = await generate_room_image(room_id, prompt)
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    
    success = sum(1 for v in results.values() if v)
    print(f"\n✅ {success}/{len(ROOM_PROMPTS)} images generated successfully")
    
    print("\n📂 Generated files:")
    for f in sorted(OUTPUT_DIR.glob("*.*")):
        size_kb = f.stat().st_size / 1024
        print(f"   - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
