#!/usr/bin/env python3
"""
Flatten BCCA Price Book to YAML for Serverless KG Architecture.

PETER AGENTIC V0.2 - Phase 1.2

Converts construction.db to a token-efficient YAML format
that can be embedded in Gemini's system instruction.

CRITICAL: Excludes Chapter 18 (quality control tests)

Output: bcca_context.yaml (~100K tokens)
"""

import sqlite3
import yaml
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "construction.db"
OUTPUT_PATH = SCRIPT_DIR / "bcca_context.yaml"

# Chapter 18 = Quality Control (TESTS, not work) - EXCLUDE
EXCLUDED_CHAPTERS = ['18']

# Chapter names for reference
CHAPTER_NAMES = {
    '01': 'Revestimientos',
    '02': 'Cimentaciones',
    '03': 'Estructuras',
    '04': 'Cubiertas',
    '05': 'Cerramientos',
    '06': 'Carpintería',
    '07': 'Vidriería',
    '08': 'Instalaciones',
    '09': 'Aislamientos',
    '10': 'Señalización',
    '11': 'Urbanización',
    '12': 'Seguridad',
    '13': 'Gestión residuos',
    '14': 'Restauración',
    '15': 'Varios',
    '16': 'Control calidad',
    '17': 'Otros',
    '18': 'EXCLUDED - Tests',  # DO NOT USE
}


def load_bcca() -> list:
    """Load BCCA items from database, only core renovation chapters."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Only include renovation-relevant BCCA chapters
    # 01 = Revestimientos (tiles, flooring, painting)
    # 06 = Carpintería (doors, windows, cabinets)
    # 08 = Instalaciones (plumbing, electrical, HVAC)
    # 09 = Aislamientos (insulation)
    # 13 = Gestión residuos (waste management)
    # This keeps token count manageable while covering 95%+ of residential renovation
    CORE_CHAPTERS = ['01', '06', '08', '09', '13']
    
    placeholders = ','.join(['?' for _ in CORE_CHAPTERS])
    
    # Build query for core chapters only
    query = f"""
        SELECT id, description, unit, price 
        FROM price_book 
        WHERE price > 0 
        AND SUBSTR(id, 1, 2) IN ({placeholders})
        ORDER BY id
    """
    
    cursor.execute(query, CORE_CHAPTERS)
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for code, desc, unit, price in rows:
        # Skip chapter 18 (tests) even if it somehow got through
        if code.startswith('18'):
            continue
            
        items.append({
            'code': code,
            'desc': (desc or '')[:80],  # Truncate to save tokens
            'unit': unit or 'ud',
            'price': round(float(price), 2) if price else 0
        })
    
    return items


def group_by_chapter(items: list) -> dict:
    """Group items by BCCA chapter."""
    chapters = defaultdict(list)
    
    for item in items:
        chapter = item['code'][:2]
        chapters[chapter].append(item)
    
    return dict(chapters)


def build_chapter_summary(chapters: dict) -> dict:
    """Build summary statistics per chapter."""
    summary = {}
    
    for ch, items in chapters.items():
        name = CHAPTER_NAMES.get(ch, 'Unknown')
        prices = [i['price'] for i in items if i['price'] > 0]
        
        summary[ch] = {
            'name': name,
            'count': len(items),
            'price_range': f"€{min(prices):.0f}-€{max(prices):.0f}" if prices else "N/A"
        }
    
    return summary


def main():
    print("=" * 60)
    print("PETER AGENTIC V0.2 - Phase 1.2: Flatten BCCA")
    print("=" * 60)
    
    # Load BCCA
    print("\n📂 Loading BCCA database...")
    items = load_bcca()
    print(f"   Found {len(items)} items (Chapter 18 excluded)")
    
    # Group by chapter
    print("\n📋 Grouping by chapter...")
    chapters = group_by_chapter(items)
    
    for ch in sorted(chapters.keys()):
        name = CHAPTER_NAMES.get(ch, 'Unknown')
        count = len(chapters[ch])
        print(f"   Chapter {ch} ({name}): {count} items")
    
    # Build summary
    print("\n📊 Building chapter summary...")
    summary = build_chapter_summary(chapters)
    
    # Assemble YAML structure
    yaml_data = {
        'metadata': {
            'version': 'BCCA 2023',
            'items_count': len(items),
            'chapters_count': len(chapters),
            'excluded': 'Chapter 18 (quality control tests)',
            'currency': 'EUR',
            'region': 'Andalucía, Spain'
        },
        'usage_rules': [
            'Chapter 18 items are TESTS/INSPECTIONS - NEVER use codes starting with "18"',
            'Match by INTENT: "install toilet" → installation item, NOT test item',
            'Prices include labor and materials unless noted',
            'Units: m² (square meters), ml (linear meters), ud (units)',
            'If a code starts with "18" or description contains "ensayo/prueba", SKIP IT'
        ],
        'chapter_index': summary,
        'items': {}
    }
    
    # Add items by chapter
    for ch in sorted(chapters.keys()):
        ch_name = CHAPTER_NAMES.get(ch, 'Unknown')
        yaml_data['items'][f'ch{ch}_{ch_name.lower().replace(" ", "_")}'] = chapters[ch]
    
    # Write YAML
    print(f"\n💾 Writing to {OUTPUT_PATH}...")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# " + "=" * 58 + "\n")
        f.write("# BCCA PRICE BOOK (Base de Costes de la Construcción)\n")
        f.write("# PETER AGENTIC V0.2 - Serverless KG Context\n")
        f.write("# " + "=" * 58 + "\n")
        f.write("# \n")
        f.write("# CRITICAL: Chapter 18 is EXCLUDED (quality control tests)\n")
        f.write("# NEVER use any code starting with '18' - these are TESTS!\n")
        f.write("# \n")
        f.write("# USAGE:\n")
        f.write("# - Match renovation tasks to BCCA codes by description\n")
        f.write("# - Verify the item is INSTALLATION work, not a test\n")
        f.write("# - Use the unit and price for quantity calculation\n")
        f.write("# " + "=" * 58 + "\n\n")
        
        yaml.dump(yaml_data, f, 
                  default_flow_style=False, 
                  allow_unicode=True,
                  sort_keys=False,
                  width=120)
    
    # Calculate token estimate
    with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    char_count = len(content)
    token_estimate = char_count // 3
    
    print(f"\n✅ Done!")
    print(f"   File size: {char_count:,} chars")
    print(f"   Estimated tokens: ~{token_estimate:,}")
    print(f"   Output: {OUTPUT_PATH}")
    
    # Warn if too large
    if token_estimate > 500000:
        print(f"\n⚠️  WARNING: Token count is high!")
        print(f"   Consider filtering to relevant chapters only.")


if __name__ == "__main__":
    main()

