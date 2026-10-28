"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗ ███████╗██████╗ ██████╗ ███████╗ ██████╗ █████╗ ████████╗███████╗  ║
║   ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝  ║
║   ██║  ██║█████╗  ██████╔╝██████╔╝█████╗  ██║     ███████║   ██║   █████╗    ║
║   ██║  ██║██╔══╝  ██╔═══╝ ██╔══██╗██╔══╝  ██║     ██╔══██║   ██║   ██╔══╝    ║
║   ██████╔╝███████╗██║     ██║  ██║███████╗╚██████╗██║  ██║   ██║   ███████╗  ║
║   ╚═════╝ ╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝  ║
║                                                                               ║
║   THIS FILE IS DEPRECATED - DO NOT USE                                        ║
║                                                                               ║
║   Replaced by: gemini_schemas_v1.py (V1.0 8-Phase Architecture)               ║
║   See: docs/DEPRECATION_PLAN.md for migration details                         ║
║                                                                               ║
║   This file will be deleted after V1.0 is fully implemented and tested.       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

V0.5 Phase Output Validation - Discrete Output Architecture [DEPRECATED]
========================================================================

ARCHITECTURE (V0.5):
--------------------
- CUMULATIVE CONTEXT: Items accumulate fields as they pass through phases
- DISCRETE OUTPUT: Each phase schema only contains fields for that phase
- POST-RESPONSE VALIDATION: Pydantic validates AFTER Gemini responds

GEMINI SCHEMAS (in gemini_schemas.py):
- Phase 1-2: SCOPE_ITEM_SCHEMA (no pricing fields)
- Phase 3-4: SCHEDULED_ITEM_SCHEMA (no pricing fields)
- Phase 5: PRICED_ITEM_SCHEMA (pricing fields added)
- Phase 6: ADJUSTED_ITEM_SCHEMA (adjustment fields added)

