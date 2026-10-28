#!/usr/bin/env python3
"""
Generate BCCA Index: WORK ITEMS ONLY with Full Descriptions + Full Breakdowns
==============================================================================

Output:
- ONLY work items (items with decomposition) - no básicos
- Full descriptions from BC3 ~T records (not AI 100-char summaries)
- Full breakdown with labor hours and all components

Format: CODE|UNIT|PRICE|FULL_DESC|LABOR_HOURS|BREAKDOWN
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
BC3_FILE = Path("/root/puedo_casa/lean-mvp/Uploads from Local/BCCA2023_V02.bc3")
OUTPUT_FILE = Path("/root/puedo_casa/lean-mvp/backend/pricing/data/bcca_full_index.txt")

# Labor codes
LABOR_CODES = {
    'TO00100': 'Oficial 1ª construcción',
    'TO00200': 'Oficial 2ª construcción',
    'TP00100': 'Peón ordinario',
    'TP00200': 'Peón especializado',
    'TO01600': 'Oficial 1ª cerrajero',
    'TO01800': 'Oficial 1ª electricista',
    'TO02100': 'Oficial 1ª rehabilitación',
    'TA00100': 'Ayudante',
    'TA00200': 'Ayudante',
    'TA00300': 'Ayudante carpintería',
    'ATC00100': 'Cuadrilla albañilería',
    'ATC00200': 'Cuadrilla instalaciones',
}


def parse_bc3_file(bc3_path: Path) -> Tuple[Dict, Dict, Dict]:
    """Parse BC3 file for concepts, decompositions, and full texts."""
    
    try:
        content = bc3_path.read_text(encoding='windows-1252')
    except:
        content = bc3_path.read_text(encoding='latin-1')
    
    concepts = {}      # code -> {unit, price, short_desc}
    decompositions = {}  # code -> [(comp_code, factor, qty), ...]
    full_texts = {}    # code -> full description
    
    for line in content.split('\n'):
        line = line.strip().replace('\r', '')
        if not line.startswith('~'):
            continue
        
        parts = line.split('|')
        record_type = parts[0][1:]
        
        if record_type == 'C' and len(parts) >= 5:
            code = parts[1]
            if code.endswith('#') or not code:
                continue
            
            unit = parts[2].lower() if len(parts) > 2 else ''
            short_desc = parts[3] if len(parts) > 3 else ''
            try:
                price = float(parts[4]) if parts[4] else 0.0
            except:
                price = 0.0
            
            concepts[code] = {'unit': unit, 'price': price, 'short_desc': short_desc}
        
        elif record_type == 'D' and len(parts) >= 3:
            parent_code = parts[1]
            if not parent_code or parent_code.endswith('#'):
                continue
            
            components = []
            comp_parts = parts[2].split('\\')
            i = 0
            while i + 2 < len(comp_parts):
                comp_code = comp_parts[i]
                try:
                    factor = float(comp_parts[i + 1]) if comp_parts[i + 1] else 1.0
                    qty = float(comp_parts[i + 2]) if comp_parts[i + 2] else 0.0
                except:
                    factor, qty = 1.0, 0.0
                
                if comp_code and qty > 0:
                    components.append((comp_code, factor, qty))
                i += 3
            
            if components:
                decompositions[parent_code] = components
        
        elif record_type == 'T' and len(parts) >= 3:
            code = parts[1]
            full_desc = parts[2] if len(parts) > 2 else ''
            if code and not code.endswith('#'):
                full_texts[code] = full_desc
    
    return concepts, decompositions, full_texts


def calculate_labor_hours(decomposition: List[Tuple], concepts: Dict) -> float:
    """Calculate total labor hours from decomposition."""
    total = 0.0
    for comp_code, factor, qty in decomposition:
        if comp_code.startswith('T') or comp_code.startswith('ATC'):
            total += qty * factor
        elif comp_code in concepts and concepts[comp_code].get('unit') == 'h':
            total += qty * factor
    return round(total, 3)


def format_breakdown(decomposition: List[Tuple], concepts: Dict) -> str:
    """Format decomposition as readable breakdown - ALL components."""
    parts = []
    for comp_code, factor, qty in decomposition:
        if qty <= 0:
            continue
        
        comp_info = concepts.get(comp_code, {})
        comp_unit = comp_info.get('unit', '')
        
        if comp_code.startswith('T') or comp_code.startswith('ATC'):
            labor_name = LABOR_CODES.get(comp_code, comp_code)
            parts.append(f"{qty:.2f}h {labor_name}")
        else:
            parts.append(f"{comp_code}:{qty:.3f}{comp_unit}")
    
    return "; ".join(parts)


def generate_index():
    """Generate BCCA index with work items only."""
    
    print(f"Parsing {BC3_FILE}...")
    concepts, decompositions, full_texts = parse_bc3_file(BC3_FILE)
    
    print(f"Found {len(concepts)} concepts, {len(decompositions)} decompositions, {len(full_texts)} texts")
    
    # Header
    lines = [
        "# BCCA Index - Work Items Only",
        "# Format: CODE|UNIT|PRICE|FULL_DESC|LABOR_HOURS|BREAKDOWN",
        "# Work items: items with decomposition (labor + materials)",
        "# Básicos excluded (redundant - visible in breakdowns)",
        "# ===",
        ""
    ]
    
    work_item_count = 0
    
    # Only include items WITH decomposition (work items)
    for code in sorted(decompositions.keys()):
        if code not in concepts:
            continue
        
        info = concepts[code]
        unit = info['unit']
        price = info['price']
        
        # Get full description (prefer ~T record)
        if code in full_texts:
            desc = full_texts[code]
        else:
            desc = info['short_desc']
        
        # Clean description
        desc = desc.replace('|', '/').replace('\n', ' ').replace('\r', '').strip()
        
        # Get breakdown
        decomp = decompositions[code]
        labor_hours = calculate_labor_hours(decomp, concepts)
        breakdown = format_breakdown(decomp, concepts)
        
        line = f"{code}|{unit}|{price}|{desc}|{labor_hours}|{breakdown}"
        lines.append(line)
        work_item_count += 1
    
    # Write
    OUTPUT_FILE.write_text('\n'.join(lines), encoding='utf-8')
    
    # Stats
    total_chars = sum(len(line) for line in lines)
    est_tokens = total_chars / 4
    
    print(f"\nGenerated {OUTPUT_FILE}")
    print(f"  Work items: {work_item_count}")
    print(f"  File size: {total_chars:,} chars")
    print(f"  Est. tokens: ~{int(est_tokens):,}")
    
    # Sample
    print("\nSample (first 3 work items):")
    for line in lines[6:9]:
        print(f"  {line[:100]}...")


if __name__ == "__main__":
    generate_index()
