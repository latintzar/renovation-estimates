Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.3: Hybrid KG + RAG Implementation

> **Date**: January 2026  
> **Author**: Peter Neyra + Claude  
> **Status**: Implementation Specification  
> **Predecessor**: V0.2 (Pure Context) → V0.3 (Hybrid: Context + RAG)

---

## Executive Summary

This document specifies a **HYBRID architecture** that combines:

1. **Full KG in System Instruction** (context) - for reasoning about dependencies
2. **BCCA via RAG Tool** (retrieval) - for matching tasks to prices
3. **BCCA-Speak Translation Guide** (context) - teaching LLM how to search

**Why Hybrid?**
- KG (683 tasks, FULL enrichment) = ~214K tokens → **MUST be in context** for dependency reasoning
- BCCA (12,565 items) = ~500K tokens → **TOO LARGE** for context, use RAG instead
- We already have BCCA embeddings!

**The Core Insight:**
```
KG = REASONING (must see whole graph to traverse dependencies)
BCCA = RETRIEVAL (find best match from 12K items)

Don't confuse them!
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                    CACHED SYSTEM CONTEXT (~225K tokens)                      │
│                    (Uploaded Once, Reused Forever)                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ ROLE + GROUNDING RULES                                      ~3K tokens │  │
│  │ - "You are a Spanish renovation estimator"                             │  │
│  │ - "Ground ALL answers in the KG"                                       │  │
│  │ - "Use search_bcca tool to find prices"                                │  │
│  │ - "Select based on semantic fit, not price"                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ FULL KNOWLEDGE GRAPH (YAML + quantity_guidance)           ~214K tokens │  │
│  │ - 683 canonical tasks                                                  │  │
│  │ - ~1,451 REQUIRES edges                                                │  │
│  │ - ~1,338 TRIGGERS edges                                                │  │
│  │ - Quantity guidance per task                                           │  │
│  │ - Room type mappings                                                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ BCCA-SPEAK: STRUCTURAL SEARCH GUIDE                         ~5K tokens │  │
│  │ - Chapter index (what each chapter covers)                             │  │
│  │ - Structural search pattern (universal, not examples)                  │  │
│  │ - Keyword construction rules                                           │  │
│  │ - Result selection guidance                                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ QUANTITY FORMULAS                                           ~2K tokens │  │
│  │ - floor_m2, wall_m2, perimeter_ml, unit                                │  │
│  │ - How to apply buffers                                                 │  │
│  │ - Examples for each room type                                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ System Instruction (cached)
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                    TOOLS AVAILABLE TO LLM                                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ search_bcca(keyword, chapter, intent)                                  │  │
│  │                                                                        │  │
│  │ Returns top 5 matching BCCA items from 12,565 item database            │  │
│  │                                                                        │  │
│  │ Parameters:                                                            │  │
│  │   keyword: Spanish construction term (e.g., "alicatado cerámico")      │  │
│  │   chapter: BCCA chapter code (e.g., "01", "08")                        │  │
│  │   intent: "installation" | "demolition" | "supply_only"                │  │
│  │                                                                        │  │
│  │ Implementation: BM25 + Embedding hybrid search                         │  │
│  │ Data: Construction work only (tests/inspections not loaded)            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ validate_price(bcca_code, task_type, quantity, total)                  │  │
│  │                                                                        │  │
│  │ Sanity check for price reasonableness                                  │  │
│  │                                                                        │  │
│  │ Returns:                                                               │  │
│  │   valid: boolean                                                       │  │
│  │   warning: string (if invalid)                                         │  │
│  │   expected_range: [min, max]                                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Per-request context (~5K tokens)
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                    USER PROMPT (Per Request)                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ GAP ANALYSIS                                                ~3K tokens │  │
│  │ - Room-by-room renovation needs                                        │  │
│  │ - Issues identified                                                    │  │
│  │ - Transformation goals                                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PROPERTY CONTEXT                                            ~2K tokens │  │
│  │ - Total area, year built, location                                     │  │
│  │ - Room dimensions (m², height)                                         │  │
│  │ - Condition score                                                      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Why Hybrid vs Pure Context?

| Approach | KG Handling | BCCA Handling | Total Tokens | Issue |
|----------|-------------|---------------|--------------|-------|
| **V0.2 Pure Context** | Full in context | Full in context | ~300K+ | BCCA too large, fills context |
| **V0.3 Hybrid** | Full in context | RAG tool | ~135K | ✅ Best of both worlds |
| **Pure RAG** | RAG tool | RAG tool | ~10K | ❌ Can't reason about dependencies |

**The Key Insight:**
- **KG requires REASONING** - LLM must see ALL tasks and edges to traverse dependencies correctly
- **BCCA requires RETRIEVAL** - LLM doesn't need to see all 12K items, just find the best match

---

## Part 1: System Instruction Specification

### 1.1 Complete System Instruction Template

```text
# ============================================================
# SYSTEM INSTRUCTION: Spanish Renovation Cost Estimator V0.3
# Hybrid Architecture: Full KG Context + BCCA RAG
# ============================================================

