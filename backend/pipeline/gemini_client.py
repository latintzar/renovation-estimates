"""
Gemini Client for Lean MVP Pipeline (using google-generativeai SDK)
===================================================================

Uses Google AI SDK for proper schema handling.

Models:
- gemini-3-flash-preview - Fast, good for text analysis
- gemini-3.1-pro-preview - Better reasoning, photos
"""

import os
import json
import base64
import logging
import asyncio
import contextvars
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

import httpx
from pathlib import Path
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Load environment
from dotenv import load_dotenv
backend_root = Path(__file__).parent.parent
# Repo-root `.env.local` must be the source of truth; load it last with override=True so stale values never win.
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

# =============================================================================
# PER-JOB CONTEXT (for DB-first observability)
# =============================================================================
_ctx_db: contextvars.ContextVar[Any] = contextvars.ContextVar("gemini_db", default=None)
_ctx_job: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("gemini_job", default={})


def set_gemini_tracking_context(db: Any, job_ctx: Dict[str, Any]) -> None:
    """
    Attach DB + job context so every Gemini call can persist usage to DB automatically.

    WHY THIS MATTERS: Call sites are spread across many modules. By setting context at the
    worker boundary (per job), we can persist token/cost data for *all* Gemini calls without
    needing "special commands" or hand-wiring every call site.

    job_ctx should include: job_id, run_id, listing_id, stage, job_type, worker_id (optional).
    """
    _ctx_db.set(db)
    _ctx_job.set(job_ctx or {})


def clear_gemini_tracking_context() -> None:
    """Clear DB + job context (best effort)."""
    _ctx_db.set(None)
    _ctx_job.set({})


def _usage_metadata_to_dict(usage_metadata: Any) -> Dict[str, Any]:
    """
    Convert SDK usage_metadata into a plain dict guaranteed to be JSON-serializable.

    WHY THIS MATTERS:
    We store this payload in DB as the durable source-of-truth for token accounting.
    The Gemini SDK returns protobuf-backed objects whose to_dict() can still contain
    nested non-serializable types (enums, RepeatedComposite, etc.). We MUST do a
    JSON round-trip at the end to guarantee every value is a primitive.
    """
    import json as _json

    if usage_metadata is None:
        return {}

    raw: Dict[str, Any] = {}

    # Strategy 1: SDK to_dict()
    to_dict = getattr(usage_metadata, "to_dict", None)
    if callable(to_dict):
        try:
            d = usage_metadata.to_dict()
            if isinstance(d, dict):
                raw = d
        except Exception:
            pass

    # Strategy 2: attribute dict fallback
    if not raw:
        try:
            d = dict(getattr(usage_metadata, "__dict__", {}) or {})
            if isinstance(d, dict):
                raw = d
        except Exception:
            pass

    if not raw:
        return {}

    # CRITICAL: JSON round-trip to catch any surviving non-serializable values.
    # Uses a default handler so enum/protobuf types become strings rather than crashing.
    def _safe_default(obj: Any) -> Any:
        """Convert non-serializable objects to primitives."""
        # Protobuf enums have a .name attribute
        if hasattr(obj, "name") and hasattr(obj, "value"):
            return obj.name
        # Anything with to_dict()
        td = getattr(obj, "to_dict", None)
        if callable(td):
            try:
                return td()
            except Exception:
                pass
        return str(obj)

    try:
        return _json.loads(_json.dumps(raw, default=_safe_default))
    except Exception as exc:
        logger.warning(
            "_usage_metadata_to_dict: JSON round-trip failed, returning empty | err=%s",
            str(exc),
        )
        return {}


def _get_usage_int(d: Dict[str, Any], *keys: str) -> int:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        try:
            return int(v)
        except Exception:
            continue
    return 0


# =============================================================================
# TOKEN TRACKING (for cost analysis)
# =============================================================================

