"""
Renovation Pipeline V2 - Shared Schemas
=======================================

Dataclasses used across all 3 pipeline phases:
- Phase 1: Condition Assessment
- Phase 2: Package Scopes
- Phase 3: Pricing

These schemas are the single source of truth.
Frontend TypeScript types must match exactly.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class TriggerType(str, Enum):
    """How a condition was detected."""
    IMPLIED_BY_AGE = "implied_by_age"  # Year dictates risk, no visual proof
    VISUAL_MATCH = "visual_match"       # Seen in photos


class PackageType(str, Enum):
    """The two package categories."""
    ESSENTIAL = "ESSENTIAL"  # ITE/Cédula compliance
    MODERN = "MODERN"        # CTE 2025 / Green Mortgage


class DefectCategory(str, Enum):
    """Categories that determine package assignment."""
    # → ESSENTIAL
    SAFETY = "SAFETY"
    LEGAL = "LEGAL"
    STRUCTURAL = "STRUCTURAL"
    HYGIENE = "HYGIENE"
    # → MODERN
    ENERGY = "ENERGY"
    COMFORT = "COMFORT"
    ACOUSTIC = "ACOUSTIC"


class SystemType(str, Enum):
    """Building systems covered by rules."""
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    ENVELOPE = "envelope"      # Windows, walls, roof
    STRUCTURE = "structure"
    FINISHES = "finishes"
    HVAC = "hvac"
    VENTILATION = "ventilation"


# =============================================================================
# PHASE 1: CONDITION ASSESSMENT
# =============================================================================

@dataclass
class DetectedCondition:
    """A single defect/risk detected in a room (Phase 1 - no package assignment).
    
    Package classification happens in Phase 2 based on rule_id → rules_engine.
    """
    rule_id: str
    trigger_type: str  # TriggerType value
    system: str        # SystemType value
    observation: str   # What was observed or assumed
    confidence: str    # "High", "Medium", "Low"
    risk_label: str    # e.g., "Non-Compliant (REBT 2002)"
    risk_description: str
    category: str      # DefectCategory value (used by Phase 2 for package assignment)
    visual_evidence: Optional[str] = None  # Photo reference if visual_match


@dataclass
class RoomAssessment:
    """Assessment results for a single room."""
    room_id: str
    room_type: str     # e.g., "cocina", "salon", "dormitorio"
    room_name: str     # Display name
    photo_urls: List[str]
    detected_conditions: List[DetectedCondition]
    
    @property
    def defect_count(self) -> int:
        return len(self.detected_conditions)
    
    @property
    def has_essential_defects(self) -> bool:
        essential_cats = {DefectCategory.SAFETY.value, DefectCategory.LEGAL.value, 
                         DefectCategory.STRUCTURAL.value, DefectCategory.HYGIENE.value}
        return any(c.category in essential_cats for c in self.detected_conditions)


class YearConfidence(str, Enum):
    """How confident we are in the year estimate."""
    CADASTRE = "cadastre"              # Direct lookup - HIGH confidence
    STREET_SAMPLING = "street_sampling"  # Multiple samples from street - MEDIUM
    NEIGHBORHOOD_SAMPLING = "neighborhood_sampling"  # Area average - LOW
    CONSERVATIVE_ESTIMATE = "conservative_estimate"  # Fallback 1975 - VERY LOW


@dataclass
class ConditionAssessmentResult:
    """Full condition assessment for a listing."""
    listing_id: int
    year_built: int
    year_source: str  # YearConfidence value - affects how we interpret age-based findings
    room_assessments: List[RoomAssessment]
    # Narrative fields - generated at end of Phase 1
    narrative_summary: Optional[str] = None  # Human-readable assessment summary
    confidence_disclaimer: Optional[str] = None  # "Year estimated, prioritize visual findings"
    created_at: Optional[str] = None
    
    @property
    def total_defects(self) -> int:
        return sum(r.defect_count for r in self.room_assessments)
    
    @property
    def rooms_with_defects(self) -> int:
        return sum(1 for r in self.room_assessments if r.defect_count > 0)
    
    @property
    def visual_findings_count(self) -> int:
        return sum(
            1 for r in self.room_assessments 
            for c in r.detected_conditions 
            if c.trigger_type == TriggerType.VISUAL_MATCH.value
        )
    
    @property
    def age_implied_count(self) -> int:
        return sum(
            1 for r in self.room_assessments 
            for c in r.detected_conditions 
            if c.trigger_type == TriggerType.IMPLIED_BY_AGE.value
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# PHASE 2: PACKAGE SCOPES
# =============================================================================

@dataclass
class ScopeTask:
    """A single remedial task in a package scope."""
    task_id: str
    title: str
    bcca_keyword: str          # For KG Estimator lookup
    defect_source: str         # rule_id that triggered this
    trigger_type: str          # How the defect was detected
    risk_label: str
    regulation: str            # e.g., "REBT 2002", "CTE DB-HE 1"
    category: str              # DefectCategory value
    room: str                  # Room where task applies
    inherited_from: Optional[str] = None   # If inherited from ESSENTIAL
    spec_upgrade: Optional[str] = None     # Upgraded spec for MODERN


@dataclass
class RoomScope:
    """Tasks for a single room within a package."""
    room_id: str
    room_name: str
    tasks: List[ScopeTask]
    
    @property
    def task_count(self) -> int:
        return len(self.tasks)


@dataclass
class PackageScope:
    """Complete scope for one package (ESSENTIAL or MODERN)."""
    package_type: str  # PackageType value
    name: str          # Display name
    goal: str          # e.g., "Pass ITE + Obtain Cédula"
    standard: str      # e.g., "REBT 2002, CTE DB-HS 4"
    room_scopes: List[RoomScope]
    
    @property
    def total_tasks(self) -> int:
        return sum(r.task_count for r in self.room_scopes)
    
    @property
    def all_tasks(self) -> List[ScopeTask]:
        tasks = []
        for room in self.room_scopes:
            tasks.extend(room.tasks)
        return tasks


@dataclass
class PackageScopesResult:
    """Complete scope mapping result for a listing."""
    listing_id: int
    essential: PackageScope
    modern: PackageScope
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# PHASE 3: PRICING
# =============================================================================

@dataclass
class BoQLine:
    """A single line in the Bill of Quantities."""
    bcca_code: str
    description: str
    unit: str          # e.g., "m²", "ud", "ml"
    quantity: float
    unit_price: float
    total: float
    task_id: str       # Links back to ScopeTask
    room: str


@dataclass
class TradeBreakdown:
    """Pricing breakdown for a single trade."""
    trade: str         # e.g., "Electricidad", "Fontanería"
    trade_code: str    # BCCA chapter code
    lines: List[BoQLine]
    subtotal: float


@dataclass
class RoomPricing:
    """Pricing breakdown for a single room."""
    room_id: str
    room_name: str
    lines: List[BoQLine]
    subtotal: float


@dataclass
class PackagePricing:
    """Complete pricing for one package."""
    package_type: str
    total_pem: float   # Presupuesto de Ejecución Material
    total_pec: float   # Presupuesto de Ejecución por Contrata (+19%)
    trade_breakdown: List[TradeBreakdown]
    room_breakdown: List[RoomPricing]
    boq_lines: List[BoQLine]


@dataclass
class PackagePricingResult:
    """Complete pricing result for a listing."""
    listing_id: int
    essential: PackagePricing
    modern: PackagePricing
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# RULES ENGINE TYPES
# =============================================================================

@dataclass
class ConditionAssessmentRule:
    """The assessment part of a rule."""
    prompt_instruction: str
    risk_label: str
    risk_description: str


@dataclass
class RemedialAction:
    """The remedial action for a rule."""
    task_id: str
    bcca_keyword: str
    package: str       # PackageType value
    category: str      # DefectCategory value


@dataclass
class Rule:
    """A single rule from rules_engine_v2.json."""
    id: str
    system: str
    room_types: List[str]
    year_trigger: int
    visual_triggers: List[str]
    condition_assessment: ConditionAssessmentRule
    remedial_action: RemedialAction

