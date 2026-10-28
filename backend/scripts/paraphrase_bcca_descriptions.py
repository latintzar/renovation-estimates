#!/usr/bin/env python3
"""
=============================================================================
paraphrase_bcca_descriptions.py - AI-Compress BCCA Descriptions to 100 chars
=============================================================================

PURPOSE: Use Gemini 2.5 Flash to intelligently paraphrase each BCCA item's
full_desc into exactly 100 characters, preserving key qualitative info.

WHY NOT TRUNCATE?
- Truncation cuts mid-sentence: "Mortero de cemento CEM II/A-L 32,5 N, tip..."
- Paraphrase captures essence: "Mortero cemento M10 (1:4), 10 N/mm², norma UNE-EN 998-2"

PROCESS:
1. Load all 12,565 BCCA items
2. Batch into groups of 20 (API efficiency)
3. Send to Gemini 2.5 Flash for paraphrasing
4. Store paraphrased descriptions in new column
5. Progress tracking and resume capability

OUTPUT: Updates construction.db with new column 'desc_100'

USAGE:
    python paraphrase_bcca_descriptions.py
    
    # Resume from where it left off:
    python paraphrase_bcca_descriptions.py --resume

AUTHOR: Reformia Team
DATE: 2026-01-11
=============================================================================
"""

import sqlite3
import json
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import google.generativeai as genai

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "pricing", "construction.db")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "bcca_paraphrase_progress.json")

# API Configuration
HELLO_KEY = ""
MODEL_ID = "gemini-2.5-flash-lite"  # Fast and cheap for paraphrasing

# Batching Configuration
BATCH_SIZE = 50  # Items per API call (larger batches = fewer calls)
DELAY_BETWEEN_BATCHES = 2.0  # Seconds between batches (rate limiting)
MAX_RETRIES = 5
RATE_LIMIT_DELAY = 30  # Seconds to wait on 429 error

# =============================================================================
# DATABASE SETUP
# =============================================================================

def setup_database():
    """Add desc_100 column if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(price_book)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'desc_100' not in columns:
        print("Adding desc_100 column to price_book...")
        cursor.execute("ALTER TABLE price_book ADD COLUMN desc_100 TEXT")
        conn.commit()
    
    conn.close()
    print("✓ Database ready")


def get_items_to_process(resume: bool = False) -> List[Tuple]:
    """Get all items that need paraphrasing."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if resume:
        # Only get items without desc_100
        cursor.execute("""
            SELECT id, short_desc, full_desc 
            FROM price_book 
            WHERE desc_100 IS NULL OR desc_100 = ''
            ORDER BY id
        """)
    else:
        # Get all items
        cursor.execute("""
            SELECT id, short_desc, full_desc 
            FROM price_book 
            ORDER BY id
        """)
    
    items = cursor.fetchall()
    conn.close()
    return items


def save_paraphrased(items: List[Dict]):
    """Save paraphrased descriptions to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for item in items:
        cursor.execute(
            "UPDATE price_book SET desc_100 = ? WHERE id = ?",
            (item['desc_100'], item['id'])
        )
    
    conn.commit()
    conn.close()


# =============================================================================
# GEMINI PARAPHRASING
# =============================================================================

def create_paraphrase_prompt(items: List[Tuple]) -> str:
    """Create a prompt for batch paraphrasing."""
    prompt = """You are a Spanish construction pricing expert. Your task is to create 
ultra-concise 100-character summaries of construction item descriptions.

RULES:
1. Output EXACTLY 100 characters per item (including spaces)
2. Preserve: dimensions, materials, standards, key specs
3. Use abbreviations: m², mm, cm, kg, ud, ml, CEM, HM, HA, UNE, CTE
4. Spanish language
5. No quotes or special formatting
6. If input is empty, create summary from short_desc

OUTPUT FORMAT (one line per item, no extra text):
CODE|100-char description

