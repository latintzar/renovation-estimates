"""
V2 BOQ Generator - Delta Scope to Bill of Quantities
=====================================================

PURPOSE:
--------
Convert Delta Scopes into a priced Bill of Quantities (BOQ).

This is V1 Phase 1, but with ONE change:
- V1: Determines scope by comparing Target PIR vs Bracket PIR
- V2: Scope already determined by Delta Scope Generation (6 dimensions)

ALL the rich reasoning about BCCA codes, quantities, sequencing, FFE, 
knowledge graphs — that's preserved EXACTLY from V1 Phase 1.

MODEL: gemini-3-pro-preview (alias: "pro")
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

# Limit concurrent DB writes across all per-scope saves to avoid timeouts
# Conservative cap to prevent Supabase connection timeouts under heavy parallelism
DB_SAVE_SEMAPHORE = asyncio.Semaphore(1)


async def _gather_or_cancel(tasks: List[asyncio.Task], label: str) -> List[Any]:
    """Gather tasks and cancel the remainder on first error."""
    try:
        return await asyncio.gather(*tasks)
    except Exception as exc:
        logger.error(f"    ❌ {label} failed, cancelling remaining tasks: {exc}")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


def _chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


class BOQWriteQueue:
    """Single-writer queue for BOQ line-item persistence with backpressure."""

    def __init__(
        self,
        db: Any,
        listing_id: int,
        strategy_name: str,
        chunk_size: int = 25,
        max_queue: int = 50,
        retry_wait_s: float = 12.0,
    ) -> None:
        self.db = db
        self.listing_id = listing_id
        self.strategy_name = strategy_name
        self.chunk_size = chunk_size
        self.retry_wait_s = retry_wait_s
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        self._task: Optional[asyncio.Task] = None
        self._error: Optional[BaseException] = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    def _raise_if_error(self) -> None:
        if self._error:
            raise self._error

    async def enqueue(self, dimension: str, room_name: str, items: List[Dict[str, Any]]) -> None:
        self._raise_if_error()
        await self._queue.put((dimension, room_name, items))

    async def close(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)
        await self._task
        self._raise_if_error()

    async def _save_chunk(
        self,
        dimension: str,
        room_name: str,
        chunk: List[Dict[str, Any]],
        attempt: int,
        total_attempts: int,
    ) -> None:
        try:
            saved_count = await self.db.save_boq_line_items_batch(
                listing_id=self.listing_id,
                strategy_name=self.strategy_name,
                dimension=dimension,
                room_name=room_name,
                items=chunk,
            )
            if saved_count != len(chunk):
                raise RuntimeError(
                    f"[BOQ SAVE FAILED] {self.strategy_name} | {dimension} | {room_name} | saved={saved_count} expected={len(chunk)}"
                )
        except httpx.ConnectTimeout as exc:
            if attempt < total_attempts:
                if hasattr(self.db, "reset_boq_client"):
                    await self.db.reset_boq_client()
                logger.warning(
                    f"    ⚠️ BOQ save connect-timeout | retrying in {self.retry_wait_s:.0f}s | {self.strategy_name} | {dimension} | {room_name}"
                )
                await asyncio.sleep(self.retry_wait_s)
                await self._save_chunk(dimension, room_name, chunk, attempt + 1, total_attempts)
                return
            raise exc

    async def _run(self) -> None:
        try:
            while True:
                payload = await self._queue.get()
                if payload is None:
                    self._queue.task_done()
                    break
                dimension, room_name, items = payload
                chunks = _chunk_list(items, self.chunk_size)
                async with DB_SAVE_SEMAPHORE:
                    for chunk in chunks:
                        await self._save_chunk(
                            dimension=dimension,
                            room_name=room_name,
                            chunk=chunk,
                            attempt=1,
                            total_attempts=2,
                        )
                self._queue.task_done()
        except Exception as exc:
            self._error = exc
            logger.error(f"    ❌ BOQ writer failed: {exc}")

# Gemini client
try:
    from ..pipeline.gemini_client import call_gemini
except ImportError:
    import sys
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from pipeline.gemini_client import call_gemini

from .schemas.gemini_schemas_v2 import V2_BOQ_OUTPUT_SCHEMA

# NOTE: No BCCAPriceLookup import - Gemini has the FULL BCCA index in context
# No fallback price verification. Trust Gemini's output. Fail loud if wrong.


# =============================================================================
# BCCA INDEX LOADING
# =============================================================================

def _load_bcca_index() -> str:
    """Load the BCCA index for context."""
    index_path = Path(__file__).parent / "data" / "bcca_optimized_index.txt"
    
    if not index_path.exists():
        alt_paths = [
            Path(__file__).parent / "data" / "bcca_index.txt",
            Path(__file__).parent / "data" / "bcca_full_index.txt",
        ]
        for alt in alt_paths:
            if alt.exists():
                index_path = alt
                break
    
    if not index_path.exists():
        raise FileNotFoundError("BCCA index not found - cannot generate BOQ")
    
    return index_path.read_text(encoding="utf-8")


def _load_ffe_index() -> str:
    """Load the FFE index for fixtures/equipment."""
    index_path = Path(__file__).parent / "data" / "ffe_index.txt"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "FFE INDEX NOT AVAILABLE"


def _load_knowledge_base(filename: str) -> str:
    """Load a knowledge base JSON file from standards folder."""
    import json
    standards_path = Path(__file__).parent.parent.parent / "standards" / filename
    if standards_path.exists():
        try:
            data = json.loads(standards_path.read_text(encoding="utf-8"))
            # Return formatted summary for prompt
            return json.dumps(data, indent=2, ensure_ascii=False)[:30000]  # Truncate if huge
        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
    return f"{filename} NOT AVAILABLE"


def _load_knowledge_graph() -> str:
    """Load the renovation knowledge graph with quantity guidance."""
    kg_path = Path(__file__).parent / "kg_context.yaml"
    if kg_path.exists():
        return kg_path.read_text(encoding='utf-8')
    return "KNOWLEDGE GRAPH NOT AVAILABLE"


def _load_all_knowledge_bases() -> Dict[str, str]:
    """Load all knowledge bases for BOQ context."""
    return {
        "energy": _load_knowledge_base("energy_knowledge.json"),
        "design": _load_knowledge_base("interior_design_knowledge.json"),
        "process": _load_knowledge_base("renovation_process_knowledge.json"),
        "knowledge_graph": _load_knowledge_graph(),
    }


# =============================================================================
# V2 BOQ PROMPT - ADAPTED FROM V1 PHASE 1
# =============================================================================
# The ONLY change: scope comes from Delta Scopes, not PIR comparison.
# ALL the rich reasoning about BCCA, quantities, scheduling is preserved.

V2_BOQ_PROMPT = """
You are a **Senior Quantity Surveyor** creating a complete BOQ (Bill of Quantities) for this Spanish property renovation.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS TASK MATTERS
═══════════════════════════════════════════════════════════════════════════════

A BOQ is the foundation of everything that follows. Every later phase — 
peer review, visualization, buyer communication — depends on the quality 
of your BOQ. If you miss items, the estimate will be incomplete. If 
you choose wrong BCCA codes, prices will be off. If you sequence badly, the 
timeline will be fiction. If your pricing doesn't match the BCCA index, 
the estimate won't be credible.

You're not filling out a form. You're acting as a thinking architect who has 
walked through this property, studied comparable renovations, and is now 
creating a complete bill of quantities that a contractor could actually 
build from.

Every item you create should feel like you're explaining it to a contractor 
who will physically do the work. "I need you to tile this bathroom floor" 
becomes a conversation about which tiles, what area, what preparation is 
needed underneath, and when in the project this happens.

The quality of your thinking here determines whether the final estimate is 
credible or whether a professional will immediately spot gaps and 
inconsistencies. So think deeply about each decision.

═══════════════════════════════════════════════════════════════════════════════
YOUR CONTEXT AND HOW TO READ IT
═══════════════════════════════════════════════════════════════════════════════

**THE SCOPE HAS ALREADY BEEN DETERMINED**

In V2, the scope comes from Delta Scope Analysis. A previous phase compared 
this Target property against a Reference comparable (one that actually sold) 
and identified exactly what work is needed, organized by 6 dimensions:

1. Shell & Preparation (Masonry/Plaster)
2. Apertures & Enclosure (Joinery/Glazing)
3. Systems & Services (MEP)
4. Surface Finishes (Decor)
5. Fixed Joinery & Equipment (Fittings)
6. Details & Fittings (Hardware)

