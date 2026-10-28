Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Knowledge Graph Traversal Architecture

## The Core Insight

**The KG already has everything we need.** The problem isn't missing data - it's that we're not traversing the graph properly.

---

## Current State (The Problem)

### What We Have
- **683 canonical tasks** with Spanish construction knowledge
- **2,789 dependency edges** (`requires` + `triggers`)
- **`quantity_guidance`** for every task (reasoning factors, constraints)
- **Room-task mappings** with wet/dry variants

### What's Broken
The resolver only traverses **selectively**:

```python
# Current code (renovation_resolver.py ~lines 1029-1044)

# Only follows 'requires' for STRUCTURAL tasks
for req_id in task.get('requires', []):
    if any(kw in req_name for kw in ['apeo', 'apuntal', 'refuerz', 'dintel', 'viga']):
        traverse(req_id, ...)  # Misses everything else!

# Only follows 'triggers' for CLEANUP tasks  
for trig_id in task.get('triggers', []):
    if any(kw in trig_name for kw in ['escomb', 'residuo', 'contenedor']):
        traverse(trig_id, ...)  # Misses everything else!
```

**Result:** Starting from "Install toilet", we only find 3-5 tasks instead of the 19 that are actually required.

---

## The Fix: Full Backward Traversal

### The Principle

In construction, work flows **forward** but planning flows **backward**:

```
PLANNING (what we need):        EXECUTION (what happens):
────────────────────────        ──────────────────────────
Start with END goal:            Start with FIRST task:
"Install new toilet"            "Protect floors"
       ↑                               ↓
What does it require?           Then demolition
       ↑                               ↓
What does THAT require?         Then plumbing rough-in
       ↑                               ↓
Keep going until                Then waterproofing
we hit tasks with               ...
no prerequisites                Finally: Install toilet
```

### The Algorithm

```python
def get_complete_task_chain(terminal_task_id: str, kg_tasks: Dict) -> List[str]:
    """
    Traverse BACKWARD from a terminal task to find ALL prerequisites.
    This gives us the complete work sequence.
    """
    all_tasks = set()
    
    def traverse_backward(task_id: str, visited: Set[str]):
        if task_id in visited:
            return
        visited.add(task_id)
        
        task = kg_tasks.get(task_id)
        if not task:
            return
        
        all_tasks.add(task_id)
        
        # Follow ALL requires edges - no filtering!
        for req_id in task.get('requires', []):
            traverse_backward(req_id, visited)
    
    traverse_backward(terminal_task_id, set())
    return list(all_tasks)
```

### Proof It Works

Testing with "Instalación de equipamiento sanitario":

```
BACKWARD TRAVERSAL (requires):
============================================================
Starting from: Instalación de equipamiento sanitario

          ↓ Demolición de revestimientos existentes
          ↓ Protección de zonas comunes/paso
          ↓ Levantado de solados y rodapiés
          ↓ Demolicón completa de solado
          ↓ Levantado de pavimentos
        ↓ Protección de zonas comunes y ascensor
        ↓ Protección de zonas de paso y elementos
        ↓ Levantado de solados y rodapiés antiguos
        ↓ Rozas y ayudas de albañilería para instalaciones
        ↓ Suelo Radiante (Fontanería)
      ↓ Demolición de solado existente
      ↓ Nivelación de solera
    ↓ Solado de gres porcelánico / rectificado
    ↓ Solado de gres de alta resistencia
    ↓ Solado de barro cocido manual
    ↓ Solado de gres porcelánico exterior
  ↓ Solado (Cerámico/Porcelánico)
  ↓ Rejuntado de cerámica
↓ Instalación de equipamiento sanitario

Total tasks found: 19
```

**19 tasks** from one terminal task - the KG knows the full sequence!

---

