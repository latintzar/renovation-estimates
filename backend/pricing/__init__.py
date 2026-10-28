"""
Pricing Module - V2
===================

Comparable-centric strategy selection pipeline.

Usage:
    # Queue-based V2 run:
    from pricing.v2_scheduler import enqueue_v2_run
    run_id = await enqueue_v2_run(db=database, listing_id=12)
    
"""

from .v2_scheduler import enqueue_v2_run

__all__ = [
    "enqueue_v2_run",
]
