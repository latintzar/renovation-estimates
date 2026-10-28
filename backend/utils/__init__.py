"""
Utility modules for Lean MVP Pipeline
=====================================

- google_search: ScrapingDog Google Search + Full Page Fetch
- domain_credibility: 3-tier credibility scoring system
"""

from .google_search import (
    search_google,
    search_google_batch,
    fetch_full_page,
    fetch_pages_batch,
    SearchResult,
)

from .domain_credibility import (
    score_domain,
    score_domain_with_title,
    filter_by_credibility,
    Credibility,
    STATIC_WHITELISTS,
)

__all__ = [
    # Google Search
    "search_google",
    "search_google_batch",
    "fetch_full_page",
    "fetch_pages_batch",
    "SearchResult",
    # Domain Credibility
    "score_domain",
    "score_domain_with_title",
    "filter_by_credibility",
    "Credibility",
    "STATIC_WHITELISTS",
]