class TokenTracker:
    """
    Global tracker for Gemini API token usage with EMPIRICAL per-call cost calculation.
    
    ═══════════════════════════════════════════════════════════════════════════════
    NO ESTIMATES. NO AVERAGES. NO APPROXIMATIONS.
    Every cost is calculated from ACTUAL API response tokens to 6 decimal places.
    ═══════════════════════════════════════════════════════════════════════════════
    
    How tokenization works:
    - Text: ~4 characters per token
    - Images: ~1290 tokens per 1024x1024 image (varies by resolution)
    - Audio: 25 tokens per second (we don't use audio)
    - The API returns total token count INCLUDING image tokens in usage_metadata
    
    Pricing tiers:
    - Standard: <=200K input tokens
    - Long context: >200K input tokens (HIGHER prices for Pro models)
    """
    _instance = None
    BASE_LISTING_CASAFARI_COST_USD = 3.5
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # GEMINI API PRICING - PAID TIER (Feb 2026)
    # Source: https://ai.google.dev/gemini-api/docs/pricing
    # All prices are USD per 1,000,000 tokens
    # ═══════════════════════════════════════════════════════════════════════════════
    
    # Standard pricing (<=200K input tokens)
    # NOTE:
    # - "input" covers text + image + video tokens (all charged at same rate)
    # - "output" includes THINKING tokens (Gemini pricing is output including thinking)
    # - Image-gen models can have different output rates for image tokens vs text tokens.
    PRICING_STANDARD = {
        # Gemini 3.1 Pro Preview (same pricing as 3 Pro)
        "gemini-3.1-pro-preview": {
            "input_text_image_video": 2.00,
            "input_audio": 2.00,
            "output": 12.00,
        },
        # Gemini 3 Preview
        "gemini-3-pro-preview": {
            "input_text_image_video": 2.00,  # Text, image, video, audio all same
            "input_audio": 2.00,              # Same as other input for Gemini 3 Pro
            "output": 12.00,
        },
        "gemini-3-flash-preview": {
            "input_text_image_video": 0.50,  # Text, image, video
            "input_audio": 1.00,              # Audio is 2x for Flash
            "output": 3.00,
        },
        # Gemini 3 Pro Image Preview (🍌)
        # Text input/output is priced like Gemini 3 Pro; image output is priced at $120 / 1M tokens.
        "gemini-3-pro-image-preview": {
            "input_text_image_video": 2.00,
            "input_audio": 2.00,
            "output": 120.00,
            "output_text": 12.00,
            "output_image": 120.00,
        },
        # Gemini 2.5
        "gemini-2.5-flash-lite": {
            "input_text_image_video": 0.10,
            "input_audio": 0.30,
            "output": 0.40,
        },
        # Image generation models
        "gemini-2.5-flash-image": {
            "input_text_image_video": 0.30,
            "input_audio": 1.00,
            # Output images are priced at $30 / 1M tokens (equivalent to ~$0.039 per 1024x1024 image).
            "output": 30.00,
        },
    }
    
    # Long context pricing (>200K input tokens)
    # CRITICAL: Pro models have HIGHER output pricing at long context!
    PRICING_LONG = {
        "gemini-3.1-pro-preview": {
            "input_text_image_video": 4.00,
            "input_audio": 4.00,
            "output": 18.00,
        },
        "gemini-3-pro-preview": {
            "input_text_image_video": 4.00,   # 2x standard
            "input_audio": 4.00,
            "output": 18.00,                   # $18 NOT $12!
        },
        "gemini-3-flash-preview": {
            "input_text_image_video": 0.50,   # Same as standard
            "input_audio": 1.00,
            "output": 3.00,
        },
        "gemini-3-pro-image-preview": {
            "input_text_image_video": 4.00,
            "input_audio": 4.00,
            "output": 120.00,      # image output pricing does not vary with context tier
            "output_text": 18.00,  # text/thinking output follows Pro long-context tier
            "output_image": 120.00,
        },
        "gemini-2.5-flash-lite": {
            "input_text_image_video": 0.10,
            "input_audio": 0.30,
            "output": 0.40,
        },
        "gemini-2.5-flash-image": {
            "input_text_image_video": 0.30,
            "input_audio": 1.00,
            "output": 30.00,
        },
    }
    
    # Cached input pricing (<=200K context) - 10x cheaper input
    PRICING_CACHED_STANDARD = {
        "gemini-3.1-pro-preview": {
            "input_text_image_video": 0.20,
            "input_audio": 0.20,
            "output": 12.00,
        },
        "gemini-3-pro-preview": {
            "input_text_image_video": 0.20,
            "input_audio": 0.20,
            "output": 12.00,
        },
        "gemini-3-flash-preview": {
            "input_text_image_video": 0.05,
            "input_audio": 0.10,
            "output": 3.00,
        },
        # For image-gen: context caching pricing is not used in this pipeline.
        # Keep cached == regular to avoid under-reporting.
        "gemini-3-pro-image-preview": {
            "input_text_image_video": 0.20,
            "input_audio": 0.20,
            "output": 120.00,
            "output_text": 12.00,
            "output_image": 120.00,
        },
        "gemini-2.5-flash-lite": {
            "input_text_image_video": 0.010,
            "input_audio": 0.030,
            "output": 0.40,
        },
        "gemini-2.5-flash-image": {
            "input_text_image_video": 0.30,
            "input_audio": 1.00,
            "output": 30.00,
        },
    }
    
    # Cached input pricing (>200K context)
    PRICING_CACHED_LONG = {
        "gemini-3.1-pro-preview": {
            "input_text_image_video": 0.40,
            "input_audio": 0.40,
            "output": 18.00,
        },
        "gemini-3-pro-preview": {
            "input_text_image_video": 0.40,
            "input_audio": 0.40,
            "output": 18.00,
        },
        "gemini-3-flash-preview": {
            "input_text_image_video": 0.05,
            "input_audio": 0.10,
            "output": 3.00,
        },
        "gemini-3-pro-image-preview": {
            "input_text_image_video": 0.40,
            "input_audio": 0.40,
            "output": 120.00,
            "output_text": 18.00,
            "output_image": 120.00,
        },
        "gemini-2.5-flash-lite": {
            "input_text_image_video": 0.010,
            "input_audio": 0.030,
            "output": 0.40,
        },
        "gemini-2.5-flash-image": {
            "input_text_image_video": 0.30,
            "input_audio": 1.00,
            "output": 30.00,
        },
    }
    
    # 200K token threshold for long context pricing
    LONG_CONTEXT_THRESHOLD = 200_000
    
    def __init__(self):
        self.reset()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def reset(self):
        """Reset all tracking data."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0  # output_tokens + thinking_tokens (billable output)
        self.total_thinking_tokens = 0
        self.total_cost_regular = 0.0  # Running total (actual, not estimated)
        self.total_cost_cached = 0.0   # Running total assuming cached pricing
        self.base_cost_usd = self.BASE_LISTING_CASAFARI_COST_USD
        self.call_count = 0
        self.by_model = {}
        self.by_stage = {}
        self.current_stage = "default"
        self.previous_stage = None
    
    def set_stage(self, stage: str):
        """Set the current pipeline stage for tracking."""
        self.previous_stage = self.current_stage
        self.current_stage = stage
        logger.info(f"  📊 Token tracking stage: {stage}")
    
    def track(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
        has_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Track tokens for a single API call and calculate EXACT cost to 6 decimal places.
        
        ═══════════════════════════════════════════════════════════════════════════════
        NO ESTIMATES. NO AVERAGES. EXACT COST FROM ACTUAL API RESPONSE.
        ═══════════════════════════════════════════════════════════════════════════════
        
        Calculation based on:
        - Actual input/output tokens from response.usage_metadata
        - Whether input exceeds 200K (triggers long context pricing)
        - Model-specific pricing tiers
        
        Note: Image tokens are INCLUDED in input_tokens by the API.
        A 1024x1024 image = ~1290 tokens. The API handles tokenization.
        
        Args:
            model: Model name (e.g., "gemini-3-flash-preview")
            input_tokens: Actual input tokens from usage_metadata.prompt_token_count
            output_tokens: Actual output tokens from usage_metadata.candidates_token_count
            has_images: Whether this call included images (for logging only)
        """
        # Determine pricing tier based on actual input tokens
        is_long_context = input_tokens > self.LONG_CONTEXT_THRESHOLD
        
        # Select pricing tables based on context length
        if is_long_context:
            pricing_regular = self.PRICING_LONG
            pricing_cached = self.PRICING_CACHED_LONG
            context_tier = "LONG"
        else:
            pricing_regular = self.PRICING_STANDARD
            pricing_cached = self.PRICING_CACHED_STANDARD
            context_tier = "std"
        
        # Get model pricing (default to 3-Flash if unknown model)
        default_pricing = {
            "input_text_image_video": 0.50,
            "input_audio": 1.00,
            "output": 3.00,
        }
        model_pricing_reg = pricing_regular.get(model, default_pricing)
        model_pricing_cache = pricing_cached.get(model, default_pricing)
        
        # Decide output token rate:
        # - For image-generation models, output tokens are priced as image output tokens.
        # - Otherwise, output tokens are priced as text output tokens (including thinking).
        is_image_model = "image" in str(model).lower()
        output_key = "output_image" if is_image_model else "output_text"
        output_rate_reg = float(model_pricing_reg.get(output_key, model_pricing_reg["output"]))
        output_rate_cache = float(model_pricing_cache.get(output_key, model_pricing_cache["output"]))

        # Billable output includes thinking tokens (per Gemini pricing tables).
        billable_output_tokens = int(output_tokens) + int(thinking_tokens or 0)

        # Calculate EXACT cost for this call
        # NOTE: We use text/image/video rate since we don't use audio
        # Images are already tokenized by the API and included in input_tokens
        input_rate_reg = model_pricing_reg["input_text_image_video"]
        input_rate_cache = model_pricing_cache["input_text_image_video"]
        
        # Cost = (tokens / 1,000,000) * rate_per_million
        input_cost_regular = (input_tokens / 1_000_000) * input_rate_reg
        output_cost_regular = (billable_output_tokens / 1_000_000) * output_rate_reg
        call_cost_regular = input_cost_regular + output_cost_regular
        
        input_cost_cached = (input_tokens / 1_000_000) * input_rate_cache
        output_cost_cached = (billable_output_tokens / 1_000_000) * output_rate_cache
        call_cost_cached = input_cost_cached + output_cost_cached
        
        # Update running totals (accumulated across all calls)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += billable_output_tokens
        self.total_thinking_tokens += int(thinking_tokens or 0)
        self.total_cost_regular += call_cost_regular
        self.total_cost_cached += call_cost_cached
        self.call_count += 1
        
        # Track by model
        if model not in self.by_model:
            self.by_model[model] = {
                "input": 0, "output": 0, "calls": 0,
                "cost_regular": 0.0, "cost_cached": 0.0,
                "long_context_calls": 0, "image_calls": 0, "thinking": 0
            }
        self.by_model[model]["input"] += input_tokens
        self.by_model[model]["output"] += billable_output_tokens
        self.by_model[model]["thinking"] += int(thinking_tokens or 0)
        self.by_model[model]["calls"] += 1
        self.by_model[model]["cost_regular"] += call_cost_regular
        self.by_model[model]["cost_cached"] += call_cost_cached
        if is_long_context:
            self.by_model[model]["long_context_calls"] += 1
        if has_images:
            self.by_model[model]["image_calls"] += 1
        
        # Track by pipeline stage
        stage = self.current_stage
        if stage not in self.by_stage:
            self.by_stage[stage] = {
                "input": 0, "output": 0, "calls": 0,
                "cost_regular": 0.0, "cost_cached": 0.0,
                "by_model": {}, "thinking": 0
            }
        self.by_stage[stage]["input"] += input_tokens
        self.by_stage[stage]["output"] += billable_output_tokens
        self.by_stage[stage]["thinking"] += int(thinking_tokens or 0)
        self.by_stage[stage]["calls"] += 1
        self.by_stage[stage]["cost_regular"] += call_cost_regular
        self.by_stage[stage]["cost_cached"] += call_cost_cached
        
        # Track by model within stage
        if model not in self.by_stage[stage]["by_model"]:
            self.by_stage[stage]["by_model"][model] = {
                "input": 0, "output": 0, "calls": 0,
                "cost_regular": 0.0, "cost_cached": 0.0, "thinking": 0
            }
        self.by_stage[stage]["by_model"][model]["input"] += input_tokens
        self.by_stage[stage]["by_model"][model]["output"] += billable_output_tokens
        self.by_stage[stage]["by_model"][model]["thinking"] += int(thinking_tokens or 0)
        self.by_stage[stage]["by_model"][model]["calls"] += 1
        self.by_stage[stage]["by_model"][model]["cost_regular"] += call_cost_regular
        self.by_stage[stage]["by_model"][model]["cost_cached"] += call_cost_cached
        
        # LOG EVERY SINGLE CALL with exact cost (6 decimal places for cent precision)
        img_marker = " 📷" if has_images else ""
        long_marker = " ⚠️>200K" if is_long_context else ""
        logger.info(
            f"  💰 [{model}]{img_marker}{long_marker} "
            f"in={input_tokens:,} out={billable_output_tokens:,} "
            f"→ ${call_cost_regular:.6f} (cached: ${call_cost_cached:.6f}) "
            f"| running: ${self.total_cost_regular:.6f}"
        )

        return {
            "is_long_context": bool(is_long_context),
            "context_tier": context_tier,
            "output_rate_key": output_key,
            "output_billable_tokens": billable_output_tokens,
            "call_cost_regular": float(call_cost_regular),
            "call_cost_cached": float(call_cost_cached),
        }
    
    def report(self, use_cached_pricing: bool = False) -> Dict[str, Any]:
        """
        Generate cost report based on ACTUAL tracked costs.
        
        NO RECALCULATION - costs were computed per-call during tracking.
        This just formats the already-calculated empirical data.
        """
        # Use pre-calculated costs (not re-computed from averages)
        llm_cost = self.total_cost_cached if use_cached_pricing else self.total_cost_regular
        base_cost = self.base_cost_usd
        total_cost = llm_cost + base_cost
        
        model_costs = {}
        for model, data in self.by_model.items():
            model_cost = data["cost_cached"] if use_cached_pricing else data["cost_regular"]
            model_costs[model] = {
                "input_tokens": data["input"],
                "output_tokens": data["output"],
                "calls": data["calls"],
                "long_context_calls": data.get("long_context_calls", 0),
                "total_cost": round(model_cost, 4),
            }
        
        # Stage breakdown with costs (using pre-calculated values)
        stage_costs = {}
        for stage, data in self.by_stage.items():
            stage_cost = data["cost_cached"] if use_cached_pricing else data["cost_regular"]
            stage_costs[stage] = {
                "input_tokens": data["input"],
                "output_tokens": data["output"],
                "calls": data["calls"],
                "total_cost": round(stage_cost, 4),
            }
        
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_calls": self.call_count,
            "llm_cost_usd": round(llm_cost, 4),
            "base_cost_usd": round(base_cost, 2),
            "total_cost_usd": round(total_cost, 4),
            "pricing_mode": "cached" if use_cached_pricing else "regular",
            "by_model": model_costs,
            "by_stage": stage_costs,
        }
    
    def log_summary(self, use_cached_pricing: bool = False):
        """
        Log EXACT cost summary with 6 decimal place precision.
        All values are from actual API responses, not estimates.
        """
        report = self.report(use_cached_pricing=use_cached_pricing)
        pricing_label = "CACHED" if use_cached_pricing else "REGULAR"
        
        logger.info("═" * 70)
        logger.info(f"💵 EXACT COST SUMMARY ({pricing_label} PRICING)")
        logger.info("═" * 70)
        logger.info(f"  Total API calls: {report['total_calls']}")
        logger.info(f"  Total input tokens: {report['total_input_tokens']:,}")
        logger.info(f"  Total output tokens: {report['total_output_tokens']:,}")
        logger.info(f"  ═══════════════════════════════════════")
        logger.info(f"  💰 LLM ONLY: ${report['llm_cost_usd']:.6f}")
        logger.info(f"  💰 BASE LISTING+CASAFARI: ${report['base_cost_usd']:.2f}")
        logger.info(f"  💰 TOTAL COST: ${report['total_cost_usd']:.6f}")
        logger.info(f"  ═══════════════════════════════════════")
        
        # Stage breakdown
        if report['by_stage']:
            logger.info("─" * 70)
            logger.info("BY PIPELINE STAGE:")
            for stage, data in report['by_stage'].items():
                logger.info(f"  📊 {stage}:")
                logger.info(f"      Calls: {data['calls']}")
                logger.info(f"      Tokens: {data['input_tokens']:,} in / {data['output_tokens']:,} out")
                logger.info(f"      Cost: ${data['total_cost']:.6f}")
        
        # Model breakdown
        logger.info("─" * 70)
        logger.info("BY MODEL:")
        for model, data in report['by_model'].items():
            long_ctx = data.get('long_context_calls', 0)
            img_calls = data.get('image_calls', 0)
            flags = []
            if long_ctx > 0:
                flags.append(f"{long_ctx} >200K")
            if img_calls > 0:
                flags.append(f"{img_calls} with images")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            
            logger.info(f"  🤖 {model}:")
            logger.info(f"      Calls: {data['calls']}{flag_str}")
            logger.info(f"      Input: {data['input_tokens']:,} tokens")
            logger.info(f"      Output: {data['output_tokens']:,} tokens")
            logger.info(f"      Cost: ${data['total_cost']:.6f}")
        
        logger.info("═" * 70)
        
        # Show both pricing for comparison
        if not use_cached_pricing:
            savings = self.total_cost_regular - self.total_cost_cached
            logger.info(f"  💡 With context caching: ${self.total_cost_cached:.6f} (saves ${savings:.6f})")
        else:
            extra = self.total_cost_regular - self.total_cost_cached
            logger.info(f"  💡 Without caching: ${self.total_cost_regular:.6f} (+${extra:.6f})")
    
    def log_stage_progress(self, stage: str = None):
        """Log current progress for a specific stage."""
        stage = stage or self.current_stage
        if stage not in self.by_stage:
            return
        
        data = self.by_stage[stage]
        logger.info(f"  📊 {stage}: {data['calls']} calls, {data['input']:,} in / {data['output']:,} out tokens")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Model configurations (per Build Plan - DO NOT CHANGE)
