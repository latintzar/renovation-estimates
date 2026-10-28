"""
Property Intelligence Report Schema
PETER AGENTIC V0.3.2

Unified schema for comprehensive property analysis that replaces:
- assess_uniclass.py (systems/products inventory)
- verify_rules.py (age-based rule verification)

Adds:
- Energy profile (from energy_knowledge.json)
- Design assessment (from interior_design_knowledge.json)
- Renovation triggers (from renovation_process_knowledge.json)
- Comparison-ready attributes
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# BUILDING PROFILE
# =============================================================================

class EnergyProfile(BaseModel):
    """Energy assessment from visual inspection + age inference."""
    rating_actual: Optional[str] = Field(None, description="From listing if available (A-G)")
    rating_expected: str = Field(..., description="Inferred from building age")
    climate_zone: str = Field(..., description="Spanish climate zone (A-E)")
    envelope_assessment: Literal["good", "fair", "poor", "very_poor"] = Field(...)
    visible_deficiencies: List[str] = Field(default_factory=list)


class BuildingProfile(BaseModel):
    """Hard facts about the building."""
    year_built: int = Field(...)
    year_source: Literal["cadastre", "listing", "estimate"] = Field(...)
    construction_era: str = Field(..., description="From interior_design_knowledge eras")
    building_type: str = Field(..., description="multi_family_block, townhouse, etc.")
    floor: Optional[int] = Field(None)
    total_floors: Optional[int] = Field(None)
    orientation: Optional[str] = Field(None)
    facade_material: Optional[str] = Field(None)
    energy: EnergyProfile = Field(...)


# =============================================================================
# SYSTEMS & PRODUCTS (Uniclass-based)
# =============================================================================

class SystemInventoryItem(BaseModel):
    """A building system identified in the property (Uniclass Ss codes)."""
    code: str = Field(..., description="Uniclass Ss code")
    title: str = Field(...)
    presence: Literal["visible", "inferred", "absent"] = Field(...)
    condition_ite: Optional[Literal["leve", "importante", "grave", "muy_grave"]] = Field(None)
    notes: Optional[str] = Field(None)


class ProductInventoryItem(BaseModel):
    """A product identified in the property (Uniclass Pr codes)."""
    code: str = Field(..., description="Uniclass Pr code")
    title: str = Field(...)
    material: Optional[str] = Field(None)
    condition: Optional[str] = Field(None)
    age_estimate: Optional[str] = Field(None)
    style: Optional[str] = Field(None)


# =============================================================================
# RULE VERIFICATION (Age-based)
# =============================================================================

class RuleVerification(BaseModel):
    """Verification of age-based construction rules."""
    rule_id: str = Field(...)
    rule_name: str = Field(...)
    status: Literal["confirmed", "concern", "rejected", "not_visible"] = Field(...)
    evidence: Optional[str] = Field(None)
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Field(None)


# =============================================================================
# DESIGN ASSESSMENT
# =============================================================================

class DesignAssessment(BaseModel):
    """Design/aesthetic assessment from interior_design_knowledge."""
    style_detected: str = Field(..., description="From interior_design_knowledge trends/eras")
    style_indicators: List[str] = Field(default_factory=list)
    finish_tier: Literal["builder_grade", "mid_range", "high_end", "luxury"] = Field(...)
    color_palette: List[str] = Field(default_factory=list)
    overall_impression: str = Field(...)
    
    # Room-specific assessments (optional, filled when relevant)
    kitchen_specific: Optional[Dict[str, str]] = Field(None)
    bathroom_specific: Optional[Dict[str, str]] = Field(None)


# =============================================================================
# ROOM ANALYSIS
# =============================================================================

class RoomDimensions(BaseModel):
    """Room dimensions (estimated from photos if not known)."""
    area_m2_estimate: Optional[float] = Field(None)
    ceiling_height: Literal["low", "standard", "high"] = Field("standard")
    natural_light: Literal["poor", "low", "moderate", "good", "excellent"] = Field("moderate")


class RoomAnalysis(BaseModel):
    """Complete analysis of a single room."""
    room_id: str = Field(...)
    room_type: str = Field(..., description="living_room, kitchen, bathroom, bedroom, etc.")
    photos: List[str] = Field(default_factory=list)
    
    dimensions: Optional[RoomDimensions] = Field(None)
    systems: List[SystemInventoryItem] = Field(default_factory=list)
    products: List[ProductInventoryItem] = Field(default_factory=list)
    rule_verifications: List[RuleVerification] = Field(default_factory=list)
    design_assessment: Optional[DesignAssessment] = Field(None)
    
    condition_summary: str = Field(...)
    key_issues: List[str] = Field(default_factory=list)


# =============================================================================
# REGULATORY ASSESSMENT
# =============================================================================

class CTEConcern(BaseModel):
    """A concern related to CTE (Spanish building code)."""
    area: str = Field(..., description="DB-HE, DB-HS, DB-SI, DB-SUA")
    section: Optional[str] = Field(None, description="HE1, HS3, etc.")
    description: str = Field(...)
    evidence: Optional[str] = Field(None)
    severity: Literal["low", "medium", "high"] = Field(...)


class REBTAssessment(BaseModel):
    """Electrical compliance assessment."""
    status: Literal["compliant", "concern", "pre_2002_concern", "non_compliant"] = Field(...)
    evidence: List[str] = Field(default_factory=list)
    likely_scope: Optional[str] = Field(None)


class ITEProjection(BaseModel):
    """Projected ITE (building inspection) findings."""
    applicable: bool = Field(..., description="True if building >50 years")
    likely_findings: List[Dict[str, str]] = Field(default_factory=list)


class RegulatoryAssessment(BaseModel):
    """Complete regulatory assessment."""
    cte_concerns: List[CTEConcern] = Field(default_factory=list)
    rebt: REBTAssessment = Field(...)
    ite: ITEProjection = Field(...)


# =============================================================================
# RENOVATION TRIGGERS
# =============================================================================

class RenovationTrigger(BaseModel):
    """A trigger that might motivate renovation (from CSCAE guide)."""
    category: Literal["regulatory", "economic", "comfort", "building_problems", "aesthetic"] = Field(...)
    trigger: str = Field(..., description="Spanish trigger name from process_knowledge")
    evidence: str = Field(...)
    urgency: Literal["low", "medium", "high", "critical"] = Field(...)
    safety_critical: bool = Field(False)


# =============================================================================
# COMPARISON ATTRIBUTES
# =============================================================================

class ComparisonAttributes(BaseModel):
    """Structured attributes for direct comparison with comparables."""
    # Energy
    energy_rating: Optional[str] = Field(None)
    envelope_condition: str = Field(...)
    window_type: str = Field(...)
    insulation_visible: bool = Field(...)
    hvac_type: Optional[str] = Field(None)
    
    # Systems
    electrical_era: str = Field(...)
    plumbing_material: Optional[str] = Field(None)
    ventilation_mechanical: bool = Field(...)
    
    # Finishes
    finish_era: str = Field(...)
    finish_tier: str = Field(...)
    kitchen_last_update: Optional[str] = Field(None)
    bathroom_last_update: Optional[str] = Field(None)
    flooring_type: str = Field(...)
    
    # Layout
    layout_type: Literal["open_plan", "semi_open", "compartmentalized"] = Field(...)
    kitchen_open: bool = Field(...)
    natural_light: str = Field(...)
    
    # Design
    style: str = Field(...)
    color_palette: str = Field(...)
    
    # Condition
    structural_concerns: bool = Field(False)
    humidity_visible: bool = Field(False)
    maintenance_level: Literal["poor", "fair", "good", "excellent"] = Field(...)


# =============================================================================
# OVERALL DESIGN PROFILE
# =============================================================================

class MaterialSummary(BaseModel):
    """Summary of materials throughout the property."""
    flooring: str = Field(...)
    walls: str = Field(...)
    woodwork: str = Field(...)
    kitchen: str = Field(...)
    bathroom: str = Field(...)


class LayoutAssessment(BaseModel):
    """Assessment of property layout."""
    type: Literal["open_plan", "semi_open", "compartmentalized"] = Field(...)
    issues: List[str] = Field(default_factory=list)
    potential: Optional[str] = Field(None)


class OverallDesignProfile(BaseModel):
    """Aggregated design profile from all rooms."""
    dominant_style: str = Field(...)
    era_authenticity: str = Field(...)
    updates_detected: List[str] = Field(default_factory=list)
    
    finish_quality_overall: str = Field(...)
    material_summary: MaterialSummary = Field(...)
    color_palette_overall: List[str] = Field(default_factory=list)
    
    layout: LayoutAssessment = Field(...)
    natural_light_assessment: Dict[str, str] = Field(default_factory=dict)


# =============================================================================
# COMPLETE PROPERTY INTELLIGENCE REPORT
# =============================================================================

class PropertyIntelligenceReport(BaseModel):
    """
    Complete Property Intelligence Report.
    
    This is the unified output that replaces:
    - assess_uniclass.py output
    - verify_rules.py output
    
    And adds:
    - Energy profile
    - Design assessment
    - Renovation triggers
    - Comparison-ready attributes
    """
    # Metadata
    listing_id: int = Field(...)
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="v0.3.2")
    
    # Sections
    building_profile: BuildingProfile = Field(...)
    rooms: List[RoomAnalysis] = Field(...)
    regulatory_assessment: RegulatoryAssessment = Field(...)
    design_profile: OverallDesignProfile = Field(...)
    triggers: List[RenovationTrigger] = Field(...)
    comparison_attributes: ComparisonAttributes = Field(...)
    
    class Config:
        json_schema_extra = {
            "description": "Unified Property Intelligence Report for renovation analysis"
        }

