Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V3 Quality Fix Plan: Renovation Costing Pipeline

## Executive Summary

**Problem**: The renovation costing pipeline produces inaccurate estimates due to:
1. BCCA matching to TEST items instead of actual work (€190K error)
2. Bathroom renovation missing most tasks (€53 instead of €5-15K)
3. Room attribution lost for dependencies (75% goes to "General")
4. No audit trail for explainability

**Goal**: Accurate, room-level costing with full explainability chain.

---

## Phase 1: BCCA Matching Fix (Priority: CRITICAL)

### Problem
```
Task: "Instalación de suelo radiante"
Matched: 18IAGB00050 "Prueba de funcionamiento de circuito..."
Price: €650/unit (TEST item!)

Should be:
Matched: 08ICB00020 "Instalación de suelo radiante por m²"
Price: €45/m² (actual installation)
```

### Root Cause
- BCCA chapter `18` = Quality Control / Testing
- Semantic search finds "suelo radiante" in test descriptions
- No filter to exclude test items

### Solution

#### 1.1 Add BCCA Filter (renovation_resolver.py)
```python
# In phase5_match_bcca or _bm25_search / _vector_search

BCCA_EXCLUSION_PATTERNS = [
    r'^18',           # Chapter 18 = Quality Control
    r'ensayo',        # "Test" in Spanish
    r'prueba',        # "Test" in Spanish  
    r'control de',    # "Quality control"
    r'certificación', # Certification
    r'inspección',    # Inspection
]

def filter_bcca_matches(matches: List[dict]) -> List[dict]:
    """Remove test/inspection items from BCCA matches."""
    filtered = []
    for match in matches:
        code = match.get('code', '')
        desc = match.get('description', '').lower()
        
        # Skip chapter 18 (quality control)
        if code.startswith('18'):
            continue
            
        # Skip ensayo/prueba items
        if any(pattern in desc for pattern in ['ensayo', 'prueba', 'control de calidad']):
            continue
            
        filtered.append(match)
    
    return filtered
```

#### 1.2 Add Price Sanity Check
```python
PRICE_SANITY_LIMITS = {
    'default': {'min': 1, 'max': 500},  # €/unit
    'demolicion': {'min': 5, 'max': 50},
    'alicatado': {'min': 20, 'max': 80},
    'solado': {'min': 25, 'max': 100},
    'sanitarios': {'min': 150, 'max': 800},
    'suelo_radiante': {'min': 30, 'max': 80},  # per m²
}

def validate_bcca_price(task_name: str, unit_price: float) -> bool:
    """Flag suspiciously high/low prices."""
    for keyword, limits in PRICE_SANITY_LIMITS.items():
        if keyword in task_name.lower():
            return limits['min'] <= unit_price <= limits['max']
    return PRICE_SANITY_LIMITS['default']['min'] <= unit_price <= PRICE_SANITY_LIMITS['default']['max']
```

#### 1.3 Files to Modify
- `Lean MVP/backend/pricing/renovation_resolver.py`
  - `_bm25_search()` - Add filtering
  - `_vector_search()` - Add filtering
  - `phase5_match_bcca()` - Add validation

#### 1.4 Test Case
```python
# Test that suelo radiante doesn't match to chapter 18
result = resolver.phase5_match_bcca([task_suelo_radiante])
assert not result[0].bcca_code.startswith('18')
assert result[0].unit_price < 100  # Not €650!
```

### Estimated Effort: 2-3 hours

---

## Phase 2: Gap→Task Matching Fix (Priority: HIGH)

### Problem
Gap analysis outputs: `"Instalar plato de ducha accesible en el baño"`
Resolver receives: `{"task": "Instalar plato de ducha accesible", "room": "Baño"}`
But KG matching fails to find: `TASK_instalar_plato_ducha`

### Root Cause
1. LLM task matching has limited task menu (150 items)
2. Bathroom-specific tasks may be excluded from relevant_tasks filter
3. No fallback when semantic match fails

### Solution

#### 2.1 Improve Task Menu Selection
```python
# In _match_actions_with_llm()

# Current: keyword-based filtering (misses bathroom tasks)
# Fix: Include FULL bathroom/kitchen task families

ROOM_TASK_FAMILIES = {
    'baño': ['sanitar', 'alicata', 'grifo', 'ducha', 'bañera', 'inodoro', 'lavabo', 
             'mampara', 'espejo', 'mueble_baño', 'impermeabil'],
    'cocina': ['encimera', 'campana', 'fregadero', 'horno', 'vitro', 'mobiliario_cocina',
               'alicata', 'grifo'],
    'dormitorio': ['armario', 'pintura', 'solado', 'rodapie'],
}

def build_task_menu(actions: List[str], rooms: List[str]) -> str:
    """Build comprehensive task menu including room-specific families."""
    relevant_tasks = set()
    
    # 1. Keyword matches from actions
    for action in actions:
        words = action.lower().split()
        for tid, task in self.tasks.items():
            if any(w in task['name'].lower() for w in words):
                relevant_tasks.add(tid)
    
    # 2. Room-specific task families (ALWAYS include)
    for room in rooms:
        room_lower = room.lower()
        for room_key, keywords in ROOM_TASK_FAMILIES.items():
            if room_key in room_lower:
                for tid, task in self.tasks.items():
                    if any(kw in task['name'].lower() for kw in keywords):
                        relevant_tasks.add(tid)
    
    # 3. Common renovation tasks (always include)
    COMMON_KEYWORDS = ['demoli', 'pintura', 'electr', 'fontaner', 'limpieza']
    for tid, task in self.tasks.items():
        if any(kw in task['name'].lower() for kw in COMMON_KEYWORDS):
            relevant_tasks.add(tid)
    
    return "\n".join(f"{tid}: {self.tasks[tid]['name']}" for tid in relevant_tasks)
```

