Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# V3 Tech Debt Audit

**Date:** 2025-01-09  
**Status:** Issues Identified - Fixes Proposed

---

## 🔴 HIGH: Biasing Examples in Gap Analysis Prompt

### Problem
The prompt (`gap_analysis.py` lines 559-704) contains **specific examples** that bias the LLM:

1. **Only 2 room examples** (kitchen, bathroom) - LLM may struggle with bedrooms, living rooms, terraces
2. **Era-specific details** ("años 80", "años 90", "Roca Victoria") - may not generalize to 2000s+ properties
3. **Fixed priority distribution** (critical:2, high:4, medium:6, low:3) - LLM gravitates toward this
4. **Fixed task counts** (4 tasks for kitchen, 3 for bathroom) - may under-report for larger rooms
5. **Specific products** ("porcelánico rectificado", "encimera de cuarzo") - overuse of these terms

### Fix
Replace specific examples with **structural guidance**:

```python
# BEFORE: Specific examples that bias
"gap_narrative": "La cocina actual presenta un aspecto anticuado con mobiliario de melamina de los años 80..."

# AFTER: Structural guidance
"""
gap_narrative: A rich paragraph describing:
1. CURRENT STATE: What the room looks like now (be specific about visible elements)
2. EVIDENCE: What you see that indicates age/condition (materials, fixtures, style)
3. TARGET STATE: What the comparable has that this room lacks
4. TRANSFORMATION SCOPE: What type of work is needed (cosmetic vs structural)

Write from observation, don't assume specific eras or brands unless visible.
"""
```

### Files to Change
- `/backend/pipeline/gap_analysis.py` - Replace examples with structural templates

---

## 🟡 MEDIUM: Hardcoded Magic Numbers

### Problem
Many arbitrary defaults in `renovation_resolver.py`:

| Location | Value | Issue |
|----------|-------|-------|
| Line 604 | `m2: float = 10.0` | Arbitrary default room size |
| Line 605 | `height: float = 2.5` | Hardcoded ceiling height |
| Line 846 | `dims.m2 ** 0.5` | Assumes square rooms |
| Line 847 | `0.12` wall thickness | Hardcoded for Spanish construction |
| Line 979 | `> 0.4` similarity | Magic threshold |
| Line 1076 | `depth > 15` | Arbitrary traversal limit |
| Line 889 | `[:100]` | Arbitrary task menu limit |

### Fix
Move to config constants with documented reasoning:

```python
# At top of file
DEFAULTS = {
    "room_m2": 12.0,  # Average Spanish room size (IDAE statistics)
    "ceiling_height_m": 2.5,  # Standard residential ceiling
    "wall_thickness_m": 0.12,  # Standard partition wall
    "similarity_threshold": 0.4,  # Empirically tuned for BCCA matching
    "max_traversal_depth": 15,  # KG max depth is ~10, buffer for safety
    "task_menu_limit": 150,  # Context window optimization
}
```

### Files to Change
- `/backend/pricing/renovation_resolver.py` - Extract to config

---

## 🟡 MEDIUM: Hardcoded Permit Prices

### Problem
Lines 364-380 have hardcoded permit costs:

```python
'LICENCIA_MENOR': {'price': 150.0, ...},
'LICENCIA_MAYOR': {'price': 2500.0, ...},
'LICENCIA_MAYOR_ESTRUC': {'price': 4000.0, ...},
```

These vary by municipality and change over time.

### Fix
Move to database or config that can be updated without code changes:

```python
# Option 1: Database table `permit_costs`
# Option 2: Environment-based config
# Option 3: Admin-editable JSON file
```

---

## 🟡 MEDIUM: Incomplete Room Icon Map

### Problem
`_get_default_room_icon()` has limited room types:

```python
icons = {
    "kitchen": "🍳",
    "bathroom": "🛁",
    "bedroom": "🛏️",
    "living": "🛋️",
    # Missing: office, laundry, garage, storage, dining, etc.
}
```

### Fix
Expand with catch-all fallback:

```python
icons = {
    "kitchen": "🍳", "cocina": "🍳",
    "bathroom": "🛁", "baño": "🛁", "aseo": "🛁",
    "bedroom": "🛏️", "dormitorio": "🛏️", "habitación": "🛏️",
    "living": "🛋️", "salon": "🛋️", "salón": "🛋️",
    "dining": "🍽️", "comedor": "🍽️",
    "office": "💼", "despacho": "💼", "estudio": "💼",
    "laundry": "🧺", "lavadero": "🧺",
    "garage": "🚗", "garaje": "🚗",
    "storage": "📦", "trastero": "📦",
    "terrace": "🌿", "terraza": "🌿", "balcony": "🌿",
    "hallway": "🚪", "pasillo": "🚪", "entrada": "🚪",
    "pool": "🏊", "piscina": "🏊",
}
# Fallback: "🏠" for unknown
```

---

## 🟢 LOW: Task Filtering by Keywords

### Problem
Line 885 filters tasks by hardcoded keywords:

```python
elif any(kw in task_name_lower for kw in ['alicata', 'solado', 'pintura', 'demoli', 'sanitar', 'grifo', 'electr', 'fontaner']):
```

This may miss relevant tasks and creates maintenance burden.

### Fix
Use the KG's `layer` or `primary_trade` fields instead of keyword matching:

```python
# Use KG metadata instead of keywords
elif task.get('layer') in ['finishes', 'mep', 'demolition']:
    relevant_tasks.append(...)
```

---

## 🟢 LOW: Quantity Formula Fallbacks

### Problem
Many formulas have fallbacks like `d.get('m2', 10)` that silently use defaults when data is missing.

### Fix
Log when fallbacks are used so we can track data quality:

```python
def get_with_warning(d: dict, key: str, default: float, context: str) -> float:
    if key not in d:
        logger.warning(f"Missing {key} for {context}, using default {default}")
    return d.get(key, default)
```

---

## Summary Table

| Issue | Severity | Effort | Impact |
|-------|----------|--------|--------|
| Biasing examples in prompt | 🔴 HIGH | 2h | Improves output diversity |
| Hardcoded magic numbers | 🟡 MED | 1h | Maintainability |
| Hardcoded permit prices | 🟡 MED | 1h | Accuracy per municipality |
| Incomplete room icons | 🟡 MED | 30m | Better UI |
| Keyword-based filtering | 🟢 LOW | 1h | Use KG metadata |
| Silent fallbacks | 🟢 LOW | 30m | Debug visibility |

---

## Recommended Fix Order

1. **🔴 Fix biasing examples** - Highest impact on output quality
2. **🟡 Extract magic numbers** - Improves maintainability
3. **🟡 Expand room icons** - Quick win for UI
4. **🟡 Move permit prices** - Accuracy improvement
5. **🟢 Use KG metadata** - Better architecture
6. **🟢 Add logging** - Debug visibility

---

## Quick Win: Fix the Prompt Examples

The most impactful fix is replacing specific examples with structural guidance. Here's the diff:

```diff
- "gap_narrative": "La cocina actual presenta un aspecto anticuado con mobiliario de melamina de los años 80..."
+ "gap_narrative": "[DESCRIBE: Current state → evidence of condition → what comparable has → what's needed]"

- "visible_outcomes": [
-   "Mobiliario lacado de diseño moderno",
-   "Encimera de cuarzo o similar",
+ "visible_outcomes": [
+   "[5-7 SPECIFIC visible deliverables the customer will see after renovation]",
+   "[Focus on tangible items, not technical work]",
```

This removes the biasing specifics while keeping the structural guidance.