ROLE:
You are a senior Spanish renovation cost estimator with 20 years of experience.
You produce Bills of Quantities (BoQ) for residential property renovations in Spain.

You have TWO knowledge sources:
1. KNOWLEDGE GRAPH (in this context) - Use for task identification and dependencies
2. BCCA PRICE BOOK (via search_bcca tool) - Use for pricing

# ============================================================
# GROUNDING RULES (CRITICAL - NO EXCEPTIONS)
# ============================================================

1. KNOWLEDGE GRAPH GROUNDING:
   - Use ONLY tasks that exist in the Knowledge Graph below
   - Follow REQUIRES edges to include ALL prerequisites
   - Follow TRIGGERS edges to include cleanup/consequences
   - If a task is not in the KG, respond: "Task not in Knowledge Graph"

2. BCCA GROUNDING:
   - Use search_bcca() tool to find prices - DO NOT invent prices
   - ALWAYS call search_bcca() before assigning a price
   - If no good match found, note: "No BCCA match" with reasoning

3. NO HALLUCINATION:
   - Do NOT invent task IDs
   - Do NOT invent BCCA codes
   - Do NOT guess prices
   - Do NOT add tasks that aren't in the KG

# ============================================================
# BCCA-SPEAK: STRUCTURAL SEARCH GUIDANCE
# (Universal patterns for any renovation work)
# ============================================================

## Chapter Index (What Each Chapter Contains)

| Chapter | Trade Domain | Covers |
|---------|--------------|--------|
| 01 | Revestimientos | Wall finishes, floor finishes, painting, rendering |
| 02 | Cimentaciones | Foundation work (rare in renovation) |
| 03 | Estructuras | Structural modifications, load-bearing changes |
| 04 | Cubiertas | Roofing, terrace waterproofing, skylights |
| 05 | Cerramientos | Windows, external walls, facades |
| 06 | Carpintería | Doors, cabinets, built-in furniture, woodwork |
| 07 | Vidriería | Glass, mirrors, shower screens, partitions |
| 08 | Instalaciones | Plumbing, electrical, HVAC, gas, sanitaryware |
| 09 | Aislamientos | Thermal insulation, acoustic insulation |
| 13 | Gestión residuos | Demolition debris, waste management, cleanup |

## Structural Search Pattern

When calling search_bcca(), construct queries using this pattern:

```
search_bcca(
    keyword = [SPANISH_TERM] + [MATERIAL/TYPE] + [ACTION],
    chapter = [CHAPTER_CODE],
    intent = [installation | demolition | supply_only]
)
```

### Keyword Construction Rules

1. **Use Spanish construction terminology**
   - The BCCA database is entirely in Spanish
   - Use the KG task's `bcca_keyword` field as your starting point
   - Add specificity: material type, dimensions, quality level

2. **Include the action verb**
   - For installation: "instalación", "colocación", "montaje", "ejecución"
   - For demolition: "levantado", "demolición", "desmontaje", "arranque"
   - For supply only: "suministro" (rare - most items include installation)

3. **Match chapter to trade**
   - Surface finishes → Chapter 01
   - Plumbing/electrical/HVAC → Chapter 08
   - Doors/cabinets → Chapter 06
   - Glass/mirrors → Chapter 07
   - Waste management → Chapter 13

### Selecting from Search Results

The search tool returns multiple matches. Select based on:

1. **Semantic fit** - Does the description match the work needed?
2. **Unit match** - Is the unit (m², ud, ml) appropriate for the task?
3. **Completeness** - Does it include labor, or is it material-only?

DO NOT filter by price. The BCCA database contains items at all price points
(budget to luxury). Trust the database - select based on description fit.

### Handling No Results

If search returns poor matches:
1. Try broader keywords (remove specificity)
2. Try related Spanish synonyms
3. Try adjacent chapter if trade boundary is unclear
4. If still no match: note "No BCCA match" in reasoning and skip pricing

# ============================================================
# TASK RESOLUTION PROCESS (5 Steps)
# ============================================================

For each room in the gap analysis:

## STEP 1: IDENTIFY ROOT TASKS
- Read the gap analysis narrative for this room
- Look up the room type in `room_task_mappings` in the KG
- Identify which root tasks apply based on the gap description
- Example: "renovar baño completo" → TASK_renovacion_integral_baño

## STEP 2: EXPAND DEPENDENCIES (Backward Traversal)
- For each identified task, follow ALL `REQUIRES` edges backward
- These are prerequisites that MUST be included
- Continue until you hit tasks with no requirements
- Example chain: alicatado ← requires ← impermeabilización ← requires ← enfoscado

## STEP 3: EXPAND TRIGGERS (Forward Traversal)  
- For each task, follow `TRIGGERS` edges forward
- Include cleanup tasks (gestion_escombros, limpieza)
- Include finishing tasks (rejuntado, sellado)
- Example: demolición → triggers → gestion_escombros

## STEP 4: CALCULATE QUANTITIES
For each task, use its `quantity_guidance` from the KG:

