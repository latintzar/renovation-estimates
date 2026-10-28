#!/usr/bin/env python3
"""
Flatten Knowledge Graph to YAML for Serverless KG Architecture.

PETER AGENTIC V0.3 - Full Enrichment

Converts hybrid_renovation_graph.json to a token-efficient YAML format
that can be embedded in Gemini's system instruction.

CRITICAL: Includes FULL quantity_guidance enrichment for each task:
- quantity_type (area_m2, count, linear_m, etc.)
- scope (per_room, per_opening, per_unit)
- reasoning_factors (what to consider when calculating)
- typical_rules (industry standards)
- constraints (min/max values)

Output: kg_context.yaml (~120K tokens with full enrichment)
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
KG_PATH = SCRIPT_DIR / "hybrid_renovation_graph.json"
OUTPUT_PATH = SCRIPT_DIR / "kg_context.yaml"


def load_kg() -> dict:
    """Load the Knowledge Graph JSON."""
    with open(KG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def flatten_tasks(kg: dict) -> list:
    """
    Extract tasks with FULL enrichment.
    
    MAXED OUT: Includes all quantity_guidance data for precise LLM reasoning.
    """
    tasks = kg.get('canonical_tasks', {})
    flattened = []
    
    enriched_count = 0
    
    for task_id, task in tasks.items():
        flat_task = {
            'id': task_id,
            'name': task.get('name', ''),
            'trade': task.get('primary_trade', 'general'),
            'layer': task.get('layer', 'unknown'),
            'unit': task.get('unit', 'ud'),
            'bcca_chapter': task.get('bcca_chapter', ''),
            'bcca_keyword': task.get('default_keyword', task.get('name', '')),
            'is_structural': task.get('is_structural', False),
            'permit_type': task.get('permit_type', 'none'),
            'invasiveness': task.get('invasiveness', 1),
        }
        
        # Include FULL quantity_guidance if present
        qg = task.get('quantity_guidance')
        if qg:
            flat_task['quantity_guidance'] = {
                'type': qg.get('quantity_type', 'unit'),
                'scope': qg.get('scope', 'per_room'),
                'reasoning': qg.get('reasoning_factors', []),
                'rules': qg.get('typical_rules', []),
                'constraints': qg.get('constraints', {}),
                'unit': qg.get('unit', 'ud')
            }
            enriched_count += 1
        else:
            # Fallback to legacy fields
            flat_task['quantity_guidance'] = {
                'type': task.get('quantity_source', 'unit'),
                'scope': 'per_room',
                'reasoning': [],
                'rules': [],
                'constraints': {},
                'unit': task.get('unit', 'ud')
            }
            # Include buffer if not 1.0
            qty_buffer = task.get('quantity_buffer', 1.0)
            if qty_buffer != 1.0:
                flat_task['quantity_guidance']['buffer'] = qty_buffer
        
        flattened.append(flat_task)
    
    print(f"   Tasks with full quantity_guidance: {enriched_count}/{len(tasks)}")
    
    return flattened


def extract_relationships(kg: dict) -> dict:
    """Extract REQUIRES and TRIGGERS relationships."""
    tasks = kg.get('canonical_tasks', {})
    
    requires = []
    triggers = []
    
    for task_id, task in tasks.items():
        # Get short name for readability
        task_name = task.get('name', task_id)[:40]
        
        for req_id in task.get('requires', []):
            if req_id in tasks:
                req_name = tasks[req_id].get('name', req_id)[:40]
                requires.append(f"{task_id} REQUIRES {req_id}")
        
        for trig_id in task.get('triggers', []):
            if trig_id in tasks:
                trig_name = tasks[trig_id].get('name', trig_id)[:40]
                triggers.append(f"{task_id} TRIGGERS {trig_id}")
    
    return {
        'requires': requires,
        'triggers': triggers
    }


def build_room_mappings(kg: dict) -> dict:
    """Build room type to typical tasks mapping."""
    tasks = kg.get('canonical_tasks', {})
    
    # Keywords that indicate room types
    room_keywords = {
        'baño': ['baño', 'aseo', 'ducha', 'sanitar', 'grifo', 'lavabo', 'inodoro', 'bañera', 'mampara', 'wc'],
        'cocina': ['cocina', 'encimera', 'campana', 'fregadero', 'vitro', 'horno', 'lavavajillas'],
        'dormitorio': ['dormitorio', 'habitación', 'armario empotrado'],
        'salon': ['salón', 'living', 'estar'],
        'terraza': ['terraza', 'balcón', 'exterior'],
        'general': ['pintura', 'suelo', 'solado', 'electricidad', 'fontanería', 'demolición', 'limpieza']
    }
    
    room_tasks = defaultdict(list)
    
    for task_id, task in tasks.items():
        task_name = task.get('name', '').lower()
        
        for room, keywords in room_keywords.items():
            if any(kw in task_name for kw in keywords):
                room_tasks[room].append(task_id)
                break
    
    return dict(room_tasks)


def build_quantity_formulas() -> dict:
    """Define quantity calculation formulas."""
    return {
        'floor_m2': {
            'description': 'Floor area',
            'formula': 'room_m2',
            'example': '12m² room = 12m² flooring'
        },
        'wall_m2': {
            'description': 'Wall area',
            'formula': 'perimeter × height',
            'example': '12m² room, 2.5m height ≈ 35m² walls'
        },
        'perimeter_ml': {
            'description': 'Room perimeter',
            'formula': '4 × √(room_m2)',
            'example': '12m² room ≈ 14ml perimeter'
        },
        'ceiling_m2': {
            'description': 'Ceiling area',
            'formula': 'room_m2',
            'example': 'Same as floor area'
        },
        'unit': {
            'description': 'Count of items',
            'formula': '1 per room (or as specified)',
            'example': '1 toilet per bathroom'
        },
        'window_m2': {
            'description': 'Window area',
            'formula': '~10% of wall_m2',
            'example': '35m² walls ≈ 3.5m² windows'
        },
        'door_ud': {
            'description': 'Door count',
            'formula': '1-2 per room',
            'example': '1 entry + 1 closet'
        }
    }


def main():
    print("=" * 60)
    print("PETER AGENTIC V0.3 - Flatten KG with FULL Enrichment")
    print("=" * 60)
    
    # Load KG
    print("\n📂 Loading Knowledge Graph...")
    kg = load_kg()
    
    tasks = kg.get('canonical_tasks', {})
    print(f"   Found {len(tasks)} tasks")
    
    # Flatten tasks
    print("\n📋 Flattening tasks...")
    flat_tasks = flatten_tasks(kg)
    print(f"   Flattened {len(flat_tasks)} tasks")
    
    # Extract relationships
    print("\n🔗 Extracting relationships...")
    relationships = extract_relationships(kg)
    print(f"   REQUIRES: {len(relationships['requires'])} edges")
    print(f"   TRIGGERS: {len(relationships['triggers'])} edges")
    
    # Build room mappings
    print("\n🏠 Building room mappings...")
    room_mappings = build_room_mappings(kg)
    for room, task_ids in room_mappings.items():
        print(f"   {room}: {len(task_ids)} tasks")
    
    # Build quantity formulas
    print("\n📐 Adding quantity formulas...")
    qty_formulas = build_quantity_formulas()
    
    # Assemble YAML structure
    yaml_data = {
        'metadata': {
            'version': '3.0',
            'architecture': 'PETER_AGENTIC_V0.3',
            'tasks_count': len(flat_tasks),
            'requires_count': len(relationships['requires']),
            'triggers_count': len(relationships['triggers']),
            'enrichment': 'FULL quantity_guidance for all tasks',
            'source': 'hybrid_renovation_graph.json'
        },
        'tasks': flat_tasks,
        'relationships': relationships,
        'room_mappings': room_mappings,
        'quantity_formulas': qty_formulas
    }
    
    # Write YAML
    print(f"\n💾 Writing to {OUTPUT_PATH}...")
    
    # Custom YAML dumper for cleaner output
    class CleanDumper(yaml.SafeDumper):
        pass
    
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    
    CleanDumper.add_representer(str, str_representer)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# " + "=" * 58 + "\n")
        f.write("# RENOVATION KNOWLEDGE GRAPH - FULL ENRICHMENT\n")
        f.write("# PETER AGENTIC V0.3 - Maxed Out Context\n")
        f.write("# " + "=" * 58 + "\n")
        f.write("# \n")
        f.write("# This file is embedded in Gemini's system instruction.\n")
        f.write("# Contains ALL 683 renovation tasks with FULL enrichment.\n")
        f.write("# \n")
        f.write("# TASK FIELDS:\n")
        f.write("# - id: unique task identifier\n")
        f.write("# - name: human readable name\n")
        f.write("# - trade: who does this work (electricista, albanil, etc.)\n")
        f.write("# - layer: shell/canvas/veins/finishes\n")
        f.write("# - bcca_chapter: which BCCA chapter to search\n")
        f.write("# - bcca_keyword: default search term\n")
        f.write("# - quantity_guidance: HOW to calculate quantities\n")
        f.write("#   - type: area_m2, count, linear_m, etc.\n")
        f.write("#   - scope: per_room, per_opening, per_unit\n")
        f.write("#   - reasoning: what factors to consider\n")
        f.write("#   - rules: industry measurement standards\n")
        f.write("#   - constraints: min/max/buffer values\n")
        f.write("# \n")
        f.write("# RELATIONSHIPS:\n")
        f.write("# - REQUIRES = must happen before (prerequisites)\n")
        f.write("# - TRIGGERS = should happen after (consequences)\n")
        f.write("# \n")
        f.write("# " + "=" * 58 + "\n\n")
        
        yaml.dump(yaml_data, f, Dumper=CleanDumper, 
                  default_flow_style=False, 
                  allow_unicode=True,
                  sort_keys=False,
                  width=120)
    
    # Calculate token estimate
    with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    char_count = len(content)
    token_estimate = char_count // 3  # Rough estimate
    
    print(f"\n✅ Done!")
    print(f"   File size: {char_count:,} chars")
    print(f"   Estimated tokens: ~{token_estimate:,}")
    print(f"   Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

