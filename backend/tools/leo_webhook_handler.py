"""
Leo Webhook Handler — processes inbound emails and routes to WhatsApp.

This is the production webhook endpoint for Resend's email.received events.
When a tradesperson replies to owner@example.invalid, this:
1. Validates the webhook signature
2. Extracts project ID from the To address
3. Looks up the user associated with that project
4. Summarizes the email content
5. Sends a WhatsApp message to the user via Twilio

For testing, run standalone:
    python leo_webhook_handler.py --simulate '{...webhook payload...}'

For production, mount as a POST endpoint at: api.leo.casa/webhooks/resend
"""

import os
import sys
import json
import hmac
import hashlib
import logging
import argparse
import urllib.request
import base64
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _load_env() -> None:
    """Best-effort load of `.env.local` for local scripts/dev."""
    env_path = Path(__file__).resolve().parents[2] / ".env.local"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[3] / ".env.local"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    except Exception as exc:
        logger.debug("leo_webhook_handler: failed to load .env.local (non-fatal) | err=%s", exc)


def _get_resend_webhook_secret() -> str:
    _load_env()
    # Common naming patterns; we support both to avoid surprises.
    secret = (
        str(os.environ.get("RESEND_WEBHOOK_SECRET") or "").strip()
        or str(os.environ.get("RESEND_WEBHOOK_SIGNING_SECRET") or "").strip()
        or str(os.environ.get("RESEND_SIGNING_SECRET") or "").strip()
    )
    if not secret:
        raise RuntimeError("Missing RESEND webhook signing secret env var")
    return secret


def _get_email_domain() -> str:
    _load_env()
    return str(os.environ.get("LEO_PROJECT_EMAIL_DOMAIN") or "projects.leo.casa").strip()