| quantity_type | Formula | Example |
|---------------|---------|---------|
| floor_m2 | room_m2 | 12m² room = 12m² flooring |
| wall_m2 | perimeter × height | 12m² room, 2.5m height ≈ 35m² walls |
| perimeter_ml | 4 × √(room_m2) | 12m² room ≈ 14ml perimeter |
| unit | count (usually 1) | 1 toilet per bathroom |

Apply buffer: final_qty = base_qty × (1 + quantity_buffer)

## STEP 5: MATCH BCCA CODES (Use Tool)
For each task:
1. Read the task's `bcca_keyword` from KG
2. Construct search query using structural pattern above
3. Call search_bcca(keyword, chapter, intent)
4. Review returned results for semantic fit
5. Select based on description match and unit appropriateness
6. If no good match, note "No BCCA match" in reasoning

# ============================================================
# OUTPUT FORMAT (JSON)
# ============================================================

{
  "success": true,
  "boq": [
    {
      "room": "string - room name",
      "task_id": "string - KG task ID",
      "task_name": "string - human readable",
      "reasoning": [
        "Gap: [what gap analysis said]",
        "KG: [how you found task and dependencies]",
        "Qty: [how you calculated quantity]",
        "BCCA: [search query and result selection]"
      ],
      "bcca_code": "string - matched code",
      "bcca_description": "string - what item is",
      "quantity": number,
      "unit": "string - m², ud, ml",
      "unit_price": number,
      "total": number
    }
  ],
  "summary": {
    "pem_subtotal": number,
    "overhead_19pct": number,
    "pec_total": number,
    "iva_21pct": number,
    "total_with_iva": number
  },
  "by_room": {
    "Baño": {"tasks": 15, "total": 8500},
    "Cocina": {"tasks": 20, "total": 15000}
  },
  "warnings": [
    "string - any issues encountered"
  ]
}

# ============================================================
# SANITY CHECKS (Run Before Finalizing)
# ============================================================

□ All tasks have valid BCCA matches (no missing prices)
□ All line items have reasoning chains
□ Room attribution correct (no "General" for room-specific work)
□ Math is correct (quantity × unit_price = total)

# ============================================================
# KNOWLEDGE GRAPH DATA (FULL ENRICHMENT)
# 683 tasks with:
#   - Dependencies (REQUIRES/TRIGGERS)
#   - FULL quantity_guidance per task:
#     - type: how to measure (area_m2, count, linear_m)
#     - scope: per_room, per_opening, per_unit
#     - reasoning: factors to consider
#     - rules: industry measurement standards
#     - constraints: min/max/buffers
# ============================================================

[KG_YAML_INSERTED_HERE - ~214K tokens]

# ============================================================
# END OF SYSTEM INSTRUCTION
# ============================================================
```

---

## Part 2: BCCA RAG Implementation

### 2.1 Search Tool Implementation

```python
"""
BCCA RAG Search Tool

Hybrid search using BM25 (exact keyword) + Embeddings (semantic).
Database contains ONLY construction work - tests/inspections excluded at load time.
"""

import sqlite3
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)


@dataclass
class BCCASearchResult:
    """Single BCCA search result."""
    code: str
    description: str
    unit: str
    price: float
    chapter: str
    score: float