Your job is NOT to determine scope — that's done. Your job is to:
1. Take each scope item and find the correct BCCA code
2. Verify/refine the quantity
3. Apply the BCCA price
4. Sequence the work logically
5. Calculate totals

**TARGET PIR (Property Intelligence Report)**

WHY YOU HAVE THIS: This describes the property AS IT EXISTS TODAY. Use it to 
understand room dimensions, conditions, and context for quantity calculations.

HOW TO READ IT: As you read each room's description, look for:
- Room dimensions (length, width, wall heights)
- Specific conditions that affect work scope
- Details that help verify delta scope quantities

**REFERENCE COMPARABLE**

WHY YOU HAVE THIS: This is the comparable that sold and represents the target 
finish level. The delta scopes describe what needs to change to match it.

**CANONICAL ROOM IDS**

WHY YOU HAVE THIS: This is the exact list of rooms. Every room_id in the 
delta scopes must appear in your BOQ. Don't invent room names.

**BCCA INDEX**

WHY YOU HAVE THIS: This is the Spanish construction price book. Every 
professional contractor prices from this. When you need to specify a work 
item, you search this index to find the matching entry. Using real BCCA 
codes makes your estimate traceable and credible — a contractor can verify 
your prices against the official book.

THE BCCA INDEX FORMAT: CODE|UNIT|PRICE|DESC_100|LABOR_HOURS|BREAKDOWN
- CODE: The BCCA item code (e.g., 10AAA00001)
- UNIT: The unit of measurement (m2, ud, ml, etc.)
- PRICE: The composite unit price in EUR (THIS IS WHAT YOU USE FOR unit_price)
- DESC_100: Short description (100 chars)
- LABOR_HOURS: Hours of labor per unit (USE THIS × quantity for labor_hours)
- BREAKDOWN: Sub-components and their costs

HOW TO PRICE EACH ITEM:
1. Find the BCCA code that matches your scope item
2. Read the PRICE column — this is your unit_price
3. Read the LABOR_HOURS column — multiply by quantity for total labor_hours
4. Calculate: line_total = unit_price × quantity
5. For FFE items: add ffe_price from FFE index + ffe_install_price from BCCA

HOW TO READ IT: As you search the index, ask yourself:
- Am I finding an item that matches the QUALITY LEVEL for this strategy?
- Is this the right unit (m², ud, ml)?
- Does the description match what I actually need done?
- If there's no exact match, what's the closest equivalent?

WHAT TO THINK DEEPLY ABOUT: BCCA prices are COMPOSITE. When you see a tiling 
price, that includes the labor to install, the adhesive, the grout — 
everything. You don't need separate "materials" and "labor" items. 
Understanding this prevents double-counting.

**FFE INDEX**

WHY YOU HAVE THIS: For furniture, fixtures, and equipment (lamps, faucets, 
appliances), use this index. The BCCA covers construction work; the FFE 
index covers the items themselves.

HOW TO READ IT: When you specify an FFE item, ask yourself:
- What tier matches the strategy? (Budget/Mid/High/Luxury)
- What BCCA code covers the installation labor?
- Have I captured both the item AND its installation?

WHAT TO THINK DEEPLY ABOUT: A pendant lamp isn't just the lamp — it's also 
the electrical point, the ceiling hook, the wiring connection. The FFE 
index gives you the lamp; the BCCA gives you the installation. You need 
both. Every FFE item should have a paired BCCA installation code.

═══════════════════════════════════════════════════════════════════════════════
HOW TO THINK ABOUT BCCA CODE SELECTION
═══════════════════════════════════════════════════════════════════════════════

WHY THIS MATTERS: The BCCA code you select determines the price. A wrong 
code means a wrong price, which undermines the entire estimate's credibility. 
The BCCA has over twelve thousand items — finding the right one requires 
semantic matching, not exact string matching.

When you need a BCCA code, think through:

1. **What work am I describing?** Not just "tile the floor" but "install 
   porcelain tiles of this specific type and size on this specific substrate."

2. **What Spanish terms describe this?** The BCCA is in Spanish. "Alicatado" 
   for wall tiling, "solado" or "pavimento" for floor. "Demolición" for 
   removal. Know the vocabulary.

3. **What quality tier?** There are budget, standard, and premium versions 
   of most items. Match the strategy level (conservative vs top_of_market).

4. **What does the BCCA description actually include?** Read it carefully. 
   Does it include adhesive? Grout? Cutting? Cleanup? Most do — don't 
   double-count by adding separate items for things already included.

If you genuinely can't find a match, find the closest equivalent and note 
the adaptation in your description. Never leave bcca_code empty.

═══════════════════════════════════════════════════════════════════════════════
HOW TO THINK ABOUT QUANTITIES
═══════════════════════════════════════════════════════════════════════════════

WHY THIS MATTERS: Quantity estimation is where credibility is built or lost. 
A contractor reading your BOQ should be able to verify your numbers. 
Implausible quantities — either too high or too low — signal amateur work.

Every quantity needs a formula showing how you calculated it. This isn't 
bureaucracy — it's how professionals work.

**USING ROOM DIMENSIONS FROM THE PIR:**

The TARGET PIR includes estimated room dimensions (if available). When 
describing rooms, it references specific walls by their characteristics 
AND their dimensions. Use these dimensions directly in your quantity formulas.

If specific dimensions aren't provided for a room, estimate conservatively 
based on the total room m² and typical proportions.

**QUANTITY CALCULATION PATTERNS:**

For floor areas: length times width. But think about the actual space — 
is it rectangular or irregular? Are there built-in elements reducing the area?

For wall areas: perimeter times height, minus openings. Think about what 
height — full height for paint, typically around two meters for tiles.

For linear items: measure the actual runs. Skirting boards follow the 
perimeter minus doorways. Cable runs follow the actual routing.

For count items: actually count them. Light points per room. Sockets per room.

**SHOWING YOUR WORK:**

Your quantity_formula field should show the actual calculation:
- "6.3m × 4.0m = 25.2m² floor" (using PIR dimensions)
- "perimeter 20.6m × 2.7m height = 55.6m² wall area"
- "~4.5m × 3.5m = 15.75m² (estimated from 16m² room)"

When uncertain, estimate conservatively and note the uncertainty.

═══════════════════════════════════════════════════════════════════════════════
HOW TO THINK ABOUT SCHEDULING
═══════════════════════════════════════════════════════════════════════════════

WHY THIS MATTERS: An unrealistic schedule undermines trust. The schedule must 
respect physical reality.

Think about physical dependencies:
- What must finish before this can start?
- What chemical or physical processes need time?
- What inspections or sign-offs gate progress?

Think about resource logic:
- Can this trade work in this space at this time?
- Does material delivery timing align with installation timing?

The renovation flows in waves: demolition clears the space, rough-in MEP 
claims it, finishes cover everything, then second-fix completes the details.

Don't be rigid about week numbers — every project is different. But do be 
rigorous about dependencies. Waterproofing needs curing time before tiling.

═══════════════════════════════════════════════════════════════════════════════
WHAT TO DOUBT AND QUESTION
═══════════════════════════════════════════════════════════════════════════════

Before finishing, challenge yourself:

- "Have I actually processed every room in the delta scopes?"
- "Does my BOQ match the strategy level, not exceed it?"
- "Have I included the preparation work, not just the finish work?"
- "Have I included site logistics — protection, permits, cleanup?"
- "Are my BCCA codes real codes from the index, or did I make them up?"
- "Do my quantities have actual formulas, or just plausible numbers?"
- "Does my sequencing reflect real construction flow?"
- "Would a contractor reading this be able to build from it?"

═══════════════════════════════════════════════════════════════════════════════
WHAT TO INCLUDE FOR SITE LOGISTICS
═══════════════════════════════════════════════════════════════════════════════

Room ID "general" captures work that isn't room-specific. Don't forget:

- Site setup: floor protection, dust barriers, temporary services
- Waste management: skip hire, debris removal
- Permits: building license applications, required certifications
- Certifications: boletín eléctrico (mandatory for ANY electrical work), 
  certificado gas (mandatory for ANY gas work)
- Cleanup: interim cleaning, final deep clean

═══════════════════════════════════════════════════════════════════════════════
THE DELTA SCOPES (YOUR INPUT — SCOPE IS ALREADY DETERMINED)
═══════════════════════════════════════════════════════════════════════════════

Strategy: {strategy_name}
Reference Comparable: #{ref_comp_id}
Transformation Philosophy: {transformation_philosophy}

The following scope items have been identified by the Delta Scope Analysis.

██████████████████████████████████████████████████████████████████████████████
██  CRITICAL: BREAK DOWN EVERY SCOPE ITEM INTO ALL REQUIRED WORK            ██
██████████████████████████████████████████████████████████████████████████████