POST-RESPONSE VALIDATION (this file):
- UnifiedItem: Pydantic model with ALL possible fields
- Used to validate items AFTER each phase
- Ensures items accumulate fields correctly
- FAIL FAST if items lost or pricing incomplete
"""

import warnings
warnings.warn(
    "phase_outputs.py is DEPRECATED. Use gemini_schemas_v1.py instead. "
    "See docs/DEPRECATION_PLAN.md for migration details.",
    DeprecationWarning,
    stacklevel=2
)

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS - Data Integrity vs Judgment Calls
# =============================================================================
#
# Philosophy: There are two kinds of "problems" in a pipeline:
#
# 1. DATA INTEGRITY issues - Items lost, prices missing, corrupted output.
#    These SHOULD raise exceptions because the estimate is broken.
#
# 2. JUDGMENT CALLS - Room coverage, item counts, distribution.
#    These SHOULD NOT raise exceptions. The model made deliberate choices.
#    We observe and report, not gatekeep.
#
# The exceptions below are for DATA INTEGRITY only.
# =============================================================================

class SchemaContinuityError(Exception):
    """
    Data Integrity Error: Items were lost between phases.
    
    What happened: The model received N items and returned fewer. Some scope
    items from earlier phases are missing in the output.
    
    Why this matters: An estimate needs all its line items. If we started with
    42 items (demolition, electrical, finishes, etc.) and Phase 5 only returns
    38, we're missing work from the estimate. The numbers won't add up.
    
    What to do: This is usually a model error (truncation, confusion). Retry
    the phase, or check if the prompt is too long.
    """
    def __init__(self, phase_num: int, expected: int, got: int, missing_ids: Set[str]):
        self.phase_num = phase_num
        self.expected = expected
        self.got = got
        self.missing_ids = missing_ids
        super().__init__(
            f"Phase {phase_num}: {expected - got} items lost (expected {expected}, got {got}). "
            f"Missing: {sorted(list(missing_ids)[:5])}{'...' if len(missing_ids) > 5 else ''}"
        )


class PricingIncompleteError(Exception):
    """
    Data Completeness Error: Items don't have prices.
    
    What happened: After the pricing phase, some items still have null/missing
    values for unit_price or line_total.
    
    Why this matters: An estimate without prices is like a menu with "price: TBD".
    The client needs to know what things cost. We can't present "???" in a quote.
    
    What to do: Check if the BCCA/FFE indexes have coverage for these items.
    The model might have used codes that don't exist in the price database.
    """
    def __init__(self, items_missing_price: List[str]):
        self.items_missing_price = items_missing_price
        count = len(items_missing_price)
        samples = items_missing_price[:5]
        super().__init__(
            f"{count} items have no price: {samples}{'...' if count > 5 else ''}"
        )


class RoomCoverageError(Exception):
    """
    DEPRECATED: Room coverage is now observational, not blocking.
    
    This exception is kept for backwards compatibility but should not be raised
    by current validators. The model's decisions about which rooms need work
    are respected - we observe and report but don't gatekeep.
    """
    def __init__(self, missing_rooms: Set[str], canonical_rooms: Set[str]):
        self.missing_rooms = missing_rooms
        self.canonical_rooms = canonical_rooms
        super().__init__(
            f"Note: {len(missing_rooms)} rooms without items: {sorted(missing_rooms)}"
        )


# =============================================================================
# UNIFIED ITEM MODEL - The One Schema (for post-response validation)
# =============================================================================

class UnifiedItem(BaseModel):
    """
    Single item model used across ALL estimation phases (1-6).
    
    IMPORTANT: This Pydantic model is for POST-RESPONSE validation only.
    We do NOT pass this to Gemini - Gemini receives plain dict schemas.
    
    Each phase fills in different fields:
    - Phase 1: identity + scope fields
    - Phase 3: scheduling fields
    - Phase 5: pricing fields
    - Phase 6: adjustment fields
    
    The structure NEVER changes - items cannot be lost.
    """
    # Identity (Set in Phase 1, IMMUTABLE)
    item_id: str = Field(description="Unique identifier: ITEM_001, ITEM_002, etc.")
    room_id: str = Field(description="Room from canonical clusters")
    room_name: Optional[str] = Field(default=None, description="Human-readable room name")
    
    # Scope (Set in Phase 1)
    name: str = Field(description="What needs to be done")
    description: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None, description="demolition, plumbing, electrical, etc.")
    bcca_chapter: Optional[str] = Field(default=None, description="BCCA chapter code")
    comparable_reference: Optional[str] = Field(default=None)
    
    # Scheduling (Set in Phase 3)
    phase_week: Optional[int] = Field(default=None)
    depends_on: Optional[List[str]] = Field(default=None)
    duration_hours: Optional[float] = Field(default=None)
    
    # Pricing (Set in Phase 5)
    bcca_code: Optional[str] = Field(default=None)
    ffe_code: Optional[str] = Field(default=None)
    unit: Optional[str] = Field(default=None)
    quantity: Optional[float] = Field(default=None)
    quantity_formula: Optional[str] = Field(default=None)
    unit_price: Optional[float] = Field(default=None)
    line_total: Optional[float] = Field(default=None)
    
    # Adjustments (Set in Phase 6)
    price_multiplier: Optional[float] = Field(default=None)
    adjusted_price: Optional[float] = Field(default=None)
    adjustment_reason: Optional[str] = Field(default=None)
    
    class Config:
        extra = "allow"  # Allow extra fields from Gemini


# =============================================================================
# VALIDATION FUNCTIONS - FAIL FAST
# =============================================================================

def validate_items_preserved(
    prev_items: List[Dict[str, Any]], 
    new_items: List[Dict[str, Any]], 
    phase_num: int
) -> None:
    """
    Verify item continuity between phases - this is a DATA INTEGRITY check.
    
    Why this matters: The multi-phase pipeline passes items through each phase.
    Each phase adds information (scheduling, pricing, adjustments) but should
    NEVER lose items. If items disappear, the estimate is fundamentally broken.
    
    This is different from room coverage (a judgment call). This is about data
    corruption - the model was given 42 items and returned 38. That's a bug.
    
    BLOCKS ON FAILURE: Yes, because the estimate would be invalid.
    
    Args:
        prev_items: Items from previous phase
        new_items: Items from current phase output
        phase_num: Current phase number
    
    Raises:
        SchemaContinuityError: If items were lost (actual data corruption)
    """
    prev_ids = {item.get("item_id") for item in prev_items if item.get("item_id")}
    new_ids = {item.get("item_id") for item in new_items if item.get("item_id")}
    
    missing = prev_ids - new_ids
    added = new_ids - prev_ids
    
    # Report what we see
    logger.info(f"  📊 Item Continuity Check (Phase {phase_num}):")
    logger.info(f"     Input items: {len(prev_items)}")
    logger.info(f"     Output items: {len(new_items)}")
    
    if added:
        logger.info(f"     + New items added: {len(added)}")
    
    if missing:
        # This is a real problem - data was lost
        logger.error(f"  ❌ DATA INTEGRITY FAILURE: {len(missing)} items LOST in Phase {phase_num}")
        logger.error(f"     This is not a judgment call - these items existed and now don't.")
        logger.error(f"     Missing item IDs: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")
        logger.error(f"     The estimate cannot proceed with missing scope items.")
        raise SchemaContinuityError(
            phase_num=phase_num,
            expected=len(prev_items),
            got=len(new_items),
            missing_ids=missing
        )
    
    logger.info(f"  ✓ Item continuity verified: all {len(prev_ids)} items preserved")


def validate_pricing_complete(items: List[Dict[str, Any]]) -> None:
    """
    Verify all items have been priced - this is a DATA COMPLETENESS check.
    
    Why this matters: After Phase 5 (Pricing), every item should have:
    - unit_price: The cost per unit from BCCA/FFE indexes
    - line_total: unit_price × quantity
    
    An item without a price is like a menu item with "price: ask waiter" - 
    it's not usable. The client needs to know what things cost.
    
    This isn't about judgment (is this price reasonable?) - that's for Phase 9.
    This is about completeness (does every line have a number?).
    
    BLOCKS ON FAILURE: Yes, because an estimate with "???" prices is broken.
    
    Args:
        items: Items after Phase 5 pricing
    
    Raises:
        PricingIncompleteError: If any items lack prices
    """
    # Categorize items by pricing status
    fully_priced = []
    missing_unit_price = []
    missing_line_total = []
    zero_priced = []
    
    for item in items:
        item_id = item.get("item_id", "UNKNOWN")
        item_name = item.get("name", "Unknown item")
        unit_price = item.get("unit_price")
        line_total = item.get("line_total")
        
        if unit_price is None:
            missing_unit_price.append({"id": item_id, "name": item_name})
        elif line_total is None:
            missing_line_total.append({"id": item_id, "name": item_name})
        elif unit_price == 0 and line_total == 0:
            zero_priced.append({"id": item_id, "name": item_name})
        else:
            fully_priced.append(item_id)
    
    # Report findings
    logger.info(f"  📊 Pricing Completeness Check:")
    logger.info(f"     Fully priced: {len(fully_priced)} items")
    
    if zero_priced:
        logger.info(f"     Zero-priced (may be intentional): {len(zero_priced)} items")
        for item in zero_priced[:3]:
            logger.info(f"        • {item['id']}: {item['name'][:40]}")
    
    # Missing prices are a real problem
    missing = missing_unit_price + missing_line_total
    if missing:
        logger.error(f"  ❌ PRICING INCOMPLETE: {len(missing)} items have no price")
        logger.error(f"     An estimate needs prices. This is not optional.")
        for item in missing[:5]:
            logger.error(f"        • {item['id']}: {item['name'][:40]}")
        if len(missing) > 5:
            logger.error(f"        ... and {len(missing) - 5} more")
        raise PricingIncompleteError(
            items_missing_price=[m['id'] for m in missing]
        )
    
    # Calculate and report totals
    total = sum(item.get("line_total", 0) for item in items)
    logger.info(f"  ✓ All {len(items)} items priced (Total: €{total:,.2f})")


def validate_room_coverage(
    items: List[Dict[str, Any]], 
    canonical_room_ids: Set[str]
) -> None:
    """
    Review room coverage like an intelligent peer - observational, not rigid.
    
    Philosophy: The model saw the photos and made deliberate choices about what
    needs work. Our job is to UNDERSTAND and REPORT those choices, flag anything
    that looks potentially off, but TRUST the model's judgment. We iterate, we
    don't gatekeep.
    
    This function NEVER fails. It observes and reports.
    
    What we report:
    - Coverage overview (how many rooms, what percentage)
    - Item distribution across rooms (visual bar chart)
    - Rooms without items (with context - is this expected?)
    - Potential review suggestions (soft flags, not hard stops)
    
    Args:
        items: Scope items from Phase 1
        canonical_room_ids: Room IDs from photo clustering
    """
    # Gather the data
    covered_rooms = {item.get("room_id") for item in items if item.get("room_id")}
    covered_rooms.discard("general")  # "general" is site-wide, not a physical room
    
    canonical_for_check = canonical_room_ids - {"general"}
    rooms_without_items = canonical_for_check - covered_rooms
    
    # Count items per room for distribution view
    items_per_room = {}
    for item in items:
        room = item.get("room_id", "unknown")
        items_per_room[room] = items_per_room.get(room, 0) + 1
    
    # === Coverage Overview ===
    coverage_pct = len(covered_rooms) / len(canonical_for_check) * 100 if canonical_for_check else 100
    logger.info(f"  📊 Room Coverage: {len(covered_rooms)}/{len(canonical_for_check)} rooms ({coverage_pct:.0f}%)")
    
    # === Item Distribution (visual) ===
    logger.info(f"  📊 Item Distribution:")
    max_items = max(items_per_room.values()) if items_per_room else 1
    for room_id in sorted(canonical_for_check):
        count = items_per_room.get(room_id, 0)
        # Scale bar to max 15 chars
        bar_len = int((count / max_items) * 15) if max_items > 0 else 0
        bar = "█" * bar_len if count > 0 else "·"
        status = "" if count > 0 else " (no items)"
        logger.info(f"     {room_id}: {count:2d} {bar}{status}")
    
    # === Analysis & Observations ===
    if rooms_without_items:
        logger.info(f"  💭 Rooms without scope items:")
        for room in sorted(rooms_without_items):
            # Provide context based on room type
            room_lower = room.lower()
            if any(x in room_lower for x in ['exterior', 'fachada']):
                context = "building exterior - often no interior work needed"
            elif any(x in room_lower for x in ['zonas_comunes', 'common', 'portal', 'escalera']):
                context = "shared/common area - typically not part of unit renovation"
            elif any(x in room_lower for x in ['terraza', 'balcon']):
                context = "outdoor space - may need minimal or no work"
            elif any(x in room_lower for x in ['trastero', 'storage']):
                context = "storage area - often left as-is"
            else:
                context = "model determined no renovation needed here"
            logger.info(f"     • {room}: {context}")
    
    # === Soft Review Suggestions (never blocking) ===
    suggestions = []
    
    # Very low coverage might warrant a look
    if coverage_pct < 40:
        suggestions.append(f"Coverage is {coverage_pct:.0f}% - unusually low, worth a quick review")
    
    # Primary living spaces with 0 items are unusual (but not wrong)
    primary_keywords = {'salon', 'cocina', 'dormitorio', 'bano', 'habitacion'}
    primary_missing = [r for r in rooms_without_items 
                       if any(kw in r.lower() for kw in primary_keywords)]
    if primary_missing:
        suggestions.append(f"Primary spaces without items: {primary_missing} - likely intentional but notable")
    
    # Extremely uneven distribution
    if items_per_room:
        counts = [c for c in items_per_room.values() if c > 0]
        if counts and max(counts) > 10 * min(counts):
            suggestions.append("Item distribution is very uneven - some rooms have 10x+ more items than others")
    
    if suggestions:
        logger.info(f"  💡 Review Suggestions (non-blocking):")
        for suggestion in suggestions:
            logger.info(f"     • {suggestion}")
    
    logger.info(f"  ✓ Room coverage review complete")


# =============================================================================
# ROOM ITEM DISTRIBUTION REVIEW - Observational, not gatekeeping
# =============================================================================

# V0.5 PHILOSOPHY: The model made deliberate choices about scope. Some rooms
# genuinely need minimal work (terraza might just need a paint refresh). Some
# rooms don't belong to the unit at all (exterior, common areas). Our job is
# to OBSERVE and REPORT, not to second-guess every decision.
#
# We iterate with the model through the phases, we don't gatekeep it.


class AntiParetoViolation(Exception):
    """
    DEPRECATED - kept for backwards compatibility but should not be raised.
    
    The new philosophy: never block on room coverage. Just report.
    """
    def __init__(self, room_id: str, room_type: str):
        self.room_id = room_id
        self.room_type = room_type
        super().__init__(
            f"Room '{room_id}' ({room_type}) has no items - worth reviewing if intentional."
        )


def validate_anti_pareto(
    items: List[Dict[str, Any]],
    room_clusters: List[Dict[str, str]]
) -> None:
    """
    Review item distribution across rooms - observational, never blocking.
    
    Philosophy: The model saw the photos, read the PIRs, and made deliberate 
    choices. A room with zero items isn't automatically wrong - exterior spaces,
    common areas, storage rooms often genuinely need no work. A room with only
    1 item isn't automatically incomplete - a terraza might just need sealing.
    
    We REPORT what we see. We flag things that might warrant review. We never
    block progress.
    
    Args:
        items: All scope items
        room_clusters: List of {"room_id": str, "room_name": str, "room_type": str}
    """
    # Count items per room
    items_by_room: Dict[str, int] = {}
    for item in items:
        room_id = item.get("room_id", "general")
        items_by_room[room_id] = items_by_room.get(room_id, 0) + 1
    
    # Categorize rooms for reporting
    rooms_without_items = []
    rooms_with_few_items = []
    rooms_with_work = []
    
    for room in room_clusters:
        room_id = room.get("room_id", "")
        room_type = room.get("room_type", "").lower()
        room_name = room.get("room_name", room_id)
        item_count = items_by_room.get(room_id, 0)
        
        if item_count == 0:
            rooms_without_items.append({
                "room_id": room_id, 
                "room_name": room_name,
                "room_type": room_type
            })
        elif item_count <= 2:
            rooms_with_few_items.append({
                "room_id": room_id, 
                "room_name": room_name,
                "room_type": room_type, 
                "count": item_count
            })
        else:
            rooms_with_work.append({
                "room_id": room_id,
                "room_name": room_name,
                "count": item_count
            })
    
    # Report findings
    logger.info(f"  📊 Item Distribution Summary:")
    logger.info(f"     Rooms with significant work: {len(rooms_with_work)}")
    logger.info(f"     Rooms with minimal work (1-2 items): {len(rooms_with_few_items)}")
    logger.info(f"     Rooms without items: {len(rooms_without_items)}")
    
    # Context for rooms without items
    if rooms_without_items:
        logger.info(f"  💭 Rooms without scope items (may be intentional):")
        for r in rooms_without_items:
            room_lower = r['room_id'].lower()
            # Provide context based on room type
            if any(x in room_lower for x in ['exterior', 'fachada']):
                context = "building exterior"
            elif any(x in room_lower for x in ['zonas_comunes', 'common', 'portal', 'escalera']):
                context = "shared space"
            elif any(x in room_lower for x in ['trastero', 'storage']):
                context = "storage area"
            elif any(x in room_lower for x in ['terraza', 'balcon']):
                context = "outdoor space"
            else:
                context = "model determined no work needed"
            logger.info(f"     • {r['room_name']}: {context}")
    
    # Note rooms with minimal work (informational)
    if rooms_with_few_items:
        logger.info(f"  📋 Rooms with minimal scope (1-2 items):")
        for r in rooms_with_few_items:
            logger.info(f"     • {r['room_name']}: {r['count']} item(s)")
    
    logger.info(f"  ✓ Distribution review complete")


def merge_added_items(
    base_items: List[Dict[str, Any]], 
    added_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge items_to_add from check phases (2, 4) with base items.
    
    Assigns sequential item_ids to new items starting after the max existing ID.
    
    Args:
        base_items: Items from previous phase
        added_items: New items to add (may have temporary IDs)
    
    Returns:
        Combined list with proper item_ids
    """
    if not added_items:
        logger.info(f"  → No items to add, returning {len(base_items)} base items")
        return base_items
    
    # Find max existing ID number
    max_num = 0
    for item in base_items:
        item_id = item.get("item_id", "")
        if item_id.startswith("ITEM_"):
            try:
                num = int(item_id.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                pass
    
    # Assign new IDs to added items
    result = list(base_items)
    for i, item in enumerate(added_items):
        new_id = f"ITEM_{max_num + i + 1:03d}"
        item["item_id"] = new_id
        result.append(item)
        logger.info(f"    + Added: {new_id} - {item.get('name', 'Unknown')}")
    
    logger.info(f"  ✓ Merged {len(added_items)} new items → total {len(result)} items")
    return result


def apply_sequencing_fixes(
    items: List[Dict[str, Any]], 
    fixes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Apply sequencing fixes from Phase 4 to items.
    
    Args:
        items: Items with phase_week values
        fixes: List of {item_id, new_week, reason} dicts
    
    Returns:
        Items with corrected phase_week values
    """
    if not fixes:
        return items
    
    fixes_by_id = {f["item_id"]: f for f in fixes}
    
    for item in items:
        item_id = item.get("item_id")
        if item_id in fixes_by_id:
            fix = fixes_by_id[item_id]
            old_week = item.get("phase_week")
            new_week = fix.get("new_week")
            reason = fix.get("reason", "No reason given")
            
            item["phase_week"] = new_week
            logger.info(f"    → Fixed {item_id}: week {old_week} → {new_week} ({reason})")
    
    logger.info(f"  ✓ Applied {len(fixes)} sequencing fixes")
    return items


# =============================================================================
# SIMPLE DICT VALIDATORS (Alternative to Pydantic)
# =============================================================================

def validate_item_dict(item: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Simple dict validation for items.
    
    Args:
        item: Item dict to validate
        required_fields: Fields that must be present and non-null
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If any required field is missing
    """
    missing = [f for f in required_fields if not item.get(f)]
    if missing:
        raise ValueError(
            f"Item {item.get('item_id', 'UNKNOWN')} missing required fields: {missing}"
        )
    return True


def validate_phase_output(
    output: Dict[str, Any], 
    phase_num: int,
    prev_item_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Review phase output structure and report findings.
    
    This is a quick structural check - does the output have the expected shape?
    Different phases produce different outputs:
    
    - Phases 1, 3, 5, 6: Return {"items": [...]} with full item list
    - Phases 2, 4: Return {"items_to_add": [...]} with new items only
    - Phases 7, 8, 9: Return validation/summary structures
    
    For data integrity, we verify item counts don't decrease unexpectedly.
    
    Args:
        output: The phase output dict from Gemini
        phase_num: Which phase this is
        prev_item_count: Number of items from previous phase
    
    Returns:
        The output dict (unchanged, this is observational)
    """
    items = output.get("items", [])
    items_to_add = output.get("items_to_add", [])
    
    # Report based on phase type
    if phase_num in [1, 3, 5, 6]:
        # Full item list phases
        logger.info(f"  📋 Phase {phase_num} Output: {len(items)} items")
        
        if prev_item_count is not None:
            delta = len(items) - prev_item_count
            if delta > 0:
                logger.info(f"     +{delta} items from previous phase")
            elif delta < 0:
                # This is concerning - items shouldn't decrease
                logger.warning(f"  ⚠️ Item count DECREASED by {abs(delta)}")
                logger.warning(f"     Previous: {prev_item_count}, Current: {len(items)}")
                logger.warning(f"     This may indicate lost items - worth investigating")
    
    elif phase_num in [2, 4]:
        # Additive phases
        logger.info(f"  📋 Phase {phase_num} Output: {len(items_to_add)} items to add")
        if items_to_add:
            for item in items_to_add[:3]:
                logger.info(f"     + {item.get('item_id', '?')}: {item.get('name', 'Unknown')[:40]}")
            if len(items_to_add) > 3:
                logger.info(f"     ... and {len(items_to_add) - 3} more")
    
    elif phase_num in [7, 8, 9]:
        # Validation phases - report key findings
        if phase_num == 7:
            timeline_valid = output.get("timeline_valid", False)
            issues = output.get("timeline_issues", [])
            logger.info(f"  📋 Phase 7 (Timeline): {'Valid' if timeline_valid else f'{len(issues)} issues'}")
        elif phase_num == 8:
            energy_ok = output.get("energy_compliant", False)
            rating = output.get("projected_rating", "?")
            logger.info(f"  📋 Phase 8 (Energy): {'Compliant' if energy_ok else 'Needs work'}, Rating: {rating}")
        elif phase_num == 9:
            passed = output.get("sanity_check_passed", False)
            confidence = output.get("confidence_score", 0)
            logger.info(f"  📋 Phase 9 (Final): {'Passed' if passed else 'Review needed'}, Confidence: {confidence:.1%}")
    
    return output


# =============================================================================
# KEPT FOR BACKWARD COMPATIBILITY (Will be removed in V0.6)
# =============================================================================
# These are referenced by multi_phase_estimator.py but will be phased out

class RegionalAdjustment(BaseModel):
    """Kept for backward compatibility with validation phases."""
    adjustment_type: str
    description: str
    multiplier: float
    reasoning: str = ""


class TimelineVerification(BaseModel):
    """Output of Phase 7: Timeline Check - kept for validation phases."""
    schedule_valid: bool
    issues_found: List[str] = []
    fixes_applied: List[str] = []
    critical_path: List[str] = []
    total_duration_weeks: int = 10


class EnergyVerification(BaseModel):
    """Output of Phase 8: Energy Check - kept for validation phases."""
    current_cee: str = "G"
    target_cee: str = "D"
    predicted_cee: str = "E"
    gap_to_target: bool = False
    items_added_for_energy: List[Dict[str, Any]] = []
    energy_interventions: List[str] = []