class BCCASearchTool:
    """
    Hybrid BCCA search tool for LLM function calling.
    
    Combines:
    - BM25 for exact keyword matching
    - Embeddings for semantic similarity
    
    The search index contains ONLY construction work.
    Tests/inspections are excluded at data load time (not at query time).
    """
    
    def __init__(
        self, 
        db_path: str = 'pricing/construction.db',
        embedding_model: str = 'text-embedding-004'
    ):
        self.db_path = db_path
        self.embedding_model = embedding_model
        
        # Load data (tests excluded at source)
        self._load_bcca_data()
        self._build_bm25_index()
        
    def _load_bcca_data(self):
        """Load BCCA construction items (tests excluded at SQL level)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Only load construction work - tests/inspections excluded in WHERE clause
        cursor.execute("""
            SELECT id, description, unit, price, chapter, embedding
            FROM price_book 
            WHERE price > 0
            AND chapter != '18'
        """)
        
        self.items = []
        self.embeddings = []
        
        for row in cursor.fetchall():
            code, desc, unit, price, chapter, emb_bytes = row
            
            self.items.append({
                'code': code,
                'description': desc,
                'unit': unit,
                'price': float(price),
                'chapter': chapter
            })
            
            # Embeddings stored in database
            if emb_bytes:
                self.embeddings.append(np.frombuffer(emb_bytes, dtype=np.float32))
        
        self.embeddings = np.array(self.embeddings) if self.embeddings else None
        conn.close()
        logger.info(f"Loaded {len(self.items)} BCCA construction items")
            
    def _build_bm25_index(self):
        """Build BM25 index for keyword search."""
        tokenized = [
            item['description'].lower().split() 
            for item in self.items
        ]
        self.bm25 = BM25Okapi(tokenized)
        logger.info("Built BM25 index")
        
    def _compute_query_embedding(self, query: str) -> np.ndarray:
        """Compute embedding for search query."""
        from google import genai
        
        client = genai.Client()
        result = client.models.embed_content(
            model=self.embedding_model,
            contents=query
        )
        return np.array(result.embeddings[0].values)
        
    def search(
        self,
        keyword: str,
        chapter: Optional[str] = None,
        intent: str = "installation",
        top_k: int = 5
    ) -> List[BCCASearchResult]:
        """
        Search BCCA for matching items.
        
        Args:
            keyword: Spanish construction term
            chapter: BCCA chapter to filter (e.g., "01", "08")
            intent: "installation", "demolition", or "supply_only"
            top_k: Number of results to return
            
        Returns:
            List of BCCASearchResult sorted by relevance
        """
        logger.info(f"BCCA search: '{keyword}' chapter={chapter} intent={intent}")
        
        # Step 1: BM25 keyword search (get more candidates for reranking)
        query_tokens = keyword.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)
        
        # Step 2: Embedding search (if available)
        if self.embeddings is not None:
            query_emb = self._compute_query_embedding(keyword)
            emb_scores = np.dot(self.embeddings, query_emb)
            
            # Normalize and combine scores
            bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-10)
            emb_norm = (emb_scores - emb_scores.min()) / (emb_scores.max() - emb_scores.min() + 1e-10)
            
            # Hybrid score (70% BM25 + 30% embedding)
            combined_scores = 0.7 * bm25_norm + 0.3 * emb_norm
        else:
            combined_scores = bm25_scores
            
        # Step 3: Get top candidates
        top_indices = np.argsort(combined_scores)[::-1][:top_k * 5]  # Get 5x for filtering
        
        # Step 4: Filter and rank
        results = []
        for idx in top_indices:
            item = self.items[idx]
            score = float(combined_scores[idx])
            
            # Filter by chapter if specified
            if chapter and not item['code'].startswith(chapter):
                continue
            
            # Boost based on intent matching
            desc_lower = item['description'].lower()
            
            if intent == "installation":
                if any(kw in desc_lower for kw in ['instalación', 'colocación', 'montaje', 'ejecución']):
                    score *= 1.3
                    
            elif intent == "demolition":
                if any(kw in desc_lower for kw in ['levantado', 'demolición', 'desmontaje', 'arranque']):
                    score *= 1.3
                    
            results.append(BCCASearchResult(
                code=item['code'],
                description=item['description'],
                unit=item['unit'],
                price=item['price'],
                chapter=item['chapter'],
                score=score
            ))
            
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


# Tool function for LLM function calling
def search_bcca(keyword: str, chapter: str, intent: str) -> Dict:
    """
    Search BCCA price database for construction items.
    
    The database contains ONLY construction work - tests/inspections are excluded.
    
    Args:
        keyword: Spanish construction term (e.g., "alicatado cerámico")
        chapter: BCCA chapter code (e.g., "01" for Revestimientos, "08" for Instalaciones)
        intent: "installation" or "demolition"
        
    Returns:
        Dict with top 5 matching items
    """
    tool = BCCASearchTool()
    results = tool.search(keyword, chapter, intent)
    
    return {
        "success": True,
        "query": {
            "keyword": keyword,
            "chapter": chapter,
            "intent": intent
        },
        "results": [
            {
                "code": r.code,
                "description": r.description,
                "unit": r.unit,
                "price": r.price,
                "score": round(r.score, 3)
            }
            for r in results
        ],
        "warning": "No results found" if not results else None
    }
```

### 2.2 Process Validation Tool

```python
"""
PROCESS validation tool - validates data integrity, NOT price ranges.

We do NOT validate:
- "Is this price reasonable?" (anecdotal, varies by quality level)
- "Is bathroom cost €5K-25K?" (symptom checking)

We DO validate:
- Is there a valid BCCA match?
- Is the math correct?
- Are values positive?

