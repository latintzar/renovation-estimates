"""
FFE Index Export Script (V0.4.8)
================================

Exports the FFE (Furniture, Fixtures & Equipment) database to a text file
for inclusion in Gemini context.

Format: CODE|name_es|budget_low|budget_mid|budget_high
Example: FFE_LIGHT_PEND_01|Lámpara Colgante Individual (Minimalista/Nórdica)|15.0|25.0|45.0

Output: pricing/data/ffe_index.txt (~15KB)
"""

import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
PRICING_DIR = BACKEND_DIR / "pricing"
FFE_DB_PATH = PRICING_DIR / "data" / "ffe.db"
OUTPUT_PATH = PRICING_DIR / "data" / "ffe_index.txt"


def export_ffe_index():
    """Export FFE items to text index file."""
    
    logger.info("=" * 60)
    logger.info("FFE INDEX EXPORT")
    logger.info("=" * 60)
    
    if not FFE_DB_PATH.exists():
        raise FileNotFoundError(f"FFE database not found: {FFE_DB_PATH}")
    
    logger.info(f"Database: {FFE_DB_PATH}")
    logger.info(f"Output: {OUTPUT_PATH}")
    
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(FFE_DB_PATH)
    cursor = conn.cursor()
    
    # Get all FFE items
    cursor.execute("""
        SELECT 
            code, 
            name_es, 
            description_es,
            budget_low, 
            budget_mid, 
            budget_high,
            unit,
            category_code
        FROM ffe_items 
        ORDER BY category_code, code
    """)
    
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} FFE items")
    
    # Write to output file
    lines_written = 0
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # Header
        f.write("# FFE Index - Furniture, Fixtures & Equipment\n")
        f.write("# Format: CODE|NAME_ES|DESCRIPTION|BUDGET_LOW|BUDGET_MID|BUDGET_HIGH|UNIT|CATEGORY\n")
        f.write(f"# Items: {len(rows)}\n")
        f.write("# ===\n\n")
        
        for row in rows:
            code, name_es, desc_es, budget_low, budget_mid, budget_high, unit, category = row
            
            # Clean up values
            name_clean = (name_es or "").strip()
            desc_clean = (desc_es or "").strip()[:100]  # Truncate long descriptions
            unit_clean = (unit or "ud").strip()
            category_clean = (category or "").strip()
            
            if name_clean:
                f.write(f"{code}|{name_clean}|{desc_clean}|{budget_low:.2f}|{budget_mid:.2f}|{budget_high:.2f}|{unit_clean}|{category_clean}\n")
                lines_written += 1
    
    conn.close()
    
    # Report stats
    file_size = OUTPUT_PATH.stat().st_size
    logger.info(f"✅ Exported {lines_written} items")
    logger.info(f"✅ File size: {file_size / 1024:.1f} KB")
    logger.info("=" * 60)
    
    return {
        "items_exported": lines_written,
        "file_size_kb": file_size / 1024,
        "output_path": str(OUTPUT_PATH)
    }


if __name__ == "__main__":
    result = export_ffe_index()
    print(f"\nResult: {result}")