## The Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORRECTED PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. CONDITION ASSESSMENT (per room)                                           │
│                                                                              │
│    Photos → Rule Violations (REBT/CTE) → Uniclass Element Conditions         │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. GAP ANALYSIS (Gemini)                                                     │
│                                                                              │
│    Compare target vs comparables. Identify OUTCOMES needed:                  │
│                                                                              │
│    Room: Baño Principal                                                      │
│    ├── Outcome: "Modern bathroom with new sanitarios"                        │
│    ├── Outcome: "REBT-compliant electrical"                                  │
│    └── Evidence: "1980s fixtures, no differential protection"               │
│                                                                              │
│    The gap analysis identifies WHAT needs to change, not HOW.                │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. TERMINAL TASK MATCHING                                                    │
│                                                                              │
│    Map outcomes to KG TERMINAL tasks (visible end states):                   │
│                                                                              │
│    "Modern bathroom sanitarios" → TASK_INSTA_EQUIP_SANIT                     │
│    "REBT electrical"            → TASK_BOLET_ELECT (certification)           │
│    "Fresh paint"                → TASK_PINTU_PLAST_PARAM                     │
│                                                                              │
│    Terminal tasks are the GOALS - the visible deliverables.                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4. KG BACKWARD TRAVERSAL (The Key Step!)                                     │
│                                                                              │
│    For each terminal task, traverse ALL `requires` edges:                    │
│                                                                              │
│    TASK_INSTA_EQUIP_SANIT                                                    │
│        ↑ requires                                                            │
│    TASK_REJUN_CERAM ─────────────┐                                           │
│        ↑ requires                │                                           │
│    TASK_SOLAD_CERAM              │                                           │
│        ↑ requires                │                                           │
│    TASK_NIVEL_SOLER              │  = Complete prerequisite chain            │
│        ↑ requires                │    (19 tasks for bathroom)                │
│    TASK_DEMOL_SOLAD              │                                           │
│        ↑ requires                │                                           │
│    TASK_PROTE_ZONAS ─────────────┘                                           │
│                                                                              │
│    NO FILTERING! Follow every edge.                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 5. FORWARD PASS (triggers) - Optional Cleanup                                │
│                                                                              │
│    After backward traversal, add triggered cleanup tasks:                    │
│    - Gestión de residuos                                                     │
│    - Limpieza final de obra                                                  │
│                                                                              │
│    These are consequences, not prerequisites.                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 6. TOPOLOGICAL SORT                                                          │
│                                                                              │
│    Order tasks so prerequisites come before dependents:                      │
│                                                                              │
│    1. Protección de zonas        (no prerequisites)                          │
│    2. Demolición de solado       (requires: protection)                      │
│    3. Nivelación de solera       (requires: demolition)                      │
│    4. Solado cerámico            (requires: leveling)                        │
│    5. Rejuntado                  (requires: tiling)                          │
│    6. Instalación sanitarios     (requires: grouting)                        │
│    7. Limpieza final             (triggered by: installation)                │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 7. QUANTITY CALCULATION (using quantity_guidance)                            │
│                                                                              │
│    Each task has KG-defined guidance:                                        │
│                                                                              │
│    TASK_SOLAD_CERAM:                                                         │
│      quantity_type: "area_m2"                                                │
│      scope: "per_room"                                                       │
│      typical_rules: ["Floor area + 10% waste"]                               │
│      constraints: {min: 1, max_per_room: 100}                                │
│                                                                              │
│    Gemini reasons within these guardrails. No hallucination.                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 8. BCCA MATCHING + PRICING                                                   │
│                                                                              │
│    Hybrid BM25 + vector search against 12,565 BCCA items.                    │
│    Produces Bill of Quantities with unit prices.                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 9. OUTPUT GENERATION                                                         │
│                                                                              │
│    FOR CUSTOMER (layman):                                                    │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │ 🛁 BAÑO PRINCIPAL                                                   │   │
│    │                                                                     │   │
│    │ Objetivo: Renovación integral del baño                             │   │
│    │                                                                     │   │
│    │ Su baño actual presenta sanitarios anticuados de los años 80       │   │
│    │ y una instalación eléctrica que no cumple normativa vigente.       │   │
│    │ La reforma incluirá:                                               │   │
│    │                                                                     │   │
│    │ ✓ Nuevos sanitarios de diseño moderno                              │   │
│    │ ✓ Revestimientos cerámicos de calidad                              │   │
│    │ ✓ Plato de ducha extraplano con mampara                            │   │
│    │ ✓ Grifería termostática                                            │   │
│    │ ✓ Iluminación LED integrada                                        │   │
│    │                                                                     │   │
│    │ Coste estimado: €8,500                                             │   │
│    │ Duración: 2-3 semanas                                              │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│    FOR CONTRACTOR (technical):                                               │
│    ┌─────────────────────────────────────────────────────────────────────┐   │
│    │ Partida          │ Ud  │ Cant  │ Precio │ Total   │ BCCA           │   │
│    │ ─────────────────┼─────┼───────┼────────┼─────────┼────────────────│   │
│    │ Protección zonas │ m²  │ 12.00 │  2.50  │   30.00 │ 18BSV000101    │   │
│    │ Demolición alic. │ m²  │ 35.00 │  8.20  │  287.00 │ 18BSV000102    │   │
│    │ Fontanería baño  │ ud  │  1.00 │ 850.00 │  850.00 │ 07IFF00001     │   │
│    │ ...              │     │       │        │         │                │   │
│    └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│    FOR ARCHITECT (PDF export):                                               │
│    - Full technical specifications                                           │
│    - Uniclass codes                                                          │
│    - CTE compliance notes                                                    │
│    - Permit requirements                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Code Changes Required