Each scope item describes WHAT needs to happen, but a BOQ needs to capture 
ALL THE WORK to make it happen. For example:

Scope item: "Install engineered oak flooring, 22m²"
BOQ breakdown:
  1. Demolition: Remove existing floor covering (m²)
  2. Prep: Apply self-leveling compound if needed (m²)
  3. Material: Supply acoustic underlay (m²)
  4. Install: Lay engineered oak flooring (m²)
  5. Finishing: Install matching skirting (ml)
  6. Finishing: Install door thresholds (ud)

Scope item: "Replace bathroom sanitaryware"
BOQ breakdown:
  1. Demolition: Remove existing toilet (ud)
  2. Demolition: Remove existing sink/vanity (ud)
  3. Plumbing: Adjust water supply points if needed (ud)
  4. Supply: Wall-hung toilet (ud)
  5. Install: Wall-hung toilet (ud)
  6. Supply: Vanity unit with basin (ud)
  7. Install: Vanity unit with basin (ud)
  8. Supply: Mixer tap (ud)
  9. Install: Mixer tap (ud)

DO NOT consolidate. DO NOT skip minor items. Every scope item should expand 
into its logical sub-tasks. If the scope has 170 items, the BOQ might have 
300-500 line items because each scope item breaks into multiple work steps.

{delta_scope_items}

═══════════════════════════════════════════════════════════════════════════════
TARGET PIR (For room dimensions and context)
═══════════════════════════════════════════════════════════════════════════════

{target_pir_summary}

═══════════════════════════════════════════════════════════════════════════════
BCCA INDEX
═══════════════════════════════════════════════════════════════════════════════

Format: CODE|UNIT|PRICE|DESC_100|LABOR_HOURS|BREAKDOWN

{bcca_index}

═══════════════════════════════════════════════════════════════════════════════
FFE INDEX (For fixtures, furniture, equipment)
═══════════════════════════════════════════════════════════════════════════════

{ffe_index}

═══════════════════════════════════════════════════════════════════════════════
ENERGY KNOWLEDGE (For insulation, efficiency, climate requirements)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: Spanish energy regulations (CTE) require specific insulation 
values and efficiency standards. Use this to ensure your BOQ includes necessary 
energy-related work: window thermal breaks, wall insulation, efficient HVAC sizing.

{energy_knowledge}

═══════════════════════════════════════════════════════════════════════════════
DESIGN KNOWLEDGE (For material quality, style matching)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: Different strategies require different quality tiers. Use this 
to match material specifications to the strategy level (conservative vs premium).

{design_knowledge}

═══════════════════════════════════════════════════════════════════════════════
RENOVATION PROCESS KNOWLEDGE (For sequencing, dependencies)
═══════════════════════════════════════════════════════════════════════════════

WHY YOU HAVE THIS: Work must be sequenced correctly. Demolition before installation.
First fix before finishes. Use this to set proper phase_week and depends_on.

{process_knowledge}

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

Return valid JSON with:
- items: Your complete list of work items, EACH WITH PRICING:
  - item_id, room_id, dimension, name, description
  - bcca_code, bcca_description, unit, quantity, quantity_formula
  - unit_price (from BCCA PRICE column), line_total (quantity × unit_price)
  - labor_hours (from BCCA LABOR_HOURS × quantity)
  - For FFE items: ffe_code, ffe_price, ffe_install_bcca, ffe_install_price
  - phase_week, depends_on
- rooms_coverage: Item count per room (verify you covered every room)
- dimension_totals: Sum per dimension
- total_pem: Sum of ALL line_total values (Presupuesto de Ejecución Material)
- iva_21_percent: 21% of total_pem
- total_with_iva: total_pem + iva_21_percent
- total_labor_hours: Sum of ALL labor_hours values
- total_weeks: Your estimate of project duration
- critical_path: The item sequence that determines total duration
- reasoning_notes: Your thinking about key decisions (in Spanish)
- total_items: Count of items

CRITICAL REQUIREMENTS:
1. BREAK DOWN each scope item into ALL required work steps (demo, prep, supply, install, finish)
2. Every BOQ item MUST have unit_price and line_total calculated from BCCA index
3. The total_pem MUST equal the sum of all line_total values
4. If you can't find a BCCA code, use the closest match and note it
5. DO NOT skip items. DO NOT consolidate. If scope has 170 items, BOQ should have 300-500+
6. All text content (names, descriptions, notes) in Spanish
"""


# =============================================================================
# BOQ AGGREGATION FROM DB (Queue-based pipeline)
# =============================================================================

async def aggregate_boq_from_db(
    listing_id: int,
    strategy_name: str,
    db: Any,
) -> Dict[str, Any]:
    """
    Aggregate BOQ totals from boq_line_items table.
    This is used by queue-based pipelines after per-scope LLM jobs and write jobs complete.
    """
    if not db or listing_id is None:
        raise ValueError("aggregate_boq_from_db requires db and listing_id")

    items = await db.get_boq_line_items(listing_id, strategy_name)
    if not items:
        raise RuntimeError(f"BOQ aggregation failed: no line items for {strategy_name} (listing {listing_id})")

    dimension_totals: Dict[str, float] = {}
    total_labor_hours = 0.0

    for item in items:
        dimension = item.get("dimension", "unknown")
        line_total = float(item.get("line_total") or 0)
        labor_hours = float(item.get("labor_hours") or 0)
        dimension_totals[dimension] = dimension_totals.get(dimension, 0.0) + line_total
        total_labor_hours += labor_hours

    total_pem = sum(dimension_totals.values())
    iva_amount = total_pem * 0.21
    total_with_iva = total_pem + iva_amount

    rooms_coverage: Dict[str, int] = {}
    for item in items:
        room = item.get("room_name") or item.get("room_id") or "unknown"
        rooms_coverage[room] = rooms_coverage.get(room, 0) + 1

    estimated_weeks = max(4, int(total_labor_hours / 40))

    return {
        "strategy_name": strategy_name,
        "line_items": items,
        "dimension_totals": {k: round(v, 2) for k, v in dimension_totals.items()},
        "total_pem": round(total_pem, 2),
        "iva_amount": round(iva_amount, 2),
        "grand_total_with_iva": round(total_with_iva, 2),
        "total_labor_hours": round(total_labor_hours, 2),
        "estimated_weeks": estimated_weeks,
        "rooms_coverage": rooms_coverage,
        "source": "boq_line_items",
    }


# =============================================================================
# HELPER: FORMAT DELTA SCOPES FOR PROMPT
# =============================================================================

def _format_delta_scopes_for_prompt(strategy_package: Dict[str, Any]) -> str:
    """Format delta scopes into readable prompt text.
    
    NEW V2 STRUCTURE (with Specification Strategy):
    dimension_deltas:
      {dimension_name}:
        room_scopes: [
          {room_name, specification_strategy, cost_components: [{action, element, description, estimated_quantity}]}
        ]
    """
    lines = []
    
    dimension_deltas = strategy_package.get("dimension_deltas", {})
    
    if not dimension_deltas:
        logger.warning("No dimension_deltas found in strategy_package!")
        return "NO SCOPE ITEMS FOUND"
    
    total_items = 0
    
    for dimension_name, dimension_data in dimension_deltas.items():
        room_scopes = dimension_data.get("room_scopes", [])
        
        if not room_scopes:
            continue
        
        lines.append(f"\n{'='*70}")
        lines.append(f"DIMENSION: {dimension_name.upper().replace('_', ' ')}")
        lines.append(f"{'='*70}")
        
        for room_scope in room_scopes:
            room_name = room_scope.get("room_name", "Unknown Room")
            spec_strategy = room_scope.get("specification_strategy", "")
            cost_components = room_scope.get("cost_components", [])
            
            if not cost_components:
                continue
            
            lines.append(f"\n  ROOM: [{room_name}]")
            lines.append(f"  ─────────────────────────────────────────")
            
            # Include specification strategy as architect's intent
            if spec_strategy:
                lines.append(f"\n  ARCHITECT'S SPECIFICATION:")
                lines.append(f"  {spec_strategy}")
            
            lines.append(f"\n  SCOPE ITEMS ({len(cost_components)} items):")
            
            for i, item in enumerate(cost_components, 1):
                action = item.get("action", "?")
                element = item.get("element", "?")
                description = item.get("description", "?")
                qty = item.get("estimated_quantity", "TBD")
                
                lines.append(f"\n    {i}. [{action.upper()}] {element}")
                lines.append(f"       Description: {description}")
                lines.append(f"       Estimated quantity: {qty}")
                total_items += 1
    
    lines.insert(0, f"TOTAL SCOPE ITEMS TO PRICE: {total_items}")
    
    logger.info(f"  Formatted {total_items} scope items for BOQ prompt")
    
    return "\n".join(lines)


def _format_target_pir_summary(target_pir: Dict[str, Any]) -> str:
    """Format target PIR into a summary with room dimensions."""
    lines = []
    
    lines.append(f"Property: {target_pir.get('property_summary', 'N/A')}")
    lines.append(f"Condition: {target_pir.get('overall_condition', 'N/A')}")
    lines.append("")
    
    for room in target_pir.get("rooms", []):
        room_id = room.get("room_id", "?")
        room_name = room.get("room_name", room_id)
        
        lines.append(f"[{room_id}] {room_name}")
        
        # Include dimension narratives for context
        dims = room.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                narrative = dim_data.get("narrative", "")
                if narrative:
                    lines.append(f"  {dim_name}: {narrative[:200]}...")
        
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# DIMENSION LIST
# =============================================================================

DIMENSIONS = [
    "shell_preparation",
    "apertures_enclosure", 
    "systems_services",
    "surface_finishes",
    "fixed_joinery_equipment",
    "details_fittings",
]

DIMENSION_DISPLAY_NAMES = {
    "shell_preparation": "Shell & Preparation (Masonry/Plaster)",
    "apertures_enclosure": "Apertures & Enclosure (Joinery/Glazing)",
    "systems_services": "Systems & Services (MEP)",
    "surface_finishes": "Surface Finishes (Decor)",
    "fixed_joinery_equipment": "Fixed Joinery & Equipment (Fittings)",
    "details_fittings": "Details & Fittings (Hardware)",
}


# =============================================================================
# DIMENSION-SPECIFIC PROMPT (SMALLER, FOCUSED)
# =============================================================================

V2_BOQ_DIMENSION_PROMPT = """
You are a **Senior Quantity Surveyor** creating BOQ line items for the {dimension_display_name} dimension.

