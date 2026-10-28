Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# PETER AGENTIC V0.2: Serverless Knowledge Graph Implementation

> **Date**: January 2026  
> **Author**: Peter Neyra + Claude  
> **Status**: Implementation Specification  
> **Predecessor**: PETER_AGENTIC_V0.1.md (Theoretical Foundation)

---

## Executive Summary

This document specifies the implementation of a **Serverless Knowledge Graph** for renovation cost estimation using Gemini's long context window and context caching.

**The Core Insight:**
```
Instead of: User → LLM → Translation → DB Query → Answer (lossy, slow)
We do:      User → LLM (reading entire KG in context) → Answer (grounded, fast)
```

**Why This Works:**
- Gemini 3 Pro has 1M+ token context window
- Our KG (72K tokens) + BCCA (100K tokens) = 172K tokens (17% of capacity)
- Context caching makes repeated queries fast and cheap
- System instruction forces grounding (no hallucination)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    CACHED SYSTEM CONTEXT                            │
│                    (Uploaded Once, Reused Forever)                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ SYSTEM INSTRUCTION                                            │ │
│  │ Role, grounding rules, output format, reasoning guidelines    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ KNOWLEDGE GRAPH (YAML)                          ~72K tokens   │ │
│  │ 683 tasks, 2789 edges, trades, quantities                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ BCCA PRICE BOOK (YAML)                         ~100K tokens   │ │
│  │ 12,000+ items (filtered, no tests)                            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ REFERENCE TABLES                                ~5K tokens    │ │
│  │ Room types, trade mappings, quantity formulas                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│                         TOTAL: ~177K tokens                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Cache ID (reused)
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    PER-REQUEST USER CONTEXT                         │
│                    (Small, Fast, Cheap)                             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ GAP ANALYSIS                                    ~3K tokens    │ │
│  │ Room-by-room renovation needs from comparable analysis        │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ PROPERTY CONTEXT                                ~1K tokens    │ │
│  │ Dimensions, year built, location, condition score             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│                         TOTAL: ~4K tokens                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    LLM RESPONSE                                     │
│                    (Grounded, Explainable)                          │
│                                                                     │
│  {                                                                  │
│    "boq": [                                                         │
│      {                                                              │
│        "room": "Baño",                                             │
│        "task_id": "TASK_alicatado_ceramico",                       │
│        "task_name": "Alicatado cerámico",                          │
│        "reasoning": [                                               │
│          "Gap analysis: 'renovar acabados del baño'",              │
│          "KG: Bathroom renovation TRIGGERS alicatado",             │
│          "KG: alicatado REQUIRES impermeabilización (included)",   │
│          "Quantity: 18m² walls (4.5m² floor × 2.4m height × 4)",   │
│          "BCCA: 01RAT00010 'Alicatado cerámico' @ €35/m²"          │
│        ],                                                           │
│        "bcca_code": "01RAT00010",                                  │
│        "quantity": 18,                                              │
│        "unit": "m²",                                               │
│        "unit_price": 35.00,                                         │
│        "total": 630.00                                              │
│      },                                                             │
│      ...                                                            │
│    ],                                                               │
│    "summary": {...},                                                │
│    "warnings": [...]                                                │
│  }                                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Data Flattening Specification

### 1.1 Knowledge Graph → YAML

**Source**: `pricing/hybrid_renovation_graph.json` (1.6MB, 683 tasks)
**Target**: `pricing/kg_context.yaml` (~72K tokens)

**Format Specification:**

