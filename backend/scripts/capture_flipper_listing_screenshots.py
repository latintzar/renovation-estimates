#!/usr/bin/env python3
"""
Capture screenshots used by the flipper landing page.

Grand goal
----------
The flipper landing page uses hardcoded, real product screenshots for speed.
This script captures those screenshots deterministically using Playwright and
writes them into:

  lean-mvp/frontend/public/images/landing/flipper/

It is designed to be fail-loud and fully logged so we can debug selectors if
the app UI changes.

Usage:
  python3 backend/scripts/capture_flipper_listing_screenshots.py --listing-id 17
  python3 backend/scripts/capture_flipper_listing_screenshots.py --listing-id 17 --headed
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("capture_flipper_shots")


def _repo_root() -> Path:
    # backend/scripts -> backend -> lean-mvp
    return Path(__file__).resolve().parents[2]


def _frontend_public_dir() -> Path:
    return _repo_root() / "frontend" / "public"


def _output_dir() -> Path:
    return _frontend_public_dir() / "images" / "landing" / "flipper"


def _ensure_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed.\n"
            "Install with:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc
    return sync_playwright


def _wait_stable(page: Any, label: str) -> None:
    logger.info("Waiting for stability: %s", label)
    page.wait_for_load_state("domcontentloaded", timeout=30_000)
    # Network can be chatty; allow a small settle period.
    page.wait_for_timeout(600)


def _save_shot(page: Any, out_path: Path, *, full_page: bool = False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out_path), full_page=full_page)
    logger.info("Saved screenshot: %s", out_path)


def _click(page: Any, locator: Any, *, label: str) -> None:
    logger.info("Click: %s", label)
    locator.first.click(timeout=15_000)


def run(listing_id: int, headed: bool) -> int:
    sync_playwright = _ensure_playwright()
    out_dir = _output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = f"https://app.leo.casa/listing/{listing_id}"
    logger.info("Target listing: %s", base_url)
    logger.info("Output dir: %s", out_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            viewport={"width": 430, "height": 932},  # iPhone-ish for consistent crops
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        # Log browser issues that explain "stuck loading" states.
        def on_console(msg: Any) -> None:
            try:
                if msg.type in ("error", "warning"):
                    logger.warning("BROWSER CONSOLE %s: %s", msg.type, msg.text)
            except Exception:
                pass

        def on_page_error(err: Any) -> None:
            logger.error("BROWSER PAGEERROR: %s", err)

        def on_request_failed(req: Any) -> None:
            failure = req.failure
            logger.error("REQUEST FAILED: %s | %s", req.url, failure)

        def on_response(resp: Any) -> None:
            url = str(resp.url)
            if "/api/" not in url:
                return
            if "/api/renovation/" in url or "/api/listings/" in url:
                try:
                    logger.info("API RESP: %s %s", resp.status, url)
                except Exception:
                    pass

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        # ------------------------------------------------------------------
        # 1) Renovation tab (default tab) — capture a clean "product on screen"
        # ------------------------------------------------------------------
        logger.info("Step 1: Load listing page (renovation tab)")
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        _wait_stable(page, "listing initial load")

        # Wait for renovation data to load (avoid capturing the spinner state).
        spinner = page.locator("text=/Cargando datos de reforma/i")
        option_ready = page.locator("button").filter(
            has_text=re.compile(r"(Inversi|Valor\\s*\\+|Plazo)", re.I)
        )

        logger.info("Waiting for renovation options to render (or spinner to disappear)")
        try:
            option_ready.first.wait_for(state="visible", timeout=60_000)
        except Exception:
            # If the options never show up, capture debug and fail loud.
            debug_path = out_dir / "listing17-debug-full.png"
            _save_shot(page, debug_path, full_page=True)
            logger.error("Spinner visible? %s", spinner.count() > 0)
            raise RuntimeError(
                "Renovation options never rendered (still loading). "
                "Saved listing17-debug-full.png for inspection."
            )

        # Ensure the renovation header is visible (sticky). If not, scroll top.
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(250)

        _save_shot(page, out_dir / "listing17-renovation.png", full_page=False)

        # ------------------------------------------------------------------
        # 2) Share modal — click the header share button
        # ------------------------------------------------------------------
        logger.info("Step 2: Open Share modal")
        share_button = page.locator("button[aria-haspopup='dialog']").filter(has=page.locator("svg"))
        if share_button.count() == 0:
            raise RuntimeError("Could not find share button (aria-haspopup='dialog'). UI changed?")
        _click(page, share_button, label="share button (renovation header)")
        _wait_stable(page, "share modal open")

        # Modal container: capture the whole viewport (phone-style screenshot).
        _save_shot(page, out_dir / "listing17-share.png", full_page=False)

        # Close modal (ESC works due to modal handlers in app)
        logger.info("Close share modal")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # ------------------------------------------------------------------
        # 3) Negotiation modal — open a renovation option → analysis modal → negotiate
        # ------------------------------------------------------------------
        logger.info("Step 3: Open BracketAnalysisModal (tap a renovation option card)")
        # The renovation options load asynchronously. Try the most specific selector
        # from the UI component first, then fall back to text heuristics.
        selectors = [
            ("option_card_css", page.locator("button.w-full.text-left.rounded-2xl")),
            ("option_card_css_alt", page.locator("button").filter(has_text=re.compile(r"Valor\\s*\\+", re.I))),
            ("option_card_text", page.locator("button").filter(has_text=re.compile(r"(Inversi|Investment)", re.I))),
            ("option_card_text_alt", page.locator("button").filter(has_text=re.compile(r"(Plazo|Timeline)", re.I))),
        ]

        option_card = None
        for sel_name, loc in selectors:
            logger.info("Trying selector: %s | count=%s", sel_name, loc.count())
            try:
                loc.first.wait_for(state="attached", timeout=60_000)
                option_card = loc
                logger.info("Selector matched: %s", sel_name)
                break
            except Exception:
                continue

        if option_card is None or option_card.count() == 0:
            debug_path = out_dir / "listing17-debug-full.png"
            _save_shot(page, debug_path, full_page=True)
            logger.error("Debug: text 'Inversión' count=%s", page.get_by_text("Inversión").count())
            logger.error("Debug: text 'Valor +' count=%s", page.get_by_text("Valor +").count())
            raise RuntimeError(
                "Could not find renovation option cards after waiting. "
                "Saved debug screenshot listing17-debug-full.png."
            )
        _click(page, option_card, label="first renovation option card")
        _wait_stable(page, "analysis modal open")

        logger.info("Open negotiation modal from ELI5 CTA")
        negotiate = page.get_by_role("button", name=re.compile(r"(Negoci|negotia)", re.I))
        if negotiate.count() == 0:
            negotiate = page.locator("button").filter(has_text=re.compile(r"(Negoci|negotia)", re.I))
        try:
            negotiate.first.wait_for(state="visible", timeout=30_000)
        except Exception as exc:
            raise RuntimeError("Could not find negotiate button inside analysis modal.") from exc
        _click(page, negotiate, label="negotiate price button")
        _wait_stable(page, "negotiation modal open")

        _save_shot(page, out_dir / "listing17-negotiation.png", full_page=False)

        logger.info("Done")
        context.close()
        browser.close()
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture flipper landing screenshots from listing page")
    parser.add_argument("--listing-id", type=int, default=17)
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run(listing_id=int(args.listing_id), headed=bool(args.headed))
    except Exception as exc:
        logger.exception("Screenshot capture failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

