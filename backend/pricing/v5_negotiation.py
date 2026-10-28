"""
V5 Negotiation Advisor — condition-aware price negotiation strategy
===================================================================

TWO MODES depending on listing condition:

1. **"A reformar" (needs renovation)** — defect-based strategy:
   Grounded in OBJECTIVE DEFECTS. "Your kitchen is outdated" is weak (seller
   says "that's your taste"). "Your electrical installation pre-dates the 1985
   REBT regulations and must be replaced" is strong (any buyer faces this).
   Hierarchy: Safety → Hidden defects → ITE → Market data.

2. **Good condition** — market-data strategy:
   When the property is NOT "a reformar", there are fewer defects to leverage.
   Instead, the prompt leans on Casafari market data: fair_market vs asking,
   price per m² vs area average, comparable pricing, days on market. Minor
   defects are still mentioned but as supporting arguments, not the main case.

Items that are explicitly EXCLUDED from negotiation leverage (both modes):
  - Cosmetic finishes (old tiles, worn paint, dated fixtures)
  - Layout preferences (open kitchen, extra bathroom)
  - Modernisation wishes (new appliances, smart home)

Input:  v5_pir_target, v5_delta_slots_market_standard, v2_market_standard,
        v5_eli5_market_standard, listing (price, features, condition),
        v5_selected_comparable, listing_market_stats (Casafari brackets)
Output: v5_negotiation (saved to unified_estimates)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def generate_v5_negotiation(
    *,
    listing_id: int,
    listing: Dict[str, Any],
    target_pir: Optional[Dict[str, Any]],
    delta_slots: Optional[Dict[str, Any]],
    boq_aggregation: Dict[str, Any],
    eli5: Optional[Dict[str, Any]],
    selected_comparable: Optional[Dict[str, Any]],
    market_stats: Optional[Dict[str, Any]] = None,
    db: Any,
    call_gemini_json: Any,
) -> Dict[str, Any]:
    """Generate a buyer-friendly negotiation guide from all pipeline data."""

    asking_price = float(listing.get("price_eur") or listing.get("price") or listing.get("asking_price") or 0)
    total_pem = float(boq_aggregation.get("total_pem") or 0)
    grand_total = float(boq_aggregation.get("grand_total_with_iva") or boq_aggregation.get("total_pem") or 0)
    estimated_weeks = int(boq_aggregation.get("estimated_weeks") or 0)
    scraped = listing.get("scraped_data") or {}
    sqm = float(
        listing.get("total_area") or listing.get("living_area") or listing.get("area")
        or scraped.get("m2_built") or scraped.get("total_area") or scraped.get("living_area") or 1
    )

    # Reference comparable price (and per-sqm).
    # WHY reference_sold_price first: The selector now computes this as
    # median_price/m² × listing_area, which is more meaningful than any
    # single comparable's absolute sale price.
    ref_price = 0.0
    ref_price_sqm = 0.0
    if isinstance(selected_comparable, dict):
        ref_price = float(
            selected_comparable.get("reference_sold_price")
            or selected_comparable.get("sale_price")
            or 0
        )
        ref_area = float(
            selected_comparable.get("listing_area_sqm")
            or selected_comparable.get("total_area")
            or selected_comparable.get("living_area")
            or 0
        )
        if ref_area > 0:
            ref_price_sqm = ref_price / ref_area

    # Build the property condition context from PIR
    pir_block = ""
    if isinstance(target_pir, dict):
        rooms_pir = target_pir.get("rooms") or []
        for room in rooms_pir:
            room_name = room.get("room_name") or room.get("room_type") or "?"
            slots = room.get("slots") or {}
            pir_block += f"\n--- {room_name} ---\n"
            for slot_key, slot_val in slots.items():
                if isinstance(slot_val, dict):
                    condition = slot_val.get("condition") or slot_val.get("state") or ""
                    notes = slot_val.get("notes") or slot_val.get("narrative") or ""
                    if condition or notes:
                        pir_block += f"  {slot_key}: {condition} — {notes}\n"
                elif isinstance(slot_val, str) and slot_val.strip():
                    pir_block += f"  {slot_key}: {slot_val}\n"

    # Build delta context (what work is needed)
    delta_block = ""
    if isinstance(delta_slots, dict):
        delta_rooms = delta_slots.get("rooms") or []
        for room in delta_rooms:
            room_type = room.get("room_type") or room.get("room_id") or "?"
            narratives = room.get("slot_work_narratives") or {}
            work_items = [(k, v) for k, v in narratives.items() if v and v.lower() != "no change"]
            if work_items:
                delta_block += f"\n--- {room_type} ---\n"
                for slot_key, narrative in work_items[:8]:  # Cap to avoid token explosion
                    delta_block += f"  {slot_key}: {narrative}\n"

    # Build cost breakdown by room
    cost_by_room = {}
    for item in (boq_aggregation.get("line_items") or []):
        room_name = item.get("room_name") or "General"
        cost_by_room[room_name] = cost_by_room.get(room_name, 0) + float(item.get("line_total") or 0)

    cost_block = "\n".join(
        f"  {name}: EUR {cost:,.0f}" for name, cost in sorted(cost_by_room.items(), key=lambda x: -x[1])
    )

    # ELI5 context (current state description)
    intro_before = ""
    if isinstance(eli5, dict):
        concept = eli5.get("concept") or {}
        intro_before = concept.get("intro_before") or ""

    # Build list of available room_ids for the model to reference
    available_rooms = set()
    for item in (boq_aggregation.get("line_items") or []):
        rid = item.get("room_id")
        if rid:
            available_rooms.add(rid)
    rooms_list = ", ".join(sorted(available_rooms)) if available_rooms else "(none)"

    # Estimate building age for ITE context
    construction_year = int(scraped.get("construction_year") or listing.get("construction_year") or 0)
    building_age = (2026 - construction_year) if construction_year > 1900 else 0
    ite_note = ""
    if building_age >= 45:
        ite_note = f"Building is ~{building_age} years old — ITE (Inspección Técnica de Edificios) is MANDATORY. Any deficiencies are legally the owner's responsibility to fix."
    elif building_age >= 30:
        ite_note = f"Building is ~{building_age} years old — approaching ITE threshold. Electrical and plumbing may predate current regulations."

    # ── Detect listing condition ──
    # WHY: If the property is in good condition (not "a reformar"), the negotiation
    # strategy should lean MORE on market data (brackets, average prices, comparable
    # pricing) rather than defects. A good-condition property has fewer objective
    # defects, so pure market positioning becomes the strongest lever.
    listing_condition = str(
        listing.get("condition") or scraped.get("condition") or ""
    ).strip().lower()

    # "good condition" = anything that ISN'T explicitly marked as needing renovation
    RENOVATION_CONDITIONS = {"a reformar", "para reformar", "needs renovation", "to renovate", "malo", "bad"}
    is_good_condition = bool(listing_condition) and listing_condition not in RENOVATION_CONDITIONS

    # ── Build market stats context (Casafari brackets) ──
    # WHY: For good-condition properties, market data is the primary negotiation
    # lever. We pass fast_sell, fair_market, and premium brackets plus average
    # price/m² so the LLM can compare asking vs. market reality.
    market_block = ""
    if isinstance(market_stats, dict):
        casafari_fast = float(market_stats.get("casafari_fast_sell") or 0)
        casafari_fair = float(market_stats.get("casafari_fair_market") or 0)
        casafari_premium = float(market_stats.get("casafari_premium") or 0)
        filtered_fast = float(market_stats.get("filtered_fast_sell") or 0)
        filtered_fair = float(market_stats.get("filtered_fair_market") or 0)
        filtered_premium = float(market_stats.get("filtered_premium") or 0)
        avg_price = float(market_stats.get("average_price") or 0)
        avg_psm = float(market_stats.get("average_price_per_sqm") or 0)
        avg_dom = int(market_stats.get("average_days_on_market") or 0)
        sold_6m = int(market_stats.get("sold_last_6_months") or 0)
        comp_count = int(market_stats.get("filtered_comparables_count") or market_stats.get("casafari_comparables_count") or 0)

        parts = []
        if filtered_fair or casafari_fair:
            fair = filtered_fair or casafari_fair
            fast = filtered_fast or casafari_fast
            premium = filtered_premium or casafari_premium
            parts.append(f"  Market price brackets (from {comp_count} recent sales):")
            if fast:
                parts.append(f"    Quick-sale price: EUR {fast:,.0f}")
            parts.append(f"    Fair market value: EUR {fair:,.0f}")
            if premium:
                parts.append(f"    Premium/top price: EUR {premium:,.0f}")
        if avg_price:
            parts.append(f"  Average comparable sale price: EUR {avg_price:,.0f}")
        if avg_psm:
            parts.append(f"  Average price per m²: EUR {avg_psm:,.0f}/m²")
            asking_psm = asking_price / max(sqm, 1)
            diff_pct = ((asking_psm - avg_psm) / avg_psm * 100) if avg_psm else 0
            if abs(diff_pct) > 2:
                parts.append(f"  Asking €/m² vs market average: {diff_pct:+.1f}%")
        if avg_dom:
            parts.append(f"  Average days on market: {avg_dom}")
        if sold_6m:
            parts.append(f"  Properties sold in last 6 months: {sold_6m}")

        if parts:
            market_block = "\n".join(parts)

    # ── Build the prompt ──
    # Condition-aware intro
    condition_label = listing_condition if listing_condition else "unknown"
    condition_context = f"- Listed condition: \"{condition_label}\""
    if is_good_condition:
        condition_context += " (property is NOT listed as needing renovation — see GOOD CONDITION STRATEGY below)"

    prompt = f"""You are a senior real estate negotiation advisor in Spain. A buyer has detailed