ITEMS TO PROCESS:
"""
    
    for code, short_desc, full_desc in items:
        if full_desc and len(full_desc) > 20:
            prompt += f"\n{code}|SHORT:{short_desc}|FULL:{full_desc[:500]}"
        else:
            prompt += f"\n{code}|SHORT:{short_desc}|FULL:(none)"
    
    prompt += "\n\nNow output the 100-char summaries:"
    return prompt


def parse_gemini_response(response_text: str, item_codes: List[str]) -> Dict[str, str]:
    """Parse Gemini response into code -> description mapping."""
    results = {}
    
    lines = response_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or '|' not in line:
            continue
        
        parts = line.split('|', 1)
        if len(parts) == 2:
            code = parts[0].strip()
            desc = parts[1].strip()[:100]  # Ensure max 100 chars
            
            # Pad to exactly 100 chars if needed
            if len(desc) < 100:
                desc = desc + ' ' * (100 - len(desc))
            
            if code in item_codes:
                results[code] = desc
    
    return results


def paraphrase_batch(items: List[Tuple], model) -> List[Dict]:
    """Paraphrase a batch of items using Gemini."""
    item_codes = [item[0] for item in items]
    prompt = create_paraphrase_prompt(items)
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,  # Low temperature for consistency
                max_output_tokens=4096,
            )
        )
        
        parsed = parse_gemini_response(response.text, item_codes)
        
        results = []
        for code, short_desc, full_desc in items:
            if code in parsed:
                results.append({
                    'id': code,
                    'desc_100': parsed[code]
                })
            else:
                # Fallback: truncate short_desc to 100 chars
                fallback = (short_desc or '')[:100]
                fallback = fallback + ' ' * (100 - len(fallback))
                results.append({
                    'id': code,
                    'desc_100': fallback
                })
        
        return results
        
    except Exception as e:
        print(f"    Error in batch: {e}")
        # Return fallback for all items
        return [{
            'id': item[0],
            'desc_100': (item[1] or '')[:100].ljust(100)
        } for item in items]


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

def save_progress(processed_count: int, total_count: int, start_time: float):
    """Save progress to file for resume capability."""
    progress = {
        'processed': processed_count,
        'total': total_count,
        'last_updated': datetime.now().isoformat(),
        'elapsed_seconds': time.time() - start_time
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def load_progress() -> Optional[Dict]:
    """Load previous progress if exists."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return None


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Paraphrase BCCA descriptions to 100 chars')
    parser.add_argument('--resume', action='store_true', help='Resume from previous progress')
    parser.add_argument('--test', action='store_true', help='Test with 5 items only')
    args = parser.parse_args()
    
    print("="*70)
    print("BCCA DESCRIPTION PARAPHRASER")
    print("Using Gemini 2.5 Flash to compress descriptions to 100 chars")
    print("="*70)
    
    # Setup
    setup_database()
    
    # Configure Gemini
    print(f"\nConfiguring Gemini ({MODEL_ID})...")
    genai.configure(api_key=HELLO_KEY)
    model = genai.GenerativeModel(MODEL_ID)
    print("✓ Gemini configured")
    
    # Get items to process
    print("\nLoading items to process...")
    items = get_items_to_process(resume=args.resume)
    total_items = len(items)
    
    if total_items == 0:
        print("✓ All items already processed!")
        return
    
    print(f"Found {total_items:,} items to process")
    
    if args.test:
        items = items[:5]
        total_items = 5
        print(f"TEST MODE: Processing only 5 items")
    
    # Calculate batches
    num_batches = (total_items + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Will process in {num_batches} batches of {BATCH_SIZE}")
    
    # Estimate time
    est_minutes = (num_batches * DELAY_BETWEEN_BATCHES) / 60
    print(f"Estimated time: {est_minutes:.1f} minutes")
    
    # Process batches
    start_time = time.time()
    processed = 0
    errors = 0
    
    print("\n" + "-"*70)
    print("Starting processing...")
    print("-"*70)
    
    for batch_num in range(num_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        batch_items = items[batch_start:batch_end]
        
        # Progress indicator
        pct = (batch_num + 1) / num_batches * 100
        elapsed = time.time() - start_time
        
        if batch_num > 0:
            eta_seconds = (elapsed / batch_num) * (num_batches - batch_num)
            eta_str = f"ETA: {eta_seconds/60:.1f}min"
        else:
            eta_str = "ETA: calculating..."
        
        print(f"\rBatch {batch_num + 1}/{num_batches} ({pct:.1f}%) | "
              f"Items {batch_start+1}-{batch_end}/{total_items} | "
              f"{eta_str}", end='', flush=True)
        
        # Process batch with retries and rate limit handling
        for attempt in range(MAX_RETRIES):
            try:
                results = paraphrase_batch(batch_items, model)
                save_paraphrased(results)
                processed += len(results)
                break
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    # Rate limit - wait longer
                    wait_time = RATE_LIMIT_DELAY * (attempt + 1)
                    print(f"\n    Rate limited! Waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif attempt < MAX_RETRIES - 1:
                    print(f"\n    Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    print(f"\n    Failed after {MAX_RETRIES} attempts: {e}")
                    errors += len(batch_items)
        
        # Save progress
        save_progress(processed, total_items, start_time)
        
        # Rate limiting delay
        if batch_num < num_batches - 1:
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"Total items processed: {processed:,}")
    print(f"Errors: {errors}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Rate: {processed/elapsed*60:.0f} items/minute")
    
    # Verify results
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM price_book WHERE desc_100 IS NOT NULL AND desc_100 != ''")
    complete = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM price_book")
    total = cursor.fetchone()[0]
    conn.close()
    
    print(f"\nDatabase status: {complete:,}/{total:,} items have desc_100")
    
    # Show samples
    print("\n--- Sample Results ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, short_desc, desc_100 
        FROM price_book 
        WHERE desc_100 IS NOT NULL AND desc_100 != ''
        ORDER BY RANDOM()
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"\n{row[0]}:")
        print(f"  SHORT: {row[1]}")
        print(f"  100ch: {row[2]}")
    conn.close()
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()

