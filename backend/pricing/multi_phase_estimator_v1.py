"""
V2 Multi-Phase Estimation Orchestrator - Post-BOQ Phases
========================================================

ARCHITECTURE (V2):
------------------
7 phases (Phase 1 includes pricing from BCCA index):

- Phase 1: BOQ (Pro) - Define scope, select BCCA codes, quantities, AND PRICES
- Phase 3: PEER REVIEW (Flash) - Add missing, fix sequencing, apply adjustments
- Phase 4: RENDERING PROMPTS (Flash) - AI image transformation prompts
- Phase 5: IMAGE GENERATION (Gemini Flash Image) - Uses existing service
- Phase 6: VIEWING CHECKLIST (Flash) - 20-minute property viewing guide
- Phase 7: ELI5 ROOM SUMMARIES (Flash) - Plain language for buyers
- Phase 8: ARCHITECT REPORT (Flash) - Professional report by trades

MODEL ASSIGNMENT (V2):
- BOQ: Pro (heavy reasoning with BCCA index)
- All other phases: Flash (formatting/restructuring)

NOTE: Phase 2 was removed. BOQ (Phase 1) calculates prices directly from the 
BCCA index (which includes PRICE and LABOR_HOURS columns). Phase 3 (Peer Review) 
validates and adjusts the prices.

PHILOSOPHY (V2):
----------------
- BOQ calculates prices FROM the BCCA index it has in context
- Full cached context with ALL knowledge graphs
- Checkpoint after EVERY phase for resume capability
- FAIL LOUD AND FAST - no silent errors, no fallbacks
- Comprehensive logging at INFO level

PATTERNS PRESERVED:
-------------------
- JSON sanitization (decimal truncation, markdown stripping)
- Retry logic for JSON parse errors
- Context caching pattern
- Validation between phases
"""

import json
import re
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# JSON SANITIZATION (CRITICAL - Preserved from V0.6)
# =============================================================================

def sanitize_gemini_json(text: str) -> str:
    """
    Sanitize Gemini JSON output to fix common hallucination issues.
    
    Known issue: Gemini sometimes outputs malformed decimal numbers like:
    - "unit_price": 1200.000000000000000000000000000000000000000...
    
    This function truncates numbers with >6 decimal places.
    """
    # Pattern: number with more than 6 decimal places
    pattern = r'(\d+)\.(\d{1,6})\d{7,}'
    
    def truncate_decimal(match):
        integer_part = match.group(1)
        decimal_part = match.group(2)
        return f"{integer_part}.{decimal_part}"
    
    sanitized = re.sub(pattern, truncate_decimal, text)
    
    # Also handle scientific notation hallucinations
    sci_pattern = r'\d+[eE][+-]?\d{5,}'
    sanitized = re.sub(sci_pattern, '0', sanitized)
    
    return sanitized


# =============================================================================
# IMPORTS
# =============================================================================

# Phase prompts and schemas
from .phase_prompts_v1 import (
    PHASE_PROMPTS,
    PHASE_SYSTEM_INSTRUCTION,
    PHASES_V1,
    get_prompt_for_phase,
    get_phase_config,
)
from .schemas.gemini_schemas_v1 import (
    GEMINI_SCHEMAS_V1,
    get_schema_for_phase_v1,
    # Validation functions (moved from deprecated phase_outputs.py)
    SchemaContinuityError,
    PricingIncompleteError,
    validate_pricing_complete,
    # Note: validate_items_preserved removed - Phase 3 now uses Plan+Apply approach
)

# Shared utilities (NOT deprecated)
from .bcca_price_lookup import BCCAPriceLookup, FFEPriceLookup
from .schemas.estimation_error import (
    EstimationError,
    PhaseError,
    GeminiError,
    DataMissingError,
)

# Gemini client
try:
    from ..pipeline.gemini_client import call_gemini, call_gemini_image
except ImportError:
    import sys
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from pipeline.gemini_client import call_gemini, call_gemini_image


# =============================================================================
# V2 PHASE DEFINITIONS
# =============================================================================

PHASES_V2_CONFIG = {
    # Phase 1: BOQ (Bill of Quantities) - Pro model
    # BOQ = scope + quantities + pricing + labor hours + schedule
    # LLM calculates prices directly from BCCA index (has PRICE and LABOR_HOURS columns)
    1: {
        "name": "complete_boq",
        "model": "pro",
        "task": "Create complete BOQ: scope, BCCA codes, quantities, prices, labor hours, and schedule",
        "temperature": 0.7,
        "checkpoint": "phase_1_boq_complete",
    },
    # Phase 2: REMOVED - BOQ includes pricing
    # Phase 3: PEER REVIEW - Flash model (post-BOQ)
    3: {
        "name": "peer_review",
        "model": "flash",  # gemini-3-flash-preview
        "task": "Review and IMPROVE scope - add missing, fix sequencing, validate prices, apply adjustments",
        "temperature": 0.5,
        "checkpoint": "phase_3_peer_review_complete",
    },
    # Phase 4: RENDERING PROMPTS - Flash model (post-BOQ)
    4: {
        "name": "rendering_prompts",
        "model": "flash",  # gemini-3-flash-preview
        "task": "Generate AI image transformation prompts per room",
        "temperature": 0.7,
        "checkpoint": "phase_4_prompts_complete",
    },
    # Phase 5: IMAGE GENERATION - Gemini Flash Image (existing service)
    5: {
        "name": "image_generation",
        "model": "gemini-2.5-flash-preview-image",
        "task": "Generate before/after images",
        "temperature": None,
        "checkpoint": "phase_5_images_complete",
    },
    # Phase 7: ELI5 ROOM SUMMARIES - Flash model
    7: {
        "name": "eli5_summaries",
        "model": "flash",
        "task": "Generate plain-language room summaries for buyers",
        "temperature": 0.7,
        "checkpoint": "phase_7_eli5_complete",
    },
    # Phase 8: ARCHITECT REPORT - Flash model (post-BOQ)
    8: {
        "name": "architect_report",
        "model": "flash",  # gemini-3-flash-preview
        "task": "Format professional report by trades for contractors/architects",
        "temperature": 0.5,
        "checkpoint": "phase_8_report_complete",
    },
}


# =============================================================================
# V2 ORCHESTRATOR CLASS
# =============================================================================