MODELS = {
    # Text analysis (T1-T4), URL validation, domain credibility fallback
    "flash-lite": "gemini-2.5-flash-lite",
    
    # Search synthesis (C1, C2, R2), Scope details (R3a-R4)
    "flash": "gemini-3-flash-preview",
    
    # Photo analysis (P1-P3), Architect (A1-A3), Scope (R1), Visuals selection (V2-V3)
    "pro": "gemini-3.1-pro-preview",
    # Image generation
    "pro-image": "gemini-2.5-flash-image",     # Stable, well-tested
    "pro-image-gen3": "gemini-3-pro-image-preview",  # Higher quality, optional
    "flash-image": "gemini-2.5-flash-image",
}

# Automatic fallback chain for rate limits
# Order: primary → fallback1 → fallback2 → fallback3
MODEL_FALLBACK_CHAIN = {
    "pro": ["gemini-3.1-pro-preview", "gemini-3-flash-preview"],
    "flash": ["gemini-3-flash-preview"],
    "flash-lite": ["gemini-2.5-flash-lite", "gemini-3-flash-preview"],
    "pro-image": ["gemini-2.5-flash-image"],
    "flash-image": ["gemini-2.5-flash-image"],
}


def _validate_gemini_pricing_tables() -> None:
    """
    Fail-loud validation so we never silently use fallback pricing.

    WHY THIS MATTERS:
    If we use default pricing for an unknown model, the totals can diverge from
    reality while still looking "plausible" in logs/UI.
    """
    strict_pricing = os.getenv("PIPELINE_STRICT_GEMINI_PRICING", "true").lower() == "true"
    tt = TokenTracker.get_instance()

    required_models = set(MODELS.values())
    required_models.update({m for chain in MODEL_FALLBACK_CHAIN.values() for m in chain})
    required_models = {m for m in required_models if isinstance(m, str) and m.strip()}

    missing: List[str] = []
    for m in sorted(required_models):
        if m not in tt.PRICING_STANDARD:
            missing.append(f"{m} missing from PRICING_STANDARD")
        if m not in tt.PRICING_LONG:
            missing.append(f"{m} missing from PRICING_LONG")
        if m not in tt.PRICING_CACHED_STANDARD:
            missing.append(f"{m} missing from PRICING_CACHED_STANDARD")
        if m not in tt.PRICING_CACHED_LONG:
            missing.append(f"{m} missing from PRICING_CACHED_LONG")

    if missing:
        msg = "Gemini pricing tables incomplete:\n- " + "\n- ".join(missing)
        if strict_pricing:
            raise RuntimeError(msg)
        logger.error(msg)


