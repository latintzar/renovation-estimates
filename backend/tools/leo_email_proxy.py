"""
Leo Email Proxy — project-based email communication with tradespeople.

Architecture:
    OUTBOUND: Leo sends email via Resend from owner@example.invalid
    INBOUND:  Tradesperson replies → Resend catches it → webhook → this handler → WhatsApp summary

Each project gets a unique email address: project-{project_id}@updates.leo.casa
The tradesperson just sees a professional email and replies normally.

Usage:
    # Send outreach email to a tradesperson
    python leo_email_proxy.py --send \\
        --project-id tatami-001 \\
        --to "owner@example.invalid" \\
        --trade-name "José Pedrosa" \\
        --subject "Tatami installation inquiry — Málaga" \\
        --scope "Tatami mat installation for a 12m² bedroom in central Málaga"

    # Process an inbound email (webhook handler simulation)
    python leo_email_proxy.py --process-inbound '{"from":"owner@example.invalid","to":"owner@example.invalid","subject":"Re: Tatami","text":"Yes we can do it"}'

    # Test the full round-trip (send + check webhook)
    python leo_email_proxy.py --test
"""

import os
import sys
import json
import logging
import argparse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


def _load_env() -> None:
    """
    Best-effort load of `.env.local` for local scripts/dev.

    IMPORTANT: do NOT raise on missing env at import time, since this module is
    imported by the WhatsApp agent in production (env is injected there).
    """
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
        logger.debug("leo_email_proxy: failed to load .env.local (non-fatal) | err=%s", exc)