### 1. Fix Dependency Traversal

**File:** `/backend/pricing/renovation_resolver.py`

**Current (selective):**
```python
# Only structural
if any(kw in req_name for kw in ['apeo', 'apuntal', 'refuerz']):
    traverse(req_id, ...)
```

**Fixed (complete):**
```python
# Follow ALL requires edges
for req_id in task.get('requires', []):
    if req_id in self.tasks:
        traverse(req_id, chain + [f"required by {task['name'][:30]}"], visited, depth + 1)
```

### 2. Add Topological Sort

After collecting all tasks, sort them so prerequisites come first:

```python
from collections import defaultdict

def topological_sort(tasks: List[str], kg_tasks: Dict) -> List[str]:
    """Sort tasks so prerequisites come before dependents."""
    # Build dependency graph
    in_degree = defaultdict(int)
    graph = defaultdict(list)
    
    for tid in tasks:
        task = kg_tasks.get(tid, {})
        for req_id in task.get('requires', []):
            if req_id in tasks:
                graph[req_id].append(tid)
                in_degree[tid] += 1
    
    # Kahn's algorithm
    queue = [t for t in tasks if in_degree[t] == 0]
    result = []
    
    while queue:
        task = queue.pop(0)
        result.append(task)
        for dependent in graph[task]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    return result
```

### 3. Update Gap Analysis Output

Gap analysis should identify **outcomes/goals**, not low-level tasks:

```python
# Current output (too specific):
{"task": "Instalar inodoro suspendido", "room": "baño"}

# Better output (outcome-focused):
{
    "room": "baño_principal",
    "outcome": "Modern bathroom meeting current standards",
    "terminal_indicators": [
        "New sanitary fixtures",
        "Updated electrical (REBT compliant)",
        "Modern finishes"
    ],
    "evidence": "1980s fixtures, exposed wiring, dated tiles"
}
```

---

## Why This Works

1. **No hardcoded recipes** - The KG defines relationships
2. **No LLM hallucination** - Traversal is deterministic
3. **Nothing missed** - Full backward traversal finds all prerequisites
4. **Correct order** - Topological sort ensures proper sequence
5. **Extensible** - Add more edges to KG, traversal automatically uses them

---

## Testing

### Verify Traversal Completeness

```bash
cd /root/puedo_casa && python3 -c "
import json

with open('experiments/renovation_costing/hybrid_renovation_graph.json', 'r') as f:
    kg = json.load(f)

tasks = kg['canonical_tasks']

def full_backward_traversal(task_id, visited=None):
    if visited is None:
        visited = set()
    if task_id in visited:
        return set()
    visited.add(task_id)
    
    result = {task_id}
    task = tasks.get(task_id, {})
    for req_id in task.get('requires', []):
        result.update(full_backward_traversal(req_id, visited))
    return result

# Test with bathroom terminal task
for tid, t in tasks.items():
    if 'equipamiento sanitario' in t['name'].lower():
        chain = full_backward_traversal(tid)
        print(f'Terminal: {t[\"name\"]}')
        print(f'Full chain: {len(chain)} tasks')
        for task_id in chain:
            print(f'  - {tasks[task_id][\"name\"]}')
        break
"
```

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Traversal | Selective (filtered) | Complete (all edges) |
| Tasks found | 3-5 | 15-20 |
| Prerequisites | Often missed | All included |
| Order | Random | Topologically sorted |
| Recipes needed | Maybe | No - KG has it |
| Hallucination risk | High | None (deterministic) |

**The KG is the single source of truth. Trust it.**