# Global tracker instance (after model config so validation can run)
_token_tracker = TokenTracker.get_instance()
_validate_gemini_pricing_tables()


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker."""
    return _token_tracker

# Error patterns that trigger fallback
RATE_LIMIT_PATTERNS = [
    "429",
    "rate limit",
    "quota exceeded",
    "resource exhausted",
    "too many requests",
    "RESOURCE_EXHAUSTED",
    "rateLimitExceeded",
]


def _is_rate_limit_error(error_str: str) -> bool:
    """Check if an error is a rate limit error."""
    error_lower = error_str.lower()
    return any(pattern.lower() in error_lower for pattern in RATE_LIMIT_PATTERNS)


def _compress_to_jpeg(image_b64: str, quality: int = 85) -> tuple[str, str]:
    """
    Compress a base64 image to JPEG to reduce payload size.
    
    Gemini returns PNGs (~100KB), this converts to JPEG (~25KB).
    
    Args:
        image_b64: Base64 encoded image (PNG or other format)
        quality: JPEG quality (1-100), default 85 is good balance
        
    Returns:
        Tuple of (compressed_base64, mime_type)
    """
    try:
        from PIL import Image
        import io
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_b64)
        
        # Open with PIL
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB (JPEG doesn't support alpha)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as JPEG to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        
        # Encode back to base64
        compressed_b64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return compressed_b64, "image/jpeg"
        
    except Exception as e:
        # If compression fails, return original
        logger.warning(f"  ⚠️ Image compression failed: {e}, using original")
        return image_b64, "image/png"


def get_api_key() -> str:
    """Read the recipient-owned Gemini key without logging its value."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
    if not key:
        raise ValueError("Configure GEMINI_API_KEY in the selected private runtime file.")
    return key


@dataclass
class GeminiResponse:
    """Response from Gemini API call."""
    success: bool
    text: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None  # [{"name": "fn_name", "args": {...}}]
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None  # e.g. "1"/"STOP" or "2"/"MAX_TOKENS"


# Default system instruction to ensure Spanish responses
DEFAULT_SYSTEM_INSTRUCTION = """IMPORTANT: You MUST respond in Spanish (Español). 
All text output, labels, descriptions, summaries, reasons, and any human-readable content MUST be written in Spanish.
Only technical field names in JSON (like "condition_score") should remain in English for parsing.
Example: Instead of "Move-in ready" write "Listo para entrar". Instead of "Bathroom needs updating" write "El baño necesita actualización"."""