═══════════════════════════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════════════════════════

Strategy: {strategy_name}
Reference Comparable: #{ref_comp_id}
Dimension: {dimension_display_name}

{system_context}

═══════════════════════════════════════════════════════════════════════════════
SCOPE ITEMS FOR THIS DIMENSION
═══════════════════════════════════════════════════════════════════════════════

{dimension_scope_items}

═══════════════════════════════════════════════════════════════════════════════
BCCA INDEX (Search for matching codes)
═══════════════════════════════════════════════════════════════════════════════

Format: CODE|UNIT|PRICE|DESC_100|LABOR_HOURS|BREAKDOWN

{bcca_index}

═══════════════════════════════════════════════════════════════════════════════
FFE INDEX (For fixtures/equipment in this dimension)
═══════════════════════════════════════════════════════════════════════════════

{ffe_index}

═══════════════════════════════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

For EACH scope item above, BREAK IT DOWN into ALL required work steps:
- Demolition/removal of existing
- Preparation work
- Supply of materials
- Installation labor
- Finishing touches

Find the BCCA code for each work step. Calculate:
- unit_price from BCCA PRICE column
- line_total = unit_price × quantity
- labor_hours from BCCA LABOR_HOURS × quantity

CRITICAL: All numeric values (prices, totals, hours) must be ROUNDED TO 2 DECIMAL PLACES.
Example: 15.89, NOT 15.890000000001. Clean numbers only!

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

Return JSON with:
- dimension: "{dimension_name}"
- line_items: Array of BOQ items for this dimension only
  Each item: item_id, room_id, description, bcca_code, quantity, unit, unit_price, line_total, labor_hours
- dimension_total: Sum of all line_total values
- dimension_labor_hours: Sum of all labor_hours
- item_count: Number of items

All descriptions in Spanish.
"""


# =============================================================================
# CACHED CONTEXT (Built once, reused for all 6 dimensions)
# =============================================================================

class BOQContextCache:
    """Cache for expensive context that's reused across dimension calls."""
    
    _instance = None
    
    def __init__(self):
        self.bcca_index = None
        self.ffe_index = None
        self.knowledge_bases = None
        self.system_context = None
        self._loaded = False
    
    @classmethod
    def get_instance(cls) -> "BOQContextCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load(self) -> None:
        """Load all context once."""
        if self._loaded:
            return
        
        logger.info("  📦 Loading BOQ context cache (one-time)...")
        
        self.bcca_index = _load_bcca_index()[:80000]
        self.ffe_index = _load_ffe_index()[:20000]
        self.knowledge_bases = _load_all_knowledge_bases()
        
        # Build system context (shared across all dimension calls)
        self.system_context = f"""
ENERGY KNOWLEDGE (for insulation, efficiency requirements):
{self.knowledge_bases['energy'][:10000]}

DESIGN KNOWLEDGE (for material quality matching):
{self.knowledge_bases['design'][:10000]}

PROCESS KNOWLEDGE (for sequencing, dependencies):
{self.knowledge_bases['process'][:10000]}

═══════════════════════════════════════════════════════════════════════════════
RENOVATION KNOWLEDGE GRAPH (683 Tasks with Quantity Guidance)
═══════════════════════════════════════════════════════════════════════════════

This is your MASTER REFERENCE for renovation tasks. Each task includes:
- QUANTITY GUIDANCE: How to measure (area_m2, count, linear_m), scope (per_room, 
  per_opening), reasoning factors, industry rules, min/max constraints
- DEPENDENCIES: REQUIRES (prerequisites) and TRIGGERS (what follows)
- BCCA chapter mappings and trade assignments

When determining QUANTITIES, CHECK THIS GRAPH for the measurement approach:
- type: area_m2, count, linear_m, volume_m3
- scope: per_room, per_opening, per_unit, per_circuit
- rules: Industry measurement standards (e.g., "no deductions for voids <1m²")
- constraints: min/max values, buffers

{self.knowledge_bases['knowledge_graph'][:200000]}
"""
        
        self._loaded = True
        logger.info(f"    BCCA: {len(self.bcca_index):,} chars")
        logger.info(f"    FFE: {len(self.ffe_index):,} chars")
        logger.info(f"    Knowledge Graph: {len(self.knowledge_bases.get('knowledge_graph', '')):,} chars")
        logger.info(f"    System context: {len(self.system_context):,} chars")


# =============================================================================
# DIMENSION BOQ SCHEMA (Smaller than full BOQ)
# =============================================================================

V2_BOQ_DIMENSION_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "room_id": {"type": "string"},
                    "description": {"type": "string"},
                    "bcca_code": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"},
                    "unit_price": {"type": "number"},
                    "line_total": {"type": "number"},
                    "labor_hours": {"type": "number"},
                },
                "required": ["item_id", "room_id", "description", "quantity", "unit"]
            }
        },
        "dimension_total": {"type": "number"},
        "dimension_labor_hours": {"type": "number"},
        "item_count": {"type": "integer"},
    },
    "required": ["dimension", "line_items"]
}


# =============================================================================
# HELPER: FORMAT SCOPE FOR SINGLE DIMENSION
# =============================================================================

def _format_dimension_scope(strategy_package: Dict[str, Any], dimension: str) -> str:
    """Format scope items for a single dimension."""
    lines = []
    
    dimension_deltas = strategy_package.get("dimension_deltas", {})
    dimension_data = dimension_deltas.get(dimension, {})
    room_scopes = dimension_data.get("room_scopes", [])
    
    if not room_scopes:
        return "NO SCOPE ITEMS FOR THIS DIMENSION"
    
    total_items = 0
    
    for room_scope in room_scopes:
        room_name = room_scope.get("room_name", "Unknown")
        spec_strategy = room_scope.get("specification_strategy", "")
        cost_components = room_scope.get("cost_components", [])
        
        if not cost_components:
            continue
        
        lines.append(f"\nROOM: [{room_name}]")
        if spec_strategy:
            lines.append(f"Architect's spec: {spec_strategy[:300]}...")
        
        for i, item in enumerate(cost_components, 1):
            action = item.get("action", "?")
            element = item.get("element", "?")
            description = item.get("description", "?")
            qty = item.get("estimated_quantity", "TBD")
            
            lines.append(f"  {i}. [{action.upper()}] {element}: {description} (Qty: {qty})")
            total_items += 1
    
    lines.insert(0, f"TOTAL SCOPE ITEMS: {total_items}\n")
    
    return "\n".join(lines)


# =============================================================================
# ROOM-LEVEL BOQ PROMPT (SMALL, FAST)
# =============================================================================