inspection data on a property. Your job is to build the STRONGEST possible
negotiation case using the data available.

PROPERTY:
- Asking: EUR {asking_price:,.0f} | Size: {sqm:.0f} m² | EUR {asking_price / max(sqm, 1):,.0f}/m²
- Renovation estimate: EUR {grand_total:,.0f} (±30% uncertainty) | {estimated_weeks} weeks
- Total investment: EUR {asking_price + grand_total:,.0f}
- Comparable sold: EUR {ref_price:,.0f} (EUR {ref_price_sqm:,.0f}/m²)
{condition_context}
{f"- {ite_note}" if ite_note else ""}

CURRENT STATE: {intro_before}

INSPECTION FINDINGS (PIR):
{pir_block[:2500] if pir_block else "(none)"}

REQUIRED WORK (Delta):
{delta_block[:2500] if delta_block else "(none)"}

COST BY ROOM:
{cost_block}

AVAILABLE ROOM IDs (use these in room_ids fields):
{rooms_list}

{f"MARKET DATA (Casafari — recent sold comparables in the area):" + chr(10) + market_block if market_block else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{"GOOD CONDITION STRATEGY" if is_good_condition else "THE CRITICAL DISTINCTION"} — read this carefully before writing anything:
{"" if is_good_condition else ""}
{"This property is listed in GOOD CONDITION — it is NOT a reformar property." if is_good_condition else "In property negotiation, there are TWO types of issues:"}

{'''When a property is already in good/acceptable condition, the negotiation approach
shifts fundamentally. You have FEWER objective defects to point to (the seller knows
the property is in decent shape). Instead, your strongest levers are:

1. MARKET POSITIONING (primary lever):
   - Compare asking price to the fair market bracket. If asking is ABOVE fair market,
     this is your #1 argument: "the data from recent sales shows fair value is X."
   - Compare asking €/m² to average €/m² from comparable sales.
   - If there's a gap between asking and fair market, quantify it clearly.
   - Use the quick-sale bracket as your aggressive anchor, fair market as your target.

2. COMPARABLE EVIDENCE:
   - The selected comparable sold for X — what does that imply for this property?
   - If the comparable was in BETTER condition or had BETTER features, that strengthens
     the argument that this property should be BELOW the comparable price.
   - If the comparable was in WORSE condition, be honest — the comparable supports
     the asking price.

3. MINOR DEFECTS STILL MATTER:
   - Even in good-condition properties, look for: outdated electrical panels,
     single-glazed windows, lack of insulation, aging plumbing, building age issues.
   - These aren't fake leverage — they're real costs that support a modest discount.
   - Use them as SUPPORTING arguments alongside market data, not as the main case.

4. DAYS ON MARKET / LIQUIDITY:
   - If average days on market is high (60+), the seller may be more motivated.
   - If few properties sold in the last 6 months, it's a slow market — buyers have time.

For the output, use the same structure as always:
- "main_issue" should be the strongest MARKET-DATA argument (overpricing vs fair market,
  price per m² above average, etc.) — treat market positioning as an "issue."
- "supporting_issues" should include both any minor defects found AND additional
  market data points (comparable pricing, days on market, etc.)
- "framing_tips" should be factual and data-driven: "Recent sales in this area
  average EUR X/m² — the asking price is Y% above that benchmark."

DO NOT fabricate defects. If the property is genuinely in good condition, say so —
but build the case from market data instead.''' if is_good_condition else '''TYPE A — OBJECTIVE DEFECTS (strong leverage):
These are things that ANY buyer would face, regardless of taste. The seller
CANNOT dismiss them as "well, that's what YOU want to do." Examples:
  - Electrical installation that predates REBT 2002 regulations (no earth wire,
    aluminium wiring, undersized panels) — must be replaced for safety, period.
  - Plumbing with lead or galvanized pipes — health hazard, any buyer replaces this.
  - Water damage, rising damp, active leaks — structural risk, not cosmetic.
  - Structural cracks, settlement, failing load-bearing elements.
  - Asbestos in ceiling tiles, pipe insulation, or floor tiles (pre-1990 buildings).
  - Non-compliant gas installation — safety obligation.
  - Missing or failed ITE (mandatory for buildings 45+ years old).
  - Windows that don't seal / broken frames — energy loss is measurable, not taste.

TYPE B — COSMETIC PREFERENCES (weak leverage — DO NOT USE):
These are things that depend on the buyer's taste. The seller will say "the price
already reflects the condition" or "that's your renovation choice." Examples:
  - "The kitchen is outdated" — subjective. Some buyers like vintage kitchens.
  - "The bathroom tiles are old" — cosmetic. Functional tiles aren't a defect.
  - "We'd want to open up the layout" — that's YOUR preference, not a defect.
  - "The finishes are worn" — normal wear for the property's age.
  - "We'd modernise the appliances" — your choice, not a seller obligation.

YOUR JOB: Go through the inspection data and identify ONLY Type A issues.
If the property mostly has Type B issues (purely cosmetic, dated but functional),
be honest and say: the leverage is limited because the problems are cosmetic, not
structural. Don't stretch a cosmetic issue into a fake defect.

For each Type A issue, explain WHY it is objective — not "the electrical is old"
but "the electrical installation appears to predate current REBT regulations and
would need full replacement for safety compliance — this is not optional for any buyer."'''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET REALITY:

1. NEGOTIATION NORMS IN SPAIN: 3-8% off asking is typical for used homes. Above 10%
   requires serious defects AND a motivated seller. 15%+ is unrealistic unless the
   property has been sitting unsold for 6+ months or has major structural problems.

2. THE COMPARABLE: We have {("one comparable at EUR " + f"{ref_price:,.0f}" + f" (EUR {ref_price_sqm:,.0f}/m²)") if ref_price else "NO comparable data"}.
   {"It may differ in floor, condition, or renovation state. It's a reference point, not proof." if ref_price else "Without comparable data, market-based arguments are weak."}

3. COST UNCERTAINTY: Our estimate of EUR {grand_total:,.0f} has ±30% uncertainty.
   Use the MIDDLE estimate for advice. Don't use the worst-case to inflate leverage.

4. IS THE PRICE ALREADY FAIR? If asking EUR/m² is within 10% of comparable EUR/m²,
   there's little room. The seller may have already discounted for condition.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT (in Spanish, be CONCISE):

1. "target_price": Realistic EUR offer. Conservative — better to underpromise.
   Round to nearest EUR 500.

2. "confidence": "low" / "medium" / "high" — how strong is the overall negotiation case?
   {"For a good-condition property: 'high' = asking is clearly above fair market with strong comparable evidence, 'medium' = some market-data arguments but not overwhelming, 'low' = asking seems fair based on available data." if is_good_condition else "'low' = mostly cosmetic issues, weak comparable, limited leverage. 'medium' = some real defects but also unknowns. 'high' = clear safety/compliance defects with cost evidence."}

3. "reality_check": 1-2 sentences. The honest caveat the buyer needs to hear.

4. "main_issue": The #1 {"market-data argument (e.g. overpricing vs fair market bracket, price per m² above area average)" if is_good_condition else "objective defect (Type A only)"}.
   - "title": 3-5 words
   - "explanation": ONE sentence explaining WHY this is {"a strong market-based argument" if is_good_condition else "objective, not taste"}.
   - "estimated_cost": EUR {"(the gap between asking and fair market value, or 0 if asking is below market)" if is_good_condition else ""}
   - "room_ids": array of room_id strings where visible {"(can be empty for market-data arguments)" if is_good_condition else ""}

5. "supporting_issues": 1-4 additional {"arguments — mix of market data points (comparable pricing, area averages, days on market) and any minor defects found" if is_good_condition else "Type A defects, ordered by severity. If there are fewer than 2 real defects, include 1-2 market-data arguments (e.g., 'Price per m² is X%% above comparable'). Do NOT pad with cosmetic items"}.

6. "framing_tips": 2-3 short phrases (max 15 words each) the buyer can say.
   {"Frame around DATA and EVIDENCE, not feelings: 'Recent comparable sales in this area average EUR X/m² — this asking price is Y%% above that.'" if is_good_condition else "Frame around RISK and OBLIGATION, not preference: BAD: 'We'd like a discount because we need to redo the kitchen.' GOOD: 'The electrical installation requires full replacement to meet current regulations — that's a cost any buyer would face.'"}
"""

    schema = {
        "type": "object",
        "required": ["target_price", "confidence", "reality_check", "main_issue", "supporting_issues", "framing_tips"],
        "properties": {
            "target_price": {"type": "number"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "reality_check": {"type": "string"},
            "main_issue": {
                "type": "object",
                "required": ["title", "explanation", "estimated_cost", "room_ids"],
                "properties": {
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "estimated_cost": {"type": "number"},
                    "room_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            "supporting_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "explanation", "room_ids"],
                    "properties": {
                        "title": {"type": "string"},
                        "explanation": {"type": "string"},
                        "estimated_cost": {"type": "number"},
                        "room_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "framing_tips": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }

    result = await call_gemini_json(
        prompt,
        model="pro",
        temperature=0.3,
        response_schema=schema,
    )

    if not result or not isinstance(result, dict) or not result.get("main_issue"):
        raise RuntimeError(f"v5_negotiation: LLM returned empty/invalid result | listing_id={listing_id}")

    target_price = float(result.get("target_price") or 0)
    savings = asking_price - target_price if asking_price and target_price else 0

    negotiation = {
        "listing_id": int(listing_id),
        "schema_version": "v5_negotiation_v5",
        "strategy_mode": "market_data" if is_good_condition else "defect_based",
        "listing_condition": listing_condition or "unknown",
        "asking_price": asking_price,
        "renovation_cost": grand_total,
        "total_investment": asking_price + grand_total,
        "comparable_sold_price": ref_price,
        "target_price": target_price,
        "savings": savings,
        "savings_pct": round(savings / asking_price * 100, 1) if asking_price else 0,
        "confidence": result.get("confidence", "medium"),
        "reality_check": result.get("reality_check", ""),
        "main_issue": result["main_issue"],
        "supporting_issues": result.get("supporting_issues", []),
        "framing_tips": result.get("framing_tips", []),
    }

    # Save
    ok = await db.save_unified_estimate(listing_id, "v5_negotiation", negotiation)
    if not ok:
        raise RuntimeError(f"v5_negotiation: save failed | listing_id={listing_id}")

    logger.info(
        "v5_negotiation: generated | listing_id=%s | mode=%s | condition=%s | target=%.0f savings=%.0f",
        listing_id,
        "market_data" if is_good_condition else "defect_based",
        listing_condition or "unknown",
        target_price,
        savings,
    )
    return negotiation
