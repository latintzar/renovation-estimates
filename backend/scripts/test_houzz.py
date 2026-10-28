import requests
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}

def extract_businesses(html):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    businesses = []
    for block in blocks:
        try:
            data = json.loads(block)
            items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "LocalBusiness":
                    businesses.append({
                        "name": item.get("name", "").strip(),
                        "phone": item.get("telephone", "").strip(),
                        "rating": item.get("aggregateRating", {}).get("ratingValue") if isinstance(item.get("aggregateRating"), dict) else None,
                        "reviews": item.get("aggregateRating", {}).get("reviewCount") if isinstance(item.get("aggregateRating"), dict) else None,
                    })
        except:
            pass
    return businesses

url = "https://www.houzz.com/professionals/plumber/c/Marbella--Spain"
resp = requests.get(url, headers=HEADERS)
print(f"Status: {resp.status_code}")
biz = extract_businesses(resp.text)
print(f"Found {len(biz)} plumbers with web presence/projects.")
for b in biz[:5]:
    print(b)
