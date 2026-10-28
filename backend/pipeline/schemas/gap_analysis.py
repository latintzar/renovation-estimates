"""
Comparative Gap Analysis Schema
PETER AGENTIC V0.3.2

Schema for direct attribute-by-attribute comparison between
target property and comparable property.

Uses Property Intelligence Reports as input.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# COMPARISON ITEMS
# =============================================================================

class AttributeValue(BaseModel):
    """Value of an attribute with evidence."""
    value: str = Field(...)
    evidence: Optional[str] = Field(None)
    from_report_field: Optional[str] = Field(None, description="Which PIR field this came from")


class AttributeComparison(BaseModel):
    """Direct comparison of a single attribute."""
    category: Literal["envelope", "systems", "finishes", "layout", "design"] = Field(...)
    attribute: str = Field(..., description="e.g., 'windows', 'kitchen', 'flooring'")
    
    target: AttributeValue = Field(...)
    comparable: AttributeValue = Field(...)
    
    gap_description: str = Field(..., description="What needs to change")
    intervention_ids: List[str] = Field(default_factory=list, description="KG task IDs")
    
    # Impact assessments
    energy_impact: Optional[str] = Field(None, description="e.g., '+1 letter'")
    design_transformation: Optional[str] = Field(None, description="e.g., 'builder_grade → high_end'")
    structural_work: bool = Field(False)
    requires_permit: Optional[str] = Field(None, description="obra_menor, obra_mayor")
    priority: Literal["low", "medium", "high", "critical"] = Field("medium")


# =============================================================================
# ENERGY GAP
# =============================================================================

class EnergyIntervention(BaseModel):
    """An intervention for energy improvement."""
    intervention_id: str = Field(...)
    name: str = Field(...)
    impact_letters: int = Field(...)
    from_comparison: str = Field(..., description="Which comparison identified this")


class EnergySummary(BaseModel):
    """Summary of energy gap."""
    target_rating: str = Field(...)
    comparable_rating: str = Field(...)
    gap_letters: int = Field(...)
    upgrade_pathway: str = Field(..., description="e.g., 'G_to_C'")
    
    interventions: List[EnergyIntervention] = Field(default_factory=list)
    
    subsidy_eligible: bool = Field(False)
    subsidy_notes: Optional[str] = Field(None)


# =============================================================================
# SCOPE SUMMARY
# =============================================================================

class ScopeCategory(BaseModel):
    """A category of work in the scope."""
    name: str = Field(...)
    interventions: List[str] = Field(default_factory=list)
    permit_type: Optional[str] = Field(None)
    note: Optional[str] = Field(None)


class RiskFactor(BaseModel):
    """A risk factor in the renovation."""
    risk: str = Field(...)
    likelihood: Literal["low", "medium", "high"] = Field("medium")
    mitigation: Optional[str] = Field(None)


class ScopeSummary(BaseModel):
    """Summary of renovation scope."""
    level: Literal["cosmetic", "moderate", "comprehensive", "full_gut"] = Field(...)
    
    intervention_count: int = Field(...)
    
    categories: List[ScopeCategory] = Field(default_factory=list)
    
    permits_required: List[Dict[str, str]] = Field(default_factory=list)
    
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    
    estimated_duration_months: Optional[str] = Field(None)


# =============================================================================
# COMPLETE GAP ANALYSIS
# =============================================================================

class ComparativeGapAnalysis(BaseModel):
    """
    Complete Comparative Gap Analysis.
    
    Compares target Property Intelligence Report with comparable(s)
    to determine what needs to change.
    """
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="v0.3.2")
    
    # Properties being compared
    target_listing_id: int = Field(...)
    comparable_listing_id: int = Field(...)
    comparable_address: Optional[str] = Field(None)
    comparable_relevance: Optional[str] = Field(None)
    
    # Direct comparisons
    comparisons: List[AttributeComparison] = Field(...)
    
    # Energy summary
    energy_summary: EnergySummary = Field(...)
    
    # Scope summary
    scope_summary: ScopeSummary = Field(...)
    
    # All intervention IDs (for KG expansion)
    all_intervention_ids: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "description": "Comparative gap analysis between target and comparable properties"
        }