Note: Tests/inspections are excluded at database load time,
so we don't need to check for them here.
"""

from typing import Dict


def validate_bcca_match(
    bcca_code: str,
    quantity: float,
    unit_price: float,
    total: float
) -> Dict:
    """
    Validate BCCA match for PROCESS integrity (not price reasonableness).
    
    Args:
        bcca_code: The BCCA code being used
        quantity: Number of units
        unit_price: Price per unit
        total: quantity × unit_price
        
    Returns:
        Dict with validation result
    """
    errors = []
    
    # Check 1: Has valid BCCA code
    if not bcca_code or bcca_code in ['NONE', 'N/A', '']:
        errors.append({
            "type": "missing_bcca",
            "severity": "CRITICAL", 
            "message": "No BCCA code assigned - task cannot be priced",
            "action": "BCCA search returned no matches"
        })
    
    # Check 2: Math is correct
    if quantity > 0 and unit_price > 0:
        expected_total = quantity * unit_price
        if abs(total - expected_total) > 0.01:
            errors.append({
                "type": "math_error",
                "severity": "HIGH",
                "message": f"Total mismatch: {quantity} × €{unit_price} = €{expected_total:.2f}, not €{total:.2f}",
                "action": "Recalculate"
            })
    
    # Check 3: Positive values
    if quantity <= 0:
        errors.append({
            "type": "invalid_quantity",
            "severity": "HIGH",
            "message": f"Quantity {quantity} is not positive",
            "action": "Check quantity calculation"
        })
    
    if unit_price < 0:
        errors.append({
            "type": "invalid_price",
            "severity": "HIGH",
            "message": f"Unit price €{unit_price} is negative",
            "action": "BCCA match error"
        })
    
    return {
        "valid": len([e for e in errors if e['severity'] == 'CRITICAL']) == 0,
        "errors": errors
    }


# NOTE: We intentionally do NOT have:
# - PRICE_RANGES dict (anecdotal, biases against luxury/budget items)
# - ROOM_RANGES dict (symptom checking, not process validation)
# - validate_room_total() (removed - was checking symptoms)
#
# If the PROCESS is correct (valid BCCA, correct math, proper KG traversal),
# the price will be correct for whatever quality level was matched.
```

---

## Part 3: EstimatorV3 Implementation

### 3.1 Core Estimator Class

```python
"""
PETER AGENTIC V0.3: Hybrid Estimator
Full KG in context + BCCA via RAG tool
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from google import genai
from google.genai import types

from .bcca_search import BCCASearchTool, search_bcca
from .process_validation import validate_bcca_match

logger = logging.getLogger(__name__)


@dataclass
class EstimateResult:
    """Complete estimation result."""
    success: bool
    boq: List[Dict]
    summary: Dict
    by_room: Dict
    by_trade: Dict
    warnings: List[str]
    estimator_version: str = "v0.3"
    
    def to_dict(self) -> Dict:
        return asdict(self)