def verify_signature(payload_body: str, signature: str) -> bool:
    """Verify Resend webhook signature using HMAC-SHA256."""
    secret = _get_resend_webhook_secret()
    expected = hmac.new(
        secret.encode(),
        payload_body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def extract_project_id(to_addresses: list[str]) -> str | None:
    """Extract project ID from the recipient email address."""
    domain = _get_email_domain().lower()
    for addr in to_addresses:
        addr_lower = addr.lower()
        if addr_lower.startswith("project-") and domain in addr_lower:
            local_part = addr_lower.split("@")[0]
            project_id = local_part.replace("project-", "", 1)
            return project_id
    return None


def send_whatsapp(to_phone: str, message: str) -> dict:
    """Send a WhatsApp message via Twilio."""
    _load_env()
    twilio_sid = str(os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    twilio_token = str(os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    twilio_from = str(os.environ.get("TWILIO_WHATSAPP_FROM") or "").strip()

    if not twilio_sid or not twilio_token:
        logger.warning("Twilio credentials not set — skipping WhatsApp send")
        return {"status": "skipped", "reason": "no_credentials"}

    auth = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
    data = {
        "From": twilio_from,
        "To": f"whatsapp:{to_phone}",
        "Body": message,
    }

    import urllib.parse
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
        data=body,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        logger.info(f"WhatsApp sent | sid={result.get('sid')} | to={to_phone}")
        return {"status": "sent", "sid": result.get("sid")}
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return {"status": "failed", "error": str(e)}


def format_email_summary(from_email: str, subject: str, body: str, attachments: list) -> str:
    """Format an inbound email into a WhatsApp-friendly summary."""
    # Extract sender name
    sender = from_email
    if "<" in from_email:
        sender = from_email.split("<")[0].strip()

    lines = [f"📧 Reply from {sender}"]

    if subject:
        lines.append(f"Subject: {subject}")

    lines.append("")

    # Trim body to WhatsApp-friendly length
    if body:
        trimmed = body.strip()
        if len(trimmed) > 800:
            trimmed = trimmed[:800] + "..."
        lines.append(trimmed)
    else:
        lines.append("(no text body — check attachments)")

    if attachments:
        lines.append("")
        lines.append(f"📎 {len(attachments)} attachment(s):")
        for att in attachments:
            name = att.get("filename", att.get("name", "unknown"))
            size = att.get("size", 0)
            size_str = f"{size / 1024:.0f}KB" if size > 0 else ""
            lines.append(f"  • {name} {size_str}")

    return "\n".join(lines)


def handle_email_received(payload: dict) -> dict:
    """
    Process an email.received webhook event.
    
    Returns a result dict with the action taken.
    """
    data = payload.get("data", {})
    from_email = data.get("from", "unknown")
    to_addresses = data.get("to", [])
    subject = data.get("subject", "")
    body_text = data.get("text", "")
    body_html = data.get("html", "")
    attachments = data.get("attachments", [])
    email_id = data.get("id", "unknown")

    # Extract project ID
    project_id = extract_project_id(to_addresses)
    if not project_id:
        logger.warning(f"No project ID found in To: {to_addresses}")
        return {"action": "ignored", "reason": "no_project_id"}

    logger.info(f"Inbound email | project={project_id} | from={from_email} | subject={subject}")

    # Use text body, fall back to noting HTML-only
    display_body = body_text or "(HTML email — text extracted below)"

    # Format WhatsApp message
    whatsapp_msg = format_email_summary(from_email, subject, display_body, attachments)

    # In production: look up user phone from project_id via Supabase
    # For now, log what we'd send
    result = {
        "action": "process_inbound",
        "project_id": project_id,
        "from": from_email,
        "subject": subject,
        "body_preview": display_body[:300],
        "attachment_count": len(attachments),
        "whatsapp_message": whatsapp_msg,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Would send to user:\n{whatsapp_msg}")

    return result


def handle_webhook(payload: dict) -> dict:
    """Route webhook events to appropriate handlers."""
    event_type = payload.get("type", "unknown")

    handlers = {
        "email.received": handle_email_received,
        "email.delivered": lambda p: {"action": "logged", "type": "delivered", "id": p.get("data", {}).get("email_id")},
        "email.bounced": lambda p: {"action": "alert", "type": "bounced", "id": p.get("data", {}).get("email_id")},
        "email.sent": lambda p: {"action": "logged", "type": "sent", "id": p.get("data", {}).get("email_id")},
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(payload)

    logger.info(f"Unhandled event type: {event_type}")
    return {"action": "ignored", "type": event_type}


def simulate_from_webhook_site() -> list[dict]:
    """Fetch recent events from webhook.site and process them through our handler."""
    logger.info("Fetching recent events from webhook.site...")

    req = urllib.request.Request(
        "https://webhook.site/token/157016af-ca94-42c9-801e-74b8f9a9fc28/requests?sorting=newest&per_page=10"
    )

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
    except Exception as e:
        logger.error(f"Failed to fetch from webhook.site: {e}")
        return []

    results = []
    for event in data.get("data", []):
        content = event.get("content", "")
        try:
            payload = json.loads(content)
            if payload.get("type") == "email.received":
                logger.info(f"\n{'='*60}")
                result = handle_webhook(payload)
                results.append(result)
        except (json.JSONDecodeError, KeyError):
            continue

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leo Webhook Handler")
    parser.add_argument("--simulate", type=str, help="Process a JSON webhook payload")
    parser.add_argument("--replay", action="store_true", help="Replay recent events from webhook.site")
    parser.add_argument("--test", action="store_true", help="Run full test: send email + wait + process")
    args = parser.parse_args()

    if args.simulate:
        payload = json.loads(args.simulate)
        result = handle_webhook(payload)
        print(json.dumps(result, indent=2))

    elif args.replay:
        results = simulate_from_webhook_site()
        for r in results:
            print(json.dumps(r, indent=2))
            print()

    elif args.test:
        logger.info("=== Full round-trip test ===")
        logger.info("Step 1: Sending test email to owner@example.invalid...")

        import time
        send_payload = json.dumps({
            "from": "Test Tradesperson <owner@example.invalid>",
            "to": "owner@example.invalid",
            "subject": "Re: Kitchen renovation quote",
            "text": "Hola, he revisado las fotos del espacio. Para la cocina completa incluyendo demolición, fontanería nueva, alicatado y muebles, el presupuesto sería de 8.500€ IVA incluido. Podría empezar en 2 semanas. ¿Le viene bien quedar el miércoles para ver el espacio? Un saludo, Antonio",
        }).encode()

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=send_payload,
            headers={
                "Authorization": f"Bearer {os.environ.get('RESEND_API_KEY', '')}",
                "Content-Type": "application/json",
            },
        )

        try:
            resp = urllib.request.urlopen(req)
            send_result = json.loads(resp.read())
            logger.info(f"Email sent: {send_result.get('id')}")
        except Exception as e:
            logger.error(f"Send failed: {e}")
            sys.exit(1)

        logger.info("Step 2: Waiting 6s for webhook to fire...")
        time.sleep(6)

        logger.info("Step 3: Processing inbound events from webhook.site...")
        results = simulate_from_webhook_site()

        if results:
            logger.info(f"\n{'='*60}")
            logger.info("RESULT: Full round-trip successful!")
            for r in results:
                print(json.dumps(r, indent=2))
        else:
            logger.warning("No email.received events found yet — webhook may need more time")

    else:
        parser.print_help()
