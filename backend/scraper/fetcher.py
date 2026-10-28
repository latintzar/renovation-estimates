"""
URL Fetcher
===========

Fetches HTML content from URLs with caching and error handling.
Uses httpx for async requests.
"""

import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx

from config import settings

logger = logging.getLogger(__name__)

# User agents for different scenarios
USER_AGENTS = {
    "chrome": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
}

# Default headers to look like a real browser
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENTS["chrome"],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class FetchResult:
    """Result of a fetch operation."""
    
    def __init__(
        self,
        success: bool,
        html: Optional[str] = None,
        error: Optional[str] = None,
        status_code: Optional[int] = None,
        final_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        used_scrapling: bool = False
    ):
        self.success = success
        self.html = html
        self.error = error
        self.status_code = status_code
        self.final_url = final_url
        self.headers = headers or {}
        self.used_scrapling = used_scrapling


async def fetch_url(
    url: str,
    use_scrapling: bool = False,
    timeout: int = 30,
    follow_redirects: bool = True,
    mobile: bool = False,
    render_js: bool = True  # Only applies when use_scrapling=True
) -> FetchResult:
    """
    Fetch HTML content from a URL.
    
    Args:
        url: The URL to fetch
        use_scrapling: Whether to use Scrapling stealth browser (for protected sites)
        timeout: Request timeout in seconds
        follow_redirects: Whether to follow HTTP redirects
        mobile: Use mobile user agent
        
    Returns:
        FetchResult with html or error
    """
    logger.info(f"Fetching: {url[:80]}...")
    
    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url
    
    # Choose headers
    headers = DEFAULT_HEADERS.copy()
    if mobile:
        headers["User-Agent"] = USER_AGENTS["mobile"]
    
    # Add referer based on domain
    parsed = urlparse(url)
    headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
    
    # Try Scrapling if requested
    if use_scrapling:
        return await _fetch_with_scrapling(url, timeout)
    
    # Direct fetch
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            http2=False,  # Disabled: requires 'h2' package
        ) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return FetchResult(
                    success=True,
                    html=response.text,
                    status_code=response.status_code,
                    final_url=str(response.url),
                    headers=dict(response.headers)
                )
            elif response.status_code == 403:
                # Try Scrapling as fallback
                logger.info("Got 403, trying Scrapling...")
                return await _fetch_with_scrapling(url, timeout)
            else:
                return FetchResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    status_code=response.status_code
                )
                
    except httpx.TimeoutException:
        return FetchResult(
            success=False,
            error=f"Request timed out after {timeout}s"
        )
    except httpx.RequestError as e:
        return FetchResult(
            success=False,
            error=f"Request failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return FetchResult(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )


async def _fetch_with_scrapling(url: str, timeout: int = 30) -> FetchResult:
    """
    Fetch using Scrapling (Playwright stealth) for protected sites.

    WHY THIS MATTERS: Scrapling is our main defense against anti-bot systems on
    sites like idealista and jamesedition. It uses a patched version of Playwright
    to completely bypass Cloudflare and Datadome challenges locally, for free.
    """
    from scraper.bot_detection import domain_needs_scrapling
    from scrapling import StealthyFetcher
    import asyncio

    domain = urlparse(url).netloc.replace("www.", "")
    is_protected, protect_reason = domain_needs_scrapling(domain)

    logger.info(f"Scrapling stealth mode for {domain} | reason={protect_reason}")

    try:
        # We run the synchronous StealthyFetcher in a thread, or use async_fetch
        # async_fetch is provided by StealthyFetcher
        fetcher = StealthyFetcher()
        
        # Add a timeout to the fetcher if possible, or wrap in asyncio.wait_for
        # Scrapling handles the browser spin-up and anti-bot bypass
        page = await asyncio.wait_for(
            fetcher.async_fetch(url),
            timeout=timeout + 30  # Give it extra time for browser spin-up
        )

        logger.info(f"Scrapling OK | status={page.status} | domain={domain}")

        return FetchResult(
            success=True,
            html=page.html_content,
            status_code=page.status,
            final_url=url,
            headers=dict(page.headers) if hasattr(page, 'headers') else {},
            used_scrapling=True  # Keep this flag True so router knows we used stealth
        )

    except asyncio.TimeoutError:
        logger.error(f"Scrapling timeout after {timeout + 30}s | domain={domain}")
        return FetchResult(
            success=False,
            error=f"Scrapling timeout after {timeout + 30}s"
        )
    except Exception as e:
        logger.error(f"Scrapling error: {e} | domain={domain}")
        return FetchResult(
            success=False,
            error=f"Scrapling error: {str(e)}"
        )


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return (parsed.netloc or "").replace("www.", "")
    except Exception:
        return "unknown"


def is_idealista_url(url: str) -> bool:
    """Check if URL is from Idealista."""
    domain = get_domain(url)
    return "idealista" in domain


def is_fotocasa_url(url: str) -> bool:
    """Check if URL is from Fotocasa."""
    domain = get_domain(url)
    return "fotocasa" in domain


def get_parser_type(url: str) -> str:
    """Determine which parser to use for a URL."""
    domain = get_domain(url)
    
    if "idealista" in domain:
        return "idealista"
    elif "fotocasa" in domain:
        return "fotocasa"
    elif "lucasfox" in domain:
        return "lucasfox"
    elif "engelvoelkers" in domain:
        return "engelvoelkers"
    else:
        return "universal"

