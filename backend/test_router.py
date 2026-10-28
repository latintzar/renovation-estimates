import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'lean-mvp/backend'))

import asyncio
import logging
from scraper.router import scrape_url

async def main():
    url = "https://www.jamesedition.com/real_estate/javea-spain/villa-romer-the-sea-as-your-horizon-near-la-granadella-javea-alicante-16787814"
    print(f"Scraping {url}...")
    response = await scrape_url(url)
    if response.success and response.data:
        print("SUCCESS!")
        print("Title:", response.data.title)
        print("Price:", response.data.price_eur)
        print("Images:", len(response.data.image_urls or []))
    else:
        print("FAILED:", response.error)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
