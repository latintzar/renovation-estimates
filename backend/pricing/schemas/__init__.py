"""
Pricing Schemas (V1.0)
======================

V1.0 8-Phase Ultimate Pipeline Architecture:
- Validation Functions: FAIL FAST on item loss or incomplete pricing
- Custom Exceptions: SchemaContinuityError, PricingIncompleteError
- Schemas for all 8 phases

NOTE: Critical validation functions are now in gemini_schemas_v1.py
(moved from the deprecated phase_outputs.py)
"""

# V1.0 - Critical validation functions (NOT deprecated)
from .gemini_schemas_v1 import (
    SchemaContinuityError,
    PricingIncompleteError,
    validate_items_preserved,
    validate_pricing_complete,
)

from .unified_estimate import (
    # Gap Analysis
    GapComparison,
    IdentifiedGap,
    GapAnalysis,
    
    # Scope
    RequiredTask,
    Intervention,
    RoomScope,
    Scope,
    
    # Bill of Quantities
    BoQLineItem,
    RoomTotal,
    BillOfQuantities,
    
    # Reasoning & Validation
    ReasoningStep,
    ValidationMetrics,
    
    # Year Context
    InspectionRecommendation,
    YearContextSummary,
    Disclaimer,
    
    # Main Schema
    UnifiedEstimate,
)

from .estimation_error import (
    EstimationError,
    PhaseError,
    ValidationError,
    ToolCallError,
    DataMissingError,
    CheckpointError,
    GeminiError,
)

__all__ = [
    # V1.0 - Exceptions (Critical data integrity)
    "SchemaContinuityError",
    "PricingIncompleteError",
    
    # V1.0 - Validation Functions (Critical)
    "validate_items_preserved",
    "validate_pricing_complete",
    
    # Unified Estimate
    "GapComparison", "IdentifiedGap", "GapAnalysis",
    "RequiredTask", "Intervention", "RoomScope", "Scope",
    "BoQLineItem", "RoomTotal", "BillOfQuantities",
    "ReasoningStep", "ValidationMetrics",
    "InspectionRecommendation", "YearContextSummary", "Disclaimer",
    "UnifiedEstimate",
    
    # Errors
    "EstimationError", "PhaseError", "ValidationError", "ToolCallError",
    "DataMissingError", "CheckpointError", "GeminiError",
]
