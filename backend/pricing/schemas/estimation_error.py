"""
Estimation Error Types (V0.4.8)
===============================

Error types for fail-fast behavior in the 9-Phase Unified Estimator.

Design Principle: FAIL LOUD AND FAST
- NO retries
- NO fallbacks
- NO silent error handling
- If something fails, let it fail with a clear error message
- Fix the actual issue, don't work around it
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Severity levels for estimation errors."""
    FATAL = "fatal"      # Stop immediately, cannot continue
    ERROR = "error"      # Phase failed, but pipeline might continue
    WARNING = "warning"  # Something unexpected, but can continue


class EstimationError(Exception):
    """
    Base exception for all estimation errors.
    
    All errors in the V0.4.8 pipeline inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.FATAL,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API response."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class PhaseError(EstimationError):
    """
    Error that occurs during a specific phase of the 9-phase pipeline.
    
    Includes phase number and name for debugging.
    """
    
    def __init__(
        self,
        phase_number: int,
        phase_name: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = f"PHASE_{phase_number}_ERROR"
        super().__init__(
            message=f"Phase {phase_number} ({phase_name}): {message}",
            error_code=error_code,
            severity=ErrorSeverity.FATAL,
            context={
                "phase_number": phase_number,
                "phase_name": phase_name,
                **(context or {})
            }
        )
        self.phase_number = phase_number
        self.phase_name = phase_name


class ValidationError(EstimationError):
    """
    Error when validation metrics don't meet thresholds.
    
    Thresholds (fail if not met):
    - room_attribution_pct >= 70
    - kg_grounding_pct == 100
    - bcca_match_pct == 100
    """
    
    def __init__(
        self,
        metric_name: str,
        actual_value: float,
        threshold: float,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"Validation failed: {metric_name} = {actual_value:.1f}%, threshold = {threshold:.1f}%"
        
        super().__init__(
            message=message,
            error_code="VALIDATION_FAILED",
            severity=ErrorSeverity.FATAL,
            context={
                "metric_name": metric_name,
                "actual_value": actual_value,
                "threshold": threshold
            }
        )
        self.metric_name = metric_name
        self.actual_value = actual_value
        self.threshold = threshold


class ToolCallError(EstimationError):
    """
    Error when a tool call (get_bcca_price, discover_ffe) fails.
    """
    
    def __init__(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        error_message: str
    ):
        super().__init__(
            message=f"Tool {tool_name} failed: {error_message}",
            error_code="TOOL_CALL_FAILED",
            severity=ErrorSeverity.FATAL,
            context={
                "tool_name": tool_name,
                "arguments": arguments,
                "error_message": error_message
            }
        )
        self.tool_name = tool_name
        self.arguments = arguments


class GeminiError(EstimationError):
    """
    Error from Gemini API call.
    """
    
    def __init__(
        self,
        phase_name: str,
        model: str,
        error_message: str,
        response_text: Optional[str] = None
    ):
        super().__init__(
            message=f"Gemini call failed in {phase_name} ({model}): {error_message}",
            error_code="GEMINI_CALL_FAILED",
            severity=ErrorSeverity.FATAL,
            context={
                "phase_name": phase_name,
                "model": model,
                "error_message": error_message,
                "response_text": response_text[:500] if response_text else None
            }
        )
        self.model = model


class DataMissingError(EstimationError):
    """
    Error when required data is missing.
    
    Examples:
    - No clusters for target property
    - No PIR generated
    - No comparables selected
    """
    
    def __init__(
        self,
        data_type: str,
        listing_id: int,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"Missing {data_type} for listing {listing_id}"
        
        super().__init__(
            message=message,
            error_code="DATA_MISSING",
            severity=ErrorSeverity.FATAL,
            context={
                "data_type": data_type,
                "listing_id": listing_id
            }
        )
        self.data_type = data_type
        self.listing_id = listing_id


class CheckpointError(EstimationError):
    """
    Error related to checkpointing (save/load).
    """
    
    def __init__(
        self,
        checkpoint_name: str,
        operation: str,  # "save" or "load"
        error_message: str
    ):
        super().__init__(
            message=f"Checkpoint {operation} failed for '{checkpoint_name}': {error_message}",
            error_code="CHECKPOINT_ERROR",
            severity=ErrorSeverity.ERROR,  # Not fatal - might be able to continue
            context={
                "checkpoint_name": checkpoint_name,
                "operation": operation,
                "error_message": error_message
            }
        )
        self.checkpoint_name = checkpoint_name
        self.operation = operation


class AntiParetoViolation(EstimationError):
    """
    Error when Anti-Pareto checks fail (incomplete work detected).
    
    Anti-Pareto measures ensure Gemini doesn't stop at 80% done.
    Examples:
    - Kitchen scope but no appliances
    - Bathroom scope but no waterproofing
    - Less than minimum items per room type
    """
    
    def __init__(
        self,
        check_name: str,
        description: str,
        missing_items: Optional[list] = None
    ):
        super().__init__(
            message=f"Anti-Pareto violation: {check_name} - {description}",
            error_code="ANTI_PARETO_VIOLATION",
            severity=ErrorSeverity.FATAL,
            context={
                "check_name": check_name,
                "description": description,
                "missing_items": missing_items or []
            }
        )
        self.check_name = check_name
        self.missing_items = missing_items or []