# =============================================================================
# OPTIMIZED BOQ: LLM picks codes + quantities, CODE does pricing
# =============================================================================
# This saves massive context by:
# 1. NOT asking LLM to calculate prices (it often hallucinates)
# 2. NOT asking LLM to output price/total fields
# 3. Code looks up prices from BCCA index and calculates totals
# =============================================================================

V2_BOQ_ROOM_PROMPT = """
You are a Quantity Surveyor. Pick BCCA codes and quantities for ONE ROOM.

Room: {room_name}
Dimension: {dimension_display_name}

ROOM DIMENSIONS (use these for accurate quantities!):
{room_dimensions}

ARCHITECT'S SPECIFICATION:
{spec_strategy}

SCOPE ITEMS:
{room_scope_items}

BCCA INDEX (format: CODE|UNIT|PRICE|DESC):
{bcca_index}

CRITICAL RULES:
1. ONLY use codes that EXACTLY appear in the BCCA INDEX above
2. DO NOT invent codes - copy them EXACTLY as shown
3. Use the ROOM DIMENSIONS above to calculate accurate quantities
4. Match quality level to the Architect's Specification
5. ROUND ALL QUANTITIES to WHOLE NUMBERS (this is an estimate, not a survey)

For EACH scope item:
1. Pick an EXISTING code from the index
2. Calculate quantity using the room dimensions provided
3. ROUND to whole numbers (e.g., 49.1m² → 49m², 3.7 windows → 4)
4. SHOW YOUR WORKING in qty_reasoning - reference the dimensions!
   - Example: "window_wall 4m × 2.5m = 10m² wall area → 10m²"
   - Example: "2 windows on window_wall → 2ud"
"""

V2_BOQ_ROOM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scope_item": {"type": "string"},
                    "bcca_code": {"type": "string"},
                    "qty": {"type": "number"},
                    "unit": {"type": "string"},
                    "qty_reasoning": {"type": "string"},
                },
                "required": ["scope_item", "bcca_code", "qty", "qty_reasoning"]
            }
        }
    },
    "required": ["items"]
}


# =============================================================================
# PER-SCOPE-ITEM BOQ PROMPT (Higher quality, more expensive)
# =============================================================================

V2_BOQ_SCOPE_ITEM_PROMPT = """
You are a senior Quantity Surveyor. Price ONE SPECIFIC scope item.

ROOM: {room_name}
DIMENSION: {dimension_display_name}

ROOM DIMENSIONS (use these for accurate quantities!):
{room_dimensions}

ARCHITECT'S SPECIFICATION FOR THIS ROOM:
{spec_strategy}

THE SCOPE ITEM TO PRICE:
Action: {scope_action}
Element: {scope_element}
Description: {scope_description}
Estimated Quantity (rough guide): {scope_estimated_qty}

YOUR TASK:
1. Find the EXACT BCCA code(s) from the index below that matches this work
2. Calculate the ACCURATE quantity using the room dimensions above
3. SHOW YOUR WORKING in qty_reasoning (reference dimensions!)
4. One scope item may need multiple BCCA codes (e.g., demolition + new work)

BCCA INDEX (format: CODE|UNIT|PRICE|DESC):
{bcca_index}

RENOVATION KNOWLEDGE GRAPH (Task definitions, quantity guidance, dependencies):
{knowledge_graph}

CRITICAL RULES:
1. ONLY use codes that EXACTLY appear in the BCCA INDEX above - copy them verbatim
2. DO NOT invent or modify codes
3. Use ROOM DIMENSIONS to calculate accurate quantities
4. Check the Knowledge Graph for quantity guidance on this task type
5. ROUND quantities to whole numbers (e.g., 49.1m² → 49m²)
6. SHOW YOUR WORKING in qty_reasoning

Think step by step:
1. What type of work is this? (demolition, installation, supply, etc.)
2. What are the physical dimensions involved?
3. What BCCA code(s) cover this work?
4. What quantity makes sense given the room dimensions?
"""

V2_BOQ_SCOPE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "BOQ line items for this scope item (may be 1 or more)",
            "items": {
                "type": "object",
                "properties": {
                    "scope_item": {"type": "string", "description": "Original scope item element"},
                    "bcca_code": {"type": "string", "description": "Exact BCCA code from index"},
                    "qty": {"type": "number", "description": "Calculated quantity (whole numbers)"},
                    "unit": {"type": "string", "description": "Unit from BCCA (m², ud, ml, etc.)"},
                    "qty_reasoning": {"type": "string", "description": "Show your working with dimensions"},
                },
                "required": ["scope_item", "bcca_code", "qty", "unit", "qty_reasoning"]
            }
        }
    },
    "required": ["items"]
}


# =============================================================================
# BCCA PRICE LOOKUP
# =============================================================================

def _build_bcca_lookup(bcca_raw: str) -> Dict[str, Dict[str, Any]]:
    """
    Build a code → {desc, unit, price, labor_hours} lookup from BCCA index.
    
    Format: CODE|UNIT|PRICE|DESC|LABOR_HOURS|BREAKDOWN
    """
    lookup = {}
    for line in bcca_raw.split("\n"):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.strip().split("|")
        if len(parts) >= 4:
            code = parts[0].strip()
            if code and not code.startswith("#"):
                try:
                    lookup[code] = {
                        "unit": parts[1].strip(),
                        "price": float(parts[2].strip()),
                        "desc": parts[3].strip() if len(parts) > 3 else "",
                        "labor_hours": float(parts[4].strip()) if len(parts) > 4 else 0,
                    }
                except (ValueError, IndexError):
                    pass
    return lookup


# =============================================================================
# GENERATE BOQ FOR SINGLE SCOPE ITEM (Per-item mode - higher quality)
# =============================================================================