#### 2.2 Add Fallback for Unmatched Actions
```python
def _match_actions_with_llm(self, actions, rooms, action_to_room):
    # ... existing LLM matching ...
    
    # Check for unmatched actions
    matched_actions = set(task_to_action.values())
    unmatched = [a for a in actions if a not in matched_actions]
    
    if unmatched:
        logger.warning(f"⚠️ {len(unmatched)} actions not matched by LLM:")
        for action in unmatched:
            logger.warning(f"  - {action[:60]}")
            
            # Fallback: embedding match for each unmatched action
            fallback_tid = self._fallback_single_action(action)
            if fallback_tid:
                direct_task_ids.add(fallback_tid)
                task_to_action[fallback_tid] = action
                logger.info(f"  → Fallback matched: {self.task_names[fallback_tid]}")
```

#### 2.3 Files to Modify
- `Lean MVP/backend/pricing/renovation_resolver.py`
  - `_match_actions_with_llm()` - Improve task menu
  - Add `_fallback_single_action()` method

#### 2.4 Test Case
```python
# Test that bathroom gap analysis produces bathroom tasks
gap_tasks = [
    {"task": "Renovar alicatado del baño", "room": "Baño"},
    {"task": "Instalar plato de ducha", "room": "Baño"},
    {"task": "Renovar sanitarios", "room": "Baño"},
]
result = await resolve_from_gap_analysis(gap_tasks, ...)
bano_items = [line for line in result.all_lines if 'baño' in line.source_room.lower()]
assert len(bano_items) >= 10  # Should have demolition + new work
```

### Estimated Effort: 3-4 hours

---

## Phase 3: Room Attribution for Dependencies (Priority: HIGH)

### Problem
```
Gap: "Renovar baño" (room=Baño)
  → Matches: TASK_instalar_sanitarios (room=Baño) ✓
    → Requires: TASK_alicatado (room=???)
      → Requires: TASK_impermeabilizacion (room=???)
        → Requires: TASK_demolicion (room=???)
```
All prerequisites get room="General" instead of inheriting "Baño".

### Solution

#### 3.1 Propagate Room Through Dependency Chain
```python
def full_backward_traversal(self, task_id, chain, visited, depth=0, 
                            inherited_room: str = ""):
    """
    V3.1: Propagate room attribution through dependency chain.
    
    Logic:
    - Direct tasks: room from action_to_room
    - Dependencies: inherit from the task that required them
    - If multiple parents: use the first non-empty room
    """
    if task_id in visited or depth > 15:
        return
    visited.add(task_id)
    
    # Set room for this task
    if task_id in self.task_to_action:
        # Direct match - use action's room
        action = self.task_to_action[task_id]
        room = self.action_to_room.get(action.lower(), "")
    else:
        # Dependency - inherit from parent
        room = inherited_room
    
    self.task_rooms[task_id] = room
    self.all_task_ids.add(task_id)
    
    # Traverse requirements (pass room down)
    task = self.tasks.get(task_id, {})
    for req_id in task.get('requires', []):
        if req_id in self.tasks:
            self.full_backward_traversal(
                req_id, 
                chain + [f"← required by {task['name'][:30]}"],
                visited, 
                depth + 1,
                inherited_room=room  # Pass room to children
            )
```

#### 3.2 Handle Multi-Parent Dependencies
Some tasks are required by multiple rooms. Strategy:
```python
# If a task has multiple parents from different rooms:
# Option A: Split the cost proportionally
# Option B: Attribute to first parent (simpler)
# Option C: Create separate line items per room (most accurate)

# Implement Option C for accuracy:
def resolve_multi_parent_tasks(self, task_id: str) -> List[Tuple[str, str]]:
    """Return list of (task_id, room) tuples for multi-parent tasks."""
    parents = self.required_by[task_id]
    rooms = set(self.task_rooms.get(p, "") for p in parents) - {""}
    
    if len(rooms) <= 1:
        return [(task_id, rooms.pop() if rooms else "General")]
    
    # Multi-room: return one entry per room
    return [(task_id, room) for room in rooms]
```

#### 3.3 Files to Modify
- `Lean MVP/backend/pricing/renovation_resolver.py`
  - `full_backward_traversal()` - Add room propagation
  - `phase2_resolve_tasks()` - Build task_rooms dict
  - `phase7_build_boq()` - Use task_rooms for line items