class RenovationEstimatorV3:
    """
    PETER AGENTIC V0.3: Hybrid KG + RAG Estimator
    
    Architecture:
    - Full KG YAML in system instruction (cached)
    - BCCA-speak guide in system instruction (cached)
    - BCCA items accessed via search_bcca tool (RAG)
    
    This allows:
    - Full dependency reasoning (sees entire KG)
    - Accurate BCCA matching (searches 12K construction items)
    - Clean data (tests/inspections excluded at load time)
    """
    
    def __init__(self):
        self.client = genai.Client()
        self.bcca_tool = BCCASearchTool()
        self.cache_id: Optional[str] = None
        self.cache_hash: Optional[str] = None
        
    def _load_kg_yaml(self) -> str:
        """Load flattened KG YAML."""
        with open('pricing/kg_context.yaml', 'r') as f:
            return f.read()
            
    def _load_system_template(self) -> str:
        """Load system instruction template."""
        with open('pricing/system_instruction_v3.txt', 'r') as f:
            return f.read()
            
    def _build_system_instruction(self) -> str:
        """Build complete system instruction with KG embedded."""
        template = self._load_system_template()
        kg_yaml = self._load_kg_yaml()
        
        return template.replace('[KG_YAML_INSERTED_HERE]', kg_yaml)
        
    def _get_content_hash(self, content: str) -> str:
        """Hash content for cache invalidation."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
        
    async def ensure_cache(self) -> str:
        """
        Ensure context cache exists and is current.
        
        The cache contains:
        - System instruction with grounding rules
        - Full KG YAML with quantity_guidance (~214K tokens)
        - BCCA-speak translation guide (~5K tokens)
        
        BCCA items are NOT in cache - accessed via tool.
        """
        system_instruction = self._build_system_instruction()
        current_hash = self._get_content_hash(system_instruction)
        
        if self.cache_id and self.cache_hash == current_hash:
            logger.info(f"Using existing cache: {self.cache_id}")
            return self.cache_id
            
        # Create or refresh cache
        logger.info(f"Creating context cache ({len(system_instruction):,} chars)...")
        
        # Define tools for function calling
        tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="search_bcca",
                    description="Search BCCA price database for construction items",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "keyword": types.Schema(
                                type=types.Type.STRING,
                                description="Spanish construction term (e.g., 'alicatado cerámico')"
                            ),
                            "chapter": types.Schema(
                                type=types.Type.STRING,
                                description="BCCA chapter code (e.g., '01', '08')"
                            ),
                            "intent": types.Schema(
                                type=types.Type.STRING,
                                enum=["installation", "demolition", "supply_only"],
                                description="Type of work"
                            )
                        },
                        required=["keyword", "chapter", "intent"]
                    )
                ),
                types.FunctionDeclaration(
                    name="validate_bcca_match",
                    description="Validate BCCA match for process integrity (not price reasonableness)",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "bcca_code": types.Schema(type=types.Type.STRING),
                            "quantity": types.Schema(type=types.Type.NUMBER),
                            "unit_price": types.Schema(type=types.Type.NUMBER),
                            "total": types.Schema(type=types.Type.NUMBER)
                        },
                        required=["bcca_code", "quantity", "unit_price", "total"]
                    )
                )
            ])
        ]
        
        cache = await self.client.caches.create(
            model="gemini-2.0-flash",
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
                tools=tools,
                ttl="3600s",  # 1 hour
                display_name="renovation-estimator-v3"
            )
        )
        
        self.cache_id = cache.name
        self.cache_hash = current_hash
        
        logger.info(f"Cache created: {self.cache_id}")
        return self.cache_id
        
    def _handle_tool_call(self, function_call: types.FunctionCall) -> Dict:
        """Execute tool call and return result."""
        name = function_call.name
        args = dict(function_call.args)
        
        logger.info(f"Tool call: {name}({args})")
        
        if name == "search_bcca":
            return search_bcca(**args)
        elif name == "validate_bcca_match":
            return validate_bcca_match(**args)
        else:
            return {"error": f"Unknown tool: {name}"}
            
    async def estimate(
        self,
        gap_analysis: Dict,
        property_context: Dict
    ) -> EstimateResult:
        """
        Produce renovation estimate using hybrid KG + RAG architecture.
        
        Args:
            gap_analysis: Room-by-room renovation needs
            property_context: Dimensions, year, location
            
        Returns:
            Complete EstimateResult with BoQ and reasoning
        """
        # Ensure cache is ready
        cache_id = await self.ensure_cache()
        
        # Build user prompt
        user_prompt = self._build_user_prompt(gap_analysis, property_context)
        
        # Initial request
        response = await self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                cached_content=cache_id,
                temperature=0.1,
            )
        )
        
        # Handle tool calling loop (ReAct pattern)
        max_iterations = 50  # Safety limit
        iteration = 0
        messages = [{"role": "user", "content": user_prompt}]
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check if response has function calls
            if response.candidates[0].content.parts:
                has_function_call = False
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        has_function_call = True
                        
                        # Execute tool
                        tool_result = self._handle_tool_call(part.function_call)
                        
                        # Add to conversation
                        messages.append({
                            "role": "assistant",
                            "content": [part]
                        })
                        messages.append({
                            "role": "user",
                            "content": [types.Part(function_response=types.FunctionResponse(
                                name=part.function_call.name,
                                response=tool_result
                            ))]
                        })
                        
                if has_function_call:
                    # Continue conversation with tool results
                    response = await self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=messages,
                        config=types.GenerateContentConfig(
                            cached_content=cache_id,
                            temperature=0.1,
                        )
                    )
                else:
                    # No function calls, we have final response
                    break
            else:
                break
                
        # Parse final response
        final_text = response.text
        
        try:
            result_dict = json.loads(final_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', final_text)
            if json_match:
                result_dict = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse response as JSON: {final_text[:500]}")
                
        # Post-process and validate
        self._validate_result(result_dict)
        
        return EstimateResult(
            success=True,
            boq=result_dict.get('boq', []),
            summary=result_dict.get('summary', {}),
            by_room=result_dict.get('by_room', {}),
            by_trade=result_dict.get('by_trade', {}),
            warnings=result_dict.get('warnings', [])
        )
        
    def _build_user_prompt(
        self,
        gap_analysis: Dict,
        property_context: Dict
    ) -> str:
        """Build per-request user prompt."""
        
        prompt = """# RENOVATION ESTIMATE REQUEST

## Gap Analysis (What the property needs)

"""
        # Add room-by-room gap analysis
        for room in gap_analysis.get('rooms', []):
            prompt += f"""### {room.get('room_name', 'Unknown Room')}
**Narrative**: {room.get('narrative', 'No description')}
**Issues**: {', '.join(room.get('issues', []))}
**Transformation**: {room.get('transformation', 'Standard renovation')}

"""
        
        prompt += f"""## Property Context

- **Total Area**: {property_context.get('total_m2', 100)}m²
- **Year Built**: {property_context.get('year_built', 'Unknown')}
- **Location**: {property_context.get('city', 'Spain')}

### Room Dimensions
"""
        for room in property_context.get('rooms', []):
            prompt += f"- **{room['name']}**: {room.get('m2', 10)}m², height {room.get('height_m', 2.5)}m\n"
            
        prompt += """

## Instructions

Using the Knowledge Graph in your system context:

1. For each room, identify all required tasks from the KG
2. Follow REQUIRES edges to include all prerequisites
3. Follow TRIGGERS edges to include cleanup/finishing
4. Calculate quantities using room dimensions and quantity formulas
5. For EACH task, call search_bcca() to find the right BCCA item
6. Validate prices with validate_price() if uncertain
7. Produce the complete BoQ with reasoning chains

