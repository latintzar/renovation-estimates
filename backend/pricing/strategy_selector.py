"""
V2 Strategy Selection Module (New Call #1)
==========================================

PURPOSE:
--------
Analyze ALL comparable PIRs + sold prices to identify 3 distinct renovation strategies.
Each strategy is anchored to a REAL comparable that proves the approach works.

INPUT:
------
- All Comparable PIRs (with 6-dimension analysis)
- All Comparable Sold Prices
- Target PIR (with 6-dimension analysis)

OUTPUT:
-------
3 Strategies:
1. CONSERVATIVE (Low Risk) - Model after lowest-intervention-yet-profitable comparable
2. MARKET STANDARD (Medium Risk) - Model after median/typical comparable
3. TOP OF MARKET (Max Potential) - Model after highest-selling comparable

MODEL: gemini-3-pro-preview (alias: "pro") - Complex reasoning required
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Gemini client
try:
    from ..pipeline.gemini_client import call_gemini
except ImportError:
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from pipeline.gemini_client import call_gemini

from .schemas.gemini_schemas_v2 import STRATEGY_SELECTION_SCHEMA


# =============================================================================
# STRATEGY SELECTION PROMPT
# =============================================================================

def _build_strategy_selection_prompt(
    target_pir: Dict[str, Any],
    comparable_pirs: List[Dict[str, Any]],
    comparable_prices: Dict[int, float],
) -> str:
    """
    Build the prompt for strategy selection.
    
    This prompt asks the model to analyze real market outcomes and identify
    3 distinct strategies anchored to actual comparables.
    """
    
    # Format comparable data
    # NOTE: Comparable PIRs store their ID in pir["_metadata"]["listing_id"] (not top-level).
    formatted_comparables = []
    valid_ref_ids: List[int] = []
    for pir in comparable_pirs:
        meta = pir.get("_metadata") or {}
        comp_id = meta.get("listing_id") or pir.get("listing_id") or pir.get("comparable_id")
        if not comp_id:
            raise ValueError("strategy_selection: comparable PIR missing listing_id in _metadata")
        comp_id = int(comp_id)
        valid_ref_ids.append(comp_id)

        sold_price = comparable_prices.get(comp_id, 0)
        if not sold_price:
            logger.warning(f"strategy_selection: missing sold price for comparable | comp_id={comp_id} (using 0)")
        
        comp_summary = f"""
═══════════════════════════════════════════════════════════════════════════════
COMPARABLE_ID={comp_id} — SOLD_PRICE_EUR=€{sold_price:,.0f}
═══════════════════════════════════════════════════════════════════════════════

PROPERTY SUMMARY:
{pir.get('property_summary', 'No summary available')}

OVERALL CONDITION: {pir.get('overall_condition', 'Unknown')}

ROOMS:
"""
        for room in pir.get("rooms", []):
            room_id = room.get("room_id", "unknown")
            room_name = room.get("room_name", room_id)
            comp_summary += f"\n  [{room_id}] {room_name}\n"
            
            dims = room.get("dimensions", {})
            for dim_name, dim_data in dims.items():
                if isinstance(dim_data, dict):
                    narrative = dim_data.get("narrative", "")
                    if narrative:
                        comp_summary += f"    • {dim_name}: {narrative[:150]}...\n" if len(narrative) > 150 else f"    • {dim_name}: {narrative}\n"
        
        formatted_comparables.append(comp_summary)
    
    comparables_text = "\n".join(formatted_comparables)
    
    # Format target PIR
    target_summary = f"""