class MultiPhaseEstimatorV1:
    """
    V2 Multi-Phase Estimator - Post-BOQ Processing Phases.
    
    Handles phases 3-8 after BOQ generation:
    - BOQ (Phase 1) includes PRICING from BCCA index
    - Phase 2 REMOVED (pricing is in BOQ)
    - Full knowledge graph context (energy, design, rules)
    - Phases 7 and 8 for buyer/professional outputs
    - Enhanced checkpointing with phase output storage
    
    Usage:
        estimator = MultiPhaseEstimatorV1()
        result = await estimator.estimate(
            target_pir=target_pir,
            bracket_pir=bracket_pir,
            strategic_reasoning=strategic_reasoning,
            listing_data=listing_data,
            canonical_room_ids=canonical_room_ids,
            package_type="fair_market"
        )
    """
    
    def __init__(
        self,
        max_output_tokens: int = 65536,
        data_dir: Optional[Path] = None
    ):
        """Initialize the V1.0 estimator."""
        self.max_output_tokens = max_output_tokens
        self.data_dir = data_dir or Path(__file__).parent / "data"
        # Standards are at lean-mvp/standards, not backend/standards
        self.standards_dir = Path(__file__).parent.parent.parent / "standards"
        
        # Phase outputs storage
        self.phase_outputs: Dict[int, Any] = {}
        
        # Current items (maintained across phases)
        self.current_items: List[Dict[str, Any]] = []
        
        # Cached context (built once, reused across all phases)
        # Uses bcca_optimized_index.txt (~322K tokens) - 55% smaller than full
        self.cached_context: Optional[str] = None
        
        # Store PIR data for Phase 8 (needs raw data, not just context string)
        self.target_pir: Optional[Dict[str, Any]] = None
        self.bracket_pir: Optional[Dict[str, Any]] = None
        self.strategic_reasoning: Optional[Dict[str, Any]] = None
        
        # Canonical room_ids from clusters
        self.canonical_room_ids: Optional[List[Dict[str, str]]] = None
        self.canonical_room_id_set: Optional[Set[str]] = None
        
        # Timing
        self.phase_times: Dict[int, float] = {}
        
        # BCCA/FFE lookup instances
        self.bcca_lookup: Optional[BCCAPriceLookup] = None
        self.ffe_lookup: Optional[FFEPriceLookup] = None
        
        # Checkpoint tracking
        self.checkpoints_completed: List[str] = []
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    async def estimate(
        self,
        target_pir: Dict[str, Any],
        bracket_pir: Dict[str, Any],
        strategic_reasoning: Dict[str, Any],
        listing_data: Dict[str, Any],
        canonical_room_ids: List[Dict[str, str]],
        package_type: str = "fair_market",
        smart_m2_data: Optional[Dict[str, Any]] = None,
        existing_checkpoints: Optional[List[str]] = None,
        listing_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run V1.0 estimation with 8-phase pipeline.
        
        Args:
            target_pir: PropertyIntelligenceReport for target property
            bracket_pir: Synthesized PIR for the target bracket
            strategic_reasoning: Pre-scope strategic brief
            listing_data: Basic listing info (price, m², rooms, location)
            canonical_room_ids: List of {"room_id": str, "room_name": str}
            package_type: "fast_sell", "fair_market", or "out_of_market"
            smart_m2_data: Optional room dimensions from Smart M² step
            existing_checkpoints: Checkpoints to skip (for resume)
            listing_id: Listing ID for checkpointing
        
        Returns:
            Unified estimate with all phase outputs
        """
        start_time = datetime.now()
        
        # Store canonical room_ids
        self.canonical_room_ids = canonical_room_ids
        self.canonical_room_id_set = {r["room_id"] for r in canonical_room_ids}
        
        # Store PIR data for Phase 8 (needs raw data for expanded architect report)
        self.target_pir = target_pir
        self.bracket_pir = bracket_pir
        self.strategic_reasoning = strategic_reasoning
        
        # Initialize checkpoints
        self.checkpoints_completed = existing_checkpoints or []
        
        # Initialize price lookup tools
        self._init_price_lookups()
        
        self._log_banner("V1.0 ESTIMATION PIPELINE - 8-PHASE ULTIMATE ARCHITECTURE")
        logger.info(f"  Package: {package_type.upper()}")
        logger.info(f"  Bracket: {bracket_pir.get('bracket_name', 'Unknown')}")
        logger.info(f"  Canonical rooms: {len(canonical_room_ids)} ({sorted(self.canonical_room_id_set)})")
        logger.info(f"  Smart M² data: {'Available' if smart_m2_data else 'Not available'}")
        self._log_separator()
        
        # Build cached context (ONCE)
        logger.info("")
        logger.info("📦 Building cached context...")
        self.cached_context = self._build_cached_context(
            target_pir=target_pir,
            bracket_pir=bracket_pir,
            strategic_reasoning=strategic_reasoning,
            listing_data=listing_data,
            package_type=package_type,
            smart_m2_data=smart_m2_data,
        )
        context_words = len(self.cached_context.split())
        logger.info(f"   → Context size: ~{context_words:,} words (~{context_words * 1.3:,.0f} tokens)")
        
        # =================================================================
        # PHASE 1: COMPLETE BOQ (scope + pricing + labor + schedule)
        # LLM calculates prices directly from BCCA index
        # =================================================================
        phase_1_output = await self._execute_phase_1_boq(listing_id)
        
        # Phase 2 REMOVED - Phase 1 now includes pricing
        
        # =================================================================
        # PHASE 3: PEER REVIEW (LLM)
        # Validates prices, adds missing items, applies adjustments
        # =================================================================
        phase_3_output = await self._execute_phase_3_peer_review(listing_id, listing_data)
        
        self._log_banner("CORE ESTIMATION COMPLETE (Phases 1+3)")
        final_total = phase_3_output.get("final_total_with_iva", 0)
        logger.info(f"  Items: {len(self.current_items)}")
        logger.info(f"  Cost: €{final_total:,.2f} (incl IVA)")
        self._log_separator()
        
        # =================================================================
        # PHASE 4: RENDERING PROMPTS (LLM) - Requires room photos
        # =================================================================
        # Build room_photos from canonical_room_ids
        # Note: In full pipeline, photos come from DB. Here we build stubs.
        room_photos = self._build_room_photos_from_canonical(canonical_room_ids, listing_data)
        if room_photos:
            phase_4_output = await self._execute_phase_4_rendering_prompts(
                room_photos=room_photos,
                package_type=package_type,
                listing_id=listing_id
            )
        else:
            logger.warning("  ⚠ No room photos available - skipping Phase 4")
            phase_4_output = {"room_prompts": [], "skipped": True}
            self.phase_outputs[4] = phase_4_output
        
        # =================================================================
        # PHASE 5: IMAGE GENERATION (Gemini Flash Image)
        # =================================================================
        if phase_4_output.get("room_prompts"):
            phase_5_output = await self._execute_phase_5_image_generation(
                room_prompts=phase_4_output.get("room_prompts", []),
                room_photos=room_photos,
                listing_id=listing_id
            )
        else:
            logger.warning("  ⚠ No rendering prompts - skipping Phase 5")
            phase_5_output = {"generated_images": [], "skipped": True}
            self.phase_outputs[5] = phase_5_output
        
        # =================================================================
        # PHASE 7: ELI5 ROOM SUMMARIES (LLM)
        # =================================================================
        phase_7_output = await self._execute_phase_7_eli5_summaries(
            listing_data=listing_data,
            listing_id=listing_id
        )
        
        # =================================================================
        # PHASE 8: ARCHITECT REPORT (LLM)
        # =================================================================
        phase_8_output = await self._execute_phase_8_architect_report(
            listing_data=listing_data,
            listing_id=listing_id
        )
        
        # =================================================================
        # BUILD UNIFIED ESTIMATE (All 8 phases complete)
        # =================================================================
        total_duration = (datetime.now() - start_time).total_seconds()
        
        self._log_banner("V1.0 PIPELINE COMPLETE - ALL 8 PHASES")
        logger.info(f"  Total time: {total_duration:.1f}s")
        logger.info(f"  Final items: {len(self.current_items)}")
        logger.info(f"  Final cost: €{final_total:,.2f} (incl IVA)")
        logger.info(f"  Phases completed: {len(self.checkpoints_completed)}")
        self._log_separator()
        
        unified = self._build_unified_estimate(
            package_type=package_type,
            listing_data=listing_data,
            total_duration=total_duration,
        )
        
        return unified
    
    def _build_room_photos_from_canonical(
        self,
        canonical_room_ids: List[Dict[str, str]],
        listing_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build room photos list from canonical room IDs."""
        # In production, photos come from database via photo_clusters
        # Here we create stubs that will be populated if photos are available
        room_photos = []
        
        # Check if listing_data has photo URLs
        photos = listing_data.get("photo_urls", []) or listing_data.get("photos", [])
        
        if not photos:
            logger.info("  → No photos in listing_data for Phase 4")
            return []
        
        # Distribute photos to rooms (simple round-robin for now)
        for i, room in enumerate(canonical_room_ids):
            if i < len(photos):
                photo_url = photos[i] if isinstance(photos[i], str) else photos[i].get("url", "")
                if photo_url:
                    room_photos.append({
                        "room_id": room.get("room_id"),
                        "room_name": room.get("room_name", room.get("room_id")),
                        "photo_url": photo_url,
                    })
        
        return room_photos
    
    # =========================================================================
    # PHASE 1: SCOPE + BOQ (LLM)
    # =========================================================================
    
    async def _execute_phase_1_boq(
        self,
        listing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Phase 1: Create complete BOQ (scope + pricing + labor hours + schedule)."""
        phase_num = 1
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]

        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 1 checkpoint found - loading from storage")
            return self.phase_outputs.get(1, {})

        self._log_phase_start(phase_num, "COMPLETE BOQ (Pro)")

        phase_start = datetime.now()

        # Build phase prompt
        phase_config = PHASES_V2_CONFIG[phase_num]
        prompt_template = get_prompt_for_phase(phase_num)
        prompt = prompt_template.format(
            task=phase_config["task"],
            previous_output="N/A (first phase)"
        )
        full_prompt = f"{self.cached_context}\n\n{prompt}"

        # Get schema
        schema = get_schema_for_phase_v1(phase_num)

        # Call Gemini
        response = await self._call_gemini_with_retry(
            prompt=full_prompt,
            model=phase_config["model"],
            temperature=phase_config["temperature"],
            schema=schema,
            phase_num=phase_num,
        )

        # Parse and validate
        phase_1_output = self._parse_json_response(response.text, phase_num)

        # Validate output
        items = phase_1_output.get("items", [])
        if not items:
            raise PhaseError(
                phase_number=phase_num,
                phase_name="complete_boq",
                message="Phase 1 produced 0 BOQ items. This is a critical failure.",
                context={"prompt_length": len(full_prompt)}
            )

        # Validate items have required fields (including pricing)
        items_missing_price = 0
        total_cost = 0.0
        total_labor = 0.0
        for item in items:
            if not item.get("bcca_code"):
                logger.warning(f"  ⚠ Item {item.get('item_id')} missing bcca_code")
            if not item.get("unit_price") or not item.get("line_total"):
                items_missing_price += 1
                logger.warning(f"  ⚠ Item {item.get('item_id')} missing pricing")
            else:
                total_cost += item.get("line_total", 0)
                total_labor += item.get("labor_hours", 0)
        
        if items_missing_price > 0:
            logger.warning(f"  ⚠ {items_missing_price}/{len(items)} items missing pricing")
        
        # Validate totals
        reported_pem = phase_1_output.get("total_pem", 0)
        if abs(reported_pem - total_cost) > 1.0:
            logger.warning(f"  ⚠ total_pem mismatch: reported €{reported_pem:,.2f} vs calculated €{total_cost:,.2f}")

        self.phase_outputs[phase_num] = phase_1_output
        self.current_items = items

        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration

        total_weeks = phase_1_output.get("total_weeks", 10)
        logger.info(f"  ✓ Phase 1: {len(items)} items, €{total_cost:,.2f} PEM, {total_labor:.0f}h labor")
        logger.info(f"  ✓ Schedule: {total_weeks} weeks")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")

        self.checkpoints_completed.append(checkpoint)

        return phase_1_output
    
    # =========================================================================
    # PHASE 2: DEPRECATED - Pricing is now done in Phase 1
    # =========================================================================
    # 
    # Phase 2 has been removed. The LLM in Phase 1 now calculates prices 
    # directly from the BCCA index (which has PRICE and LABOR_HOURS columns).
    # This is more efficient and allows the LLM to reason about prices in
    # context with scope decisions. Phase 3 (Peer Review) validates prices.
    #
    # The BCCA/FFE lookup tools are still available for validation if needed.
    # =========================================================================
    
    # =========================================================================
    # PHASE 3: PEER REVIEW (LLM)
    # =========================================================================
    
    async def _execute_phase_3_peer_review(
        self,
        listing_id: Optional[int] = None,
        listing_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 3: Peer review using Plan + Apply approach.
        
        Step 1 (LLM): Generate a review plan (items to add, modify, resequence)
        Step 2 (CODE): Apply the plan deterministically (guarantees item preservation)
        """
        phase_num = 3
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]

        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 3 checkpoint found - loading from storage")
            return self.phase_outputs.get(3, {})

        self._log_phase_start(phase_num, "PEER REVIEW - Plan + Apply")

        phase_start = datetime.now()
        input_item_count = len(self.current_items)

        # =====================================================================
        # STEP 1: Generate Review Plan (LLM)
        # =====================================================================
        logger.info(f"    Step 1: Generating review plan...")
        
        phase_config = PHASES_V2_CONFIG[phase_num]
        prompt_template = get_prompt_for_phase(phase_num)

        prev_json = json.dumps(
            {"items": self.current_items, "total_items": len(self.current_items)},
            indent=2,
            ensure_ascii=False
        )

        prompt = prompt_template.format(
            task=phase_config["task"],
            previous_output=prev_json
        )
        full_prompt = f"{self.cached_context}\n\n{prompt}"

        if listing_data:
            sqm = listing_data.get("sqm", 81)
            full_prompt += f"\n\nPROPERTY SIZE: {sqm} m²"

        schema = get_schema_for_phase_v1(phase_num)

        response = await self._call_gemini_with_retry(
            prompt=full_prompt,
            model=phase_config["model"],
            temperature=phase_config["temperature"],
            schema=schema,
            phase_num=phase_num,
        )

        review_plan = self._parse_json_response(response.text, phase_num)
        
        plan_time = (datetime.now() - phase_start).total_seconds()
        items_to_add = review_plan.get("items_to_add", [])
        items_to_modify = review_plan.get("items_to_modify", [])
        sequencing_changes = review_plan.get("sequencing_changes", [])
        
        logger.info(f"    ✓ Plan generated in {plan_time:.1f}s")
        logger.info(f"      + Items to add: {len(items_to_add)}")
        logger.info(f"      ~ Items to modify: {len(items_to_modify)}")
        logger.info(f"      ↔ Sequencing changes: {len(sequencing_changes)}")

        # =====================================================================
        # STEP 2: Apply Plan (CODE - deterministic, guarantees preservation)
        # =====================================================================
        logger.info(f"    Step 2: Applying plan to {input_item_count} items...")
        
        apply_start = datetime.now()
        
        final_items, apply_stats = self._apply_review_plan(
            original_items=self.current_items,
            review_plan=review_plan,
            listing_data=listing_data,
        )
        
        apply_time = (datetime.now() - apply_start).total_seconds()
        
        # Verify item count (must be >= input)
        assert len(final_items) >= input_item_count, \
            f"Item preservation failed: {len(final_items)} < {input_item_count}"
        
        logger.info(f"    ✓ Plan applied in {apply_time:.1f}s")
        logger.info(f"      Final items: {len(final_items)} ({len(final_items) - input_item_count} added)")

        # Update current items
        self.current_items = final_items

        # Build Phase 3 output
        phase_3_output = self._build_phase_3_output(
            items=final_items,
            review_plan=review_plan,
            apply_stats=apply_stats,
            listing_data=listing_data,
        )

        self.phase_outputs[phase_num] = phase_3_output

        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration

        final_total = phase_3_output.get("final_total_with_iva", 0)
        confidence = review_plan.get("review_analysis", {}).get("confidence_score", 80)

        logger.info(f"  ✓ Phase 3: {len(items_to_add)} items added, {len(final_items)} total")
        logger.info(f"  💰 Final total (incl IVA): €{final_total:,.2f}")
        logger.info(f"  📊 Confidence: {confidence}%")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s (plan: {plan_time:.1f}s, apply: {apply_time:.1f}s)")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")

        self.checkpoints_completed.append(checkpoint)

        return phase_3_output

    def _apply_review_plan(
        self,
        original_items: List[Dict[str, Any]],
        review_plan: Dict[str, Any],
        listing_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply the review plan to original items (deterministic, no items lost).
        
        Returns:
            Tuple of (final_items, stats)
        """
        import copy
        
        # Start with deep copy of ALL original items (guarantees preservation)
        items = copy.deepcopy(original_items)
        items_by_id = {item["item_id"]: item for item in items}
        
        stats = {
            "modifications_applied": 0,
            "sequencing_applied": 0,
            "items_added": 0,
            "regional_multiplier": 1.0,
        }
        
        # 1. Apply modifications to existing items
        for mod in review_plan.get("items_to_modify", []):
            item_id = mod.get("item_id")
            field = mod.get("field")
            new_value = mod.get("new_value")
            
            if item_id in items_by_id and field and new_value is not None:
                item = items_by_id[item_id]
                # Convert numeric fields
                if field in ["quantity", "unit_price", "line_total", "labor_hours", "phase_week"]:
                    try:
                        new_value = float(new_value) if field != "phase_week" else int(new_value)
                    except (ValueError, TypeError):
                        continue
                item[field] = new_value
                
                # Recalculate line_total if quantity or unit_price changed
                if field in ["quantity", "unit_price"]:
                    item["line_total"] = item.get("quantity", 0) * item.get("unit_price", 0)
                
                stats["modifications_applied"] += 1
        
        # 2. Apply sequencing changes
        for seq in review_plan.get("sequencing_changes", []):
            item_id = seq.get("item_id")
            new_week = seq.get("new_week")
            
            if item_id in items_by_id and new_week is not None:
                items_by_id[item_id]["phase_week"] = int(new_week)
                stats["sequencing_applied"] += 1
        
        # 3. Add new items
        next_item_num = len(items) + 1
        for new_item in review_plan.get("items_to_add", []):
            # Generate permanent item_id
            item_id = f"ITEM_{next_item_num:03d}"
            next_item_num += 1
            
            # Build the item
            item = {
                "item_id": item_id,
                "room_id": new_item.get("room_id", "general"),
                "name": new_item.get("name", ""),
                "bcca_code": new_item.get("bcca_code", ""),
                "bcca_description": new_item.get("bcca_description", ""),
                "unit": new_item.get("unit", "ud"),
                "quantity": float(new_item.get("quantity", 1)),
                "unit_price": float(new_item.get("unit_price", 0)),
                "line_total": float(new_item.get("line_total", 0)),
                "labor_hours": float(new_item.get("labor_hours", 0)),
                "phase_week": int(new_item.get("phase_week", 1)),
            }
            
            # Ensure line_total is calculated
            if item["line_total"] == 0 and item["quantity"] and item["unit_price"]:
                item["line_total"] = item["quantity"] * item["unit_price"]
            
            items.append(item)
            stats["items_added"] += 1
        
        # 4. Apply regional adjustment to ALL items
        regional = review_plan.get("regional_adjustment", {})
        multiplier = regional.get("multiplier", 1.0)
        if multiplier and multiplier != 1.0:
            stats["regional_multiplier"] = multiplier
            for item in items:
                line_total = item.get("line_total", 0)
                item["price_multiplier"] = multiplier
                item["adjusted_price"] = round(line_total * multiplier, 2)
                item["adjustment_reason"] = regional.get("reasoning", "Regional adjustment")
        else:
            # No adjustment - adjusted_price equals line_total
            for item in items:
                item["price_multiplier"] = 1.0
                item["adjusted_price"] = item.get("line_total", 0)
                item["adjustment_reason"] = "No regional adjustment"
        
        return items, stats

    def _build_phase_3_output(
        self,
        items: List[Dict[str, Any]],
        review_plan: Dict[str, Any],
        apply_stats: Dict[str, Any],
        listing_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the Phase 3 output structure from applied plan."""
        
        # Calculate totals
        pem_subtotal = sum(item.get("adjusted_price", item.get("line_total", 0)) for item in items)
        overhead = round(pem_subtotal * 0.13, 2)
        profit = round(pem_subtotal * 0.06, 2)
        subtotal = pem_subtotal + overhead + profit
        iva = round(subtotal * 0.21, 2)
        final_total = round(subtotal + iva, 2)
        
        sqm = listing_data.get("sqm", 81) if listing_data else 81
        cost_per_sqm = round(final_total / sqm, 2) if sqm else 0
        
        # Get analysis from plan
        analysis = review_plan.get("review_analysis", {})
        
        return {
            "items": items,
            "items_added": [f"ITEM_{len(items) - apply_stats['items_added'] + i + 1:03d}" 
                          for i in range(apply_stats["items_added"])],
            "items_added_reasoning": [item.get("reason", "") 
                                     for item in review_plan.get("items_to_add", [])],
            "sequencing_fixes": review_plan.get("sequencing_changes", []),
            "regional_adjustments": [review_plan.get("regional_adjustment", {})],
            "pem_subtotal": round(pem_subtotal, 2),
            "overhead_13pct": overhead,
            "profit_6pct": profit,
            "iva_21pct": iva,
            "final_total_with_iva": final_total,
            "cost_per_sqm": cost_per_sqm,
            "cost_per_sqm_assessment": self._assess_cost_per_sqm(cost_per_sqm),
            "confidence_score": analysis.get("confidence_score", 80),
            "risk_flags": [{"flag": f, "severity": "medium"} for f in analysis.get("risk_flags", [])],
            "recommendations": analysis.get("gaps_found", []),
            "sanity_check_passed": cost_per_sqm < 1500,  # Reasonable threshold
            "review_notes": analysis.get("errors_corrected", []),
            "_plan": review_plan,  # Store plan for debugging
            "_stats": apply_stats,
        }

    def _assess_cost_per_sqm(self, cost_per_sqm: float) -> str:
        """Assess whether cost per sqm is reasonable."""
        if cost_per_sqm < 200:
            return "Very light renovation (cosmetic only)"
        elif cost_per_sqm < 400:
            return "Light renovation (paint, floors, bathroom refresh)"
        elif cost_per_sqm < 600:
            return "Standard renovation (kitchen, bathrooms, electrical)"
        elif cost_per_sqm < 900:
            return "High-quality renovation (premium finishes)"
        elif cost_per_sqm < 1200:
            return "Premium renovation (structural + high-end)"
        else:
            return "Luxury renovation (exceptional scope)"
    
    # =========================================================================
    # PHASE 4: RENDERING PROMPTS (LLM) - Internal execution
    # =========================================================================
    
    async def _execute_phase_4_rendering_prompts(
        self,
        room_photos: List[Dict[str, Any]],
        package_type: str,
        listing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Internal Phase 4 execution called from estimate()."""
        return await self.generate_rendering_prompts(
            room_photos=room_photos,
            package_type=package_type,
            listing_id=listing_id
        )
    
    async def generate_rendering_prompts(
        self,
        room_photos: List[Dict[str, Any]],
        package_type: str = "fair_market",
        listing_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Phase 4: Generate AI image transformation prompts for each room.
        
        Args:
            room_photos: List of {room_id, room_name, photo_url, photo_bytes?}
            package_type: Package type for styling
            listing_id: For checkpointing
        
        Returns:
            Phase 4 output with room_prompts, hero_room_id, etc.
        """
        phase_num = 4
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]
        
        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 4 checkpoint found - loading from storage")
            return self.phase_outputs.get(4, {})
        
        if not self.current_items:
            logger.warning("No items available - Phase 4 will have limited context")
        
        self._log_phase_start(phase_num, "RENDERING PROMPTS (Pro)")
        
        phase_start = datetime.now()
        phase_config = PHASES_V2_CONFIG[phase_num]
        
        logger.info(f"  Rooms: {len(room_photos)}")
        
        # Fetch photo bytes if not provided
        import httpx
        import base64
        
        photos_with_bytes = []
        async with httpx.AsyncClient(timeout=30) as client:
            for room in room_photos:
                room_name = room.get('room_name', room.get('room_id', 'unknown'))
                
                if room.get("photo_bytes"):
                    photos_with_bytes.append(room)
                elif room.get("photo_url"):
                    try:
                        response = await client.get(room["photo_url"])
                        if response.status_code == 200:
                            room["photo_bytes"] = response.content
                            room["content_type"] = response.headers.get("content-type", "image/jpeg")
                            photos_with_bytes.append(room)
                            logger.info(f"    ✓ Fetched: {room_name}")
                    except Exception as e:
                        logger.error(f"    ✗ Failed: {room_name} - {e}")
        
        if not photos_with_bytes:
            raise PhaseError(
                phase_number=phase_num,
                phase_name="rendering_prompts",
                message="No photos could be fetched for Phase 4",
            )
        
        # Build image parts
        image_parts = []
        for room in photos_with_bytes:
            if room.get("photo_bytes"):
                encoded = base64.b64encode(room["photo_bytes"]).decode()
                image_parts.append({
                    "mime_type": room.get("content_type", "image/jpeg"),
                    "data": encoded
                })
        
        # Build Phase 4 prompt
        phase_prompt = self._build_phase_4_prompt(photos_with_bytes, package_type)
        full_prompt = f"{self.cached_context}\n\n{phase_prompt}"
        
        # Get schema
        schema = get_schema_for_phase_v1(phase_num)
        
        # Call Gemini with images
        response = await call_gemini(
            prompt=full_prompt,
            images=image_parts,
            model=phase_config['model'],  # flash for speed
            temperature=phase_config['temperature'],
            max_tokens=self.max_output_tokens,
            response_schema=schema,
            # No thinking_level - use flash as configured
        )
        
        if not response.success:
            raise GeminiError(
                phase_name="rendering_prompts",
                model=phase_config['model'],
                error_message=str(response.error),
                response_text=response.text
            )
        
        # Parse response
        phase_4_output = self._parse_json_response(response.text, phase_num)
        
        # Add before_url to each room prompt
        for room_prompt in phase_4_output.get("room_prompts", []):
            photo_index = room_prompt.get("photo_index", 0)
            if photo_index < len(photos_with_bytes):
                room_prompt["before_url"] = photos_with_bytes[photo_index].get("photo_url", "")
        
        self.phase_outputs[phase_num] = phase_4_output
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration
        
        logger.info(f"  ✓ Phase 4: {len(phase_4_output.get('room_prompts', []))} room prompts generated")
        logger.info(f"  🎨 Hero room: {phase_4_output.get('hero_room_id', 'N/A')}")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")
        
        self.checkpoints_completed.append(checkpoint)
        
        return phase_4_output
    
    def _build_phase_4_prompt(
        self,
        room_photos: List[Dict[str, Any]],
        package_type: str
    ) -> str:
        """Build the Phase 4 prompt with items context."""
        # Group items by room
        items_by_room: Dict[str, List[Dict[str, Any]]] = {}
        for item in self.current_items:
            room_id = item.get("room_id", "general")
            if room_id not in items_by_room:
                items_by_room[room_id] = []
            items_by_room[room_id].append(item)
        
        # Build room descriptions
        room_descriptions = []
        for i, room in enumerate(room_photos):
            room_id = room.get("room_id", f"room_{i}")
            room_name = room.get("room_name", room_id)
            
            desc = f"\n### ROOM {i+1}: {room_name} (room_id: {room_id})\n"
            desc += f"Photo: IMAGE_{i+1} (photo_index: {i})\n\n"
            
            if room_id in items_by_room:
                desc += "PRICED ITEMS FOR THIS ROOM:\n"
                for item in items_by_room[room_id][:15]:
                    unit_price = item.get('unit_price', 0)
                    desc += f"  - {item.get('name', '')} ({item.get('quantity', '')} {item.get('unit', '')} @ €{unit_price})\n"
            
            room_descriptions.append(desc)
        
        template = get_prompt_for_phase(4)
        
        return f"""
═══════════════════════════════════════════════════════════════════════════════
PHASE 4 CONTEXT
═══════════════════════════════════════════════════════════════════════════════

PACKAGE TYPE: {package_type.upper()}
TOTAL ITEMS: {len(self.current_items)}

ROOMS TO TRANSFORM ({len(room_photos)} rooms):
{''.join(room_descriptions)}

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════════════════════

{template.format(task="Generate rendering prompts", previous_output="See above")}
"""
    
    # =========================================================================
    # PHASE 5: IMAGE GENERATION (Gemini 2.5 Flash Image)
    # =========================================================================
    
    async def _execute_phase_5_image_generation(
        self,
        room_prompts: List[Dict[str, Any]],
        room_photos: List[Dict[str, Any]],
        listing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Internal Phase 5 execution called from estimate()."""
        return await self.generate_images(
            room_prompts=room_prompts,
            original_photos=room_photos,
            listing_id=listing_id
        )
    
    async def generate_images(
        self,
        room_prompts: List[Dict[str, Any]],
        original_photos: List[Dict[str, Any]],
        listing_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Phase 5: Generate before/after images using Gemini 2.5 Flash Image.
        
        Uses call_gemini_image to transform room photos based on Phase 4 prompts.
        
        Args:
            room_prompts: From Phase 4 output
            original_photos: Original room photos (before images)
            listing_id: For checkpointing
        
        Returns:
            Phase 5 output with generated image data
        """
        import httpx
        import base64
        
        phase_num = 5
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]
        
        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 5 checkpoint found - loading from storage")
            return self.phase_outputs.get(5, {})
        
        self._log_phase_start(phase_num, "IMAGE GENERATION (Gemini Flash Image)")
        
        phase_start = datetime.now()
        
        # Build URL map from original photos
        photo_url_map = {}
        for photo in original_photos:
            room_id = photo.get("room_id")
            if room_id:
                photo_url_map[room_id] = photo.get("photo_url", "")
        
        generated_images = []
        images_generated = 0
        errors = []
        
        for room_prompt in room_prompts:
            room_id = room_prompt.get("room_id")
            room_name = room_prompt.get("room_name", room_id)
            transformation_prompt = room_prompt.get("transformation_prompt", "")
            before_url = room_prompt.get("before_url") or photo_url_map.get(room_id, "")
            
            if not transformation_prompt:
                logger.warning(f"    ⚠ No transformation prompt for {room_name}")
                generated_images.append({
                    "room_id": room_id,
                    "room_name": room_name,
                    "before_url": before_url,
                    "after_data": None,
                    "error": "No transformation prompt",
                })
                continue
            
            if not before_url:
                logger.warning(f"    ⚠ No before photo for {room_name}")
                generated_images.append({
                    "room_id": room_id,
                    "room_name": room_name,
                    "before_url": None,
                    "after_data": None,
                    "error": "No before photo URL",
                })
                continue
            
            try:
                logger.info(f"    🖼️ Generating image for {room_name}...")
                
                # Fetch the before photo
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(before_url)
                    if response.status_code != 200:
                        raise ValueError(f"Failed to fetch photo: {response.status_code}")
                    
                    photo_base64 = base64.b64encode(response.content).decode()
                    content_type = response.headers.get("content-type", "image/jpeg")
                
                # Build full prompt with structural constraints
                full_prompt = f"""{transformation_prompt}

CRITICAL CONSTRAINTS - DO NOT VIOLATE:
- Camera angle: IDENTICAL to input image
- Walls, doors, windows: DO NOT move, add, or remove
- Floor plan: DO NOT change room shape or dimensions
- Change ONLY: surfaces, materials, colors, fixtures, finishes
- Output: Photorealistic 16:9 aspect ratio image"""
                
                # Call Gemini image generation
                result = await call_gemini_image(
                    prompt=full_prompt,
                    image_data=photo_base64,
                    image_mime_type=content_type,
                    model="pro-image",  # Uses gemini-2.0-flash-exp for image gen
                    temperature=1.0,
                )
                
                if result.get("success") and result.get("image_data"):
                    generated_images.append({
                        "room_id": room_id,
                        "room_name": room_name,
                        "before_url": before_url,
                        "after_data": result["image_data"],  # Base64 image data
                        "transformation_prompt": transformation_prompt,
                    })
                    images_generated += 1
                    logger.info(f"    ✅ Generated image for {room_name}")
                else:
                    error_msg = result.get("error", "Unknown error")
                    errors.append({"room_id": room_id, "error": error_msg})
                    generated_images.append({
                        "room_id": room_id,
                        "room_name": room_name,
                        "before_url": before_url,
                        "after_data": None,
                        "error": error_msg,
                    })
                    logger.error(f"    ✗ Failed for {room_name}: {error_msg}")
                    
            except Exception as e:
                logger.error(f"    ✗ Error generating image for {room_name}: {e}")
                errors.append({"room_id": room_id, "error": str(e)})
                generated_images.append({
                    "room_id": room_id,
                    "room_name": room_name,
                    "before_url": before_url,
                    "after_data": None,
                    "error": str(e),
                })
        
        phase_5_output = {
            "generated_images": generated_images,
            "hero_room_id": self.phase_outputs.get(4, {}).get("hero_room_id"),
            "images_generated": images_generated,
            "images_failed": len(errors),
            "errors": errors,
        }
        
        self.phase_outputs[phase_num] = phase_5_output
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration
        
        logger.info(f"  ✓ Phase 5: {images_generated}/{len(room_prompts)} images generated")
        if errors:
            logger.warning(f"  ⚠ {len(errors)} images failed")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")
        
        self.checkpoints_completed.append(checkpoint)
        
        return phase_5_output
    
    # Phase 6 (20-minute viewing checklist) removed.
    
    # =========================================================================
    # PHASE 7: ELI5 ROOM SUMMARIES (LLM) - Internal execution
    # =========================================================================
    
    async def _execute_phase_7_eli5_summaries(
        self,
        listing_data: Dict[str, Any],
        listing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Internal Phase 7 execution called from estimate()."""
        return await self.generate_eli5_summaries(
            listing_data=listing_data,
            listing_id=listing_id
        )
    
    async def generate_eli5_summaries(
        self,
        listing_data: Dict[str, Any],
        listing_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Phase 7: Generate plain-language room summaries for buyers.
        
        Args:
            listing_data: Listing info
            listing_id: For checkpointing
        
        Returns:
            Phase 7 output with ELI5 summaries
        """
        phase_num = 7
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]
        
        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 7 checkpoint found - loading from storage")
            return self.phase_outputs.get(7, {})
        
        if not self.current_items:
            raise PhaseError(
                phase_number=phase_num,
                phase_name="eli5_summaries",
                message="No items available - run estimate() first",
            )
        
        self._log_phase_start(phase_num, "ELI5 ROOM SUMMARIES (Flash)")
        
        phase_start = datetime.now()
        phase_config = PHASES_V2_CONFIG[phase_num]
        
        # Get Phase 3 totals
        phase_3 = self.phase_outputs.get(3, {})
        final_total = phase_3.get("final_total_with_iva", 0)
        total_weeks = phase_3.get("total_weeks") or self.phase_outputs.get(1, {}).get("total_weeks", 10)
        energy = phase_3.get("energy_compliance", {})
        
        # Group items by room for summaries
        items_by_room: Dict[str, List[Dict[str, Any]]] = {}
        for item in self.current_items:
            room_id = item.get("room_id", "general")
            if room_id not in items_by_room:
                items_by_room[room_id] = []
            items_by_room[room_id].append(item)
        
        room_summaries = []
        for room_id, items in items_by_room.items():
            room_cost = sum(item.get("adjusted_price", item.get("line_total", 0)) or 0 for item in items)
            room_summaries.append(f"- {room_id}: {len(items)} items, €{room_cost:,.0f}")
        
        # Build prompt
        template = get_prompt_for_phase(phase_num)
        address = listing_data.get('address', '') or listing_data.get('formatted_address', '') or 'Propiedad'
        
        prompt = f"""
═══════════════════════════════════════════════════════════════════════════════
PHASE 7: ELI5 SUMMARIES
═══════════════════════════════════════════════════════════════════════════════

PROPERTY: {address}
TOTAL COST: €{final_total:,.2f} (incl IVA)
TOTAL WEEKS: {total_weeks}

ENERGY:
- Current rating: {energy.get('current_rating', 'Unknown')}
- Target rating: {energy.get('target_rating', 'Unknown')}
- Measures: {energy.get('measures_included', [])}

ROOM BREAKDOWN:
{chr(10).join(room_summaries)}

COMPLETE PRICED ITEMS:
{json.dumps(self.current_items, indent=2, ensure_ascii=False)[:10000]}

{template.format(task="Generate plain-language summaries", previous_output="See above")}
"""
        
        schema = get_schema_for_phase_v1(phase_num)
        
        response = await call_gemini(
            prompt=prompt,
            model=phase_config['model'],
            response_schema=schema,
            temperature=phase_config['temperature'],
            max_tokens=self.max_output_tokens,
            system_instruction=PHASE_SYSTEM_INSTRUCTION,
        )
        
        if not response.success:
            raise GeminiError(
                phase_name="eli5_summaries",
                model=phase_config['model'],
                error_message=str(response.error),
                response_text=response.text
            )
        
        phase_7_output = self._parse_json_response(response.text, phase_num)
        
        self.phase_outputs[phase_num] = phase_7_output
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration
        
        rooms_count = len(phase_7_output.get("rooms", []))
        
        logger.info(f"  ✓ Phase 7: {rooms_count} room summaries generated")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")
        
        self.checkpoints_completed.append(checkpoint)
        
        return phase_7_output
    
    # =========================================================================
    # PHASE 8: ARCHITECT REPORT (LLM) - Internal execution
    # =========================================================================
    
    async def _execute_phase_8_architect_report(
        self,
        listing_data: Dict[str, Any],
        listing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Internal Phase 8 execution called from estimate()."""
        return await self.generate_architect_report(
            listing_data=listing_data,
            listing_id=listing_id
        )
    
    async def generate_architect_report(
        self,
        listing_data: Dict[str, Any],
        listing_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Phase 8: Generate professional report by trades for contractors/architects.
        
        Args:
            listing_data: Listing info
            listing_id: For checkpointing
        
        Returns:
            Phase 8 output with architect report
        """
        phase_num = 8
        checkpoint = PHASES_V2_CONFIG[phase_num]["checkpoint"]
        
        if checkpoint in self.checkpoints_completed:
            logger.info(f"  ✓ Phase 8 checkpoint found - loading from storage")
            return self.phase_outputs.get(8, {})
        
        if not self.current_items:
            raise PhaseError(
                phase_number=phase_num,
                phase_name="architect_report",
                message="No items available - run estimate() first",
            )
        
        self._log_phase_start(phase_num, "EXPANDED ARCHITECT REPORT (Pro)")
        
        phase_start = datetime.now()
        phase_config = PHASES_V2_CONFIG[phase_num]
        
        # Get previous phase data
        phase_3 = self.phase_outputs.get(3, {})
        phase_4 = self.phase_outputs.get(4, {})
        
        # Extract concept_narrative from Phase 4 (NEW)
        concept_narrative = phase_4.get("concept_narrative", {})
        
        # Build prompt with full context for expanded report
        template = get_prompt_for_phase(phase_num)
        address = listing_data.get('address', '') or listing_data.get('formatted_address', '') or 'Propiedad'
        
        prompt = f"""
═══════════════════════════════════════════════════════════════════════════════
PHASE 8: EXPANDED ARCHITECT REPORT
═══════════════════════════════════════════════════════════════════════════════

PROPERTY: {address}
ASKING PRICE: €{listing_data.get('price', 0):,.0f}
SIZE: {listing_data.get('sqm', 0)} m²

═══════════════════════════════════════════════════════════════════════════════
TARGET PIR (Property Intelligence Report)
Use this to generate target_pir_summary section
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(self.target_pir, indent=2, ensure_ascii=False)[:12000] if self.target_pir else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
BRACKET PIR (Comparable Properties)
Use this to generate bracket_summary section
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(self.bracket_pir, indent=2, ensure_ascii=False)[:8000] if self.bracket_pir else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
CONCEPT NARRATIVE (from Phase 4)
Copy this into design_concept section
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(concept_narrative, indent=2, ensure_ascii=False) if concept_narrative else "Not available - generate from context"}

═══════════════════════════════════════════════════════════════════════════════
STRATEGIC REASONING
Use this for design direction and terms of reference
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(self.strategic_reasoning, indent=2, ensure_ascii=False)[:6000] if self.strategic_reasoning else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
PHASE 3 OUTPUT (Peer Review with Pricing)
Use this for scope & BOQ sections
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(phase_3, indent=2, ensure_ascii=False)[:12000]}

═══════════════════════════════════════════════════════════════════════════════
COMPLETE PRICED ITEMS
Use this for by_trade and by_room sections
═══════════════════════════════════════════════════════════════════════════════
{json.dumps(self.current_items, indent=2, ensure_ascii=False)[:12000]}

{template.format(task="Generate comprehensive architect brief with all 5 sections", previous_output="See above")}
"""
        
        schema = get_schema_for_phase_v1(phase_num)
        
        response = await call_gemini(
            prompt=prompt,
            model=phase_config['model'],  # flash for speed
            response_schema=schema,
            temperature=phase_config['temperature'],
            max_tokens=self.max_output_tokens,
            system_instruction=PHASE_SYSTEM_INSTRUCTION,
            # No thinking_level - use flash as configured
        )
        
        if not response.success:
            raise GeminiError(
                phase_name="architect_report",
                model=phase_config['model'],
                error_message=str(response.error),
                response_text=response.text
            )
        
        phase_8_output = self._parse_json_response(response.text, phase_num)
        
        self.phase_outputs[phase_num] = phase_8_output
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.phase_times[phase_num] = phase_duration
        
        trades_count = len(phase_8_output.get("by_trade", []))
        confidence = phase_8_output.get("confidence_score", 0)
        
        logger.info(f"  ✓ Phase 8: Report generated with {trades_count} trade sections")
        logger.info(f"  📊 Confidence: {confidence}%")
        logger.info(f"  ⏱ Duration: {phase_duration:.1f}s")
        logger.info(f"  💾 CHECKPOINT: {checkpoint}")
        
        self.checkpoints_completed.append(checkpoint)
        
        return phase_8_output
    
    # =========================================================================
    # CONTEXT BUILDING
    # =========================================================================
    
    def _build_cached_context(
        self,
        target_pir: Dict[str, Any],
        bracket_pir: Dict[str, Any],
        strategic_reasoning: Dict[str, Any],
        listing_data: Dict[str, Any],
        package_type: str,
        smart_m2_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the FULL cached context for all phases.
        
        This includes:
        - BCCA Index (FULL ~12,565 items)
        - FFE Index (FULL ~207 items)
        - ALL THREE knowledge graphs (energy, process, design)
        - Target PIR, Bracket PIR, Strategic Reasoning
        - Canonical Room IDs
        - Smart M² data (if available)
        """
        # Load BCCA optimized index (DESC_100 + full structure)
        # bcca_optimized_index.txt: CODE|UNIT|PRICE|DESC_100|LABOR_HOURS|BREAKDOWN (~322K tokens)
        # - Keeps UNIT, LABOR_HOURS, BREAKDOWN (critical for quantities/timeline)
        # - Uses AI-compressed 100-char descriptions (55% smaller than full)
        bcca_index = self._load_file("bcca_optimized_index.txt")
        ffe_index = self._load_file("ffe_index.txt")
        
        # Load ALL knowledge graphs
        energy_kg = self._load_json("energy_knowledge.json", from_standards=True)
        process_kg = self._load_json("renovation_process_knowledge.json", from_standards=True)
        design_kg = self._load_json("interior_design_knowledge.json", from_standards=True)
        
        # Build canonical rooms section
        rooms_section = self._build_canonical_rooms_section(self.canonical_room_ids)
        
        # Build smart m² section if available
        smart_m2_section = ""
        if smart_m2_data:
            smart_m2_section = self._build_smart_m2_section(smart_m2_data)
        
        # Handle None strategic_reasoning
        sr = strategic_reasoning or {}
        
        context = f"""
═══════════════════════════════════════════════════════════════════════════════
V1.0 UNIFIED ESTIMATOR - 8-PHASE ULTIMATE PIPELINE
═══════════════════════════════════════════════════════════════════════════════

{PHASE_SYSTEM_INSTRUCTION}

PACKAGE TYPE: {package_type.upper()}

{rooms_section}
{smart_m2_section}
═══════════════════════════════════════════════════════════════════════════════
BRACKET PIR - What This Price Bracket "Looks Like"
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(bracket_pir, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
🔴 STRATEGIC REASONING LAYER - PRE-SCOPE BRIEF (MANDATORY READING) 🔴
═══════════════════════════════════════════════════════════════════════════════

{sr.get('strategic_summary', 'Not available')}

STRUCTURAL REALITIES:
{sr.get('structural_realities', 'Not available')}

INHERENT ADVANTAGES:
{sr.get('inherent_advantages', 'Not available')}

BRACKET ALIGNMENT:
{sr.get('bracket_alignment_analysis', 'Not available')}

IMPOSSIBILITIES:
{sr.get('impossibilities', 'Not available')}

OPPORTUNITY ZONES:
{sr.get('opportunity_zones', 'Not available')}

STRATEGIC DIRECTION:
{sr.get('strategic_direction', 'Not available')}

SCOPER GUIDANCE:
{sr.get('scoper_guidance', 'Not available')}

═══════════════════════════════════════════════════════════════════════════════
TARGET PROPERTY - Current State
═══════════════════════════════════════════════════════════════════════════════

LISTING DATA:
{json.dumps(listing_data, indent=2, ensure_ascii=False)}

PROPERTY INTELLIGENCE REPORT (PIR):
{json.dumps(target_pir, indent=2, ensure_ascii=False)}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: ENERGY EFFICIENCY
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(energy_kg, indent=2, ensure_ascii=False) if energy_kg else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: RENOVATION PROCESS
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(process_kg, indent=2, ensure_ascii=False) if process_kg else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
KNOWLEDGE GRAPH: INTERIOR DESIGN
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(design_kg, indent=2, ensure_ascii=False) if design_kg else "Not available"}

═══════════════════════════════════════════════════════════════════════════════
BCCA INDEX - {len(bcca_index.splitlines()):,} SPANISH CONSTRUCTION WORK ITEMS
═══════════════════════════════════════════════════════════════════════════════

COLUMN FORMAT (pipe-separated):
  Col 1: CODE         → Use for bcca_code field
  Col 2: UNIT         → Use for unit field (m2, ud, ml, etc.)
  Col 3: PRICE        → Use for unit_price field (EUR per unit)
  Col 4: DESC_100     → Use for bcca_description field
  Col 5: LABOR_HOURS  → Use for labor_hours calculation (hours per unit)
  Col 6: BREAKDOWN    → Reference only (labor composition)

EXAMPLE ROW:
  01ADS00001|m2|60.13|Demolición tabique...|2.0|1.00h Peón ordinario...
  
  For 10m² demolition using this code:
  - bcca_code: "01ADS00001"
  - unit: "m2"
  - unit_price: 60.13 (Col 3)
  - quantity: 10
  - line_total: 60.13 × 10 = 601.30
  - labor_hours: 2.0 × 10 = 20.0 (Col 5 × quantity)

CRITICAL: For EVERY item, you MUST extract BOTH:
  1. unit_price from Col 3 (PRICE)
  2. labor_hours from Col 5 (LABOR_HOURS) × quantity
═══════════════════════════════════════════════════════════════════════════════

{bcca_index}

═══════════════════════════════════════════════════════════════════════════════
FFE INDEX - FURNITURE, FIXTURES & EQUIPMENT
Format: CODE|NAME|DESCRIPTION|BUDGET_LOW|BUDGET_MID|BUDGET_HIGH|UNIT|CATEGORY

IMPORTANT: FFE items are the PRODUCTS (lamp, faucet, appliance).
The BCCA INDEX above contains the INSTALLATION work items.
Every FFE item needs a paired ffe_install_bcca code from the BCCA index above.
Example: FFE gives you the pendant lamp; BCCA gives you "electrical point installation".

NO LIMITS: Include ALL work items needed. A proper renovation can have 100+ items.
═══════════════════════════════════════════════════════════════════════════════

{ffe_index}
"""
        
        return context
    
    def _build_canonical_rooms_section(
        self,
        canonical_room_ids: Optional[List[Dict[str, str]]]
    ) -> str:
        """Build the canonical rooms constraint section."""
        if not canonical_room_ids:
            return ""
        
        room_lines = []
        for room in canonical_room_ids:
            room_id = room.get("room_id", "unknown")
            room_name = room.get("room_name", room_id)
            room_lines.append(f'  - room_id: "{room_id}"  →  {room_name}')
        
        return f"""
═══════════════════════════════════════════════════════════════════════════════
CANONICAL ROOM IDS (MANDATORY - USE EXACTLY THESE)
═══════════════════════════════════════════════════════════════════════════════

ROOMS IN THIS PROPERTY:
{chr(10).join(room_lines)}

For items that apply to the whole property, use room_id: "general"

"""
    
    def _build_smart_m2_section(self, smart_m2_data: Dict[str, Any]) -> str:
        """Build the Smart M² dimensions section for context."""
        if not smart_m2_data:
            return ""
        
        rooms = smart_m2_data.get("rooms", [])
        if not rooms:
            return ""
        
        room_lines = []
        for room in rooms:
            cluster_name = room.get("cluster_name", "Unknown")
            m2 = room.get("estimated_m2", 0)
            dims = room.get("estimated_dimensions", {})
            length = dims.get("length_m", 0)
            width = dims.get("width_m", 0)
            height = room.get("estimated_height_m", 2.7)
            perimeter = room.get("perimeter_m", 0)
            
            room_lines.append(
                f"  - {cluster_name}: ~{m2}m² ({length}m × {width}m), "
                f"height {height}m, perimeter {perimeter}m"
            )
        
        return f"""
═══════════════════════════════════════════════════════════════════════════════
SMART M² - ESTIMATED ROOM DIMENSIONS
═══════════════════════════════════════════════════════════════════════════════

{chr(10).join(room_lines)}

Use these dimensions in your quantity formulas where applicable.
"""
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _init_price_lookups(self):
        """
        Initialize BCCA and FFE price lookup tools.
        
        NOTE: These are kept for potential validation in Phase 3, but Phase 1 
        now calculates prices directly from the BCCA index in context.
        """
        try:
            self.bcca_lookup = BCCAPriceLookup()
            logger.info("  ✓ BCCA price lookup initialized (for validation)")
        except FileNotFoundError as e:
            logger.warning(f"  ⚠ BCCA database not found (optional): {e}")
            self.bcca_lookup = None

        try:
            self.ffe_lookup = FFEPriceLookup()
            logger.info("  ✓ FFE price lookup initialized (for validation)")
        except FileNotFoundError as e:
            logger.warning(f"  ⚠ FFE database not found (optional): {e}")
            self.ffe_lookup = None
    
    def _load_file(self, filename: str) -> str:
        """Load a file from the data directory."""
        path = self.data_dir / filename
        if not path.exists():
            logger.warning(f"Data file not found: {path}")
            return f"[File not found: {filename}]"
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_json(self, filename: str, from_standards: bool = False) -> Optional[Dict[str, Any]]:
        """Load a JSON file from data or standards directory."""
        if from_standards:
            path = self.standards_dir / filename
        else:
            path = self.data_dir / filename
        
        if not path.exists():
            logger.warning(f"JSON file not found: {path}")
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {path}: {e}")
            return None
    
    async def _call_gemini_with_retry(
        self,
        prompt: str,
        model: str,
        temperature: float,
        schema: Dict[str, Any],
        phase_num: int,
        max_retries: int = 2
    ):
        """Call Gemini with retry logic for JSON parse errors."""
        phase_config = PHASES_V2_CONFIG[phase_num]
        
        for attempt in range(max_retries):
            if attempt == 0:
                logger.info(f"    Model: {model}, Temp: {temperature}")
            else:
                logger.warning(f"  ⟳ Retry {attempt}/{max_retries-1}...")
            
            response = await call_gemini(
                prompt=prompt,
                model=model,  # Uses phase_config model (flash for post-BOQ)
                temperature=temperature,
                max_tokens=self.max_output_tokens,
                response_schema=schema,
                # No thinking_level - respect the configured model
            )
            
            if not response.success:
                raise GeminiError(
                    phase_name=phase_config["name"],
                    model=model,
                    error_message=str(response.error),
                    response_text=response.text
                )
            
            # Try to parse - if successful, return
            try:
                self._parse_json_response(response.text, phase_num)
                return response
            except json.JSONDecodeError as e:
                logger.error(f"  ✗ Phase {phase_num} JSON parse error: {e}")
                logger.error(f"    Response (first 500 chars): {(response.text or '')[:500]}")
                
                if attempt < max_retries - 1:
                    continue
                
                raise PhaseError(
                    phase_number=phase_num,
                    phase_name=phase_config["name"],
                    message=f"JSON parse error after {max_retries} attempts: {e}"
                )
        
        raise PhaseError(
            phase_number=phase_num,
            phase_name=phase_config["name"],
            message="Unexpected error in _call_gemini_with_retry"
        )
    
    def _parse_json_response(self, text: str, phase_num: int) -> Dict[str, Any]:
        """Parse JSON response with sanitization."""
        text = (text or "").strip()
        
        # Strip markdown wrappers
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        # Find JSON start
        json_start = text.find('{')
        if json_start == -1:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        if json_start > 0:
            logger.warning(f"    ⚠ Stripping {json_start} chars before JSON")
        text = text[json_start:]
        
        # Find matching closing brace
        brace_count = 0
        json_end = 0
        for i, c in enumerate(text):
            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end > 0 and json_end < len(text):
            logger.warning(f"    ⚠ Stripping {len(text) - json_end} chars after JSON")
            text = text[:json_end]
        
        # Sanitize and parse
        sanitized_text = sanitize_gemini_json(text.strip())
        return json.loads(sanitized_text)
    
    def _build_unified_estimate(
        self,
        package_type: str,
        listing_data: Dict[str, Any],
        total_duration: float
    ) -> Dict[str, Any]:
        """Build unified estimate from all phase outputs."""
        phase_3 = self.phase_outputs.get(3, {})
        
        # Calculate totals from items
        total_cost = sum(
            item.get("adjusted_price", item.get("line_total", 0)) or 0
            for item in self.current_items
        )
        
        # Cost by system
        cost_by_system: Dict[str, float] = {}
        for item in self.current_items:
            system = item.get("system", "other")
            cost = item.get("adjusted_price", item.get("line_total", 0)) or 0
            cost_by_system[system] = cost_by_system.get(system, 0) + cost
        
        # Cost by room
        cost_by_room: Dict[str, float] = {}
        for item in self.current_items:
            room_id = item.get("room_id", "general")
            cost = item.get("adjusted_price", item.get("line_total", 0)) or 0
            cost_by_room[room_id] = cost_by_room.get(room_id, 0) + cost
        
        # Area for cost/m² calculation
        sqm = listing_data.get("sqm", 81)
        cost_per_sqm = round(total_cost / sqm, 2) if sqm > 0 else 0
        
        # Use Phase 3 totals if available
        pem = phase_3.get("pem_subtotal", total_cost)
        overhead = phase_3.get("overhead_13pct", pem * 0.13)
        profit = phase_3.get("profit_6pct", pem * 0.06)
        subtotal = pem + overhead + profit
        iva = phase_3.get("iva_21pct", subtotal * 0.21)
        final_with_iva = phase_3.get("final_total_with_iva", subtotal + iva)
        
        unified = {
            # V1.0 Metadata
            "v1_8_phase_architecture": True,
            "pipeline_version": "V1.0",
            "package_type": package_type,
            "generated_at": datetime.now().isoformat(),
            "estimation_duration_seconds": total_duration,
            
            # Item counts
            "item_counts": {
                "phase_1_with_pricing": len(self.phase_outputs.get(1, {}).get("items", [])),
                "phase_3_reviewed": len(self.phase_outputs.get(3, {}).get("items", [])),
                "final_total": len(self.current_items),
            },
            
            # Costs
            "pem_subtotal": round(pem, 2),
            "overhead_13pct": round(overhead, 2),
            "profit_6pct": round(profit, 2),
            "iva_21pct": round(iva, 2),
            "total_cost": round(total_cost, 2),
            "cost_per_sqm": cost_per_sqm,
            "cost_by_system": {k: round(v, 2) for k, v in cost_by_system.items()},
            "cost_by_room": {k: round(v, 2) for k, v in cost_by_room.items()},
            "final_total_with_iva": round(final_with_iva, 2),
            
            # All items
            "priced_items": self.current_items,
            "line_items_count": len(self.current_items),
            
            # Timeline
            "total_weeks": self.phase_outputs.get(1, {}).get("total_weeks", 10),
            "critical_path": self.phase_outputs.get(1, {}).get("critical_path", []),
            
            # Quality metrics
            "confidence_score": phase_3.get("confidence_score", 80),
            "sanity_check_passed": phase_3.get("sanity_check_passed", True),
            "risk_flags": phase_3.get("risk_flags", []),
            "recommendations": phase_3.get("recommendations", []),
            
            # Energy
            "energy_compliance": phase_3.get("energy_compliance", {}),
            
            # Regional adjustments
            "regional_adjustments": phase_3.get("regional_adjustments", []),
            
            # Phase outputs (for debugging/transparency)
            "phase_outputs": {
                f"phase_{i}": self.phase_outputs.get(i, {})
                for i in range(1, 9)
            },
            "phase_times": self.phase_times.copy(),
            "checkpoints_completed": self.checkpoints_completed.copy(),
        }
        
        logger.info(f"  → Unified estimate built: {len(self.current_items)} items, €{final_with_iva:,.2f}")
        
        return unified
    
    # =========================================================================
    # LOGGING HELPERS
    # =========================================================================
    
    def _log_banner(self, title: str):
        """Log a section banner."""
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"  {title}")
        logger.info("=" * 70)
    
    def _log_separator(self):
        """Log a separator line."""
        logger.info("=" * 70)
    
    def _log_phase_start(self, phase_num: int, phase_name: str):
        """Log phase start banner."""
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"  PHASE {phase_num}: {phase_name}")
        logger.info("=" * 70)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_phase_output(self, phase_num: int) -> Optional[Any]:
        """Get the output of a specific phase."""
        return self.phase_outputs.get(phase_num)
    
    def get_all_phase_outputs(self) -> Dict[int, Any]:
        """Get all phase outputs."""
        return self.phase_outputs.copy()
    
    def get_current_items(self) -> List[Dict[str, Any]]:
        """Get current items array."""
        return self.current_items.copy()
    
    def get_checkpoints_completed(self) -> List[str]:
        """Get list of completed checkpoints."""
        return self.checkpoints_completed.copy()
