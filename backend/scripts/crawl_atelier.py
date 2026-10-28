"""
Recursive crawler for atelierneyra.com using Scrapling StealthyFetcher.
Renders JS (Squarespace) and extracts all internal links + page content.
"""

import asyncio
import json
import logging
import re
from urllib.parse import urljoin, urlparse
from scrapling import StealthyFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DOMAIN = "atelierneyra.com"
START_URL = "https://atelierneyra.com/"
MAX_PAGES = 50

visited = set()
results = {}


def is_internal(url: str) -> bool:
    parsed = urlparse(url)
    return BASE_DOMAIN in (parsed.netloc or "")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return clean.rstrip("/")


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all href links from HTML."""
    links = set()
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html):
        raw = match.group(1)
        if raw.startswith("#") or raw.startswith("mailto:") or raw.startswith("tel:"):
            continue
        absolute = urljoin(base_url, raw)
        if is_internal(absolute):
            links.add(normalize_url(absolute))
    return sorted(links)


def extract_text(html: str) -> str:
    """Quick HTML-to-text: strip tags, collapse whitespace."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line)


async def crawl_page(url: str, fetcher: StealthyFetcher, depth: int = 0):
    norm = normalize_url(url)
    if norm in visited or len(visited) >= MAX_PAGES:
        return
    visited.add(norm)

    logger.info(f"[depth={depth}] Crawling: {norm}")

    try:
        page = await asyncio.wait_for(
            fetcher.async_fetch(norm),
            timeout=60
        )
        html = page.html_content
        status = page.status
        logger.info(f"  -> status={status} | html_len={len(html)}")

        links = extract_links(html, norm)
        text = extract_text(html)

        results[norm] = {
            "url": norm,
            "status": status,
            "html_length": len(html),
            "text_content": text,
            "links_found": links,
            "depth": depth,
        }

        logger.info(f"  -> Found {len(links)} internal links: {links}")

        for link in links:
            if link not in visited:
                await crawl_page(link, fetcher, depth + 1)

    except asyncio.TimeoutError:
        logger.error(f"  -> TIMEOUT for {norm}")
        results[norm] = {"url": norm, "error": "timeout", "depth": depth}
    except Exception as e:
        logger.error(f"  -> ERROR for {norm}: {e}")
        results[norm] = {"url": norm, "error": str(e), "depth": depth}


async def main():
    logger.info(f"Starting recursive crawl of {START_URL}")
    fetcher = StealthyFetcher()

    await crawl_page(START_URL, fetcher)

    logger.info(f"\n{'='*60}")
    logger.info(f"CRAWL COMPLETE: {len(results)} pages")
    logger.info(f"{'='*60}\n")

    out_path = "/root/puedo_casa/lean-mvp/backend/scripts/atelier_crawl_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {out_path}")

    for url, data in results.items():
        print(f"\n{'='*60}")
        print(f"URL: {url}")
        print(f"Depth: {data.get('depth', '?')}")
        if "error" in data:
            print(f"ERROR: {data['error']}")
        else:
            print(f"Status: {data.get('status')}")
            print(f"HTML Length: {data.get('html_length')}")
            print(f"Links: {data.get('links_found', [])}")
            print(f"--- TEXT CONTENT ---")
            print(data.get("text_content", "")[:3000])
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
