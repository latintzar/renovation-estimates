"""
=========================================================
PHASE 2: SCOPE MAPPER
=========================================================
Maps detected conditions from Phase 1 to remedial task scopes.

Pipeline Flow:
  Phase 1 (Condition Assessment) → Phase 2 (Scope Mapper) → Phase 3 (Pricing)

This step:
1. Fetches Phase 1 condition assessments from DB
2. Loads rules_engine_v2.json for task definitions
3. Calls Gemini to consolidate and specify tasks
4. Saves ESSENTIAL and MODERN package scopes to DB

Output: Two package scopes ready for Phase 3 pricing
=========================================================
"""

import json
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict
from pathlib import Path

if TYPE_CHECKING:
    from ..orchestrator import PipelineOrchestrator

from ..gemini_client import call_gemini
from ..prompts.scope_mapper_v2 import (
    build_scope_prompt,
    get_system_context,
    RESPONSE_SCHEMA,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ScopeTask:
    """A single remedial task in a package scope."""
    task_id: str
    title: str
    system: str
    category: str
    regulation: str
    specification: str
    bcca_keywords: List[str]
    quantity_description: str
    rooms_affected: List[str]
    source_conditions: List[str]
    essential_reason: Optional[str] = None  # For ESSENTIAL package
    inherited_from_essential: bool = False   # For MODERN package
    modern_upgrade: Optional[str] = None     # For MODERN package


@dataclass
class PackageScopeResult:
    """Result of scope mapping for one package."""
    package_type: str  # "ESSENTIAL" or "MODERN"
    name: str
    goal: str
    standard: str
    tasks: List[ScopeTask]
    
    @property
    def task_count(self) -> int:
        return len(self.tasks)
    
    @property
    def systems_covered(self) -> List[str]:
        return list(set(t.system for t in self.tasks))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def run_ps2_package_scopes(
    orchestrator: "PipelineOrchestrator",
    listing_id: int,
) -> Dict[str, Any]:
    """
    Phase 2: Map conditions to package scopes.
    
    Prerequisites:
    - Phase 1 (Condition Assessment) must be complete
    
    Returns:
        Dict with essential_package and modern_package scopes
    """
    logger.info(f"[Phase 2] Starting scope mapping for listing {listing_id}")
    
    # =========================================================================
    # STEP 1: Fetch prerequisites
    # =========================================================================
    
    # Get listing data for sqm
    listing = await orchestrator.db.get_listing(listing_id)
    if not listing:
        raise ValueError(f"Listing {listing_id} not found")
    
    sqm = listing.get("sqm") or listing.get("size_m2") or 80  # Default if missing
    
    # Get Phase 1 condition assessments
    assessments = await orchestrator.db.get_condition_assessments(listing_id)
    if not assessments:
        raise ValueError(
            f"No condition assessments found for listing {listing_id}. "
            "Run Phase 1 (Condition Assessment) first."
        )
    
    logger.info(f"[Phase 2] Found {len(assessments)} room assessments")
    
    # Extract year_built from first assessment (they all have the same year)
    year_built = assessments[0].get("year_built") or 1975
    year_source = assessments[0].get("year_source", "conservative_estimate")
    
    # Count total conditions
    total_conditions = sum(
        len(a.get("detected_conditions", [])) 
        for a in assessments
    )
    logger.info(f"[Phase 2] Total conditions to map: {total_conditions}")
    
    if total_conditions == 0:
        logger.warning("[Phase 2] No conditions to map - returning empty scopes")
        return await _save_empty_scopes(orchestrator, listing_id, year_built)
    
    # =========================================================================
    # STEP 2: Call Gemini for scope generation
    # =========================================================================
    
    prompt = build_scope_prompt(
        year_built=year_built,
        year_source=year_source,
        sqm=sqm,
        room_assessments=assessments,
    )
    
    logger.info("[Phase 2] Calling Gemini for scope generation...")
    
    response = await call_gemini(
        prompt=prompt,
        model="gemini-3-pro-preview",
        temperature=0.2,  # Lower for more deterministic output
        max_tokens=30000,
        system_instruction=get_system_context(),
        use_spanish=True,
        response_schema=RESPONSE_SCHEMA,
    )
    
    if not response.success:
        raise ValueError(f"Gemini call failed: {response.error}")
    
    # Parse JSON response
    try:
        scope_data = json.loads(response.text)
        logger.info("[Phase 2] Successfully parsed Gemini response")
    except json.JSONDecodeError as e:
        logger.error(f"[Phase 2] Failed to parse JSON: {e}")
        logger.error(f"[Phase 2] Raw response: {response.text[:1000]}")
        raise ValueError(f"Failed to parse scope response: {e}")
    
    # =========================================================================
    # STEP 3: Process and validate response
    # =========================================================================
    
    essential_data = scope_data.get("essential_package", {})
    modern_data = scope_data.get("modern_package", {})
    consolidation_notes = scope_data.get("consolidation_notes", [])
    
    # Convert to ScopeTask objects
    essential_tasks = _parse_tasks(essential_data.get("tasks", []), is_essential=True)
    modern_tasks = _parse_tasks(modern_data.get("tasks", []), is_essential=False)
    
    logger.info(
        f"[Phase 2] Generated scopes: "
        f"ESSENTIAL={len(essential_tasks)} tasks, "
        f"MODERN={len(modern_tasks)} tasks"
    )
    
    if consolidation_notes:
        logger.info(f"[Phase 2] Consolidation notes: {consolidation_notes[:3]}")
    
    # =========================================================================
    # STEP 4: Save to database
    # =========================================================================
    
    # Save ESSENTIAL package
    await orchestrator.db.save_package_scope(
        listing_id=listing_id,
        package_type="ESSENTIAL",
        name=essential_data.get("name", "Paquete Esencial"),
        goal=essential_data.get("goal", "Cumplimiento legal y seguridad"),
        standard=essential_data.get("standard", "REBT 2002, CTE DB-HS"),
        room_scopes=_group_tasks_by_room(essential_tasks),
    )
    logger.info("[Phase 2] Saved ESSENTIAL package scope")
    
    # Save MODERN package
    await orchestrator.db.save_package_scope(
        listing_id=listing_id,
        package_type="MODERN",
        name=modern_data.get("name", "Paquete Moderno"),
        goal=modern_data.get("goal", "Eficiencia energética y confort"),
        standard=modern_data.get("standard", "CTE DB-HE 2019, Estándares EU 2030"),
        room_scopes=_group_tasks_by_room(modern_tasks),
    )
    logger.info("[Phase 2] Saved MODERN package scope")
    
    # =========================================================================
    # STEP 5: Return summary
    # =========================================================================
    
    return {
        "success": True,
        "listing_id": listing_id,
        "year_built": year_built,
        "year_source": year_source,
        "sqm": sqm,
        "conditions_processed": total_conditions,
        "essential_package": {
            "task_count": len(essential_tasks),
            "systems": list(set(t.system for t in essential_tasks)),
            "goal": essential_data.get("goal"),
        },
        "modern_package": {
            "task_count": len(modern_tasks),
            "systems": list(set(t.system for t in modern_tasks)),
            "goal": modern_data.get("goal"),
            "inherited_from_essential": sum(1 for t in modern_tasks if t.inherited_from_essential),
        },
        "consolidation_notes": consolidation_notes,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_tasks(tasks_data: List[Dict], is_essential: bool) -> List[ScopeTask]:
    """Parse task dictionaries into ScopeTask objects."""
    tasks = []
    for t in tasks_data:
        try:
            task = ScopeTask(
                task_id=t.get("task_id", "unknown"),
                title=t.get("title", "Unknown Task"),
                system=t.get("system", "unknown"),
                category=t.get("category", "UNKNOWN"),
                regulation=t.get("regulation", ""),
                specification=t.get("specification", ""),
                bcca_keywords=t.get("bcca_keywords", []),
                quantity_description=t.get("quantity_description", ""),
                rooms_affected=t.get("rooms_affected", []),
                source_conditions=t.get("source_conditions", []),
                essential_reason=t.get("essential_reason") if is_essential else None,
                inherited_from_essential=t.get("inherited_from_essential", False) if not is_essential else False,
                modern_upgrade=t.get("modern_upgrade") if not is_essential else None,
            )
            tasks.append(task)
        except Exception as e:
            logger.warning(f"[Phase 2] Failed to parse task: {e} - {t}")
    
    return tasks


def _group_tasks_by_room(tasks: List[ScopeTask]) -> List[Dict[str, Any]]:
    """Group tasks by room for database storage."""
    room_tasks = {}
    
    for task in tasks:
        # Each task may affect multiple rooms - create entries for each
        for room in task.rooms_affected:
            if room not in room_tasks:
                room_tasks[room] = {
                    "room_id": room.lower().replace(" ", "_"),
                    "room_name": room,
                    "tasks": [],
                }
            room_tasks[room]["tasks"].append(asdict(task))
    
    return list(room_tasks.values())


async def _save_empty_scopes(
    orchestrator: "PipelineOrchestrator",
    listing_id: int,
    year_built: int,
) -> Dict[str, Any]:
    """Save empty scopes when no conditions are found."""
    
    for package_type in ["ESSENTIAL", "MODERN"]:
        await orchestrator.db.save_package_scope(
            listing_id=listing_id,
            package_type=package_type,
            name=f"Paquete {'Esencial' if package_type == 'ESSENTIAL' else 'Moderno'}",
            goal="No se detectaron condiciones que requieran intervención",
            standard="N/A",
            room_scopes=[],
        )
    
    return {
        "success": True,
        "listing_id": listing_id,
        "year_built": year_built,
        "conditions_processed": 0,
        "essential_package": {"task_count": 0, "systems": [], "goal": "N/A"},
        "modern_package": {"task_count": 0, "systems": [], "goal": "N/A"},
        "consolidation_notes": ["No conditions detected - empty scopes generated"],
    }

