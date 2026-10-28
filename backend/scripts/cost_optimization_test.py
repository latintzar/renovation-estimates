"""
Cost Optimization Test: Can we do exhaustive tradesperson search for < $0.50?
=============================================================================

Hypothesis: Most of the pipeline can run on Gemma ($0.00005/call).
DeepSeek ($0.003/call) is only needed for final synthesis (1-3 calls).

Tests:
1. Heuristic pre-filter: classify URLs WITHOUT any LLM (free)
2. Gemma page classification: service vs directory vs product vs forum
3. Gemma structured entity extraction from a real VIK page
4. Gemma entity profile synthesis (can it replace DeepSeek here?)
5. Cost projection for full exhaustive pipeline
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path

import boto3
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

pass  # Recipient runtime supplies its explicit private environment.

bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

GEMMA = "google.gemma-3-4b-it"
DEEPSEEK = "deepseek.v3.2"
PRICING = {GEMMA: (0.04, 0.08), DEEPSEEK: (0.62, 1.85)}

calls = []

def llm(model, prompt, purpose, max_tokens=400):
    t0 = time.time()
    r = bedrock.converse(
        modelId=model,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
    )
    ms = int((time.time() - t0) * 1000)
    txt = r["output"]["message"]["content"][0]["text"]
    u = r["usage"]
    p = PRICING[model]
    cost = (u["inputTokens"] / 1e6) * p[0] + (u["outputTokens"] / 1e6) * p[1]
    calls.append({"model": model, "purpose": purpose, "cost": cost,
                   "in": u["inputTokens"], "out": u["outputTokens"], "ms": ms})
    tag = "GEMMA" if "gemma" in model else "DEEPSEEK"
    print(f"  [{tag}] ${cost:.6f} | {u['inputTokens']}in {u['outputTokens']}out | {ms}ms | {purpose}")
    return txt


async def scrape(url):
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
            })
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup.find_all(["script", "style", "nav", "footer", "header"]):
                t.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return re.sub(r"\s+", " ", text).strip()[:8000]
    except:
        return None


# ── TEST 1: Heuristic pre-filter (ZERO LLM cost) ────────────────────────

def test_heuristic_classifier():
    print("\n" + "=" * 70)
    print("TEST 1: Heuristic URL classifier (zero LLM cost)")
    print("=" * 70)

    test_urls = [
        ("https://vik-sofia.eu/montaj-dush-kabina-cena/", "service"),
        ("https://mastersofia.bg/remont-na-banya-ceni/", "service"),
        ("https://bestmaster.bg/testimonials/", "service"),
        ("https://vikremont.com/препоръки/", "service"),
        ("https://elvidom.bg/услуги-вик/", "service"),
        ("https://hidro-start.com/montaz-na-dush-kabina/", "service"),
        ("https://sos-vik.com/montaj-dush-kabini/", "service"),
        ("https://vikuslugi-sofia.com/вик-услуги-център/", "service"),
        ("https://www.alo.bg/obiavi/uslugi/remont-vik/", "directory"),
        ("https://maistorplus.com/pros/remont-bania/sofia", "directory"),
        ("https://www.daibau.bg/ukazatel/remont_na_banya/sofiya", "directory"),
        ("https://www.411.bg/vik-uslugi/vik-remont-montaj/", "directory"),
        ("https://forum.napravisam.bg/viewtopic.php?t=26899", "forum"),
        ("https://www.bg-mamma.com/?topic=202048", "forum"),
        ("https://www.aquanet.ru/feedbacks/", "product"),
        ("https://baniastil.com/душ-кабини/", "product"),
        ("https://www.home-max.bg/banya/dush-kabini/", "product"),
        ("https://youtube.com/watch?v=abc123", "noise"),
        ("https://facebook.com/group/sofia-living", "noise"),
    ]

    service_patterns = [
        r"vik[-_]", r"uslugi", r"remont", r"montaj", r"vodoprovod",
        r"maistor", r"master", r"plumb", r"hidro", r"sos[-_]vik",
        r"avari", r"kanaldo", r"elvidom", r"shalom",
    ]
    directory_patterns = [
        r"alo\.bg", r"maistorplus", r"daibau", r"411\.bg",
        r"starofservice", r"flattro",
    ]
    forum_patterns = [
        r"forum\.", r"viewtopic", r"bg-mamma", r"napravisam",
        r"topic=", r"reddit\.com",
    ]
    product_patterns = [
        r"home-max\.bg", r"baniastil\.com", r"aquanova\.bg",
        r"dush-kabini$", r"aquanet\.ru",
    ]
    noise_patterns = [
        r"youtube\.com", r"facebook\.com", r"instagram\.com",
        r"tiktok\.com", r"pinterest\.com",
    ]

    def classify_url(url):
        url_lower = url.lower()
        for p in noise_patterns:
            if re.search(p, url_lower):
                return "noise"
        for p in directory_patterns:
            if re.search(p, url_lower):
                return "directory"
        for p in forum_patterns:
            if re.search(p, url_lower):
                return "forum"
        for p in product_patterns:
            if re.search(p, url_lower):
                return "product"
        for p in service_patterns:
            if re.search(p, url_lower):
                return "service"
        return "unknown"

    correct = 0
    for url, expected in test_urls:
        predicted = classify_url(url)
        match = "OK" if predicted == expected else "MISS"
        if match == "OK":
            correct += 1
        print(f"  {match:4} | {predicted:10} (expected {expected:10}) | {url[:60]}")

    print(f"\n  Accuracy: {correct}/{len(test_urls)} = {correct/len(test_urls)*100:.0f}%")
    print(f"  Cost: $0.00 (pure regex, no LLM)")
    return correct / len(test_urls)


# ── TEST 2: Gemma page classification ────────────────────────────────────

async def test_gemma_classification():
    print("\n" + "=" * 70)
    print("TEST 2: Gemma page classification (on real scraped pages)")
    print("=" * 70)

    test_pages = [
        ("https://vik-sofia.eu/montaj-dush-kabina-cena/", "service_website"),
        ("https://mastersofia.bg/remont-na-banya-ceni/", "service_website"),
        ("https://maistorplus.com/pros/remont-bania/sofia", "directory"),
        ("https://forum.napravisam.bg/viewtopic.php?t=26899", "forum"),
        ("https://www.home-max.bg/banya/dush-kabini/", "product_shop"),
    ]

    for url, expected in test_pages:
        content = await scrape(url)
        if not content:
            print(f"  SKIP | Could not scrape {url}")
            continue

        result = llm(GEMMA,
            f"Classify this webpage. ONE WORD answer only.\n"
            f"Options: service_website, directory, forum, product_shop, irrelevant\n"
            f"- service_website = a plumber/contractor's own business page\n"
            f"- directory = lists multiple service providers\n"
            f"- forum = discussion/Q&A where people recommend services\n"
            f"- product_shop = sells products (shower cabins, tiles etc)\n"
            f"- irrelevant = none of the above\n\n"
            f"URL: {url}\nContent: {content[:1500]}\n\nClassification:",
            f"classify:{url[:40]}",
            max_tokens=20
        )
        predicted = result.strip().lower().split()[0] if result.strip() else "?"
        match = "OK" if predicted == expected else "MISS"
        print(f"  {match:4} | got={predicted:18} expected={expected:18} | {url[:50]}")


# ── TEST 3: Gemma structured extraction from a VIK service page ──────────

async def test_gemma_extraction():
    print("\n" + "=" * 70)
    print("TEST 3: Gemma structured entity extraction")
    print("=" * 70)

    service_urls = [
        "https://vik-sofia.eu/montaj-dush-kabina-cena/",
        "https://mastersofia.bg/remont-na-banya-ceni/",
        "https://bestmaster.bg/remont-na-banya-ceni/",
        "https://hidro-start.com/montaz-na-dush-kabina/",
        "https://sos-vik.com/montaj-dush-kabini/",
    ]

    for url in service_urls:
        content = await scrape(url)
        if not content:
            print(f"  SKIP | {url}")
            continue

        result = llm(GEMMA,
            f"Extract business info from this plumber/contractor page.\n"
            f"URL: {url}\nContent: {content[:2500]}\n\n"
            f'JSON only: {{"business_name":"...","phone":"...or not_found",'
            f'"address":"...or not_found","services":["list of services"],'
            f'"prices":{{"service":"price in BGN"}},'
            f'"serves_area":"...","has_reviews":true/false}}',
            f"extract:{url[:35]}",
            max_tokens=350
        )
        print(f"\n  URL: {url}")
        print(f"  Extracted: {result[:300]}")


# ── TEST 4: Gemma vs DeepSeek for profile synthesis ──────────────────────

async def test_gemma_vs_deepseek_synthesis():
    print("\n" + "=" * 70)
    print("TEST 4: Gemma vs DeepSeek profile synthesis (quality + cost)")
    print("=" * 70)

    # Gather real facts from a few pages about one entity
    urls = [
        "https://vik-sofia.eu/montaj-dush-kabina-cena/",
        "https://vik-sofia.eu/izgrazhdane-na-banya-ceni/",
    ]
    facts = []
    for url in urls:
        content = await scrape(url)
        if content:
            f = llm(GEMMA,
                f"Extract ALL facts about this plumbing business.\n"
                f"URL: {url}\nContent: {content[:2500]}\n\n"
                f"List: business name, phone, address, services, prices, "
                f"specialties, years active, reviews, anything useful.",
                f"facts:{url[:30]}",
                max_tokens=300
            )
            facts.append(f"Source: {url}\nFacts: {f}")

    context = "\n---\n".join(facts)
    prompt = (
        f"Write a scored profile for vik-sofia.eu (plumber in Sofia).\n\n"
        f"Sources:\n{context}\n\n"
        f"Include: name, phone, address, services, prices, reviews.\n"
        f"Score 1-10: reliability, quality, value, communication, shower experience.\n"
        f"Be honest. Say 'not found' if missing."
    )

    print("\n  --- GEMMA profile ---")
    gemma_profile = llm(GEMMA, prompt, "profile:gemma", max_tokens=600)
    print(f"  {gemma_profile[:500]}")

    print("\n  --- DEEPSEEK profile ---")
    ds_profile = llm(DEEPSEEK, prompt, "profile:deepseek", max_tokens=600)
    print(f"  {ds_profile[:500]}")

    # Cost comparison
    gemma_calls_here = [c for c in calls if c["purpose"] == "profile:gemma"]
    ds_calls_here = [c for c in calls if c["purpose"] == "profile:deepseek"]
    if gemma_calls_here and ds_calls_here:
        ratio = ds_calls_here[0]["cost"] / gemma_calls_here[0]["cost"]
        print(f"\n  Gemma cost:    ${gemma_calls_here[0]['cost']:.6f}")
        print(f"  DeepSeek cost: ${ds_calls_here[0]['cost']:.6f}")
        print(f"  DeepSeek is {ratio:.0f}x more expensive for this task")


# ── TEST 5: Cost projection ──────────────────────────────────────────────

def test_cost_projection():
    print("\n" + "=" * 70)
    print("TEST 5: Cost projection for full exhaustive pipeline")
    print("=" * 70)

    # Use actual per-call costs from our test
    gemma_avg = sum(c["cost"] for c in calls if "gemma" in c["model"]) / max(1, len([c for c in calls if "gemma" in c["model"]]))
    ds_avg = sum(c["cost"] for c in calls if "deepseek" in c["model"]) / max(1, len([c for c in calls if "deepseek" in c["model"]]))

    print(f"\n  Measured costs per call:")
    print(f"  Gemma avg:    ${gemma_avg:.6f}")
    print(f"  DeepSeek avg: ${ds_avg:.6f}")

    scenarios = [
        ("Conservative (like Sofia v1)", 500, 50, 15, 2),
        ("Thorough (recursive expansion)", 1500, 100, 20, 2),
        ("Exhaustive (tireless recursive)", 3000, 150, 25, 3),
        ("Obsessive (every single page)", 5000, 200, 30, 3),
    ]

    # Two strategies
    print(f"\n  Strategy A: Gemma triage + Gemma extraction + DeepSeek top-N profiles")
    print(f"  Strategy B: Gemma for EVERYTHING + DeepSeek ONLY for final recommendation")
    print()

    for name, pages, entities, top_n, final_calls in scenarios:
        # Strategy A: DeepSeek for top-N profiles
        a_gemma = (pages * 2 + entities) * gemma_avg  # classify + extract + score
        a_ds = (top_n + final_calls) * ds_avg
        a_total = a_gemma + a_ds

        # Strategy B: Gemma for everything, DeepSeek only for final 1-2 calls
        b_gemma = (pages * 2 + entities + top_n) * gemma_avg
        b_ds = final_calls * ds_avg
        b_total = b_gemma + b_ds

        # Strategy C: Heuristic pre-filter (skip 40% of pages) + Gemma + minimal DeepSeek
        filtered_pages = int(pages * 0.6)
        c_gemma = (filtered_pages * 2 + entities + top_n) * gemma_avg
        c_ds = final_calls * ds_avg
        c_total = c_gemma + c_ds

        print(f"  {name}:")
        print(f"    Pages: {pages} | Entities: {entities} | Deep profiles: {top_n}")
        print(f"    Strategy A (DS profiles):     ${a_total:.3f}")
        print(f"    Strategy B (Gemma profiles):   ${b_total:.3f}")
        print(f"    Strategy C (heuristic+Gemma):  ${c_total:.3f}")
        print()


# ── MAIN ──────────────────────────────────────────────────────────────────

async def main():
    t0 = time.time()

    # Test 1: Heuristic (free)
    test_heuristic_classifier()

    # Test 2: Gemma classification
    await test_gemma_classification()

    # Test 3: Gemma extraction
    await test_gemma_extraction()

    # Test 4: Gemma vs DeepSeek synthesis
    await test_gemma_vs_deepseek_synthesis()

    # Test 5: Cost projection
    test_cost_projection()

    # Summary
    elapsed = time.time() - t0
    gemma_c = [c for c in calls if "gemma" in c["model"]]
    ds_c = [c for c in calls if "deepseek" in c["model"]]

    print("\n" + "=" * 70)
    print("COST OPTIMIZATION SUMMARY")
    print("=" * 70)
    print(f"Total Gemma calls:    {len(gemma_c)} (${sum(c['cost'] for c in gemma_c):.6f})")
    print(f"Total DeepSeek calls: {len(ds_c)} (${sum(c['cost'] for c in ds_c):.6f})")
    print(f"TOTAL TEST COST:      ${sum(c['cost'] for c in calls):.6f}")
    print(f"ELAPSED:              {elapsed:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