#### 3.4 Test Case
```python
# Test that bathroom dependencies get Baño room
result = await resolve_from_gap_analysis(bathroom_gap_tasks, ...)
bano_lines = [line for line in result.all_lines if line.source_room == "Baño"]
general_lines = [line for line in result.all_lines if line.source_room == "General"]

# Most bathroom work should be attributed to Baño
assert sum(l.total for l in bano_lines) > sum(l.total for l in general_lines) * 0.5
```

### Estimated Effort: 4-5 hours

---

## Phase 4: Audit Trail for Explainability (Priority: MEDIUM)

### Problem
Can't trace why a specific BCCA code was selected or why a task got a particular room.

### Solution

#### 4.1 Add Reasoning Chain to BoQLine
```python
@dataclass
class BoQLine:
    # ... existing fields ...
    
    # Audit trail
    reasoning_chain: List[str] = field(default_factory=list)
    # Example: ["Gap: 'renovar baño'", "→ KG: TASK_alicatado (0.87 similarity)", 
    #           "→ BCCA: 01RAT00010 (0.72 BM25 + 0.65 vector)", "→ Room: Baño (inherited)"]
    
    gap_source: str = ""  # Original gap analysis text
    kg_match_score: float = 0.0
    bcca_match_score: float = 0.0
    room_attribution_reason: str = ""  # "direct" | "inherited from X"
```

#### 4.2 Log Reasoning at Each Step
```python
# In _match_actions_with_llm:
reasoning = f"Gap: '{action[:50]}' → KG: {task_id} ({self.task_names[task_id]})"
self.reasoning_chains[task_id] = [reasoning]

# In phase5_match_bcca:
reasoning = f"→ BCCA: {bcca_code} (BM25: {bm25_score:.2f}, Vector: {vec_score:.2f})"
self.reasoning_chains[task_id].append(reasoning)

# In room attribution:
if inherited:
    reasoning = f"→ Room: {room} (inherited from {parent_task})"
else:
    reasoning = f"→ Room: {room} (direct from gap analysis)"
self.reasoning_chains[task_id].append(reasoning)
```

#### 4.3 Store in Database
```sql
-- Add to listing_bracket_analyses
ALTER TABLE listing_bracket_analyses 
ADD COLUMN audit_trail JSONB DEFAULT '[]';

-- Structure:
-- [
--   {
--     "task_id": "TASK_xxx",
--     "task_name": "Alicatado cerámico",
--     "reasoning_chain": ["Gap: '...'", "→ KG: ...", "→ BCCA: ..."],
--     "bcca_code": "01RAT00010",
--     "room": "Baño",
--     "total": 1234.56
--   }
-- ]
```

#### 4.4 Files to Modify
- `Lean MVP/backend/pricing/renovation_resolver.py`
  - Add reasoning_chain tracking throughout
- `Lean MVP/backend/routes/renovation.py`
  - Store audit_trail in database
- Supabase migration for new column

### Estimated Effort: 3-4 hours

---

## Implementation Order

| Phase | Task | Priority | Effort | Dependencies |
|-------|------|----------|--------|--------------|
| 1 | BCCA Filter (chapter 18, ensayo) | CRITICAL | 2h | None |
| 1 | Price sanity check | CRITICAL | 1h | None |
| 2 | Task menu improvement | HIGH | 2h | None |
| 2 | Fallback for unmatched actions | HIGH | 2h | Phase 2.1 |
| 3 | Room propagation in traversal | HIGH | 3h | None |
| 3 | Multi-parent handling | HIGH | 2h | Phase 3.1 |
| 4 | Reasoning chain tracking | MEDIUM | 2h | None |
| 4 | Database storage | MEDIUM | 1h | Phase 4.1 |
| - | Testing & validation | HIGH | 2h | All |

**Total Estimated Effort: 15-17 hours**

---

## Success Metrics

After implementation, listing 12 should show:

| Metric | Before | After |
|--------|--------|-------|
| Baño cost | €53 | €5,000-15,000 |
| Climatización (wrong) | €186K | €5,000-15,000 |
| "General" % of total | 75% | <30% |
| BCCA chapter 18 items | 6 | 0 |
| Audit trail entries | 0 | 74 (all items) |

---

## Test Script

```bash
# After implementation, run:
curl -X POST "http://localhost:8000/api/renovation/12/comparables/analyse" \
  -H "Content-Type: application/json" \
  -d '{"bracket": "fair_market", "view": "buyer", "target_price": 500000}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d['data']

# Check 1: No chapter 18 BCCA codes
for trade, items in data['architect_view']['boq_by_trade'].items():
    for item in items:
        assert not item['bcca_code'].startswith('18'), f'Chapter 18 found: {item}'

# Check 2: Baño cost > €1000
bano_cost = sum(r['cost'] for r in data['customer_view']['rooms'] if 'baño' in r['room_name'].lower())
assert bano_cost > 1000, f'Baño too low: €{bano_cost}'

# Check 3: General < 50%
total = data['renovation_cost']
general = sum(r['total'] for r in data['scope_of_work']['by_room'] if r['name'] == 'General')
assert general / total < 0.5, f'General too high: {general/total:.0%}'

print('✅ All quality checks passed!')
"
```

