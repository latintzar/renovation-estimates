"""
Google Search via ScrapingDog + Full Page Fetch
================================================

ScrapingDog ONLY - NO Google API fallback.

Usage:
    results = await search_google("renovation costs Madrid Spain 2025")
    pages = await fetch_pages_batch([r.url for r in results[:3]])
"""

import os
import re
import asyncio
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Load environment
from pathlib import Path
from dotenv import load_dotenv
backend_root = Path(__file__).parent.parent
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY", "")
SCRAPINGDOG_BASE_URL = "https://api.scrapingdog.com/google"

# Rate limiting
MAX_CONCURRENT_SEARCHES = 3
MAX_CONCURRENT_FETCHES = 5
SEARCH_DELAY_MS = 500  # Delay between search batches


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SearchResult:
    """A single Google search result."""
    title: str
    url: str
    snippet: str
    domain: str
    rank: int
    query: str = ""
    
    # Populated after credibility check
    credibility: Optional[str] = None
    credibility_method: Optional[str] = None
    
    # Populated after full page fetch
    full_content: Optional[str] = None
    fetch_error: Optional[str] = None


@dataclass
class SearchResponse:
    """Response from a batch of searches."""
    results: List[SearchResult] = field(default_factory=list)
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: List[str] = field(default_factory=list)
    error: Optional[str] = None


# =============================================================================
# GOOGLE SEARCH (ScrapingDog)
# =============================================================================

async def search_google(
    query: str,
    num_results: int = 10,
    country: str = "es",
) -> List[SearchResult]:
    """
    Execute a single Google search via ScrapingDog.
    
    Args:
        query: Search query string
        num_results: Number of results to return (max 10)
        country: Country code for localized results
    
    Returns:
        List of SearchResult objects
    """
    if not SCRAPINGDOG_API_KEY:
        raise ValueError("SCRAPINGDOG_API_KEY not set")
    
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "query": query,
        "results": str(min(num_results, 10)),
        "country": country,
        "page": "0",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(SCRAPINGDOG_BASE_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"ScrapingDog error {response.status_code}: {response.text[:200]}")
                return []
            
            data = response.json()
            
            # ScrapingDog returns organic_results or organic_data
            items = data.get("organic_results") or data.get("organic_data") or []
            
            results = []
            for idx, item in enumerate(items):
                url = item.get("link") or item.get("url", "")
                domain = extract_domain(url)
                
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                    domain=domain,
                    rank=idx + 1,
                    query=query,
                ))
            
            logger.info(f"🔍 Search '{query[:50]}...' returned {len(results)} results")
            return results
            
    except Exception as e:
        logger.error(f"ScrapingDog search failed for '{query}': {e}")
        return []


async def search_google_batch(
    queries: List[str],
    num_results: int = 10,
    country: str = "es",
    concurrency: int = MAX_CONCURRENT_SEARCHES,
) -> SearchResponse:
    """
    Execute multiple Google searches in parallel with rate limiting.
    
    Args:
        queries: List of search queries
        num_results: Results per query
        country: Country code
        concurrency: Max concurrent requests
    
    Returns:
        SearchResponse with all results
    """
    if not queries:
        return SearchResponse()
    
    # Deduplicate queries
    unique_queries = list(dict.fromkeys(queries))
    
    response = SearchResponse(total_queries=len(unique_queries))
    semaphore = asyncio.Semaphore(concurrency)
    
    async def search_with_semaphore(query: str) -> List[SearchResult]:
        async with semaphore:
            results = await search_google(query, num_results, country)
            # Small delay between requests
            await asyncio.sleep(SEARCH_DELAY_MS / 1000)
            return results
    
    # Execute all searches
    tasks = [search_with_semaphore(q) for q in unique_queries]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    for query, result in zip(unique_queries, all_results):
        if isinstance(result, Exception):
            logger.error(f"Search failed for '{query}': {result}")
            response.failed_queries.append(query)
        elif result:
            response.results.extend(result)
            response.successful_queries += 1
        else:
            response.failed_queries.append(query)
    
    logger.info(f"📊 Batch search: {response.successful_queries}/{response.total_queries} queries successful, {len(response.results)} total results")
    
    return response


# =============================================================================
# FULL PAGE FETCH
# =============================================================================

async def fetch_full_page(
    url: str,
    timeout: int = 15,
) -> Optional[str]:
    """
    Fetch and extract text content from a web page.
    
    Args:
        url: Page URL to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Extracted text content or None on failure
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Page fetch failed for {url}: HTTP {response.status_code}")
                return None
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                logger.warning(f"Non-HTML content at {url}: {content_type}")
                return None
            
            # Parse HTML and extract text
            html = response.text
            text = extract_text_from_html(html)
            
            if text and len(text) > 100:
                logger.info(f"📄 Fetched {url[:50]}... ({len(text)} chars)")
                return text
            else:
                logger.warning(f"Insufficient content from {url}")
                return None
                
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


async def fetch_pages_batch(
    urls: List[str],
    concurrency: int = MAX_CONCURRENT_FETCHES,
) -> Dict[str, Optional[str]]:
    """
    Fetch multiple pages in parallel with deduplication.
    
    Args:
        urls: List of URLs to fetch
        concurrency: Max concurrent requests
    
    Returns:
        Dict mapping URL to content (or None if failed)
    """
    if not urls:
        return {}
    
    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(urls))
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def fetch_with_semaphore(url: str) -> tuple[str, Optional[str]]:
        async with semaphore:
            content = await fetch_full_page(url)
            return (url, content)
    
    # Execute all fetches
    tasks = [fetch_with_semaphore(url) for url in unique_urls]
    results = await asyncio.gather(*tasks)
    
    # Build result dict
    result_dict = {url: content for url, content in results}
    
    successful = sum(1 for c in result_dict.values() if c is not None)
    logger.info(f"📦 Batch fetch: {successful}/{len(unique_urls)} pages successful")
    
    return result_dict


# =============================================================================
# HTML TEXT EXTRACTION
# =============================================================================

def extract_text_from_html(html: str) -> str:
    """
    Extract clean text content from HTML.
    
    Removes scripts, styles, nav, footer, etc.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe"]):
        tag.decompose()
    
    # Get main content if available
    main_content = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r"content|article|post|entry"))
    
    if main_content:
        text = main_content.get_text(separator=" ", strip=True)
    else:
        # Fall back to body
        body = soup.find("body")
        text = body.get_text(separator=" ", strip=True) if body else soup.get_text(separator=" ", strip=True)
    
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    
    # Truncate very long content (keep first 15K chars)
    if len(text) > 15000:
        text = text[:15000] + "..."
    
    return text


def extract_domain(url: str) -> str:
    """Extract domain from URL, removing www prefix."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


# =============================================================================
# COST TRACKING
# =============================================================================

def estimate_search_cost(num_queries: int) -> float:
    """Estimate cost for a batch of searches ($0.002 per query)."""
    return num_queries * 0.002

