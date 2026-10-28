"""
Model Shootout: Which Bedrock model is cheapest AND good enough?
================================================================

Pricing per 1M tokens (us-east-1):
  Gemma 3 4B:           $0.04 in / $0.08 out  ← current baseline
  Gemma 3 12B:          $0.09 in / $0.29 out
  Amazon Nova Micro:    $0.035 in / $0.14 out  (cheap in, expensive out)
  Amazon Nova Lite:     $0.06 in / $0.24 out
  Mistral Ministral 3B: $0.10 in / $0.10 out
  Mistral Ministral 8B: $0.15 in / $0.15 out
  NVIDIA Nemotron Nano 9B: $0.06 in / $0.23 out
  GLM 4.7 Flash:        $0.07 in / $0.40 out
  Llama 3 8B:           $0.30 in / $0.60 out   (too expensive)

Test: Same 3 tasks on each model, compare cost AND quality.
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

MODELS = {
    "gemma-4b":       ("google.gemma-3-4b-it",             0.04,  0.08),
    "gemma-12b":      ("google.gemma-3-12b-it",            0.09,  0.29),
    "nova-micro":     ("amazon.nova-micro-v1:0",           0.035, 0.14),
    "nova-lite":      ("amazon.nova-lite-v1:0",            0.06,  0.24),
    "ministral-3b":   ("mistral.ministral-3-3b-instruct",  0.10,  0.10),
    "ministral-8b":   ("mistral.ministral-3-8b-instruct",  0.15,  0.15),
    "nemotron-9b":    ("nvidia.nemotron-nano-9b-v2",       0.06,  0.23),
    "glm-flash":      ("zai.glm-4.7-flash",               0.07,  0.40),
}

results = []


def call_model(alias, prompt, max_tokens=200):
    model_id, price_in, price_out = MODELS[alias]
    t0 = time.time()
    try:
        r = bedrock.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
        )
        ms = int((time.time() - t0) * 1000)
        txt = r["output"]["message"]["content"][0]["text"]
        u = r["usage"]
        cost = (u["inputTokens"] / 1e6) * price_in + (u["outputTokens"] / 1e6) * price_out
        results.append({
            "model": alias, "cost": cost,
            "in": u["inputTokens"], "out": u["outputTokens"], "ms": ms
        })
        return txt, cost, ms
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return f"ERROR: {e}", 0, ms


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
            return re.sub(r"\s+", " ", text).strip()[:6000]
    except:
        return None


async def main():
    t0 = time.time()

    # Scrape test pages
    print("Scraping test pages...")
    service_page = await scrape("https://vik-sofia.eu/montaj-dush-kabina-cena/")
    if not service_page:
        service_page = await scrape("https://mastersofia.bg/remont-na-banya-ceni/")
    print(f"  Got {len(service_page or '')} chars")

    if not service_page:
        print("FAILED to scrape any test page!")
        return

    # ── TASK 1: Classification (short output) ─────────────────────────────
    print("\n" + "=" * 70)
    print("TASK 1: Page Classification (expect: service_website)")
    print("=" * 70)

    classify_prompt = (
        f"Classify this webpage. ONE WORD answer.\n"
        f"Options: service_website, directory, forum, product_shop, irrelevant\n"
        f"URL: https://vik-sofia.eu/montaj-dush-kabina-cena/\n"
        f"Content: {service_page[:1500]}\n\nClassification:"
    )

    for alias in MODELS:
        txt, cost, ms = call_model(alias, classify_prompt, max_tokens=20)
        answer = txt.strip().split()[0].lower() if txt and not txt.startswith("ERROR") else txt
        correct = "service_website" in (answer or "")
        print(f"  {alias:15} | {'OK' if correct else 'MISS':4} | {answer:20} | ${cost:.7f} | {ms:5}ms")

    # ── TASK 2: Structured extraction (medium output) ──────────────────────
    print("\n" + "=" * 70)
    print("TASK 2: Structured Entity Extraction")
    print("=" * 70)

    extract_prompt = (
        f"Extract business info from this plumber page.\n"
        f"URL: https://vik-sofia.eu/montaj-dush-kabina-cena/\n"
        f"Content: {service_page[:2500]}\n\n"
        f'JSON: {{"business_name":"...","phone":"...or not_found",'
        f'"services":["list"],"prices":{{"service":"price BGN"}},'
        f'"serves_area":"..."}}'
    )

    for alias in MODELS:
        txt, cost, ms = call_model(alias, extract_prompt, max_tokens=350)
        has_json = "{" in (txt or "")
        preview = (txt or "")[:100].replace("\n", " ")
        print(f"  {alias:15} | {'JSON' if has_json else 'NO  ':4} | ${cost:.7f} | {ms:5}ms | {preview}")

    # ── TASK 3: Mini synthesis (longer output) ─────────────────────────────
    print("\n" + "=" * 70)
    print("TASK 3: Mini Profile Synthesis")
    print("=" * 70)

    synth_prompt = (
        f"Write a 5-line profile of this plumber business. "
        f"Include: name, services, price range, area served, overall impression.\n\n"
        f"Content: {service_page[:2000]}\n\nProfile:"
    )

    for alias in MODELS:
        txt, cost, ms = call_model(alias, synth_prompt, max_tokens=300)
        preview = (txt or "")[:120].replace("\n", " ")
        print(f"  {alias:15} | ${cost:.7f} | {ms:5}ms | {preview}")

    # ── SUMMARY ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("COST SUMMARY (per call, averaged across 3 tasks)")
    print("=" * 70)

    model_costs = {}
    model_times = {}
    for r in results:
        m = r["model"]
        if m not in model_costs:
            model_costs[m] = []
            model_times[m] = []
        model_costs[m].append(r["cost"])
        model_times[m].append(r["ms"])

    print(f"\n  {'Model':15} | {'Avg Cost':>12} | {'Avg Latency':>12} | {'Cost at 5000 calls':>18}")
    print(f"  {'-'*15}-+-{'-'*12}-+-{'-'*12}-+-{'-'*18}")
    for alias in sorted(model_costs, key=lambda x: sum(model_costs[x])/len(model_costs[x])):
        avg_cost = sum(model_costs[alias]) / len(model_costs[alias])
        avg_ms = sum(model_times[alias]) / len(model_times[alias])
        at_5k = avg_cost * 5000
        print(f"  {alias:15} | ${avg_cost:.7f} | {avg_ms:>8.0f}ms | ${at_5k:.3f}")

    total = sum(r["cost"] for r in results)
    elapsed = time.time() - t0
    print(f"\n  Total test cost: ${total:.6f}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