async def _generate_boq_for_scope_item(
    scope_item: Dict[str, Any],
    room_name: str,
    dimension: str,
    strategy_name: str,
    spec_strategy: str,
    context: BOQContextCache,
    room_dimensions: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate BOQ for a SINGLE scope item using Gemini 3 Flash.
    
    This is the per-scope-item mode for better quantity reasoning.
    Returns a list of line items (one scope item may map to multiple BCCA codes).
    """
    raise RuntimeError(
        "DISABLED: per-scope-item Gemini BOQ generation is intentionally removed to prevent runaway costs. "
        "Use v3 BOQ (deterministic + embeddings-only) or a batched/room-level BOQ flow."
    )
    
    # Format room dimensions
    dim_text = "No detailed dimensions available - use estimated_quantity from scope item."
    if room_dimensions:
        dim_lines = [
            f"Floor area: {room_dimensions.get('estimated_m2', '?')} m²",
            f"Wall area (total): {room_dimensions.get('wall_area_m2', '?')} m²",
            f"Perimeter: {room_dimensions.get('perimeter_m', '?')} m",
            f"Ceiling height: {room_dimensions.get('estimated_height_m', '?')} m",
        ]
        dims = room_dimensions.get('estimated_dimensions', {})
        if dims:
            dim_lines.append(f"Room size: {dims.get('width_m', '?')}m × {dims.get('length_m', '?')}m")
        
        walls = room_dimensions.get('wall_descriptions', [])
        if walls:
            dim_lines.append("Walls:")
            for wall in walls:
                features = wall.get('features', [])
                feat_str = f" [{', '.join(features)}]" if features else ""
                dim_lines.append(f"  - {wall.get('name_es', wall.get('name', '?'))}: {wall.get('length_m', '?')}m{feat_str}")
        
        dim_text = "\n".join(dim_lines)
    
    # Build prompt for single scope item
    prompt = V2_BOQ_SCOPE_ITEM_PROMPT.format(
        room_name=room_name,
        dimension_display_name=DIMENSION_DISPLAY_NAMES.get(dimension, dimension),
        room_dimensions=dim_text,
        spec_strategy=spec_strategy[:500] if spec_strategy else "Standard quality finish",
        scope_action=scope_item.get("action", "?"),
        scope_element=scope_item.get("element", "?"),
        scope_description=scope_item.get("description", "?"),
        scope_estimated_qty=scope_item.get("estimated_quantity", "TBD"),
        bcca_index=context.bcca_index[:60000],  # 60K for better code coverage
        knowledge_graph=context.knowledge_graph[:100000] if hasattr(context, 'knowledge_graph') else "",
    )
    
    response = await call_gemini(
        prompt=prompt,
        model="flash",  # Gemini 3 Flash for quality
        temperature=0.2,  # Lower temp for more consistent pricing
        max_tokens=20000,  # Allow full reasoning + multiple codes
        response_schema=V2_BOQ_SCOPE_ITEM_SCHEMA,
        use_spanish=True,
    )
    
    if not response.success:
        raise RuntimeError(
            f"[BOQ scope item FAILED] {scope_item.get('element', '?')}: {response.error}"
        )
    
    try:
        result = json.loads(response.text)
        raw_items = result.get("items", [])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"[BOQ scope item INVALID JSON] {scope_item.get('element', '?')}"
        ) from exc
    
    # Build BCCA lookup (cached in context)
    if not hasattr(context, '_bcca_lookup'):
        context._bcca_lookup = _build_bcca_lookup(context.bcca_index)
    
    # Code does pricing lookup
    line_items = []
    for item in raw_items:
        code = item.get("bcca_code", "")
        qty = item.get("qty", 0)
        qty_reasoning = item.get("qty_reasoning", "")
        
        bcca_data = context._bcca_lookup.get(code, {})
        unit_price = bcca_data.get("price", 0)
        labor_per_unit = bcca_data.get("labor_hours", 0)
        unit = item.get("unit") or bcca_data.get("unit", "ud")
        desc = bcca_data.get("desc", scope_item.get("element", "Unknown"))
        
        line_total = round(qty * unit_price, 2)
        labor_hours = round(qty * labor_per_unit, 2)
        
        line_items.append({
            "scope_item": item.get("scope_item", scope_item.get("element", "")),
            "scope_item_element": scope_item.get("element", ""),
            "bcca_code": code,
            "description": desc,
            "quantity": qty,
            "unit": unit,
            "quantity_reasoning": qty_reasoning,
            "unit_price": unit_price,
            "line_total": line_total,
            "labor_hours": labor_hours,
        })
    
    if not line_items:
        raise RuntimeError(
            f"[BOQ scope item ZERO ITEMS] {scope_item.get('element', '?')}"
        )
    
    return line_items


# =============================================================================
# GENERATE BOQ FOR SINGLE ROOM (LLM picks codes, CODE prices)
# =============================================================================

async def _generate_boq_for_room(
    room_name: str,
    room_scope: Dict[str, Any],
    dimension: str,
    strategy_name: str,
    context: BOQContextCache,
    room_dimensions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate BOQ for a single room.
    
    OPTIMIZED: LLM only picks BCCA codes + quantities.
    Code does price lookup and total calculation.
    Room dimensions from smart_m2 are passed for accurate quantity calculation.
    """
    
    cost_components = room_scope.get("cost_components", [])
    if not cost_components:
        return {"room": room_name, "line_items": [], "room_total": 0}
    
    # Get the specification strategy (Architect's Note) - critical for quality level
    spec_strategy = room_scope.get("specification_strategy", "Standard quality finish")
    
    # Format room dimensions from smart_m2 (if available)
    dim_text = "No detailed dimensions available - use estimated_quantity from scope items."
    if room_dimensions:
        dim_lines = [
            f"Floor area: {room_dimensions.get('estimated_m2', '?')} m²",
            f"Wall area (total): {room_dimensions.get('wall_area_m2', '?')} m²",
            f"Perimeter: {room_dimensions.get('perimeter_m', '?')} m",
            f"Ceiling height: {room_dimensions.get('estimated_height_m', '?')} m",
        ]
        dims = room_dimensions.get('estimated_dimensions', {})
        if dims:
            dim_lines.append(f"Room size: {dims.get('width_m', '?')}m × {dims.get('length_m', '?')}m")
        
        # Add wall descriptions with features (windows, doors, etc.)
        walls = room_dimensions.get('wall_descriptions', [])
        if walls:
            dim_lines.append("Walls:")
            for wall in walls:
                features = wall.get('features', [])
                feat_str = f" [{', '.join(features)}]" if features else ""
                dim_lines.append(f"  - {wall.get('name_es', wall.get('name', '?'))}: {wall.get('length_m', '?')}m{feat_str}")
        
        dim_text = "\n".join(dim_lines)
    
    # Format scope items
    scope_lines = []
    for item in cost_components:
        action = item.get("action", "")
        element = item.get("element", "")
        desc = item.get("description", "")
        qty = item.get("estimated_quantity", "?")
        scope_lines.append(f"- [{action}] {element}: {desc} (Est: {qty})")
    
    room_scope_text = "\n".join(scope_lines)
    
    # Compact prompt with dimensions for accurate quantities
    prompt = V2_BOQ_ROOM_PROMPT.format(
        room_name=room_name,
        dimension_display_name=DIMENSION_DISPLAY_NAMES.get(dimension, dimension),
        room_dimensions=dim_text,
        spec_strategy=spec_strategy,
        room_scope_items=room_scope_text,
        bcca_index=context.bcca_index[:50000],  # 50K to cover most codes
    )
    
    logger.info(f"      [{room_name}] {len(cost_components)} scope items")
    
    response = await call_gemini(
        prompt=prompt,
        model="flash",  # Back to flash for quality
        temperature=0.3,
        max_tokens=20000,  # Room for codes + quantities + reasoning
        response_schema=V2_BOQ_ROOM_SCHEMA,
        use_spanish=True,
    )
    
    if not response.success:
        logger.error(f"      [{room_name}] FAILED: {response.error}")
        return {"room": room_name, "line_items": [], "room_total": 0}
    
    result = json.loads(response.text)
    raw_items = result.get("items", [])
    
    # Build BCCA lookup (cached in context)
    if not hasattr(context, '_bcca_lookup'):
        context._bcca_lookup = _build_bcca_lookup(context.bcca_index)
    
    # CODE does the pricing + labor hours calculation
    line_items = []
    total = 0.0
    total_hours = 0.0
    
    for item in raw_items:
        code = item.get("bcca_code", "")
        qty = item.get("qty", 0)
        qty_reasoning = item.get("qty_reasoning", "")
        
        # Lookup price + labor from BCCA
        bcca_data = context._bcca_lookup.get(code, {})
        unit_price = bcca_data.get("price", 0)
        labor_per_unit = bcca_data.get("labor_hours", 0)
        unit = item.get("unit") or bcca_data.get("unit", "ud")
        desc = bcca_data.get("desc", item.get("scope_item", "Unknown"))
        
        line_total = round(qty * unit_price, 2)
        labor_hours = round(qty * labor_per_unit, 2)
        
        total += line_total
        total_hours += labor_hours
        
        line_items.append({
            "scope_item": item.get("scope_item", ""),
            "bcca_code": code,
            "desc": desc,
            "qty": qty,
            "unit": unit,
            "qty_reasoning": qty_reasoning,  # Shows the working
            "unit_price": unit_price,
            "line_total": line_total,
            "labor_hours": labor_hours,
        })
    
    logger.info(f"      [{room_name}] ✓ {len(line_items)} items, €{total:.2f}, {total_hours:.1f}h")
    
    return {
        "room": room_name,
        "dimension": dimension,
        "line_items": line_items,
        "room_total": round(total, 2),
        "room_labor_hours": round(total_hours, 2),
    }


# =============================================================================
# GENERATE BOQ FOR SINGLE DIMENSION (PER-SCOPE-ITEM MODE)
# =============================================================================

async def _generate_boq_for_dimension(
    dimension: str,
    strategy_package: Dict[str, Any],
    context: BOQContextCache,
    smart_m2_rooms: Optional[List[Dict[str, Any]]] = None,
    writer: Optional[BOQWriteQueue] = None,
) -> Dict[str, Any]:
    """
    Generate BOQ for a dimension using PER-SCOPE-ITEM processing.
    
    Each scope item gets its own Gemini call for better quantity reasoning.
    Results are saved incrementally to boq_line_items table.
    """
    raise RuntimeError(
        "DISABLED: per-scope-item BOQ dimension generation is intentionally removed to prevent runaway costs. "
        "Use v3 BOQ (deterministic + embeddings-only)."
    )
    
    strategy_name = strategy_package.get("strategy_name", "unknown")
    
    dimension_deltas = strategy_package.get("dimension_deltas", {})
    dimension_data = dimension_deltas.get(dimension, {})
    room_scopes = dimension_data.get("room_scopes", [])
    
    # Count total scope items for logging
    total_scope_items = sum(len(rs.get("cost_components", [])) for rs in room_scopes)
    logger.info(f"    → {dimension}: {len(room_scopes)} rooms, {total_scope_items} scope items (per-item mode)")
    
    if not room_scopes:
        return {"dimension": dimension, "line_items": [], "dimension_total": 0, "dimension_labor_hours": 0, "item_count": 0}
    
    # Build room dimensions lookup from smart_m2
    room_dims_lookup = {}
    if smart_m2_rooms:
        for room in smart_m2_rooms:
            room_dims_lookup[room.get("cluster_name", "")] = room
            room_dims_lookup[room.get("cluster_id", "")] = room
    
    # Semaphore to limit concurrent Gemini calls (10 per dimension)
    semaphore = asyncio.Semaphore(10)
    
    all_items = []
    total = 0.0
    total_hours = 0.0
    items_processed = 0
    
    async def process_scope_item(
        scope_item: dict,
        room_name: str,
        spec_strategy: str,
        room_dims: Optional[dict],
    ) -> List[Dict[str, Any]]:
        """Process a single scope item (no DB writes here)."""
        async with semaphore:
            line_items = await _generate_boq_for_scope_item(
                scope_item=scope_item,
                room_name=room_name,
                dimension=dimension,
                strategy_name=strategy_name,
                spec_strategy=spec_strategy,
                context=context,
                room_dimensions=room_dims,
            )
            
            if not line_items:
                raise RuntimeError(
                    f"[BOQ ROOM ZERO ITEMS] {room_name} | {dimension} | {scope_item.get('element', '?')}"
                )
            
            return line_items
    
    # Process all rooms and their scope items
    for room_scope in room_scopes:
        room_name = room_scope.get("room_name", "unknown")
        spec_strategy = room_scope.get("specification_strategy", "Standard quality finish")
        cost_components = room_scope.get("cost_components", [])
        
        if not cost_components:
            continue
        
        # Find matching room dimensions
        room_dims = room_dims_lookup.get(room_name)
        if not room_dims:
            for key, dims in room_dims_lookup.items():
                if key.lower().replace("_", " ") in room_name.lower().replace("_", " "):
                    room_dims = dims
                    break
        
        # Process all scope items in this room in parallel
        tasks = [
            asyncio.create_task(
                process_scope_item(item, room_name, spec_strategy, room_dims)
            )
            for item in cost_components
        ]
        
        results = await _gather_or_cancel(tasks, f"{dimension}:{room_name}:scope_items")

        # Save once per room (chunked) to reduce Supabase POST count
        if writer:
            room_flat_items: List[Dict[str, Any]] = []
            for line_items in results:
                room_flat_items.extend(line_items)

            if not room_flat_items:
                raise RuntimeError(f"[BOQ ROOM ZERO ITEMS] {room_name} | {dimension} | <room_flat_items>")

            await writer.enqueue(dimension=dimension, room_name=room_name, items=room_flat_items)
        
        # Aggregate results
        for line_items in results:
            for item in line_items:
                item_id = f"{dimension[:3]}_{room_name[:3]}_{len(all_items)+1}"
                all_items.append({
                    "item_id": item_id,
                    "room_id": room_name,
                    "dimension": dimension,
                    "scope_item": item.get("scope_item", ""),
                    "scope_item_element": item.get("scope_item_element", ""),
                    "description": item.get("description", ""),
                    "bcca_code": item.get("bcca_code", ""),
                    "quantity": item.get("quantity", 0),
                    "unit": item.get("unit", "ud"),
                    "qty_reasoning": item.get("quantity_reasoning", ""),
                    "unit_price": item.get("unit_price", 0),
                    "line_total": item.get("line_total", 0),
                    "labor_hours": item.get("labor_hours", 0),
                })
                total += item.get("line_total", 0)
                total_hours += item.get("labor_hours", 0)
        
        items_processed += len(cost_components)
        logger.info(f"      [{room_name}] ✓ {len(cost_components)} scope items → {sum(len(r) for r in results)} BOQ items")
    
    logger.info(f"    ✓ {dimension}: {len(all_items)} BOQ items, €{total:.2f}, {total_hours:.1f}h")
    
    return {
        "dimension": dimension,
        "line_items": all_items,
        "dimension_total": round(total, 2),
        "dimension_labor_hours": round(total_hours, 2),
        "item_count": len(all_items),
    }


# =============================================================================
# MAIN FUNCTION - GENERATES BOQ PER DIMENSION (PER-SCOPE-ITEM MODE)
# =============================================================================

async def generate_v2_boq(
    target_pir: Dict[str, Any],
    strategy_package: Dict[str, Any],
    listing_data: Dict[str, Any],
    smart_m2_rooms: Optional[List[Dict[str, Any]]] = None,
    db: Any = None,
    listing_id: int = None,
) -> Dict[str, Any]:
    """
    Generate a complete BOQ using PER-SCOPE-ITEM processing.
    
    Each scope item gets its own Gemini 3 Flash call for better quantity reasoning.
    Results are saved incrementally to boq_line_items table for resilience.
    
    Args:
        target_pir: Target property PIR with 6-dimension analysis
        strategy_package: Strategy package with delta_scopes
        listing_data: Listing metadata
        smart_m2_rooms: Room dimensions from smart_m2 table (optional)
        db: Database instance for incremental saves (optional)
        listing_id: Listing ID for incremental saves (optional)
    
    Returns:
        Complete BOQ with BCCA codes and pricing (aggregated from 6 dimensions)
    
    Raises:
        RuntimeError: On any failure (no fallbacks)
    """
    strategy_name = strategy_package.get("strategy_name", "unknown")
    
    # Count total scope items
    total_scope_items = 0
    for dim in DIMENSIONS:
        dim_deltas = strategy_package.get("dimension_deltas", {}).get(dim, {})
        for rs in dim_deltas.get("room_scopes", []):
            total_scope_items += len(rs.get("cost_components", []))
    
    logger.info("=" * 70)
    logger.info(f"  V2 BOQ GENERATION: {strategy_name.upper()}")
    logger.info(f"  MODE: Per-Scope-Item (Gemini 3 Flash)")
    logger.info(f"  SCOPE ITEMS: {total_scope_items} items across 6 dimensions")
    if smart_m2_rooms:
        logger.info(f"  Room dimensions: {len(smart_m2_rooms)} rooms from smart_m2")
    if db and listing_id:
        logger.info(f"  INCREMENTAL SAVES: Enabled (listing_id={listing_id})")
    logger.info("=" * 70)
    
    if db is None or listing_id is None:
        raise ValueError("generate_v2_boq requires db and listing_id for incremental persistence.")

    # Load context cache (one-time)
    context = BOQContextCache.get_instance()
    context.load()
    
    writer: Optional[BOQWriteQueue] = BOQWriteQueue(
        db=db,
        listing_id=listing_id,
        strategy_name=strategy_name,
        chunk_size=25,
        max_queue=50,
        retry_wait_s=12.0,
    )
    writer.start()
    
    # Generate BOQ for ALL 6 dimensions in parallel
    all_line_items = []
    dimension_totals = {}
    total_labor_hours = 0
    
    logger.info(f"    All 6 dimensions in parallel ({total_scope_items} scope item calls)")
    
    # Run ALL dimensions in parallel
    tasks = [
        asyncio.create_task(
            _generate_boq_for_dimension(
                dimension=dimension,
                strategy_package=strategy_package,
                context=context,
                smart_m2_rooms=smart_m2_rooms,
                writer=writer,
            )
        )
        for dimension in DIMENSIONS
    ]
    
    try:
        results = await _gather_or_cancel(tasks, f"{strategy_name}:dimensions")
    finally:
        if writer:
            await writer.close()
    
    # Aggregate results from all dimensions
    for dimension, result in zip(DIMENSIONS, results):
        all_line_items.extend(result["line_items"])
        dimension_totals[dimension] = result["dimension_total"]
        total_labor_hours += result["dimension_labor_hours"]
    
    # Calculate totals
    total_pem = sum(dimension_totals.values())
    iva_amount = total_pem * 0.21
    total_with_iva = total_pem + iva_amount
    
    # Count items per room
    rooms_coverage = {}
    for item in all_line_items:
        room = item.get("room_id", "unknown")
        rooms_coverage[room] = rooms_coverage.get(room, 0) + 1
    
    # Estimate weeks (rough: 1 week per 40 labor hours)
    estimated_weeks = max(4, int(total_labor_hours / 40))
    
    # ═══════════════════════════════════════════════════════════════════
    # REGULATORY CONTINGENCY (worst-case buffer as rounded %)
    # ═══════════════════════════════════════════════════════════════════
    # 1. Filter rules by property year → these COULD apply
    # 2. Price WORST-CASE remediation for each rule
    # 3. Express as ROUNDED % (this is POSSIBILITY, not certainty)
    # 4. PIR flags (confirmed/debunked) inform confidence narrative only
    
    # Extract regulatory flags from target PIR (for confidence breakdown)
    regulatory_flags = target_pir.get("regulatory_flags", [])
    flags_by_rule = {f.get("rule_id"): f for f in regulatory_flags if f.get("rule_id")}
    
    # Load rules engine
    rules_path = Path(__file__).parent.parent / "pipeline" / "rules_engine_v2.json"
    rules_by_id = {}
    if rules_path.exists():
        with open(rules_path) as f:
            rules_data = json.load(f)
            for rule in rules_data.get("rules", []):
                rules_by_id[rule.get("id")] = rule
    
    property_year = listing_data.get("year_built") or listing_data.get("year") or 1990
    total_m2 = listing_data.get("sqm") or listing_data.get("m2_built") or 74
    
    # Worst-case remediation costs per rule (typical scope for ~75m² apartment)
    # These are estimates from BCCA-based remediation work
    RULE_REMEDIATION_COSTS = {
        # ESSENTIAL / SAFETY
        "ELEC_REBT_001": {"base": 5500, "per_m2": 70, "desc": "Full rewire to REBT 2002"},
        "ELEC_GROUND_002": {"base": 1200, "per_m2": 15, "desc": "Earth system installation"},
        "PLUMB_LEAD_001": {"base": 2500, "per_m2": 35, "desc": "Lead pipe replacement"},
        "PLUMB_GALV_002": {"base": 2000, "per_m2": 30, "desc": "Galvanized pipe replacement"},
        "PLUMB_HEATER_003": {"base": 1800, "per_m2": 0, "desc": "Sealed water heater"},
        "VENT_KITCHEN_001": {"base": 700, "per_m2": 0, "desc": "Kitchen extraction"},
        "VENT_BATH_001": {"base": 500, "per_m2": 0, "desc": "Bathroom extraction"},
        "WET_WATERPROOF_001": {"base": 1200, "per_m2": 0, "desc": "Bathroom waterproofing"},
        "STRUCT_CRACK_001": {"base": 1500, "per_m2": 20, "desc": "Structural crack repair"},
        "STRUCT_DAMP_001": {"base": 2500, "per_m2": 35, "desc": "Rising damp treatment"},
        # MODERN / ENERGY
        "ENV_WIN_001": {"base": 3500, "per_m2": 45, "desc": "Window replacement CTE"},
        "ENV_INSUL_001": {"base": 3000, "per_m2": 40, "desc": "Wall insulation"},
        "HVAC_HEATING_001": {"base": 4500, "per_m2": 0, "desc": "Heat pump installation"},
        "HVAC_COOLING_001": {"base": 2500, "per_m2": 0, "desc": "AC installation"},
        "ACOUSTIC_001": {"base": 2000, "per_m2": 25, "desc": "Acoustic insulation"},
        # COMFORT
        "FINISH_FLOOR_001": {"base": 1200, "per_m2": 40, "desc": "Floor replacement"},
        "FINISH_KITCHEN_001": {"base": 7000, "per_m2": 0, "desc": "Kitchen renovation"},
        "FINISH_BATH_001": {"base": 4500, "per_m2": 0, "desc": "Bathroom renovation"},
    }
    
    # Calculate worst-case for ALL applicable rules (by year)
    contingency_items = []
    total_worst_case = 0.0
    likely_cost = 0.0      # confirmed by PIR
    unlikely_cost = 0.0    # debunked by PIR
    unknown_cost = 0.0     # not checked / inconclusive
    
    for rule_id, rule in rules_by_id.items():
        year_trigger = rule.get("year_trigger", 0)
        
        # Skip if property is newer than rule's year trigger
        if property_year >= year_trigger:
            continue
        
        # Calculate worst-case cost for this rule
        cost_data = RULE_REMEDIATION_COSTS.get(rule_id, {"base": 1500, "per_m2": 20})
        worst_case = cost_data["base"] + (cost_data["per_m2"] * total_m2)
        total_worst_case += worst_case
        
        # Get PIR's determination (for confidence breakdown)
        flag = flags_by_rule.get(rule_id, {})
        status = flag.get("status", "unknown")  # unknown if not in PIR flags
        evidence = flag.get("evidence", "")
        
        if status == "confirmed":
            likely_cost += worst_case
            confidence = "likely"
        elif status == "debunked":
            unlikely_cost += worst_case
            confidence = "unlikely"
        else:
            unknown_cost += worst_case
            confidence = "unknown"
        
        contingency_items.append({
            "rule_id": rule_id,
            "system": rule.get("system", "unknown"),
            "desc": cost_data.get("desc", rule_id),
            "year_trigger": year_trigger,
            "worst_case_cost": round(worst_case, 0),
            "pir_status": status,
            "pir_evidence": evidence,
            "confidence": confidence,
        })
    
    # Express as ROUNDED % of BOQ (5% increments, capped 5-25%)
    contingency_pct_raw = (total_worst_case / total_pem * 100) if total_pem > 0 else 0
    contingency_pct_rounded = round(contingency_pct_raw / 5) * 5
    contingency_pct_rounded = max(5, min(contingency_pct_rounded, 25))
    
    # Calculate actual contingency amount from rounded %
    contingency_amount = total_pem * (contingency_pct_rounded / 100)
    
    # Confidence breakdown (what % of the buffer is likely/unlikely/unknown)
    likely_pct = round((likely_cost / total_worst_case * 100) if total_worst_case > 0 else 0, 0)
    unlikely_pct = round((unlikely_cost / total_worst_case * 100) if total_worst_case > 0 else 0, 0)
    unknown_pct = round((unknown_cost / total_worst_case * 100) if total_worst_case > 0 else 0, 0)
    
    # Build explanation
    explanation_parts = [f"{contingency_pct_rounded}% contingency buffer for {len(contingency_items)} applicable regulations"]
    if likely_pct > 0:
        explanation_parts.append(f"{likely_pct}% of buffer is LIKELY (confirmed in photos)")
    if unlikely_pct > 0:
        explanation_parts.append(f"{unlikely_pct}% of buffer is UNLIKELY (debunked in photos)")
    if unknown_pct > 0:
        explanation_parts.append(f"{unknown_pct}% of buffer is UNKNOWN (could not verify)")
    
    contingency_summary = {
        "property_year": property_year,
        "property_m2": total_m2,
        "rules_applicable": len(contingency_items),
        "worst_case_total": round(total_worst_case, 0),
        "contingency_percentage": contingency_pct_rounded,
        "contingency_before_iva": round(contingency_amount, 2),
        "contingency_with_iva": round(contingency_amount * 1.21, 2),
        "confidence_breakdown": {
            "likely_pct": likely_pct,
            "likely_cost": round(likely_cost, 0),
            "unlikely_pct": unlikely_pct,
            "unlikely_cost": round(unlikely_cost, 0),
            "unknown_pct": unknown_pct,
            "unknown_cost": round(unknown_cost, 0),
        },
        "items": contingency_items,
        "explanation": ". ".join(explanation_parts) + "."
    }
    
    # Build final result
    final_result = {
        "strategy_name": strategy_name,
        "line_items": all_line_items,
        "line_items_count": len(all_line_items),
        "rooms_coverage": rooms_coverage,
        "dimension_totals": dimension_totals,
        "grand_total_before_iva": total_pem,
        "iva_amount": iva_amount,
        "grand_total_with_iva": total_with_iva,
        "total_labor_hours": total_labor_hours,
        "estimated_duration_weeks": estimated_weeks,
        # Regulatory contingency (worst-case buffer as rounded %)
        "regulatory_contingency": contingency_summary,
        "grand_total_with_contingency": round(total_with_iva + contingency_summary["contingency_with_iva"], 2),
        "critical_path": [],  # Could be enhanced
        "reasoning_notes": f"BOQ generado por dimensión (6 llamadas). Total items: {len(all_line_items)}",
    }
    
    logger.info("")
    logger.info(f"  BOQ COMPLETE: {strategy_name.upper()}")
    logger.info(f"    Line items: {len(all_line_items)}")
    logger.info(f"    Grand total (before IVA): €{total_pem:,.2f}")
    logger.info(f"    IVA (21%): €{iva_amount:,.2f}")
    logger.info(f"    Grand total (with IVA): €{total_with_iva:,.2f}")
    logger.info(f"    Regulatory contingency: {contingency_summary['contingency_percentage']}% (€{contingency_summary['contingency_with_iva']:,.2f}) - {len(contingency_items)} rules")
    logger.info(f"    TOTAL WITH CONTINGENCY: €{final_result['grand_total_with_contingency']:,.2f}")
    logger.info(f"    Labor hours: {total_labor_hours:,.0f}")
    logger.info(f"    Est. duration: {estimated_weeks} weeks")
    
    return final_result