async def call_gemini(
    prompt: str,
    model: str = "flash",
    temperature: float = 0.3,
    max_tokens: int = 65536,
    response_schema: Optional[Dict] = None,
    images: Optional[List[Dict[str, str]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_config: Optional[Dict[str, Any]] = None,
    system_instruction: Optional[str] = None,
    use_spanish: bool = True,  # Default to Spanish responses
    strict_db_write: Optional[bool] = None,  # Override PIPELINE_STRICT_GEMINI_COST_DB_WRITE for non-pipeline calls
    auto_fallback: bool = True,  # DEPRECATED: fallbacks disabled (fail-fast)
    no_fallback: bool = False,  # DEPRECATED: fallbacks disabled (fail-fast)
    thinking_level: Optional[str] = None,  # 'HIGH', 'MEDIUM', 'LOW' for extended reasoning
) -> GeminiResponse:
    """
    Call Gemini API with text and optional images using SDK.
    
    AUTOMATIC FALLBACK: If rate limited, automatically tries fallback models:
    - pro: gemini-3-pro-preview → gemini-3-flash-preview → gemini-2.5-pro
    - flash: gemini-3-flash-preview → gemini-2.5-flash → gemini-2.5-pro
    
    V0.5 ADDITION: no_fallback parameter
    ------------------------------------
    For critical operations like photo clustering, we want to FAIL FAST
    if the Pro model is unavailable, rather than falling back to Flash
    which produces lower-quality results.
    
    Args:
        prompt: The text prompt
        model: Model alias ("flash", "pro", "flash-lite") or full model name
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum output tokens
        response_schema: JSON schema for structured output (SDK handles conversion)
        images: List of {"mime_type": str, "data": str (base64)} dicts
        system_instruction: Optional system instruction
        auto_fallback: Whether to automatically fallback on rate limit (default True)
        no_fallback: V0.5 - If True, FAIL if model unavailable (overrides auto_fallback)
    
    Returns:
        GeminiResponse with success status and text/error
    """
    # CRITICAL SIMPLIFICATION:
    # - No model fallbacks. No retry chain. Fail fast on the chosen model alias.
    # WHY THIS MATTERS: fallbacks hide root causes and make runs non-deterministic.
    if auto_fallback or no_fallback:
        # Keep args for backwards compatibility but make behavior explicit.
        logger.info("  → Model fallbacks disabled (fail-fast).")

    model_name = os.getenv("GEMINI_" + model.upper().replace("-", "_") + "_MODEL") or MODELS.get(model, model)
    try:
        genai.configure(api_key=get_api_key())
        return await _call_gemini_single(
            prompt=prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
            images=images,
            tools=tools,
            tool_config=tool_config,
            system_instruction=system_instruction,
            use_spanish=use_spanish,
            thinking_level=thinking_level,
            strict_db_write=strict_db_write,
        )
    except Exception as e:
        error_str = str(e)
        logger.exception(f"Gemini call failed on {model_name}: {e}")
        return GeminiResponse(success=False, error=error_str, model=model_name)


async def _call_gemini_single(
    prompt: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    response_schema: Optional[Dict],
    images: Optional[List[Dict[str, str]]],
    tools: Optional[List[Dict[str, Any]]],
    tool_config: Optional[Dict[str, Any]],
    system_instruction: Optional[str],
    use_spanish: bool,
    thinking_level: Optional[str] = None,
    strict_db_write: Optional[bool] = None,
) -> GeminiResponse:
    """
    Call a single Gemini model (no fallback logic).
    
    Args:
        thinking_level: Optional 'HIGH', 'MEDIUM', 'LOW' for extended reasoning.
                       Only works with Gemini 3 models (gemini-3-pro-preview, etc.)
    """
    # Create generation config with all parameters in constructor
    generation_config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "top_p": 0.95,
    }
    
    # Add response schema if provided - MUST be in constructor, not set after
    if response_schema:
        generation_config_kwargs["response_mime_type"] = "application/json"
        generation_config_kwargs["response_schema"] = response_schema
    
    # Note: thinking_config is only available in Vertex AI SDK, not google-generativeai
    # For the API key SDK, we achieve similar results by:
    # 1. Using gemini-3-pro-preview which has strong reasoning
    # 2. Increasing temperature slightly for creative reasoning
    # 3. Using detailed prompts with explicit reasoning instructions
    if thinking_level:
        logger.info(f"  → Reasoning mode: {thinking_level} (using gemini-3 model with optimized settings)")
    
    generation_config = genai.GenerationConfig(**generation_config_kwargs)
    
    # Build final system instruction (always include Spanish instruction by default)
    final_system_instruction = system_instruction
    if use_spanish:
        if final_system_instruction:
            final_system_instruction = f"{DEFAULT_SYSTEM_INSTRUCTION}\n\n{final_system_instruction}"
        else:
            final_system_instruction = DEFAULT_SYSTEM_INSTRUCTION
    
    # Safety settings - allow all content for property assessment
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    # Create model instance
    gemini_model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=final_system_instruction,
        safety_settings=safety_settings,
        tools=tools,
        tool_config=tool_config,
    )
    
    # Build content parts
    content_parts = []
    
    # Add images first if present
    if images:
        for img in images:
            content_parts.append({
                "inline_data": {
                    "mime_type": img.get("mime_type", "image/jpeg"),
                    "data": img["data"]
                }
            })
    
    # Add text prompt
    content_parts.append(prompt)
    
    # Generate content - run in thread pool for TRUE parallelism
    # The SDK's generate_content is sync and blocks the event loop
    # Comparable vision calls can legitimately take several minutes, especially with schema-constrained JSON output.
    # Keep an env override, but default higher to avoid spurious timeouts on healthy calls.
    timeout_s = float(os.getenv("GEMINI_REQUEST_TIMEOUT_S", "600"))

    # Keepalive: emit a log line every 60s while waiting for the Gemini response.
    # WHY THIS MATTERS: The pipeline worker's stall watchdog (default 300s) monitors
    # _JOB_LAST_ACTIVITY_TS which is bumped by any log emission.  Vision calls with
    # many images can legitimately take 3-8 minutes of radio silence.  Without this
    # heartbeat the watchdog kills the job and downstream steps cascade-reschedule.
    keepalive_interval_s = 60
    _keepalive_running = True

    async def _keepalive() -> None:
        elapsed = 0
        while _keepalive_running:
            await asyncio.sleep(keepalive_interval_s)
            if not _keepalive_running:
                return
            elapsed += keepalive_interval_s
            n_images = len(images) if images else 0
            logger.info(
                "Gemini keepalive | model=%s | images=%d | waiting=%ds",
                model_name, n_images, elapsed,
            )

    keepalive_task = asyncio.create_task(_keepalive())
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(gemini_model.generate_content, content_parts),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            f"Gemini request timed out after {timeout_s:.0f}s | model={model_name} | has_images={bool(images)}"
        ) from exc
    finally:
        _keepalive_running = False
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass
    
    finish_reason_out: Optional[str] = None
    # Log finish reason for debugging truncation issues
    if response.candidates:
        finish_reason = response.candidates[0].finish_reason
        finish_reason_str = str(finish_reason)
        finish_reason_out = finish_reason_str
        logger.info(f"  → Finish reason: {finish_reason}")
        if finish_reason_str in ["STOP", "FinishReason.STOP", "1"]:
            pass
        elif finish_reason_str in ["FinishReason.MAX_TOKENS", "MAX_TOKENS", "2"]:
            logger.warning(f"  ⚠️ MAX_TOKENS reached (finish_reason={finish_reason}). Response may be truncated.")
        else:
            logger.error(f"  ❌ Unusual finish reason: {finish_reason}")
            raise RuntimeError(f"Unusual finish reason: {finish_reason}")
    
    # ── Helper: coerce protobuf / MapComposite args to plain dict ──────────
    def _args_to_dict(raw: Any) -> Dict[str, Any]:
        """Convert function_call args (protobuf Struct / MapComposite / dict) to a plain dict."""
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        # Protobuf Struct / MapComposite has dict() or items()
        try:
            d = dict(raw)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
        # SDK objects sometimes have to_dict()
        td = getattr(raw, "to_dict", None)
        if callable(td):
            try:
                d2 = td()
                if isinstance(d2, dict):
                    return d2
            except Exception:
                pass
        # Last resort: JSON round-trip
        try:
            return json.loads(json.dumps(raw, default=str))
        except Exception:
            return {}

    # Extract text and/or tool calls.
    # NOTE: Function calling responses may have no text parts, only function_call parts.
    text_out: Optional[str] = None
    tool_calls_out: List[Dict[str, Any]] = []
    try:
        text_out = response.text
    except Exception:
        text_out = None
    if not text_out:
        try:
            if response.candidates:
                parts = getattr(response.candidates[0].content, "parts", None) if getattr(response.candidates[0], "content", None) else None
                if parts:
                    texts: List[str] = []
                    for p in parts:
                        t = getattr(p, "text", None)
                        if isinstance(t, str) and t.strip():
                            texts.append(t)
                        # Some SDK/schema responses can arrive as a structured function-call part.
                        # If tools were provided, treat this as a tool call.
                        fc = getattr(p, "function_call", None)
                        if fc is not None:
                            name = getattr(fc, "name", None)
                            raw_args = getattr(fc, "args", None)
                            args = _args_to_dict(raw_args)
                            if isinstance(name, str) and name.strip():
                                tool_calls_out.append({"name": name.strip(), "args": args})
                                # For schema-constrained JSON output (no tools), the SDK may wrap the JSON as function_call args.
                                if not tools and response_schema and text_out is None and args:
                                    text_out = json.dumps(args, ensure_ascii=False)
                            else:
                                logger.warning(
                                    "  ⚠️ function_call part with invalid name | name=%s | args_type=%s",
                                    repr(name), type(raw_args).__name__,
                                )
                    if texts:
                        text_out = "\n".join(texts).strip()
        except Exception as _exc:
            logger.debug("Parts extraction failed: %s", _exc)
            text_out = None
    if not text_out:
        # Final fallback: convert SDK response to dict and extract from there.
        # This catches cases where .text isn't populated but the payload exists.
        try:
            to_dict = getattr(response, "to_dict", None)
            if callable(to_dict):
                d = response.to_dict()
                cand0 = (d.get("candidates") or [None])[0] if isinstance(d, dict) else None
                content = cand0.get("content") if isinstance(cand0, dict) else None
                parts2 = content.get("parts") if isinstance(content, dict) else None
                if isinstance(parts2, list) and parts2:
                    for part in parts2:
                        if isinstance(part, dict) and isinstance(part.get("text"), str) and part.get("text").strip():
                            text_out = str(part["text"]).strip()
                            break
                        fc = part.get("functionCall") if isinstance(part, dict) else None
                        if isinstance(fc, dict):
                            name = fc.get("name")
                            args = _args_to_dict(fc.get("args"))
                            if isinstance(name, str) and name.strip():
                                tool_calls_out.append({"name": name.strip(), "args": args})
                                if not tools and response_schema and text_out is None and args:
                                    text_out = json.dumps(args, ensure_ascii=False)
        except Exception:
            text_out = None
    if not text_out and not tool_calls_out:
        # Treat as a failed call but do not throw: caller can decide how to handle.
        # Include useful debugging context so callers can fix root cause (blocked, empty parts, etc.).
        debug_bits: List[str] = []
        try:
            if response.candidates:
                c0 = response.candidates[0]
                debug_bits.append(f"finish_reason={getattr(c0, 'finish_reason', None)}")
                content = getattr(c0, "content", None)
                parts = getattr(content, "parts", None) if content is not None else None
                try:
                    debug_bits.append(f"parts_count={(len(parts) if hasattr(parts, '__len__') else 0)}")
                except Exception:
                    debug_bits.append("parts_count=?")
                # Dump each part's type + attributes so we can diagnose extraction failures.
                if parts:
                    for pi, pp in enumerate(parts):
                        ptype = type(pp).__name__
                        has_text = bool(getattr(pp, "text", None))
                        has_fc = getattr(pp, "function_call", None) is not None
                        fc_name = getattr(getattr(pp, "function_call", None), "name", None) if has_fc else None
                        fc_args_type = type(getattr(getattr(pp, "function_call", None), "args", None)).__name__ if has_fc else None
                        debug_bits.append(
                            f"part[{pi}]={ptype} text={has_text} fc={has_fc} fc_name={fc_name} fc_args_type={fc_args_type}"
                        )
                # prompt_feedback sometimes includes block reasons
                pf = getattr(response, "prompt_feedback", None)
                if pf is not None:
                    debug_bits.append(f"prompt_feedback={repr(pf)}")
        except Exception:
            pass
        suffix = (" | " + " ".join(debug_bits)) if debug_bits else ""
        return GeminiResponse(success=False, error=f"No text parts in response{suffix}", model=model_name, finish_reason=finish_reason_out)
    
    # Get usage metadata if available - THIS IS THE ACTUAL TOKEN COUNT FROM THE API
    usage: Dict[str, Any] = {}
    strict_usage = os.getenv("PIPELINE_STRICT_GEMINI_USAGE_METADATA", "true").lower() == "true"
    strict_db_write_flag = os.getenv("PIPELINE_STRICT_GEMINI_COST_DB_WRITE", "true").lower() == "true"
    if strict_db_write is not None:
        strict_db_write_flag = bool(strict_db_write)

    usage_md = getattr(response, "usage_metadata", None)
    usage_md_dict = _usage_metadata_to_dict(usage_md)

    if usage_md:
        prompt_tokens = int(getattr(usage_md, "prompt_token_count", 0) or _get_usage_int(usage_md_dict, "prompt_token_count", "promptTokenCount"))
        candidates_tokens = int(getattr(usage_md, "candidates_token_count", 0) or _get_usage_int(usage_md_dict, "candidates_token_count", "candidatesTokenCount"))
        thinking_tokens = int(getattr(usage_md, "thoughts_token_count", 0) or _get_usage_int(usage_md_dict, "thoughts_token_count", "thoughtsTokenCount"))
        total_tokens = int(getattr(usage_md, "total_token_count", 0) or _get_usage_int(usage_md_dict, "total_token_count", "totalTokenCount"))

        if total_tokens <= 0:
            total_tokens = prompt_tokens + candidates_tokens + thinking_tokens

        # These keys are used by call_gemini_json and any callers that inspect usage.
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": candidates_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        }

        if prompt_tokens <= 0:
            msg = f"Gemini usage_metadata returned prompt_tokens=0 | model={model_name}"
            if strict_usage:
                raise RuntimeError(msg)
            logger.error(f"  ❌ {msg}")

        # Track ACTUAL tokens for EXACT cost calculation
        # Image tokens are INCLUDED in prompt_token_count by the API
        tracked = _token_tracker.track(
            model=model_name,
            input_tokens=prompt_tokens,
            output_tokens=candidates_tokens,
            thinking_tokens=thinking_tokens,
            has_images=bool(images),  # Flag for logging/tracking (input images)
        )

        # Durable per-call persistence: every Gemini call writes a row.
        db = _ctx_db.get(None)
        job_ctx = _ctx_job.get({}) or {}
        if db is None:
            msg = f"Gemini call had usage_metadata but no DB context set; cannot persist call log | model={model_name}"
            if strict_db_write_flag:
                raise RuntimeError(msg)
            logger.error(f"  ❌ {msg}")
        else:
            listing_id = job_ctx.get("listing_id")
            run_id = job_ctx.get("run_id")
            stage = job_ctx.get("stage") or "unknown"
            job_id = job_ctx.get("job_id")
            job_type = job_ctx.get("job_type")

            if not listing_id or not run_id:
                msg = f"Gemini DB context missing listing_id/run_id; cannot persist call log | ctx={job_ctx}"
                if strict_db_write_flag:
                    raise RuntimeError(msg)
                logger.error(f"  ❌ {msg}")
            else:
                pricing_tier = "long" if tracked.get("is_long_context") else "standard"
                req_meta = {
                    "model_name": model_name,
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "has_images": bool(images),
                    "response_schema": bool(response_schema),
                }
                row = await db.add_gemini_call_log_row(
                    listing_id=int(listing_id),
                    run_id=str(run_id),
                    job_id=str(job_id) if job_id else None,
                    stage=str(stage),
                    job_type=str(job_type) if job_type else None,
                    model=str(model_name),
                    has_images=bool(images),
                    pricing_tier=pricing_tier,
                    pricing_mode="regular",
                    prompt_tokens=prompt_tokens,
                    output_tokens=candidates_tokens,
                    thinking_tokens=thinking_tokens,
                    total_tokens=total_tokens,
                    cost_regular=float(tracked.get("call_cost_regular") or 0.0),
                    cost_cached=float(tracked.get("call_cost_cached") or 0.0),
                    usage_metadata=usage_md_dict or None,
                    request_meta=req_meta,
                )
                if not row:
                    msg = f"Failed to persist gemini_call_log row | listing_id={listing_id} run_id={run_id} stage={stage} model={model_name}"
                    if strict_db_write_flag:
                        raise RuntimeError(msg)
                    logger.error(f"  ❌ {msg}")
    else:
        # NO usage metadata = we CANNOT track costs accurately
        msg = f"Gemini response missing usage_metadata | model={model_name}"
        if strict_usage:
            raise RuntimeError(msg)
        logger.warning(f"  ⚠️ {msg}")
    
    return GeminiResponse(
        success=True,
        text=text_out,
        tool_calls=tool_calls_out or None,
        usage=usage,
        model=model_name,
        finish_reason=finish_reason_out,
    )