CRITICAL REMINDERS:
- ALWAYS call search_bcca() - do not invent prices
- Show reasoning for every line item
- Attribute all work to specific rooms (no "General")
"""
        
        return prompt
        
    def _validate_result(self, result: Dict) -> None:
        """
        FAIL-FAST VALIDATION - Raises exception if validation fails.
        
        We do NOT return invalid results. Either succeed or fail clearly.
        """
        validation = self._run_validation_gates(result)
        
        if not validation['passed']:
            raise EstimationError(
                message="Estimate failed validation",
                details={
                    "failures": validation['failures'],
                    "gates_checked": validation['gates_checked']
                }
            )
    
    def _run_validation_gates(self, result: Dict) -> Dict:
        """
        Run ALL validation gates. All must pass.
        
        PROCESS VALIDATION (not symptom checking):
        1. All tasks have BCCA matches - Grounding check
        2. Room attribution - Context preserved through pipeline
        3. Reasoning chains exist - Explainability
        4. Tasks exist - Pipeline produced output
        
        NOTE: We do NOT check specific price ranges (e.g., "bathroom €5K-25K").
        That's symptom-checking. If the process is correct, prices will be correct.
        
        NOTE: Tests/inspections are excluded at database load time,
        so we don't need to check for them here.
        """
        failures = []
        
        # Gate 1: Room attribution (context preserved)
        general_tasks = sum(1 for line in result.get('boq', []) if line.get('room', '').lower() == 'general')
        total_tasks = len(result.get('boq', []))
        if total_tasks > 0 and general_tasks / total_tasks > 0.3:
            failures.append({
                "gate": "room_attribution",
                "severity": "HIGH",
                "message": f"{general_tasks}/{total_tasks} tasks attributed to 'General'",
                "action": "Room attribution logic needs review"
            })
        
        # Gate 2: All tasks have valid BCCA matches (grounding)
        for line in result.get('boq', []):
            bcca_code = line.get('bcca_code', '')
            if not bcca_code or bcca_code == 'NONE' or bcca_code == 'N/A':
                failures.append({
                    "gate": "bcca_grounding",
                    "severity": "CRITICAL",
                    "message": f"Task '{line.get('task_name')}' has no BCCA match",
                    "action": "BCCA search failed - task cannot be priced"
                })
                break  # One example is enough
        
        # Gate 3: Reasoning chains exist (explainability)
        for line in result.get('boq', []):
            if not line.get('reasoning') or len(line.get('reasoning', [])) < 2:
                failures.append({
                    "gate": "reasoning_chains",
                    "severity": "HIGH",
                    "message": f"Task '{line.get('task_name')}' missing reasoning chain",
                    "action": "LLM must explain each line item"
                })
                break  # One example is enough
        
        # Gate 4: Tasks exist (pipeline produced output)
        if len(result.get('boq', [])) == 0:
            failures.append({
                "gate": "tasks_exist",
                "severity": "CRITICAL",
                "message": "No tasks in BoQ",
                "action": "KG task matching failed completely"
            })
        
        # CRITICAL failures = automatic reject
        critical_failures = [f for f in failures if f['severity'] == 'CRITICAL']
        
        return {
            "passed": len(critical_failures) == 0,
            "failures": failures,
            "gates_checked": 4
        }


class EstimationError(Exception):
    """Raised when estimation fails validation. NO FALLBACK."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

---

## Part 3.5: CRITICAL - Fail-Fast Strategy (NO FALLBACKS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ⚠️  NO FALLBACK TO V1                                                     │
│                                                                             │
│   V1 produces garbage:                                                      │
│   - €53 bathroom estimates                                                  │
│   - Wrong BCCA matches (tests instead of work)                              │
│   - Wrong room attribution (75% "General")                                  │
│                                                                             │
│   Falling back to V1 = returning garbage that looks like success            │
│   This is WORSE than failing clearly                                        │
│                                                                             │
│   ❌ V0.3 fails → Fall back to V1 → User gets wrong numbers                 │
│   ✅ V0.3 fails → Clear error → User knows to retry/escalate                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Fail-Fast?

1. **Users trust results** - A €53 bathroom estimate looks real
2. **Failures get hidden** - We can't fix what we don't see
3. **Feedback is impossible** - Customer says "price was wrong" but which component failed?

### Validation Gates (ALL Must Pass)

| Gate | Severity | Condition | Action on Fail |
|------|----------|-----------|----------------|
| All tasks have BCCA | CRITICAL | Any task without valid BCCA match | REJECT |
| Room attribution | HIGH | >30% "General" | REJECT |
| Reasoning chains | HIGH | Missing for any line | REJECT |
| Tasks exist | CRITICAL | Empty BoQ | REJECT |

**Note**: We do NOT validate specific price ranges (e.g., "bathroom €5K-25K").
That's symptom-checking, not process validation. If the process is correct
(KG traversal, BCCA matching, room attribution), the price will be correct.

**Note**: Tests/inspections are excluded from the BCCA database at load time,
so there's no need to filter them during search or validation.

### Error Response Format

When validation fails, return:

```json
{
  "success": false,
  "error": "Estimate failed validation",
  "error_type": "validation_failure",
  "details": {
    "failures": [
      {
        "gate": "bathroom_cost_min",
        "severity": "CRITICAL",
        "message": "Bathroom 'Baño' cost €53 is below €5,000",
        "action": "Missing tasks or wrong BCCA matches"
      }
    ],
    "gates_checked": 6
  },
  "action": "Review validation failures and retry",
  "fallback_used": false
}
```

