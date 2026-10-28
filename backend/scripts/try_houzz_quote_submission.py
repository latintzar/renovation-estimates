#!/usr/bin/env python3
"""
Headless probe for Houzz.es quote submission flow.

Grand goal
----------
Provide a deterministic, fully logged automation attempt for Houzz quote
submission so we can answer: "Can we automate this end-to-end?"

This script is intentionally fail-loud:
- raises on setup/runtime errors
- writes a structured JSON report
- captures screenshots for each step

Usage examples:
  python3 scripts/try_houzz_quote_submission.py --listing-id 13
  python3 scripts/try_houzz_quote_submission.py --listing-id 13 --headed
  python3 scripts/try_houzz_quote_submission.py --email "$HOUZZ_EMAIL" --password "$HOUZZ_PASSWORD"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("houzz_probe")


def _project_root() -> Path:
    # backend/scripts -> backend -> lean-mvp
    return Path(__file__).resolve().parents[2]


def _workspace_root() -> Path:
    # lean-mvp -> puedo_casa
    return _project_root().parent


def _load_env() -> None:
    env_path = _workspace_root() / ".env.local"
    if env_path.exists():
        pass  # Recipient runtime supplies its explicit private environment.
        logger.info("Loaded env file: %s", env_path)
    else:
        logger.warning(".env.local not found at %s", env_path)


@dataclass
class ProbeConfig:
    listing_id: int
    service_slug: str
    city: str
    postcode: str
    street: str
    country_domain: str
    target_url: str | None
    headed: bool
    email: str | None
    password: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    contact_message: str
    submit_live: bool
    timeout_ms: int
    output_dir: str


def parse_args() -> ProbeConfig:
    parser = argparse.ArgumentParser(description="Try Houzz quote flow headlessly")
    parser.add_argument("--listing-id", type=int, default=13)
    parser.add_argument(
        "--service-slug",
        default="reformas-de-banos",
        help="Houzz service slug used to build a direct service URL",
    )
    parser.add_argument("--city", default="Málaga")
    parser.add_argument("--postcode", default="29015")
    parser.add_argument("--street", default="Calle Granada")
    parser.add_argument("--country-domain", default="www.houzz.es")
    parser.add_argument(
        "--target-url",
        default=None,
        help="Optional direct Houzz page (e.g. pro profile) to probe contact flow",
    )
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--email", default=os.getenv("HOUZZ_EMAIL"))
    parser.add_argument("--password", default=os.getenv("HOUZZ_PASSWORD"))
    parser.add_argument("--contact-name", default=os.getenv("HOUZZ_CONTACT_NAME"))
    parser.add_argument("--contact-email", default=os.getenv("HOUZZ_CONTACT_EMAIL"))
    parser.add_argument("--contact-phone", default=os.getenv("HOUZZ_CONTACT_PHONE"))
    parser.add_argument(
        "--contact-message",
        default=(
            "Hola, nos interesa solicitar presupuesto para reforma. "
            "Gracias por contactarnos."
        ),
    )
    parser.add_argument(
        "--submit-live",
        action="store_true",
        help="If set, attempts to click final submit/send buttons.",
    )
    parser.add_argument("--timeout-ms", type=int, default=15_000)
    parser.add_argument(
        "--output-dir",
        default=str(_project_root() / "backend" / "reports" / "houzz_probe"),
    )

    args = parser.parse_args()
    return ProbeConfig(
        listing_id=args.listing_id,
        service_slug=args.service_slug,
        city=args.city,
        postcode=args.postcode,
        street=args.street,
        country_domain=args.country_domain,
        target_url=args.target_url,
        headed=args.headed,
        email=args.email,
        password=args.password,
        contact_name=args.contact_name,
        contact_email=args.contact_email,
        contact_phone=args.contact_phone,
        contact_message=args.contact_message,
        submit_live=args.submit_live,
        timeout_ms=args.timeout_ms,
        output_dir=args.output_dir,
    )


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


def _mk_run_dirs(base_output_dir: str) -> tuple[Path, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(base_output_dir) / f"run_{timestamp}"
    shots_dir = run_dir / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, shots_dir


def _safe_filename(label: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in label).strip("_")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_probe(config: ProbeConfig) -> int:
    sync_playwright = _ensure_playwright()
    run_dir, shots_dir = _mk_run_dirs(config.output_dir)
    report_path = run_dir / "report.json"
    report: dict[str, Any] = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "steps": [],
        "status": "running",
        "error": None,
        "artifacts": {
            "run_dir": str(run_dir),
            "screenshots_dir": str(shots_dir),
            "report_json": str(report_path),
        },
    }
    post_events: list[dict[str, Any]] = []

    def log_step(name: str, ok: bool, details: str = "") -> None:
        step = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "name": name,
            "ok": ok,
            "details": details,
        }
        report["steps"].append(step)
        if ok:
            logger.info("STEP OK: %s | %s", name, details)
        else:
            logger.error("STEP FAIL: %s | %s", name, details)
        _write_json(report_path, report)

    def save_shot(page: Any, label: str) -> str:
        file_name = f"{int(time.time())}_{_safe_filename(label)}.png"
        target = shots_dir / file_name
        page.screenshot(path=str(target), full_page=True)
        logger.info("Saved screenshot: %s", target)
        return str(target)

    def click_first_available(
        page: Any,
        candidates: list[tuple[str, str]],
        click_timeout_ms: int = 1200,
    ) -> tuple[bool, str]:
        """
        candidates: list of (kind, value)
        kind is one of: role_button, role_link, text, selector
        """
        for kind, value in candidates:
            try:
                if kind == "role_button":
                    page.get_by_role("button", name=value).first.click(timeout=click_timeout_ms)
                    return True, f"{kind}:{value}"
                if kind == "role_link":
                    page.get_by_role("link", name=value).first.click(timeout=click_timeout_ms)
                    return True, f"{kind}:{value}"
                if kind == "text":
                    page.get_by_text(value).first.click(timeout=click_timeout_ms)
                    return True, f"{kind}:{value}"
                if kind == "selector":
                    page.locator(value).first.click(timeout=click_timeout_ms)
                    return True, f"{kind}:{value}"
            except Exception:
                continue
        return False, "none"

    def get_visible_button_labels(page: Any, limit: int = 30) -> list[str]:
        labels: list[str] = []
        buttons = page.locator("button")
        count = min(buttons.count(), limit)
        for idx in range(count):
            try:
                label = buttons.nth(idx).inner_text().strip()
            except Exception:
                continue
            if label:
                labels.append(" ".join(label.split()))
        return labels

    def get_dialog_text(page: Any) -> str:
        for selector in ("div[role='dialog']", ".modal", "[data-modal]"):
            dialog = page.locator(selector)
            if dialog.count() > 0:
                try:
                    text = dialog.first.inner_text().strip()
                    if text:
                        return " ".join(text.split())
                except Exception:
                    continue
        return ""

    def click_consent_anywhere(page: Any) -> tuple[bool, str]:
        labels = [
            "Aceptar",
            "Aceptar todo",
            "Aceptar todas",
            "Consentir",
            "Estoy de acuerdo",
            "Accept",
            "Accept all",
        ]
        # Main page first
        for label in labels:
            try:
                page.get_by_role("button", name=label).first.click(timeout=1200)
                return True, f"main:{label}"
            except Exception:
                continue
        # Then all frames (CMP often lives in an iframe)
        for frame in page.frames:
            for label in labels:
                try:
                    frame.get_by_role("button", name=label).first.click(timeout=1200)
                    return True, f"frame:{label}"
                except Exception:
                    continue
        return False, "none"

    def fill_contact_form(page: Any) -> list[str]:
        fills: list[str] = []
        if config.contact_name:
            for selector in (
                "input[autocomplete='name']",
                "input[name*='name']",
                "input[placeholder*='Nombre']",
                "input[aria-label*='Nombre']",
            ):
                loc = page.locator(selector)
                if loc.count() > 0:
                    try:
                        loc.first.fill(config.contact_name)
                        fills.append(f"name:{selector}")
                        break
                    except Exception:
                        continue

        if config.contact_email:
            for selector in (
                "input[type='email']",
                "input[name*='email']",
                "input[placeholder*='Email']",
                "input[placeholder*='correo']",
            ):
                loc = page.locator(selector)
                if loc.count() > 0:
                    try:
                        loc.first.fill(config.contact_email)
                        fills.append(f"email:{selector}")
                        break
                    except Exception:
                        continue

        if config.contact_phone:
            for selector in (
                "input[type='tel']",
                "input[name*='phone']",
                "input[name*='telefono']",
                "input[name*='tel']",
                "input[placeholder*='Teléfono']",
                "input[placeholder*='telefono']",
            ):
                loc = page.locator(selector)
                if loc.count() > 0:
                    try:
                        loc.first.fill(config.contact_phone)
                        fills.append(f"phone:{selector}")
                        break
                    except Exception:
                        continue

        for selector in (
            "textarea[name*='message']",
            "textarea[placeholder*='mensaje']",
            "textarea[placeholder*='proyecto']",
            "textarea",
        ):
            loc = page.locator(selector)
            if loc.count() > 0:
                try:
                    loc.first.fill(config.contact_message)
                    fills.append(f"message:{selector}")
                    break
                except Exception:
                    continue
        return fills

    base = f"https://{config.country_domain}"
    hire_url = f"{base}/hire"
    service_url = (
        f"{base}/professionals/instalacion-y-reformas-de-cocinas-y-banos/"
        f"tipo-de-proyecto-{config.service_slug}-probr1-bo~t_17760~sv_32586"
    )
    login_url = f"{base}/houzz-login"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not config.headed)
        context = browser.new_context(
            locale="es-ES",
            viewport={"width": 1440, "height": 1200},
        )
        page = context.new_page()
        page.set_default_timeout(config.timeout_ms)

        def on_response(response: Any) -> None:
            try:
                request = response.request
                if request.method.upper() != "POST":
                    return
                event: dict[str, Any] = {
                    "url": request.url,
                    "status": response.status,
                    "ok": response.ok,
                }
                try:
                    body = response.text()
                    if body:
                        event["body_snippet"] = body[:300]
                except Exception:
                    event["body_snippet"] = ""
                post_events.append(event)
            except Exception:
                # Keep probe resilient; diagnostics must never crash run.
                return

        page.on("response", on_response)

        try:
            page.goto(hire_url, wait_until="domcontentloaded")
            log_step("open_hire", True, hire_url)
            save_shot(page, "01_hire")

            if "Empezar" in page.content():
                log_step("detect_start_cta", True, "Found 'Empezar' text on page")
            else:
                log_step("detect_start_cta", False, "No 'Empezar' text found on first render")

            # Try explicit start click if visible.
            start_clicked = False
            try:
                page.get_by_role("button", name="Empezar").first.click()
                start_clicked = True
            except Exception:
                try:
                    page.get_by_role("link", name="Empezar").first.click()
                    start_clicked = True
                except Exception:
                    start_clicked = False
            log_step("click_start", start_clicked, "Attempted to click 'Empezar'")
            save_shot(page, "02_after_start_click")

            # Try direct target page (if provided), otherwise use service page.
            probe_url = config.target_url or service_url
            page.goto(probe_url, wait_until="domcontentloaded")
            log_step("open_probe_page", True, probe_url)
            save_shot(page, "03_service_page")

            # Build location candidate from listing context.
            full_location = f"{config.street}, {config.city} {config.postcode}"
            log_step("prepare_location", True, full_location)

            # Try to type location in likely input fields (if page has one).
            location_filled = False
            is_direct_profile_probe = bool(config.target_url and "/profesionales/" in config.target_url)
            if is_direct_profile_probe:
                log_step("fill_location", True, "Skipped on direct profile probe")
            else:
                for selector in (
                    "input[placeholder*='Ubicación']",
                    "input[placeholder*='ubicación']",
                    "input[placeholder*='Location']",
                    "input[aria-label*='Ubicación']",
                    "input[type='search']",
                    "input[type='text']",
                ):
                    candidates = page.locator(selector)
                    if candidates.count() < 1:
                        continue
                    try:
                        candidates.first.fill(full_location)
                        location_filled = True
                        log_step("fill_location", True, f"Filled via selector: {selector}")
                        break
                    except Exception:
                        continue

            if (not location_filled) and (not is_direct_profile_probe):
                log_step("fill_location", False, "No location input on current probe page")
            save_shot(page, "04_after_location")

            # Cookie consent often blocks the page; try to resolve it.
            consent_ok, consent_selector = click_consent_anywhere(page)
            log_step("cookie_consent_click", consent_ok, consent_selector)
            save_shot(page, "05_after_cookie")

            # Some profile pages already render the contact form immediately.
            pre_send_fills = fill_contact_form(page)
            log_step(
                "fill_contact_fields_pre_send",
                len(pre_send_fills) > 0,
                ", ".join(pre_send_fills) if pre_send_fills else "No visible form before click",
            )

            # If no visible form yet, click "Enviar mensaje" to reveal it.
            send_clicked, send_selector = True, "skipped_click_send_message_form_already_visible"
            if not pre_send_fills:
                send_clicked, send_selector = click_first_available(
                    page,
                    [
                        ("role_button", "Enviar mensaje"),
                        ("role_link", "Enviar mensaje"),
                        ("text", "Enviar mensaje"),
                        ("selector", "button:has-text('Enviar mensaje')"),
                        ("selector", "a:has-text('Enviar mensaje')"),
                    ],
                )
            log_step("click_send_message", send_clicked, send_selector)
            save_shot(page, "06_after_send_message")

            # A second CMP gate may appear after interaction; attempt consent again.
            consent2_ok, consent2_selector = click_consent_anywhere(page)
            log_step("cookie_consent_click_after_send", consent2_ok, consent2_selector)
            dialog_text = get_dialog_text(page)
            if dialog_text:
                log_step("dialog_text_after_send", True, dialog_text)

            # Only handle interstitials if this is clearly not just CMP consent text.
            interstitial_advanced, interstitial_advance_selector = True, "skipped_non_interstitial"
            interstitial_closed, interstitial_selector = True, "skipped_non_interstitial"
            dialog_lower = dialog_text.lower() if dialog_text else ""
            should_handle_interstitial = (
                ("solicitar presupuesto" in dialog_lower)
                or ("contactar" in dialog_lower and "consent" not in dialog_lower)
            )
            if should_handle_interstitial:
                # First, try positive CTA options (continue flow) rather than closing.
                interstitial_advanced, interstitial_advance_selector = click_first_available(
                    page,
                    [
                        ("role_button", "Contactar"),
                        ("role_button", "Solicitar presupuesto"),
                        ("role_button", "Continuar"),
                        ("selector", "button:has-text('Contactar')"),
                        ("selector", "button:has-text('Solicitar presupuesto')"),
                        ("selector", "button:has-text('Continuar')"),
                    ],
                )
                interstitial_closed, interstitial_selector = click_first_available(
                    page,
                    [
                        ("role_button", "Ahora no"),
                        ("role_button", "No, gracias"),
                        ("role_button", "Omitir"),
                        ("role_button", "Cancelar"),
                        ("selector", "button:has-text('Ahora no')"),
                        ("selector", "button:has-text('No, gracias')"),
                    ],
                )
            log_step("advance_interstitial", interstitial_advanced, interstitial_advance_selector)
            log_step("dismiss_interstitial", interstitial_closed, interstitial_selector)

            # Fill contact form when available.
            form_fills = fill_contact_form(page)

            log_step(
                "fill_contact_fields",
                len(form_fills) > 0,
                ", ".join(form_fills) if form_fills else "No contact fields discovered",
            )
            save_shot(page, "07_after_contact_fill")

            if config.submit_live:
                post_count_before_submit = len(post_events)
                sent, sent_selector = click_first_available(
                    page,
                    [
                        ("role_button", "Enviar"),
                        ("role_button", "Enviar mensaje"),
                        ("role_button", "Enviar solicitud"),
                        ("role_button", "Contactar"),
                        ("role_button", "Solicitar presupuesto"),
                        ("role_button", "Continuar"),
                        ("role_button", "Siguiente"),
                        ("selector", "button[type='submit']"),
                        ("selector", "input[type='submit']"),
                        ("selector", "button:has-text('Enviar')"),
                        ("selector", "button:has-text('Contactar')"),
                        ("selector", "button:has-text('Solicitar presupuesto')"),
                    ],
                )
                log_step("submit_contact_form", sent, sent_selector)
                page.wait_for_timeout(4000)
                new_post_events = post_events[post_count_before_submit:]
                log_step(
                    "submit_network_posts",
                    len(new_post_events) > 0,
                    json.dumps(new_post_events[:10], ensure_ascii=False),
                )
                page_html_after_submit = page.content().lower()
                validation_markers = []
                for marker in (
                    "obligatorio",
                    "required",
                    "inválido",
                    "invalido",
                    "error",
                    "captcha",
                    "recaptcha",
                ):
                    if marker in page_html_after_submit:
                        validation_markers.append(marker)
                log_step(
                    "submit_validation_markers",
                    len(validation_markers) == 0,
                    ",".join(validation_markers) if validation_markers else "none",
                )
                if not sent:
                    labels = get_visible_button_labels(page)
                    log_step(
                        "debug_visible_buttons",
                        len(labels) > 0,
                        json.dumps(labels, ensure_ascii=False),
                    )
                    dialog_text = get_dialog_text(page)
                    log_step(
                        "debug_dialog_text",
                        bool(dialog_text),
                        dialog_text or "No dialog text found",
                    )
                save_shot(page, "08_after_submit_attempt")
            else:
                log_step("submit_contact_form", True, "Skipped (run without --submit-live)")

            # Attempt optional login if credentials are provided.
            if config.email and config.password:
                page.goto(login_url, wait_until="domcontentloaded")
                log_step("open_login", True, login_url)
                save_shot(page, "09_login_page")

                email_done = False
                for selector in ("input[type='email']", "input[name='email']"):
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        loc.first.fill(config.email)
                        email_done = True
                        break
                if not email_done:
                    raise RuntimeError("Login page loaded but email field was not found")

                password_done = False
                for selector in ("input[type='password']", "input[name='password']"):
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        loc.first.fill(config.password)
                        password_done = True
                        break
                if not password_done:
                    raise RuntimeError("Login page loaded but password field was not found")

                clicked_login = False
                for role_name in ("Inicia sesión", "Iniciar sesión", "Entrar", "Log in"):
                    try:
                        page.get_by_role("button", name=role_name).first.click()
                        clicked_login = True
                        break
                    except Exception:
                        continue

                if not clicked_login:
                    # Try generic submit
                    submit = page.locator("button[type='submit']")
                    if submit.count() > 0:
                        submit.first.click()
                        clicked_login = True

                log_step("submit_login", clicked_login, "Attempted login submit")
                save_shot(page, "10_after_login_submit")
            else:
                log_step(
                    "skip_login",
                    True,
                    "No HOUZZ_EMAIL/HOUZZ_PASSWORD provided, login not attempted",
                )

            # Final state snapshot
            final_url = page.url
            page_html = page.content()
            indicators = {
                "url": final_url,
                "contains_empezar": "Empezar" in page_html,
                "contains_enviar_mensaje": "Enviar mensaje" in page_html,
                "contains_captcha_hint": (
                    ("captcha" in page_html.lower()) or ("recaptcha" in page_html.lower())
                ),
                "contains_terms_account_creation_hint": (
                    "estarás creando una cuenta de Houzz" in page_html
                ),
            }
            log_step("collect_indicators", True, json.dumps(indicators, ensure_ascii=False))
            save_shot(page, "11_final")

            report["status"] = "completed"
            report["result"] = {
                "final_url": final_url,
                "indicators": indicators,
                "summary": (
                    "Probe completed. Check indicators + screenshots to determine if full "
                    "submission can be automated with current selectors/session."
                ),
            }
            _write_json(report_path, report)
            logger.info("Probe completed: %s", report_path)
            return 0
        except Exception as exc:
            logger.exception("Houzz probe failed")
            report["status"] = "failed"
            report["error"] = f"{type(exc).__name__}: {exc}"
            _write_json(report_path, report)
            return 1
        finally:
            context.close()
            browser.close()


def main() -> int:
    _load_env()
    config = parse_args()
    logger.info(
        "Starting Houzz headless probe | listing_id=%s | city=%s | postcode=%s | street=%s | headed=%s",
        config.listing_id,
        config.city,
        config.postcode,
        config.street,
        config.headed,
    )
    return run_probe(config)


if __name__ == "__main__":
    raise SystemExit(main())