async def call_gemini_json(
    prompt: str,
    model: str = "flash",
    temperature: float = 0.3,
    max_tokens: int = 65536,
    images: Optional[List[Dict[str, str]]] = None,
    response_schema: Optional[Dict] = None,
    use_spanish: bool = True,  # Default to Spanish responses
) -> Union[Dict, List, None]:
    """
    Call Gemini API and parse JSON response.
    
    Returns parsed JSON or None on failure.
    """
    response = await call_gemini(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        images=images,
        response_schema=response_schema,
        use_spanish=use_spanish,
    )
    
    if not response.success or not response.text:
        logger.error(f"Gemini JSON call failed: {response.error}")
        return None
    
    # Clean response text
    text = response.text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response text: {text[:500]}...")
        return None


async def fetch_image_as_base64(url: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
    """
    Fetch an image from URL and convert to base64 with retry logic.
    
    Returns dict with mime_type and data, or None on failure.
    """
    import asyncio as _asyncio
    strict_http = os.getenv("PIPELINE_STRICT_HTTP", "true").lower() == "true"
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; PuedoCasa/1.0)"}
                )
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        await _asyncio.sleep(1 * (attempt + 1))
                        continue
                    message = f"Failed to fetch image (HTTP {response.status_code}): {url[:120]}"
                    if strict_http:
                        raise RuntimeError(message)
                    logger.warning(f"{message}...")
                    return None
                
                content_type = response.headers.get("content-type", "image/jpeg")
                
                # Determine mime type
                if "webp" in content_type:
                    mime_type = "image/webp"
                elif "png" in content_type:
                    mime_type = "image/png"
                elif "gif" in content_type:
                    mime_type = "image/gif"
                else:
                    mime_type = "image/jpeg"
                
                # Convert to base64
                data = base64.b64encode(response.content).decode("utf-8")
                
                return {"mime_type": mime_type, "data": data}
                
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await _asyncio.sleep(2 * (attempt + 1))
                continue
            message = f"Timeout fetching image: {url[:120]}"
            if strict_http:
                raise RuntimeError(message)
            logger.warning(f"{message}...")
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                await _asyncio.sleep(1 * (attempt + 1))
                continue
            message = f"Error fetching image ({type(e).__name__}: {str(e)[:120]}): {url[:120]}"
            if strict_http:
                raise RuntimeError(message)
            logger.warning(f"{message}...")
            return None
    
    return None