def _get_resend_api_key() -> str:
    _load_env()
    key = str(os.environ.get("RESEND_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("RESEND_API_KEY must be set")
    return key


def _get_email_domain() -> str:
    _load_env()
    # Default matches existing MX configuration for the project inbox.
    return str(os.environ.get("LEO_PROJECT_EMAIL_DOMAIN") or "projects.leo.casa").strip()


def project_email(project_id: str) -> str:
    """Generate the project-specific email address."""
    domain = _get_email_domain()
    return f"project-{project_id}@{domain}"


def send_outreach(
    project_id: str,
    to_email: str,
    trade_name: str,
    subject: str,
    scope_description: str,
    user_name: str = "a client",
    reply_deadline_days: int = 3,
) -> dict:
    """
    Send a professional outreach email to a tradesperson on behalf of a Leo user.
    
    The email comes from project-{id}@updates.leo.casa so replies
    go back to the same address → caught by Resend inbound webhook.
    """
    resend_key = _get_resend_api_key()
    from_email = project_email(project_id)

    body_text = f"""Hi {trade_name},

I'm reaching out on behalf of {user_name} who is looking for help with a home improvement project in their area.

Project scope:
{scope_description}

Are you available in the next couple of weeks? If so, could you provide a rough estimate or let us know what information you'd need to quote accurately?

We'd appreciate a reply within {reply_deadline_days} days if possible.

Best regards,
Leo Projects
{from_email}

---
This email was sent via Leo (leo.casa), a home improvement concierge service.
To stop receiving emails from this project, reply with "unsubscribe"."""

    body_html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
    <p>Hi {trade_name},</p>
    
    <p>I'm reaching out on behalf of {user_name} who is looking for help with a home improvement project in their area.</p>
    
    <div style="background: #f7f7f7; border-left: 4px solid #2563eb; padding: 16px; margin: 16px 0; border-radius: 4px;">
        <strong style="color: #2563eb;">Project scope:</strong><br>
        {scope_description}
    </div>
    
    <p>Are you available in the next couple of weeks? If so, could you provide a rough estimate or let us know what information you'd need to quote accurately?</p>
    
    <p>We'd appreciate a reply within {reply_deadline_days} days if possible.</p>
    
    <p>Best regards,<br>
    <strong>Leo Projects</strong><br>
    <span style="color: #666;">{from_email}</span></p>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
    <p style="font-size: 12px; color: #999;">
        This email was sent via <a href="https://leo.casa" style="color: #2563eb;">Leo</a>, a home improvement concierge service.<br>
        To stop receiving emails from this project, reply with "unsubscribe".
    </p>
</div>"""

    payload_dict = {
        "from": f"Leo Projects <{from_email}>",
        "to": to_email,
        "subject": subject,
        "text": body_text,
        "html": body_html,
        "reply_to": from_email,
        "headers": {
            "X-Leo-Project-ID": project_id,
        },
    }

    logger.info(f"Sending outreach | project={project_id} | to={to_email} | subject={subject}")

    try:
        # NOTE: Using httpx instead of urllib because Resend's edge/WAF can block
        # python-urllib user agents (observed as HTTP 403 "error code: 1010").
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                "https://api.resend.com/emails",
                json=payload_dict,
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "leo-casa-backend/1.0",
                },
            )
        if resp.status_code >= 400:
            logger.error("Send failed | status=%s | body=%s", resp.status_code, (resp.text or "")[:500])
            return {"success": False, "error": resp.text, "status_code": resp.status_code}

        result = resp.json() if (resp.text or "").strip().startswith("{") else {}
        email_id = result.get("id", "UNKNOWN")
        logger.info(f"Email sent | id={email_id} | from={from_email} | to={to_email}")
        return {
            "success": True,
            "email_id": email_id,
            "from": from_email,
            "to": to_email,
            "project_id": project_id,
        }
    except Exception as exc:
        logger.error("Send failed (unexpected) | err=%s", exc, exc_info=True)
        return {"success": False, "error": str(exc), "status_code": None}


def process_inbound_email(webhook_payload: dict) -> dict:
    """
    Process an inbound email received via Resend webhook.
    
    This is what runs when a tradesperson replies to a project email.
    In production, this would:
    1. Parse the project ID from the To address
    2. Store the email in Supabase
    3. Send a WhatsApp summary to the user
    4. If attachments (quotes, drawings), save to Supabase Storage
    
    For now, we just parse and log.
    """
    event_type = webhook_payload.get("type", "unknown")

    if event_type == "email.received":
        data = webhook_payload.get("data", {})
        from_email = data.get("from", "unknown")
        to_addresses = data.get("to", [])
        subject = data.get("subject", "")
        text = data.get("text", "")
        attachments = data.get("attachments", [])

        # Extract project ID from the To address
        project_id = None
        for addr in to_addresses:
            domain = _get_email_domain()
            if addr.startswith("project-") and f"@{domain}" in addr:
                project_id = addr.split("@")[0].replace("project-", "")
                break

        logger.info(f"Inbound email | project={project_id} | from={from_email} | subject={subject}")
        logger.info(f"  Body preview: {text[:200]}...")
        logger.info(f"  Attachments: {len(attachments)}")

        # In production: save to Supabase, notify user on WhatsApp
        result = {
            "event": "email_received",
            "project_id": project_id,
            "from": from_email,
            "subject": subject,
            "body_preview": text[:500] if text else "",
            "attachment_count": len(attachments),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "WOULD_NOTIFY_USER_ON_WHATSAPP",
        }

        if attachments:
            result["attachments"] = [
                {
                    "filename": a.get("filename", "unknown"),
                    "content_type": a.get("content_type", "unknown"),
                    "size": a.get("size", 0),
                }
                for a in attachments
            ]

        return result

    logger.info(f"Non-inbound event: {event_type}")
    return {"event": event_type, "action": "ignored"}


def send_test_email() -> dict:
    """Send a test outreach email to Resend's test inbox."""
    return send_outreach(
        project_id="test-tatami-001",
        to_email="owner@example.invalid",
        trade_name="Test Tradesperson",
        subject="Test: Tatami installation inquiry — Málaga",
        scope_description=(
            "Tatami mat installation for a 12m² bedroom in central Málaga.\n"
            "- Full room coverage with traditional Japanese tatami mats\n"
            "- Need to assess subfloor condition first\n"
            "- Client prefers igusa grass tatami, standard thickness"
        ),
        user_name="a client in Málaga",
    )


def check_sent_emails(limit: int = 5) -> list:
    """Check recently sent emails via Resend API."""
    try:
        resend_key = _get_resend_api_key()
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                "https://api.resend.com/emails",
                params={"limit": str(int(limit))},
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Accept": "application/json",
                    "User-Agent": "leo-casa-backend/1.0",
                },
            )
        if resp.status_code >= 400:
            logger.error("Failed to check emails | status=%s | body=%s", resp.status_code, (resp.text or "")[:300])
            return []
        data = resp.json() if (resp.text or "").strip().startswith("{") else {}
        return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"Failed to check emails: {e}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leo Email Proxy")
    parser.add_argument("--test", action="store_true", help="Send a test email")
    parser.add_argument("--send", action="store_true", help="Send outreach email")
    parser.add_argument("--project-id", type=str, default="test-001")
    parser.add_argument("--to", type=str, help="Recipient email")
    parser.add_argument("--trade-name", type=str, default="Tradesperson")
    parser.add_argument("--subject", type=str, default="Project inquiry")
    parser.add_argument("--scope", type=str, default="Home improvement project")
    parser.add_argument("--process-inbound", type=str, help="Process webhook JSON payload")
    parser.add_argument("--recent", action="store_true", help="Show recent sent emails")
    args = parser.parse_args()

    if args.test:
        result = send_test_email()
        print(json.dumps(result, indent=2))

    elif args.send and args.to:
        result = send_outreach(
            project_id=args.project_id,
            to_email=args.to,
            trade_name=args.trade_name,
            subject=args.subject,
            scope_description=args.scope,
        )
        print(json.dumps(result, indent=2))

    elif args.process_inbound:
        payload = json.loads(args.process_inbound)
        result = process_inbound_email(payload)
        print(json.dumps(result, indent=2))

    elif args.recent:
        emails = check_sent_emails()
        for e in emails:
            print(f"  {e.get('id', '?')[:8]}... | {e.get('from', '?')} → {e.get('to', '?')} | {e.get('subject', '?')}")

    else:
        parser.print_help()