═══════════════════════════════════════════════════════════════════════════════
TARGET PROPERTY (The one we're renovating)
═══════════════════════════════════════════════════════════════════════════════

PROPERTY SUMMARY:
{target_pir.get('property_summary', 'No summary available')}

OVERALL CONDITION: {target_pir.get('overall_condition', 'Unknown')}

ROOMS:
"""
    for room in target_pir.get("rooms", []):
        room_id = room.get("room_id", "unknown")
        room_name = room.get("room_name", room_id)
        target_summary += f"\n  [{room_id}] {room_name}\n"
        
        dims = room.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                narrative = dim_data.get("narrative", "")
                if narrative:
                    target_summary += f"    • {dim_name}: {narrative[:150]}...\n" if len(narrative) > 150 else f"    • {dim_name}: {narrative}\n"
    
    coverage_note = ""
    if len(comparable_pirs) < 3:
        coverage_note = f"""
═══════════════════════════════════════════════════════════════════════════════
LIMITED COMPARABLE COVERAGE
═══════════════════════════════════════════════════════════════════════════════

We only have {len(comparable_pirs)} comparable PIRs available right now. WHY THIS MATTERS:
You still need to propose three strategies, but your evidence base is thinner than usual.
You may need to reuse a comparable as the anchor for more than one strategy, while clearly
explaining the tradeoff and uncertainty. Be explicit about what is confidently supported
by the evidence vs. what is inferred.
"""

    valid_ids_text = ", ".join(str(x) for x in sorted(set(valid_ref_ids)))
    prompt = f"""
You are analyzing real market data to discover what renovation approaches actually worked.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS MATTERS
═══════════════════════════════════════════════════════════════════════════════

The buyer needs to understand what the DATA shows, not what theory suggests. You have 
actual sold comparables with actual prices. These are FACTS. Your job is to find the 
patterns in this data — what finish levels correlated with what prices? What did buyers 
actually pay for in this specific market?

You are not designing strategies. You are DISCOVERING them from the evidence. The 
comparables will tell you what works here. Some markets reward high-spec kitchens. 
Others reward space. Others barely care about finishes at all. Let the data speak.

═══════════════════════════════════════════════════════════════════════════════
THE COMPARABLE EVIDENCE
═══════════════════════════════════════════════════════════════════════════════
IMPORTANT: Valid reference IDs

- In your JSON output, `reference_comparable_id` MUST be ONE of these exact integers:
  {valid_ids_text}
- WHY THIS MATTERS: Downstream pipeline steps look up comparable PIRs by this exact ID.
  If you output an ordinal like 1..N ("Comparable #5") the pipeline will fail.
- Do NOT invent IDs. Do NOT output the position in the list. Use `COMPARABLE_ID=...` shown above.

{comparables_text}

{coverage_note}

═══════════════════════════════════════════════════════════════════════════════
THE TARGET PROPERTY
═══════════════════════════════════════════════════════════════════════════════
{target_summary}

═══════════════════════════════════════════════════════════════════════════════
YOUR ANALYSIS APPROACH
═══════════════════════════════════════════════════════════════════════════════

Start by studying the comparables. For each one, ask yourself:

"What finish level does this comparable represent across all 6 dimensions? And what 
price did that finish level achieve?"

Look for the relationship between finish and price in THIS specific dataset. Does higher 
finish correlate strongly with higher price here? Or are there comparables that sold 
well despite modest finishes? Are there comparables that over-invested in finishes but 
didn't recoup proportionally?

Once you understand the finish-to-price relationship in this data, identify THREE 
distinct approaches that the data supports:

1. A CONSERVATIVE approach — which comparable proves you can achieve a solid return 
   with minimal transformation? What does that comparable look like?

2. A MARKET-MATCHING approach — which comparable represents what buyers typically 
   expect in this area? What's the finish level that appears most commonly among 
   successful sales?

3. A MAXIMUM-POTENTIAL approach — which comparable achieved the highest price, and 
   what specifically drove that premium? Was it materials? Layout? Systems? The data 
   will tell you.

For each approach, the comparable IS the strategy. Don't theorize — point to the 
evidence and describe what you observe.

═══════════════════════════════════════════════════════════════════════════════
WHAT TO OBSERVE FOR EACH STRATEGY
═══════════════════════════════════════════════════════════════════════════════

When you identify a reference comparable for a strategy, describe what you actually 
observe about its 6 dimensions:

- Shell & Preparation: What do you see? Original plaster or refinished? Evidence of 
  structural work or preserved as-was?

- Apertures & Enclosure: What state are the windows, doors, shutters? Original or 
  upgraded? What quality level?

- Systems & Services: What MEP evidence is visible? Modern installations or retained 
  original? What does the electrical/plumbing suggest about investment level?

- Surface Finishes: What flooring, wall treatments, junctions do you observe? What 
  quality tier do they represent in this market?

- Fixed Joinery & Equipment: What kitchen, bathroom, storage quality? Entry-level, 
  mid-range, or premium for this area?

- Details & Fittings: What hardware finish grade? Coordinated or mixed? Budget or 
  quality?

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

Provide your market_analysis_summary first — what does this comparable set reveal 
about finish-to-price correlation in this market?

Then provide exactly 3 strategies (conservative, market_standard, top_of_market), 
each anchored to a specific comparable that proves the approach works. For each, 
describe what you observe in that comparable's 6 dimensions and what transformation 
philosophy that implies for the Target.
"""
    
    return prompt


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def select_strategies(
    target_pir: Dict[str, Any],
    comparable_pirs: List[Dict[str, Any]],
    comparable_prices: Dict[int, float],
) -> Dict[str, Any]:
    """
    Analyze comparable PIRs and prices to select 3 renovation strategies.
    
    Args:
        target_pir: The target property's PIR (with 6-dimension analysis)
        comparable_pirs: List of comparable PIRs (with 6-dimension analysis)
        comparable_prices: Dict mapping comparable_id to sold_price
    
    Returns:
        Strategy selection result with 3 strategies, each anchored to a real comparable
    
    Raises:
        ValueError: If insufficient comparables for analysis
    """
    logger.info("=" * 70)
    logger.info("  V2 STRATEGY SELECTION (New Call #1)")
    logger.info("=" * 70)
    
    # Validate inputs
    if len(comparable_pirs) < 2:
        raise ValueError(
            f"Strategy selection requires at least 2 comparables with PIRs. "
            f"Got {len(comparable_pirs)}. Cannot identify strategies."
        )
    if len(comparable_pirs) < 3:
        logger.warning(
            "Strategy selection using limited comparables | "
            f"count={len(comparable_pirs)}"
        )
    
    logger.info(f"  Input: {len(comparable_pirs)} comparable PIRs")
    logger.info(f"  Price range: €{min(comparable_prices.values()):,.0f} - €{max(comparable_prices.values()):,.0f}")
    
    # Build prompt
    prompt = _build_strategy_selection_prompt(
        target_pir=target_pir,
        comparable_pirs=comparable_pirs,
        comparable_prices=comparable_prices,
    )
    
    logger.info(f"  Prompt length: {len(prompt):,} chars")
    logger.info("  Calling Gemini (flash model)...")
    
    # Call Gemini with schema - Flash for strategy selection (comparison task)
    response = await call_gemini(
        prompt=prompt,
        model="flash",  # gemini-3-flash-preview
        temperature=0.5,  # Balanced for reasoning
        response_schema=STRATEGY_SELECTION_SCHEMA,
        use_spanish=False,  # Strategy analysis in English for consistency
    )
    
    if not response.success:
        raise RuntimeError(f"Strategy selection failed: {response.error}")
    
    # Parse response
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text: {response.text[:500]}...")
        raise RuntimeError(f"Failed to parse strategy selection response: {e}")
    
    # Validate result
    strategies = result.get("strategies", [])
    if len(strategies) != 3:
        raise ValueError(f"Expected 3 strategies, got {len(strategies)}")
    
    strategy_names = {s.get("strategy_name") for s in strategies}
    expected_names = {"conservative", "market_standard", "top_of_market"}
    if strategy_names != expected_names:
        raise ValueError(f"Expected strategies {expected_names}, got {strategy_names}")

    # Validate reference_comparable_id values.
    # WHY THIS MATTERS: downstream pipeline steps look up comparable PIRs by this exact ID.
    valid_ids = set(int(k) for k in comparable_prices.keys())
    invalid_refs = []
    for s in strategies:
        ref_id = s.get("reference_comparable_id")
        try:
            ref_id_int = int(ref_id)
        except Exception:
            invalid_refs.append(ref_id)
            continue
        if ref_id_int not in valid_ids:
            invalid_refs.append(ref_id_int)
    if invalid_refs:
        raise ValueError(
            "strategy_selection: invalid reference_comparable_id(s) returned by LLM | "
            f"invalid={invalid_refs} | valid_ids={sorted(valid_ids)}"
        )
    
    # Log results
    logger.info("")
    logger.info("  STRATEGY SELECTION RESULTS:")
    for strategy in strategies:
        name = strategy.get("strategy_name")
        ref_id = strategy.get("reference_comparable_id")
        ref_price = strategy.get("reference_sold_price", 0)
        risk = strategy.get("risk_level")
        intervention = strategy.get("estimated_intervention_level")
        
        logger.info(f"    {name.upper()}:")
        logger.info(f"      Reference: Comparable ID={ref_id} (€{ref_price:,.0f})")
        logger.info(f"      Risk: {risk} | Intervention: {intervention}")
    
    logger.info("")
    logger.info("  ✓ Strategy selection complete")
    
    return result


# =============================================================================
# HELPER: EXTRACT STRATEGY BY NAME
# =============================================================================

def get_strategy_by_name(
    selection_result: Dict[str, Any],
    strategy_name: str
) -> Dict[str, Any]:
    """
    Extract a specific strategy from the selection result.
    
    Args:
        selection_result: Full output from select_strategies()
        strategy_name: "conservative", "market_standard", or "top_of_market"
    
    Returns:
        The strategy dict
    
    Raises:
        ValueError: If strategy not found
    """
    for strategy in selection_result.get("strategies", []):
        if strategy.get("strategy_name") == strategy_name:
            return strategy
    
    raise ValueError(f"Strategy '{strategy_name}' not found in selection result")