def _guess_mime_type_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "image/jpeg"


async def fetch_image_source_as_base64(source: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
    """
    Fetch an image from either a URL or a local filesystem path and convert to base64.

    WHY THIS MATTERS: Some pipeline steps (e.g., cluster panoramas) create local artifacts
    that we still want to pass into Gemini as images, without needing a public URL.
    """
    if not source:
        return None

    src = str(source).strip()
    if not src:
        return None

    # Local file path support (absolute or relative)
    # We treat any existing path as a local artifact.
    try:
        p = Path(src)
        if p.exists() and p.is_file():
            data = base64.b64encode(p.read_bytes()).decode("utf-8")
            return {"mime_type": _guess_mime_type_from_path(p), "data": data}
    except Exception as e:
        logger.warning(f"Error reading local image ({type(e).__name__}): {src[:120]}")

    # Otherwise, assume it's a URL
    return await fetch_image_as_base64(src, max_retries=max_retries)


async def fetch_images_batch(urls: List[str], max_concurrent: int = 3) -> List[Optional[Dict[str, str]]]:
    """
    Fetch multiple images concurrently.
    
    Returns list of image dicts (or None for failed fetches) in same order as URLs.
    """
    import asyncio
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(url: str) -> Optional[Dict[str, str]]:
        async with semaphore:
            return await fetch_image_source_as_base64(url)
    
    tasks = [fetch_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    return list(results)


async def call_gemini_image(
    prompt: str,
    image_data: str,
    image_mime_type: str = "image/jpeg",
    model: str = "pro-image",
    temperature: float = 1.0,
    system_instruction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call Gemini image generation/editing model using REST API.
    
    Uses the same approach as the working TypeScript implementation:
    - REST API with generateContent
    - responseModalities: ['IMAGE']
    
    The text prompt comes BEFORE the image so the model understands the task
    before seeing the input. The system instruction (if provided) sets
    persistent behavioral rules like geometry preservation.
    
    Args:
        prompt: The editing instruction
        image_data: Base64 encoded input image
        image_mime_type: MIME type of input image
        model: Model alias or full name
        temperature: Generation temperature
        system_instruction: Optional system-level instruction for the model
    
    Returns:
        Dict with:
        - success: bool
        - image_data: base64 string (if success)
        - error: string (if failed)
    """
    try:
        model_name = MODELS.get(model, model)
        api_key = get_api_key()
        
        logger.info(f"🎨 Calling Gemini image generation with model: {model_name}")
        
        # Build request body
        # Text BEFORE image: model reads the editing task first, then sees the photo
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": image_mime_type,
                                "data": image_data,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.95,
                "maxOutputTokens": 8192,
                "responseModalities": ["IMAGE"],
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}
            ]
        }
        
        # Add system instruction if provided
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Use generativelanguage API (works with API keys, unlike Vertex AI which needs OAuth)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        logger.info(f"  📡 Calling: {url.replace(api_key, 'HIDDEN_KEY')}")
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            raw = response.text
            
            if not response.is_success:
                logger.error(f"  ❌ HTTP {response.status_code}: {raw[:500]}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {raw[:200]}",
                }
            
            # Parse stream response - it's a JSON array
            import json as json_module
            try:
                response_array = json_module.loads(raw)
                if not isinstance(response_array, list):
                    if isinstance(response_array, dict) and "candidates" in response_array:
                        response_array = [response_array]
                    else:
                        raise ValueError("Response is not an array")

                # Best-effort token accounting for REST image calls.
                # The generativelanguage REST payload can include usageMetadata (camelCase).
                strict_usage = os.getenv("PIPELINE_STRICT_GEMINI_USAGE_METADATA", "true").lower() == "true"
                strict_db_write = os.getenv("PIPELINE_STRICT_GEMINI_COST_DB_WRITE", "true").lower() == "true"

                usage_md: Optional[Dict[str, Any]] = None
                for chunk in response_array:
                    if isinstance(chunk, dict) and isinstance(chunk.get("usageMetadata"), dict):
                        usage_md = chunk.get("usageMetadata")

                if usage_md:
                    prompt_tokens = int(usage_md.get("promptTokenCount") or 0)
                    candidates_tokens = int(usage_md.get("candidatesTokenCount") or 0)
                    thinking_tokens = int(usage_md.get("thoughtsTokenCount") or 0)
                    total_tokens = int(usage_md.get("totalTokenCount") or 0) or (prompt_tokens + candidates_tokens + thinking_tokens)

                    tracked = _token_tracker.track(
                        model=model_name,
                        input_tokens=prompt_tokens,
                        output_tokens=candidates_tokens,
                        thinking_tokens=thinking_tokens,
                        has_images=True,  # image edit always includes an input image
                    )

                    db = _ctx_db.get(None)
                    job_ctx = _ctx_job.get({}) or {}
                    if db is None:
                        msg = f"Gemini image call had usageMetadata but no DB context set; cannot persist call log | model={model_name}"
                        if strict_db_write:
                            raise RuntimeError(msg)
                        logger.error(f"  ❌ {msg}")
                    else:
                        listing_id = job_ctx.get("listing_id")
                        run_id = job_ctx.get("run_id")
                        stage = job_ctx.get("stage") or "unknown"
                        job_id = job_ctx.get("job_id")
                        job_type = job_ctx.get("job_type")
                        if not listing_id or not run_id:
                            msg = f"Gemini image DB context missing listing_id/run_id; cannot persist call log | ctx={job_ctx}"
                            if strict_db_write:
                                raise RuntimeError(msg)
                            logger.error(f"  ❌ {msg}")
                        else:
                            pricing_tier = "long" if tracked.get("is_long_context") else "standard"
                            req_meta = {
                                "model_name": model_name,
                                "temperature": temperature,
                                "max_output_tokens": 8192,
                                "has_images": True,
                                "response_schema": False,
                                "response_modalities": ["IMAGE"],
                            }
                            row = await db.add_gemini_call_log_row(
                                listing_id=int(listing_id),
                                run_id=str(run_id),
                                job_id=str(job_id) if job_id else None,
                                stage=str(stage),
                                job_type=str(job_type) if job_type else None,
                                model=str(model_name),
                                has_images=True,
                                pricing_tier=pricing_tier,
                                pricing_mode="regular",
                                prompt_tokens=prompt_tokens,
                                output_tokens=candidates_tokens,
                                thinking_tokens=thinking_tokens,
                                total_tokens=total_tokens,
                                cost_regular=float(tracked.get("call_cost_regular") or 0.0),
                                cost_cached=float(tracked.get("call_cost_cached") or 0.0),
                                usage_metadata=usage_md,
                                request_meta=req_meta,
                            )
                            if not row:
                                msg = f"Failed to persist gemini_call_log row (image call) | listing_id={listing_id} run_id={run_id} stage={stage} model={model_name}"
                                if strict_db_write:
                                    raise RuntimeError(msg)
                                logger.error(f"  ❌ {msg}")
                else:
                    msg = f"Gemini image response missing usageMetadata | model={model_name}"
                    if strict_usage:
                        raise RuntimeError(msg)
                    logger.warning(f"  ⚠️ {msg}")
                
                # Extract images from response
                for chunk in response_array:
                    candidates = chunk.get("candidates", [])
                    for candidate in candidates:
                        parts = candidate.get("content", {}).get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                image_b64 = part["inlineData"]["data"]
                                orig_mime = part["inlineData"].get("mimeType", "image/png")
                                
                                # Compress to JPEG to reduce payload size (~100KB PNG → ~25KB JPEG)
                                compressed_b64, final_mime = _compress_to_jpeg(image_b64, quality=85)
                                
                                orig_size = len(image_b64) * 3 // 4 // 1024  # Approx KB
                                new_size = len(compressed_b64) * 3 // 4 // 1024
                                logger.info(f"  ✅ Image generated ({orig_mime} {orig_size}KB → JPEG {new_size}KB)")
                                
                                return {
                                    "success": True,
                                    "image_data": compressed_b64,
                                    "mime_type": final_mime,
                                }
                
                # Check if we got text instead
                text_content = ""
                for chunk in response_array:
                    candidates = chunk.get("candidates", [])
                    for candidate in candidates:
                        parts = candidate.get("content", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                text_content += part["text"]
                
                if text_content:
                    logger.warning(f"  ⚠️ Got text instead of image: {text_content[:200]}")
                    return {
                        "success": False,
                        "error": f"Model returned text instead of image: {text_content[:200]}",
                    }
                
                return {
                    "success": False,
                    "error": "No image in response",
                }
                
            except json_module.JSONDecodeError as e:
                logger.error(f"  ❌ JSON parse error: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse response: {str(e)}",
                }
        
    except Exception as e:
        logger.exception(f"Gemini image call failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }
