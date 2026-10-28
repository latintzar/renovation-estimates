"""
BCCA Index Export Script (V0.4.8)
=================================

Exports the BCCA (Spanish Construction Price Book) to a text file
for inclusion in Gemini context.

Format: CODE|desc_100
Example: 004600100|Sensor temperatura ambiente STR100. Medición Tª. Para control climático.

Output: pricing/data/bcca_index.txt (~700KB)
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
BCCA_DB_PATH = PRICING_DIR / "construction.db"
OUTPUT_PATH = PRICING_DIR / "data" / "bcca_index.txt"


def export_bcca_index():
    """Export BCCA items to text index file."""
    
    logger.info("=" * 60)
    logger.info("BCCA INDEX EXPORT")
    logger.info("=" * 60)
    
    if not BCCA_DB_PATH.exists():
        raise FileNotFoundError(f"BCCA database not found: {BCCA_DB_PATH}")
    
    logger.info(f"Database: {BCCA_DB_PATH}")
    logger.info(f"Output: {OUTPUT_PATH}")
    
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(BCCA_DB_PATH)
    cursor = conn.cursor()
    
    # Get items with desc_100
    cursor.execute("""
        SELECT id, desc_100, price 
        FROM price_book 
        WHERE desc_100 IS NOT NULL AND desc_100 != ''
        ORDER BY id
    """)
    
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} items with desc_100")
    
    # Write to output file
    lines_written = 0
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # Header
        f.write("# BCCA Index - Spanish Construction Price Book\n")
        f.write("# Format: CODE|DESC_100|PRICE\n")
        f.write(f"# Items: {len(rows)}\n")
        f.write("# ===\n\n")
        
        for item_code, desc_100, price in rows:
            # Clean up description (remove trailing whitespace, normalize)
            desc_clean = desc_100.strip() if desc_100 else ""
            if desc_clean:
                f.write(f"{item_code}|{desc_clean}|{price:.2f}\n")
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
    result = export_bcca_index()
    print(f"\nResult: {result}")