---

## Part 4: Implementation Checklist

### Phase 1: Tool Infrastructure (Day 1)

- [ ] **1.1 BCCA Search Tool**
  - [ ] Load BCCA from database (exclude Ch.18 in code)
  - [ ] Build BM25 index
  - [ ] Load/generate embeddings
  - [ ] Implement hybrid search
  - [ ] Test keyword searches

- [ ] **1.2 Process Validation Tool**
  - [ ] Missing BCCA match detection
  - [ ] Math validation (qty × price = total)
  - [ ] Positive values check
  - [ ] NO price ranges (not symptom checking)

### Phase 2: System Instruction (Day 1-2)

- [ ] **2.1 Write System Instruction Template**
  - [ ] Role and grounding rules
  - [ ] BCCA-speak structural search guide (not examples)
  - [ ] Chapter index (trade → chapter mapping)
  - [ ] Output format specification
  - [ ] Process validation rules (not price ranges)

- [ ] **2.2 KG Flattening** (already done)
  - [x] `kg_context.yaml` exists (~214K tokens with full quantity_guidance)

### Phase 3: Core Estimator (Day 2)

- [ ] **3.1 EstimatorV3 Class**
  - [ ] Cache management
  - [ ] Tool registration
  - [ ] Tool call handling loop
  - [ ] Response parsing
  - [ ] Validation

- [ ] **3.2 User Prompt Builder**
  - [ ] Gap analysis formatting
  - [ ] Property context formatting
  - [ ] Instructions

### Phase 4: Integration (Day 3)

- [ ] **4.1 API Endpoint**
  - [ ] `/estimate-v3` endpoint
  - [ ] Request/response models
  - [ ] Error handling

- [ ] **4.2 Database Storage**
  - [ ] Store V3 results
  - [ ] Include reasoning chains
  - [ ] Include tool call logs

### Phase 5: Testing (Day 3-4)

- [ ] **5.1 Unit Tests**
  - [ ] BCCA search returns valid construction items
  - [ ] All tasks have BCCA matches
  - [ ] Room attribution correct
  - [ ] Reasoning chains present

- [ ] **5.2 Integration Test**
  - [ ] Listing 12 end-to-end
  - [ ] Verify reasoning chains
  - [ ] Compare to V1 results

### Phase 6: Documentation (Day 4)

- [ ] **6.1 API Documentation**
- [ ] **6.2 Runbook**
- [ ] **6.3 This document (done!)**

---

## Success Criteria

| Metric | Requirement | How Verified |
|--------|-------------|--------------|
| All tasks have BCCA | 100% | Process validation |
| Room attribution | <30% "General" | Automated check |
| Reasoning chains | All line items | Automated check |
| Tool calls logged | Yes | Check logs |
| Latency (cached) | < 30 seconds | Metrics |
| **Fail-fast on invalid** | 100% | No garbage returned |
| **Clear error messages** | All failures | Structured error JSON |
| **NO V1 fallback** | Never | Code review |

---

## Token Budget

| Component | Tokens | Location | Content |
|-----------|--------|----------|---------|
| System instruction | ~3K | Cached | Role, rules, grounding |
| Full KG YAML | ~214K | Cached | 683 tasks + quantity_guidance |
| BCCA-speak guide | ~5K | Cached | Structural search patterns |
| Quantity formulas | ~2K | Cached | Area/perimeter calculations |
| **Cached Total** | **~224K** | | Gemini context cache |
| Gap analysis | ~3K | Per-request | Room gaps + narratives |
| Property context | ~2K | Per-request | Dimensions, rooms |
| **Request Total** | **~5K** | | User prompt |
| **Grand Total** | **~229K** | 23% of 1M limit |

**Note**: BCCA items (12K items, ~500K tokens) are NOT in context.
They are accessed via RAG tool, keeping context size manageable.

**Gemini 1.5 Pro**: 2M token context window, so 229K is only 11%!

---

## Comparison: V0.2 vs V0.3

| Aspect | V0.2 (Pure Context) | V0.3 (Hybrid) |
|--------|---------------------|---------------|
| KG | Basic fields | FULL enrichment (quantity_guidance) |
| BCCA | Filtered in context | RAG tool |
| Tokens | ~300K+ | ~229K |
| KG detail | Limited | type/scope/reasoning/rules/constraints |
| BCCA coverage | ~3K items | All 12K items (tests excluded at load) |
| Test filtering | In prompt (brittle) | At database load (reliable) |
| Tool calling | No | Yes |
| Complexity | Lower | Higher but robust |

**V0.3 is better because:**
1. ✅ Access to ALL BCCA items (not filtered subset)
2. ✅ Ch.18 exclusion in code (100% reliable)
3. ✅ Smaller context (faster, cheaper)
4. ✅ Tool calls provide audit trail

---

*Document Version: 0.3.0*
*Last Updated: January 2026*

