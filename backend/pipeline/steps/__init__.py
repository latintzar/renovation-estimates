"""
Pipeline Steps
==============

Each step module contains functions that:
1. Read required inputs from the database
2. Call Gemini AI for analysis
3. Write results back to the database
4. Return success/failure status

Step Naming Convention:
- T1-T4: Text Analysis steps
- P1-P3: Photo Analysis steps
- M1: Smart M2 (room sizing)
- A1-A3: Architect steps
- R1-R4: Renovation scope steps
- V1-V4: Visual generation steps
"""

# NOTE: This package now only exposes steps that still exist in the codebase.
# Deprecated steps were removed; importing them here would break runtime imports.

# §1 Home Condition (M1)
from .smart_m2 import run_m1_smart_m2

# §3 Visuals (V1-V4)
from .visuals import run_v1_defurnish, run_v2_select_before, run_v3_prompts, run_v4_render

__all__ = [
    "run_m1_smart_m2",
    "run_v1_defurnish",
    "run_v2_select_before",
    "run_v3_prompts",
    "run_v4_render",
]