```yaml
# ============================================================
# RENOVATION KNOWLEDGE GRAPH
# 683 canonical tasks with dependency relationships
# ============================================================

metadata:
  version: "2.0"
  tasks_count: 683
  edges_count: 2789
  last_updated: "2026-01-09"

# ------------------------------------------------------------
# TASKS
# Each task represents a discrete unit of renovation work
# ------------------------------------------------------------
tasks:

  - id: TASK_demolicion_alicatado
    name: "Demolición de alicatado existente"
    name_en: "Demolition of existing wall tiles"
    trade: albañilería
    layer: demolition
    unit: m²
    quantity_source: wall_m2
    quantity_buffer: 1.05
    bcca_keyword: "Levantado alicatado"
    permit_type: none
    
  - id: TASK_alicatado_ceramico
    name: "Alicatado cerámico"
    name_en: "Ceramic wall tiling"
    trade: albañilería
    layer: finish
    unit: m²
    quantity_source: wall_m2
    quantity_buffer: 1.10
    bcca_keyword: "Alicatado azulejo cerámico"
    permit_type: none

  # ... (683 tasks total)

# ------------------------------------------------------------
# RELATIONSHIPS
# REQUIRES = must happen before (prerequisite)
# TRIGGERS = should happen after (consequence)
# ------------------------------------------------------------
relationships:

  requires:
    - TASK_alicatado_ceramico REQUIRES TASK_demolicion_alicatado
    - TASK_alicatado_ceramico REQUIRES TASK_impermeabilizacion
    - TASK_alicatado_ceramico REQUIRES TASK_enfoscado
    - TASK_instalacion_sanitarios REQUIRES TASK_fontaneria_agua
    - TASK_instalacion_sanitarios REQUIRES TASK_fontaneria_desague
    # ... (all REQUIRES edges)

  triggers:
    - TASK_alicatado_ceramico TRIGGERS TASK_rejuntado
    - TASK_demolicion_alicatado TRIGGERS TASK_gestion_escombros
    - TASK_instalacion_sanitarios TRIGGERS TASK_sellado_silicona
    # ... (all TRIGGERS edges)

# ------------------------------------------------------------
# ROOM TYPE MAPPINGS
# What tasks are typically needed for each room type
# ------------------------------------------------------------
room_task_mappings:

  baño:
    root_tasks:
      - TASK_renovacion_integral_baño
    typical_scope:
      - demolicion_alicatado
      - demolicion_solado
      - impermeabilizacion
      - fontaneria
      - alicatado
      - solado
      - sanitarios
      - griferia
      - mampara_ducha
      - electricidad_baño

  cocina:
    root_tasks:
      - TASK_renovacion_integral_cocina
    typical_scope:
      - demolicion_mobiliario
      - demolicion_alicatado
      - fontaneria
      - electricidad
      - alicatado
      - solado
      - mobiliario_cocina
      - encimera
      - electrodomesticos

  # ... (all room types)

# ------------------------------------------------------------
# QUANTITY FORMULAS
# How to calculate quantities from room dimensions
# ------------------------------------------------------------
quantity_formulas:

  floor_m2:
    description: "Floor area in square meters"
    formula: "room_m2"
    example: "12m² room = 12m² of flooring"

  wall_m2:
    description: "Wall area in square meters"
    formula: "perimeter × height"
    example: "12m² room, 2.5m height, ~14m perimeter = 35m² walls"

  perimeter_ml:
    description: "Perimeter in linear meters"
    formula: "4 × sqrt(room_m2)"
    example: "12m² room = ~14ml perimeter"

  unit:
    description: "Count of items"
    formula: "1 per room (default) or as specified"
    example: "1 toilet per bathroom"

  # ... (all quantity types)
```

**Flattening Rules:**
1. Remove redundant fields (keep only what LLM needs)
2. Use abbreviated keys where clear (`qty` not `quantity_source`)
3. Group relationships separately for clarity
4. Include English translations for LLM comprehension
5. Add room mappings to guide task selection

### 1.2 BCCA Price Book → YAML

**Source**: `pricing/construction.db` (12,565 items)
**Target**: `pricing/bcca_context.yaml` (~100K tokens)

**Format Specification:**

```yaml
# ============================================================
# BCCA PRICE BOOK (Base de Costes de la Construcción de Andalucía)
# Official Spanish construction pricing database
# ============================================================

metadata:
  version: "2023"
  items_count: 11946
  excluded: "Chapter 18 (quality control tests)"
  currency: "EUR"
  region: "Andalucía, Spain"

# ------------------------------------------------------------
# IMPORTANT USAGE RULES
# ------------------------------------------------------------
rules:
  - "Chapter 18 items are TESTS/INSPECTIONS, not construction work. NEVER use them."
  - "Match by INTENT: 'install toilet' → installation item, not 'test toilet'"
  - "Prices include labor and materials unless noted"
  - "Units: m² (square meters), ml (linear meters), ud (units), kg, etc."

# ------------------------------------------------------------
# CHAPTER 01: REVESTIMIENTOS (Wall/Floor Finishes)
# Use for: alicatado, solado, pintura, enlucido
# ------------------------------------------------------------
chapter_01_revestimientos:

  - code: 01RAA00001
    desc: "Alicatado con azulejo cerámico 20x20cm"
    unit: m²
    price: 28.50
    includes: "material + colocación + rejuntado"

  - code: 01RAA00010
    desc: "Alicatado con azulejo cerámico 30x60cm rectificado"
    unit: m²
    price: 35.00
    includes: "material + colocación + rejuntado"

  - code: 01RSO00001
    desc: "Solado gres porcelánico 45x45cm"
    unit: m²
    price: 32.00
    includes: "material + colocación + rejuntado"

  # ... (479 items in chapter 01)

# ------------------------------------------------------------
# CHAPTER 08: INSTALACIONES (Plumbing, Electrical, HVAC)
# Use for: fontanería, sanitarios, electricidad, climatización
# ------------------------------------------------------------
chapter_08_instalaciones:

  - code: 08IFS00001
    desc: "Inodoro de porcelana vitrificada con tanque bajo"
    unit: ud
    price: 285.00
    includes: "aparato + instalación + conexión"

  - code: 08IFS00010
    desc: "Lavabo de porcelana sobre pedestal"
    unit: ud
    price: 195.00
    includes: "aparato + grifería + instalación"

  - code: 08IFS00020
    desc: "Plato de ducha acrílico 80x80cm"
    unit: ud
    price: 320.00
    includes: "plato + válvula + instalación"

  - code: 08IFG00001
    desc: "Grifería monomando para lavabo"
    unit: ud
    price: 85.00
    includes: "grifo + instalación + conexiones"

  # ... (1990 items in chapter 08)

# ------------------------------------------------------------
# EXCLUDED: CHAPTER 18 (Quality Control - DO NOT USE)
# These are tests/inspections, NOT construction work
# ------------------------------------------------------------
# 18xxx items are intentionally excluded from this context.
# If you see a task that seems to match a test item, SKIP IT
# and note in warnings: "No valid BCCA match - appears to be test item"

# ------------------------------------------------------------
# CHAPTER INDEX (for reference)
# ------------------------------------------------------------
chapters:
  "01": "Revestimientos (finishes)"
  "02": "Cimentaciones (foundations)"
  "03": "Estructuras (structures)"
  "04": "Cubiertas (roofing)"
  "05": "Cerramientos (enclosures)"
  "06": "Carpintería (woodwork/doors)"
  "07": "Vidriería (glazing)"
  "08": "Instalaciones (MEP)"
  "09": "Aislamientos (insulation)"
  "10": "Señalización (signage)"
  "11": "Urbanización (landscaping)"
  "12": "Seguridad (safety)"
  "13": "Gestión residuos (waste)"
  "14": "Restauración (restoration)"
  "15": "Varios (miscellaneous)"
  # 18: EXCLUDED - Quality control tests
```

**Flattening Rules:**
1. **EXCLUDE chapter 18** entirely (quality control tests)
2. Group by chapter for LLM navigation
3. Include `includes` field to clarify what's in the price
4. Add explicit rules about test items
5. Keep descriptions concise but complete

---

## Part 2: System Instruction Specification

The system instruction is the "soft fine-tuning" that ensures grounded, consistent behavior.

```text
# ============================================================
# SYSTEM INSTRUCTION: Renovation Cost Estimator
# ============================================================

ROLE:
You are a senior Spanish renovation cost estimator with 20 years of experience.
You produce Bills of Quantities (BoQ) for residential property renovations in Spain.
You work EXCLUSIVELY with the Knowledge Graph and BCCA data provided below.

KNOWLEDGE SOURCES:
1. KNOWLEDGE GRAPH: Contains 683 canonical renovation tasks with dependencies
2. BCCA PRICE BOOK: Official Andalucían construction prices (2023)
3. QUANTITY FORMULAS: How to calculate quantities from room dimensions

# ============================================================
# GROUNDING RULES (CRITICAL - NO EXCEPTIONS)
# ============================================================

1. DATA GROUNDING:
   - Use ONLY tasks from the Knowledge Graph
   - Use ONLY prices from the BCCA Price Book
   - If a task is not in the KG, respond: "Task not in Knowledge Graph: [description]"
   - If no BCCA match exists, respond: "No BCCA match for: [task]"

2. NO HALLUCINATION:
   - Do NOT invent task IDs
   - Do NOT invent BCCA codes
   - Do NOT guess prices
   - Do NOT add tasks that aren't in the KG

3. CHAPTER 18 EXCLUSION:
   - BCCA Chapter 18 items are quality control TESTS, not construction work
   - NEVER use any code starting with "18"
   - If semantic search suggests a "18xxx" code, SKIP IT and note the issue

4. INTENT MATCHING:
   - Match tasks to BCCA items by INTENT, not just keywords
   - "Install toilet" → installation item (08IFS...), NOT test item (18...)
   - "Demolish tiles" → demolition item (01RD...), NOT inspection item

# ============================================================
# TASK RESOLUTION PROCESS
# ============================================================

When given a gap analysis for a room:

STEP 1: IDENTIFY ROOT TASKS
- Look up the room type in `room_task_mappings`
- Identify which root tasks apply based on the gap description
- Example: "renovar baño completo" → TASK_renovacion_integral_baño

STEP 2: EXPAND DEPENDENCIES
- For each root task, follow ALL `REQUIRES` edges backward
- These are prerequisites that MUST be included
- Example: alicatado REQUIRES demolicion, impermeabilizacion, enfoscado

STEP 3: EXPAND TRIGGERS
- For each task, follow `TRIGGERS` edges forward
- These are consequences that SHOULD be included
- Example: demolicion TRIGGERS gestion_escombros

STEP 4: CALCULATE QUANTITIES
- Use room dimensions from the property context
- Apply the quantity formula for each task's `quantity_source`
- Apply the `quantity_buffer` (waste factor)
- Example: wall_m2 for 4.5m² bathroom = perimeter(~8.5m) × height(2.4m) = 20.4m²

STEP 5: MATCH BCCA CODES
- Use the task's `bcca_keyword` to find matching BCCA items
- Verify the match is an INSTALLATION/WORK item, not a test
- If multiple matches, prefer the most specific one

STEP 6: BUILD LINE ITEM
- Combine: task, quantity, BCCA code, unit price, total
- Add reasoning chain showing HOW you arrived at this

# ============================================================
# OUTPUT FORMAT
# ============================================================

Respond with valid JSON in this exact structure:

{
  "success": true,
  "boq": [
    {
      "room": "string - room name from gap analysis",
      "task_id": "string - KG task ID",
      "task_name": "string - human readable name",
      "reasoning": [
        "string - step 1 of reasoning",
        "string - step 2 of reasoning",
        "string - step 3 of reasoning"
      ],
      "bcca_code": "string - matched BCCA code",
      "bcca_description": "string - what the BCCA item is",
      "quantity": number,
      "unit": "string - m², ud, ml, etc.",
      "unit_price": number,
      "total": number
    }
  ],
  "summary": {
    "total_pem": number,
    "overhead_19pct": number,
    "subtotal_pec": number,
    "iva_21pct": number,
    "total_with_iva": number,
    "tasks_count": number,
    "rooms_processed": ["list of room names"]
  },
  "by_room": {
    "room_name": {
      "tasks_count": number,
      "total": number
    }
  },
  "by_trade": {
    "trade_name": {
      "tasks_count": number,
      "total": number
    }
  },
  "warnings": [
    "string - any issues encountered (missing matches, suspicious items, etc.)"
  ]
}

# ============================================================
# REASONING CHAIN REQUIREMENTS
# ============================================================

Every line item MUST have a reasoning chain that shows:
1. SOURCE: What gap analysis text triggered this task
2. KG LOOKUP: How you found the task in the Knowledge Graph
3. DEPENDENCIES: What REQUIRES/TRIGGERS edges you followed
4. QUANTITY: How you calculated the quantity
5. BCCA MATCH: How you selected the BCCA code

Example reasoning chain:
[
  "Gap: 'El baño necesita renovación completa de acabados'",
  "KG: Room type 'baño' maps to TASK_renovacion_integral_baño",
  "KG: This root task TRIGGERS TASK_alicatado_ceramico",
  "KG: TASK_alicatado_ceramico REQUIRES TASK_impermeabilizacion (added)",
  "Quantity: wall_m2 = perimeter(8.5m) × height(2.4m) = 20.4m² × 1.10 buffer = 22.4m²",
  "BCCA: 01RAA00010 'Alicatado azulejo cerámico 30x60' @ €35/m² (installation item)"
]

# ============================================================
# SANITY CHECKS
# ============================================================

Before finalizing, verify PROCESS integrity:
1. All tasks have valid BCCA codes (no Chapter 18 test items)
2. All tasks have room attribution (not excessive "General")
3. All line items have reasoning chains explaining the match
4. KG dependency traversal was complete (check for missing prerequisites)

If totals seem wrong, review for:
- Missing tasks (incomplete dependency traversal)
- Wrong BCCA matches (test items instead of installation)
- Quantity errors (wrong formula or missing buffer)

# ============================================================
# KNOWLEDGE GRAPH DATA
# ============================================================

[KG_CONTEXT_YAML_INSERTED_HERE]

# ============================================================
# BCCA PRICE BOOK DATA
# ============================================================

[BCCA_CONTEXT_YAML_INSERTED_HERE]

# ============================================================
# END OF SYSTEM INSTRUCTION
# ============================================================
```

---

## Part 3: Context Caching Implementation

### 3.1 Caching Strategy

```python
"""
Context Caching for Serverless Knowledge Graph

The cached context contains:
- System instruction (~3K tokens)
- Knowledge Graph YAML (~72K tokens)
- BCCA Price Book YAML (~100K tokens)
- Reference tables (~5K tokens)

Total cached: ~180K tokens
Per-request: ~4K tokens (gap analysis + dimensions)
"""

from google import genai
from google.genai import types
import hashlib

class RenovationEstimatorV2:
    """
    PETER AGENTIC V0.2: Serverless Knowledge Graph Estimator
    
    Uses Gemini's context caching to maintain KG+BCCA in "RAM"
    for instant, grounded renovation estimates.
    """
    
    def __init__(self):
        self.client = genai.Client()
        self.cache_id = None
        self.cache_hash = None
        
    def _load_context_files(self) -> tuple[str, str]:
        """Load flattened KG and BCCA YAML files."""
        with open('pricing/kg_context.yaml', 'r') as f:
            kg_yaml = f.read()
        with open('pricing/bcca_context.yaml', 'r') as f:
            bcca_yaml = f.read()
        return kg_yaml, bcca_yaml
    
    def _build_system_instruction(self, kg_yaml: str, bcca_yaml: str) -> str:
        """Build complete system instruction with embedded data."""
        # Load system instruction template
        with open('pricing/system_instruction.txt', 'r') as f:
            template = f.read()
        
        # Insert KG and BCCA data
        system_instruction = template.replace(
            '[KG_CONTEXT_YAML_INSERTED_HERE]', kg_yaml
        ).replace(
            '[BCCA_CONTEXT_YAML_INSERTED_HERE]', bcca_yaml
        )
        
        return system_instruction
    
    def _get_content_hash(self, content: str) -> str:
        """Hash content to detect changes."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def ensure_cache(self) -> str:
        """
        Ensure context cache exists and is current.
        Returns cache ID for use in queries.
        """
        kg_yaml, bcca_yaml = self._load_context_files()
        system_instruction = self._build_system_instruction(kg_yaml, bcca_yaml)
        
        # Check if cache needs refresh
        current_hash = self._get_content_hash(system_instruction)
        
        if self.cache_id and self.cache_hash == current_hash:
            # Cache is current
            return self.cache_id
        
        # Create or refresh cache
        print(f"Creating context cache ({len(system_instruction):,} chars)...")
        
        cache = await self.client.caches.create(
            model="gemini-2.0-flash",  # or gemini-3-pro when available
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
                ttl="3600s",  # 1 hour cache lifetime
                display_name="renovation-kg-bcca-v2"
            )
        )
        
        self.cache_id = cache.name
        self.cache_hash = current_hash
        
        print(f"Cache created: {self.cache_id}")
        return self.cache_id
    
    async def estimate(
        self, 
        gap_analysis: dict,
        property_context: dict
    ) -> dict:
        """
        Produce renovation estimate using cached KG+BCCA context.
        
        Args:
            gap_analysis: Room-by-room renovation needs
            property_context: Dimensions, year, location
            
        Returns:
            Complete BoQ with reasoning chains
        """
        # Ensure cache is ready
        cache_id = await self.ensure_cache()
        
        # Build user prompt (small, per-request)
        user_prompt = self._build_user_prompt(gap_analysis, property_context)
        
        # Query with cached context
        response = await self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                cached_content=cache_id,
                temperature=0.1,  # Low temperature for consistency
                response_mime_type="application/json",
            )
        )
        
        return json.loads(response.text)
    
    def _build_user_prompt(
        self, 
        gap_analysis: dict, 
        property_context: dict
    ) -> str:
        """Build the per-request user prompt."""
        
        prompt = """
# RENOVATION ESTIMATE REQUEST

## Gap Analysis (What the property needs)

"""
        # Add room-by-room gap analysis
        for room in gap_analysis.get('rooms', []):
            prompt += f"""
### {room.get('room_name', 'Unknown Room')}
**Narrative**: {room.get('narrative', 'No description')}
**Key Issues**: {', '.join(room.get('issues', []))}
**Transformation Goal**: {room.get('transformation', 'Standard renovation')}

"""
        
        prompt += """
## Property Context

"""
        # Add property dimensions
        prompt += f"""
- **Total Area**: {property_context.get('total_m2', 100)}m²
- **Year Built**: {property_context.get('year_built', 'Unknown')}
- **Location**: {property_context.get('city', 'Spain')}
- **Condition Score**: {property_context.get('condition_score', 'Unknown')}/10

### Room Dimensions
"""
        for room in property_context.get('rooms', []):
            prompt += f"- **{room['name']}**: {room.get('m2', 10)}m², height {room.get('height_m', 2.5)}m\n"
        
        prompt += """

## Instructions

Using the Knowledge Graph and BCCA Price Book in your context:

1. For each room in the gap analysis, identify all required tasks
2. Follow REQUIRES edges to include prerequisites
3. Follow TRIGGERS edges to include consequences
4. Calculate quantities from room dimensions
5. Match each task to a BCCA installation item (NOT tests)
6. Produce the complete BoQ with reasoning chains

Remember:
- Include ALL tasks from KG dependency chains
- NEVER use Chapter 18 BCCA codes (tests)
- Show reasoning for every line item
"""
        
        return prompt
```

### 3.2 Cache Refresh Strategy

```python
"""
Cache Refresh Logic

The cache should be refreshed when:
1. KG is updated (new tasks, changed dependencies)
2. BCCA is updated (new prices, new items)
3. System instruction changes
4. Cache TTL expires (hourly by default)
"""

class CacheManager:
    """Manages context cache lifecycle."""
    
    def __init__(self, client: genai.Client):
        self.client = client
        self.cache_metadata = {}
        
    async def check_cache_health(self, cache_id: str) -> dict:
        """Check if cache is still valid."""
        try:
            cache = await self.client.caches.get(name=cache_id)
            return {
                "valid": True,
                "expires_at": cache.expire_time,
                "token_count": cache.usage_metadata.total_token_count
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def refresh_if_needed(
        self, 
        cache_id: str,
        kg_path: str,
        bcca_path: str
    ) -> str:
        """Refresh cache if source files changed."""
        
        # Check file modification times
        kg_mtime = os.path.getmtime(kg_path)
        bcca_mtime = os.path.getmtime(bcca_path)
        
        cached_kg_mtime = self.cache_metadata.get('kg_mtime', 0)
        cached_bcca_mtime = self.cache_metadata.get('bcca_mtime', 0)
        
        if kg_mtime > cached_kg_mtime or bcca_mtime > cached_bcca_mtime:
            print("Source files changed, refreshing cache...")
            # Delete old cache
            await self.client.caches.delete(name=cache_id)
            # Create new cache (handled by ensure_cache)
            return None  # Signal to recreate
        
        return cache_id  # Cache is current
```

---

## Part 4: Integration with Existing Pipeline

### 4.1 API Endpoint Update

```python
# routes/renovation.py

from pricing.estimator_v2 import RenovationEstimatorV2

# Initialize estimator (singleton)
estimator_v2 = RenovationEstimatorV2()

@router.post("/api/renovation/{listing_id}/estimate-v2")
async def estimate_renovation_v2(
    listing_id: int,
    request: EstimateRequest
) -> EstimateResponse:
    """
    V2 Renovation Estimate using Serverless Knowledge Graph.
    
    This replaces the multi-phase pipeline with a single
    LLM call using cached KG+BCCA context.
    """
    
    # 1. Get gap analysis (existing pipeline)
    gap_result = await get_gap_analysis(listing_id, request.bracket)
    
    # 2. Get property context
    property_context = await get_property_context(listing_id)
    
    # 3. Estimate using V2 (single LLM call with cached context)
    result = await estimator_v2.estimate(
        gap_analysis=gap_result.to_dict(),
        property_context=property_context
    )
    
    # 4. Store result
    await store_estimate(listing_id, request.bracket, result)
    
    return EstimateResponse(
        success=True,
        data=result
    )
```

### 4.2 Fail-Fast Strategy (NO FALLBACKS)

```python
"""
FAIL-FAST VALIDATION - NO FALLBACK TO V1

⚠️  CRITICAL: V1 produces garbage (€53 bathrooms, Chapter 18 codes, wrong room attribution)
    We NEVER fall back to V1. Either V2 succeeds with validated results or we fail clearly.

Failure modes:
- Cache unavailable → Error with retry suggestion
- LLM timeout → Error with retry suggestion  
- Validation fails → Error with specific failure reason
- Chapter 18 detected → Error: invalid BCCA match
"""

class EstimationError(Exception):
    """Raised when estimation fails validation."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


async def estimate_v2(
    listing_id: int,
    gap_analysis: dict,
    property_context: dict
) -> dict:
    """
    Produce estimate using V2 architecture.
    
    CRITICAL: No fallback to V1. Either succeed with valid result or fail clearly.
    Returning garbage that looks like success is WORSE than failing.
    """
    
    try:
        # Attempt V2 estimation
        result = await estimator_v2.estimate(gap_analysis, property_context)
        
        # MANDATORY VALIDATION - must pass ALL gates
        validation = validate_estimate_strict(result)
        
        if not validation['passed']:
            # DO NOT RETURN INVALID RESULT - fail clearly instead
            raise EstimationError(
                message="Estimate failed validation",
                details={
                    "failures": validation['failures'],
                    "partial_result": result
                }
            )
        
        result['estimator_version'] = 'v2'
        result['validation_passed'] = True
        return {"success": True, "data": result}
        
    except EstimationError as e:
        # Validation failure - return structured error, NOT V1 garbage
        logger.error(f"V2 validation failed for listing {listing_id}: {e.details}")
        
        return {
            "success": False,
            "error": e.message,
            "error_type": "validation_failure",
            "details": e.details,
            "action": "Review validation failures and retry",
            "fallback_used": False  # Explicitly: we did NOT return garbage
        }
        
    except Exception as e:
        # Unexpected failure - return error, NOT V1 result
        logger.error(f"V2 estimation failed for listing {listing_id}: {e}")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": "estimation_failure", 
            "action": "Retry or contact support",
            "fallback_used": False
        }
```

---

## Part 5: Testing & Validation

### 5.1 Test Cases

```python
"""
Test suite for PETER AGENTIC V0.2

Critical test cases based on known issues:
1. Bathroom should cost €5-15K, not €53
2. No Chapter 18 BCCA codes should appear
3. Room attribution should work correctly
4. Reasoning chains should be complete
"""

import pytest

class TestEstimatorV2:
    
    @pytest.fixture
    def estimator(self):
        return RenovationEstimatorV2()
    
    @pytest.fixture
    def bathroom_gap_analysis(self):
        return {
            "rooms": [
                {
                    "room_name": "Baño",
                    "narrative": "El baño es una cápsula del tiempo de los años 70. Necesita renovación completa.",
                    "issues": ["alicatado antiguo", "sanitarios obsoletos", "instalación eléctrica peligrosa"],
                    "transformation": "Baño moderno y seguro con plato de ducha accesible"
                }
            ]
        }
    
    @pytest.fixture
    def property_context(self):
        return {
            "total_m2": 80,
            "year_built": 1975,
            "city": "Madrid",
            "rooms": [
                {"name": "Baño", "m2": 4.5, "height_m": 2.4}
            ]
        }
    
    async def test_all_tasks_have_bcca(self, estimator, bathroom_gap_analysis, property_context):
        """All tasks should have valid BCCA matches (process validation)."""
        result = await estimator.estimate(bathroom_gap_analysis, property_context)
        
        bathroom_total = result['by_room']['Baño']['total']
        
        assert bathroom_total >= 5000, f"Bathroom too cheap: €{bathroom_total}"
        assert bathroom_total <= 20000, f"Bathroom too expensive: €{bathroom_total}"
    
    async def test_no_chapter_18_codes(self, estimator, bathroom_gap_analysis, property_context):
        """No test/inspection BCCA codes should be used."""
        result = await estimator.estimate(bathroom_gap_analysis, property_context)
        
        for line in result['boq']:
            bcca_code = line.get('bcca_code', '')
            assert not bcca_code.startswith('18'), \
                f"Chapter 18 code used: {bcca_code} for {line['task_name']}"
    
    async def test_room_attribution(self, estimator, bathroom_gap_analysis, property_context):
        """All bathroom tasks should be attributed to Baño."""
        result = await estimator.estimate(bathroom_gap_analysis, property_context)
        
        for line in result['boq']:
            assert line['room'] == 'Baño', \
                f"Wrong room attribution: {line['task_name']} → {line['room']}"
    
    async def test_reasoning_chains_complete(self, estimator, bathroom_gap_analysis, property_context):
        """Every line item should have a complete reasoning chain."""
        result = await estimator.estimate(bathroom_gap_analysis, property_context)
        
        for line in result['boq']:
            reasoning = line.get('reasoning', [])
            
            # Must have at least 3 reasoning steps
            assert len(reasoning) >= 3, \
                f"Incomplete reasoning for {line['task_name']}: {reasoning}"
            
            # Must reference KG
            kg_referenced = any('KG' in step or 'Knowledge Graph' in step for step in reasoning)
            assert kg_referenced, \
                f"KG not referenced in reasoning for {line['task_name']}"
            
            # Must reference BCCA
            bcca_referenced = any('BCCA' in step for step in reasoning)
            assert bcca_referenced, \
                f"BCCA not referenced in reasoning for {line['task_name']}"
    
    async def test_dependencies_included(self, estimator, bathroom_gap_analysis, property_context):
        """Alicatado should include its prerequisites."""
        result = await estimator.estimate(bathroom_gap_analysis, property_context)
        
        task_names = [line['task_name'].lower() for line in result['boq']]
        
        # If alicatado is present, its prerequisites should be too
        if any('alicatado' in name for name in task_names):
            assert any('demolici' in name for name in task_names), \
                "Alicatado present but demolition missing"
            assert any('impermeabil' in name for name in task_names), \
                "Alicatado present but waterproofing missing"
```

### 5.2 Validation Functions

```python
def validate_estimate(result: dict) -> bool:
    """
    Validate estimate result for sanity.
    
    Returns True if estimate passes all checks.
    """
    errors = []
    
    # Check structure
    if 'boq' not in result:
        errors.append("Missing 'boq' in result")
        return False
    
    if 'summary' not in result:
        errors.append("Missing 'summary' in result")
    
    # Check totals
    total = result.get('summary', {}).get('total_with_iva', 0)
    
    if total < 1000:
        errors.append(f"Total too low: €{total}")
    
    if total > 1000000:
        errors.append(f"Total too high: €{total}")
    
    # Check for chapter 18 codes
    for line in result.get('boq', []):
        if line.get('bcca_code', '').startswith('18'):
            errors.append(f"Chapter 18 code: {line['bcca_code']}")
    
    # Check reasoning chains exist
    for line in result.get('boq', []):
        if not line.get('reasoning'):
            errors.append(f"Missing reasoning for {line.get('task_name')}")
    
    if errors:
        logger.warning(f"Validation errors: {errors}")
        return False
    
    return True
```

---

## Part 6: Monitoring & Observability

### 6.1 Logging Strategy

```python
"""
Logging for V2 Estimator

Log levels:
- INFO: Request/response summaries
- DEBUG: Full prompts and responses
- WARNING: Validation issues, fallbacks
- ERROR: Failures
"""

import structlog

logger = structlog.get_logger()

class EstimatorLogger:
    
    @staticmethod
    def log_request(listing_id: int, gap_analysis: dict):
        logger.info(
            "estimate_request",
            listing_id=listing_id,
            rooms=len(gap_analysis.get('rooms', [])),
            room_names=[r['room_name'] for r in gap_analysis.get('rooms', [])]
        )
    
    @staticmethod
    def log_response(listing_id: int, result: dict, duration_ms: int):
        logger.info(
            "estimate_response",
            listing_id=listing_id,
            success=result.get('success', False),
            total_eur=result.get('summary', {}).get('total_with_iva', 0),
            tasks_count=len(result.get('boq', [])),
            duration_ms=duration_ms,
            warnings=result.get('warnings', [])
        )
    
    @staticmethod
    def log_cache_status(cache_id: str, status: str, token_count: int):
        logger.info(
            "cache_status",
            cache_id=cache_id,
            status=status,
            token_count=token_count
        )
    
    @staticmethod
    def log_validation_failure(listing_id: int, errors: list):
        logger.warning(
            "validation_failure",
            listing_id=listing_id,
            errors=errors
        )
```

### 6.2 Metrics

```python
"""
Key metrics to track:

1. Estimate Quality
   - % of estimates passing validation
   - Average bathroom cost (should be €5-15K)
   - % with Chapter 18 codes (should be 0%)

2. Performance
   - p50/p95/p99 latency
   - Cache hit rate
   - Token usage per request

3. Cost
   - $ per estimate
   - Cache storage cost
"""

from prometheus_client import Counter, Histogram, Gauge

# Counters
estimates_total = Counter('estimates_total', 'Total estimates', ['version', 'status'])
validation_failures = Counter('validation_failures', 'Validation failures', ['reason'])
chapter_18_usage = Counter('chapter_18_usage', 'Chapter 18 codes used (should be 0)')

# Histograms
estimate_duration = Histogram('estimate_duration_seconds', 'Estimate duration')
estimate_total_eur = Histogram('estimate_total_eur', 'Estimate total in EUR', 
                                buckets=[1000, 5000, 10000, 20000, 50000, 100000, 200000])

# Gauges
cache_token_count = Gauge('cache_token_count', 'Tokens in cached context')
cache_age_seconds = Gauge('cache_age_seconds', 'Age of current cache')
```

---

## Part 7: Implementation Checklist

### Phase 1: Data Preparation (Day 1)

- [ ] **1.1 Flatten KG to YAML**
  - [ ] Write `flatten_kg.py` script
  - [ ] Convert `hybrid_renovation_graph.json` → `kg_context.yaml`
  - [ ] Verify task count (683)
  - [ ] Verify edge count (~2789)
  - [ ] Measure token count (target: ~72K)

- [ ] **1.2 Flatten BCCA to YAML**
  - [ ] Write `flatten_bcca.py` script
  - [ ] Export from `construction.db`
  - [ ] EXCLUDE Chapter 18 entirely
  - [ ] Group by chapter
  - [ ] Measure token count (target: ~100K)

- [ ] **1.3 Write System Instruction**
  - [ ] Create `system_instruction.txt` template
  - [ ] Define grounding rules
  - [ ] Define output format
  - [ ] Define sanity checks

### Phase 2: Core Implementation (Day 2)

- [ ] **2.1 Implement EstimatorV2 class**
  - [ ] `__init__` with client setup
  - [ ] `_load_context_files()`
  - [ ] `_build_system_instruction()`
  - [ ] `ensure_cache()`
  - [ ] `estimate()`

- [ ] **2.2 Implement Context Caching**
  - [ ] Create cache on startup
  - [ ] Cache hash for change detection
  - [ ] Cache refresh logic
  - [ ] TTL management

- [ ] **2.3 Implement User Prompt Builder**
  - [ ] Format gap analysis
  - [ ] Format property context
  - [ ] Format room dimensions

### Phase 3: Integration (Day 3)

- [ ] **3.1 API Endpoint**
  - [ ] Create `/estimate-v2` endpoint
  - [ ] Request/response models
  - [ ] Error handling

- [ ] **3.2 Fail-Fast Validation**
  - [ ] Implement validation gates (no Ch.18, room attribution, cost sanity)
  - [ ] Return clear errors on validation failure
  - [ ] NO fallback to V1 (V1 produces garbage)

- [ ] **3.3 Database Storage**
  - [ ] Store V2 results in `listing_bracket_analyses`
  - [ ] Include reasoning chains
  - [ ] Include estimator version

### Phase 4: Testing (Day 4)

- [ ] **4.1 Unit Tests**
  - [ ] Test bathroom cost range
  - [ ] Test no Chapter 18 codes
  - [ ] Test room attribution
  - [ ] Test reasoning chains

- [ ] **4.2 Integration Tests**
  - [ ] Test with listing 12 (known problem case)
  - [ ] Test with full property
  - [ ] Test cache refresh

- [ ] **4.3 Manual QA**
  - [ ] Review bathroom estimate for listing 12
  - [ ] Verify reasoning makes sense
  - [ ] Compare V1 vs V2 results

### Phase 5: Production Readiness (Day 5)

- [ ] **5.1 Monitoring**
  - [ ] Add logging
  - [ ] Add metrics
  - [ ] Set up alerts

- [ ] **5.2 Documentation**
  - [ ] Update API docs
  - [ ] Update pipeline docs
  - [ ] Create runbook

- [ ] **5.3 Deployment**
  - [ ] Deploy to staging
  - [ ] Run smoke tests
  - [ ] Deploy to production
  - [ ] Monitor metrics

---

## Success Criteria

After implementation, the following MUST be true:

| Metric | Requirement | Verification |
|--------|-------------|--------------|
| Chapter 18 BCCA codes | 0 | Automated check |
| All tasks have BCCA | 100% | Process validation |
| Room attribution accuracy | <30% "General" | Automated check |
| Reasoning chains present | 100% of line items | Automated check |
| Estimate latency (cached) | < 10 seconds | Metrics |
| Validation pass rate | > 95% | Metrics |
| Clear error on failure | 100% | No silent failures |

---

## Appendix: Token Budget

| Component | Tokens | Notes |
|-----------|--------|-------|
| System Instruction | ~3,000 | Role, rules, format |
| KG (minimal YAML) | ~72,000 | 683 tasks + edges |
| BCCA (filtered YAML) | ~100,000 | ~11K items (no Ch.18) |
| Reference Tables | ~5,000 | Room mappings, formulas |
| **Cached Total** | **~180,000** | 18% of 1M limit |
| Gap Analysis | ~3,000 | Per-request |
| Property Context | ~1,000 | Per-request |
| **Request Total** | **~4,000** | Per-request |
| **Grand Total** | **~184,000** | Well under 1M |

---

## Appendix: Cost Estimate

| Component | Cost | Frequency |
|-----------|------|-----------|
| Cache storage | ~$0.01/hour | Continuous |
| Cache creation | ~$0.02 | Per refresh (~daily) |
| Per-request (cached) | ~$0.001 | Per estimate |
| Per-request (output) | ~$0.005 | Per estimate |
| **Total per estimate** | **~$0.006** | |
| **1000 estimates/month** | **~$6** | Plus ~$7 cache |

Compare to V1 (multi-phase):
- 5 LLM calls × ~$0.01 = ~$0.05 per estimate
- V2 is **8x cheaper**

---

*Document Version: 0.2.0*
*Last Updated: January 2026*

