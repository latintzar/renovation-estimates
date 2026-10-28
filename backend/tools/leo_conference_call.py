"""
Leo Conference Call — Uber-style "connect me" for tradespeople.

Flow:
1. User says on WhatsApp: "connect me with José the tiler"
2. Leo creates a conference room named "project-{id}-call-{n}"
3. Leo calls the USER's phone → on answer, joins conference (hears hold music)
4. Leo calls the TRADESPERSON → on answer, joins conference
5. Both hear each other. Call is recorded.
6. After call ends, Leo transcribes + summarizes on WhatsApp.

Usage:
    python leo_conference_call.py --test          # dry-run, shows what would happen
    python leo_conference_call.py --call-self     # calls YOUR number into a conference (real test)
    python leo_conference_call.py \\
        --user-phone +12025550101 \\
        --trade-phone +12025550103 \\
        --project-id proj-abc123
"""

import os
import sys
import json
import logging
import argparse
import urllib.request
import urllib.parse
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_env() -> None:
    """
    Best-effort load of `.env.local` for local scripts/dev.

    IMPORTANT: do NOT raise on missing env at import time, since this module can
    be imported by the WhatsApp agent in production.
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
        logger.debug("leo_conference_call: failed to load .env.local (non-fatal) | err=%s", exc)


def _get_twilio_config() -> tuple[str, str, str, str]:
    _load_env()
    account_sid = str(os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    auth_token = str(os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    from_number = str(os.environ.get("TWILIO_WHATSAPP_FROM") or "").strip().replace("whatsapp:", "")
    public_base_url = str(os.environ.get("PUBLIC_BASE_URL") or (os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/") + '')).strip()

    if not account_sid or not auth_token:
        raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
    if not from_number:
        raise RuntimeError("TWILIO_WHATSAPP_FROM must be set (used as caller ID for voice calls)")
    return account_sid, auth_token, from_number, public_base_url


def _twilio_request(path: str, data: dict | None = None, method: str = "GET") -> dict:
    """Make an authenticated Twilio API request."""
    account_sid, auth_token, _from, _pub = _get_twilio_config()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}{path}"
    auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def _twiml_conference(
    conference_name: str,
    record: bool = True,
    recording_callback_url: str = "",
) -> str:
    """
    Generate inline TwiML for joining a conference.

    WHY recording_callback_url MATTERS:
    When the recording finishes, Twilio POSTs to this URL so we can download,
    transcribe (Whisper + AWS), and build a call_memory for the Gordon debrief.
    The URL includes project_id + conference_name as query params so the webhook
    handler knows which leo_project_comms row to update.
    """
    record_attrs = ""
    if record:
        record_attrs = 'record="record-from-start"'
        if recording_callback_url:
            record_attrs += (
                f'\n            recordingStatusCallback="{recording_callback_url}"'
                '\n            recordingStatusCallbackEvent="completed"'
                '\n            recordingStatusCallbackMethod="POST"'
            )

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-GB">
        Connecting you now. Please hold.
    </Say>
    <Dial>
        <Conference
            startConferenceOnEnter="true"
            endConferenceOnExit="true"
            {record_attrs}
            beep="true"
            waitUrl="http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical">
            {conference_name}
        </Conference>
    </Dial>
</Response>"""
    return twiml


def create_conference_call(
    user_phone: str,
    trade_phone: str,
    project_id: str,
    call_number: int = 1,
    record: bool = True,
    dry_run: bool = False,
) -> dict:
    """
    Create an Uber-style conference call between user and tradesperson.
    
    Returns dict with call SIDs and conference name.
    """
    conference_name = f"{project_id}-call-{call_number}"
    _account_sid, _auth_token, from_number, public_base_url = _get_twilio_config()

    # Build recording callback URL so Twilio tells us when the recording is ready.
    # We embed project_id and conference_name as query params for easy lookup.
    recording_callback_url = ""
    if record:
        recording_callback_url = (
            f"{public_base_url}/api/webhooks/twilio/recording-complete"
            f"?project_id={urllib.parse.quote(project_id, safe='')}"
            f"&conf={urllib.parse.quote(conference_name, safe='')}"
        )
    twiml = _twiml_conference(conference_name, record=record, recording_callback_url=recording_callback_url)

    logger.info(f"Conference: {conference_name}")
    logger.info(f"User phone: {user_phone}")
    logger.info(f"Trade phone: {trade_phone}")
    logger.info(f"From number: {from_number}")
    logger.info(f"Record: {record}")

    if dry_run:
        logger.info("DRY RUN — no calls made")
        return {
            "conference_name": conference_name,
            "user_call_sid": "DRY_RUN",
            "trade_call_sid": "DRY_RUN",
            "from_number": from_number,
            "record": record,
            "twiml_preview": twiml,
        }

    # Call 1: Dial the user into the conference
    logger.info(f"Calling user at {user_phone}...")
    user_call = _twilio_request("/Calls.json", {
        "To": user_phone,
        "From": from_number,
        "Twiml": twiml,
        "StatusCallback": f"{public_base_url}/webhooks/twilio/call-status",
        "StatusCallbackEvent": "initiated ringing answered completed",
        "StatusCallbackMethod": "POST",
    })
    user_sid = user_call.get("sid", "UNKNOWN")
    logger.info(f"User call SID: {user_sid} | Status: {user_call.get('status')}")

    # Call 2: Dial the tradesperson into the same conference
    logger.info(f"Calling tradesperson at {trade_phone}...")
    trade_call = _twilio_request("/Calls.json", {
        "To": trade_phone,
        "From": from_number,
        "Twiml": twiml,
        "StatusCallback": f"{public_base_url}/webhooks/twilio/call-status",
        "StatusCallbackEvent": "initiated ringing answered completed",
        "StatusCallbackMethod": "POST",
    })
    trade_sid = trade_call.get("sid", "UNKNOWN")
    logger.info(f"Trade call SID: {trade_sid} | Status: {trade_call.get('status')}")

    result = {
        "conference_name": conference_name,
        "user_call_sid": user_sid,
        "trade_call_sid": trade_sid,
        "from_number": from_number,
        "record": record,
    }

    logger.info(f"Conference created: {json.dumps(result, indent=2)}")
    return result


def test_call_self(phone: str) -> dict:
    """Test by calling a single number into a conference (you'll hear hold music)."""
    conference_name = "leo-test-conference"
    twiml = _twiml_conference(conference_name, record=False)
    _account_sid, _auth_token, from_number, _public_base_url = _get_twilio_config()

    logger.info(f"TEST: Calling {phone} into conference '{conference_name}'...")

    call = _twilio_request("/Calls.json", {
        "To": phone,
        "From": from_number,
        "Twiml": twiml,
    })

    sid = call.get("sid", "UNKNOWN")
    status = call.get("status", "UNKNOWN")
    logger.info(f"Call SID: {sid} | Status: {status}")

    return {"call_sid": sid, "status": status, "conference": conference_name}


def get_account_balance() -> dict:
    """Check Twilio account balance."""
    return _twilio_request("/Balance.json")


def get_voice_pricing(country_code: str) -> list:
    """Get voice pricing for a country (ISO 2-letter)."""
    account_sid, auth_token, _from_number, _public_base_url = _get_twilio_config()
    auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    req = urllib.request.Request(
        f"https://pricing.twilio.com/v2/Voice/Countries/{country_code}",
        headers={"Authorization": f"Basic {auth}"},
    )
    data = json.loads(urllib.request.urlopen(req).read())
    return data.get("outbound_prefix_prices", [])


def estimate_call_cost(
    user_country: str,
    trade_country: str,
    duration_minutes: int = 10,
) -> dict:
    """
    Estimate the cost of a conference call.
    
    Conference = 2 outbound legs billed separately.
    """
    user_prices = get_voice_pricing(user_country)
    trade_prices = get_voice_pricing(trade_country)

    # Find mobile pricing (most common case)
    def find_mobile_price(prices: list) -> float:
        for p in prices:
            name = p.get("friendly_name", "").lower()
            if "mobile" in name and "special" not in name and "surcharge" not in name and "other" not in name:
                return float(p["current_price"])
        # Fallback to first non-special price
        for p in prices:
            name = p.get("friendly_name", "").lower()
            if "special" not in name and "surcharge" not in name:
                return float(p["current_price"])
        return 0.0

    user_rate = find_mobile_price(user_prices)
    trade_rate = find_mobile_price(trade_prices)

    user_cost = user_rate * duration_minutes
    trade_cost = trade_rate * duration_minutes
    total = user_cost + trade_cost

    return {
        "user_leg": {
            "country": user_country,
            "rate_per_min": f"${user_rate:.4f}",
            "duration_min": duration_minutes,
            "cost": f"${user_cost:.2f}",
        },
        "trade_leg": {
            "country": trade_country,
            "rate_per_min": f"${trade_rate:.4f}",
            "duration_min": duration_minutes,
            "cost": f"${trade_cost:.2f}",
        },
        "total_cost": f"${total:.2f}",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leo Conference Calls")
    parser.add_argument("--test", action="store_true", help="Dry run showing what would happen")
    parser.add_argument("--call-self", type=str, help="Call this number into a test conference")
    parser.add_argument("--user-phone", type=str, help="User's phone number")
    parser.add_argument("--trade-phone", type=str, help="Tradesperson's phone number")
    parser.add_argument("--project-id", type=str, default="test-proj-001")
    parser.add_argument("--estimate", nargs=2, metavar=("USER_COUNTRY", "TRADE_COUNTRY"),
                        help="Estimate call cost for two countries (e.g. GB ES)")
    parser.add_argument("--balance", action="store_true", help="Show account balance")
    args = parser.parse_args()

    if args.balance:
        bal = get_account_balance()
        print(f"Balance: {bal.get('currency')} {bal.get('balance')}")

    elif args.estimate:
        est = estimate_call_cost(args.estimate[0], args.estimate[1])
        print(json.dumps(est, indent=2))

    elif args.call_self:
        result = test_call_self(args.call_self)
        print(json.dumps(result, indent=2))

    elif args.test:
        result = create_conference_call(
            user_phone=args.user_phone or "+12025550101",
            trade_phone=args.trade_phone or "+12025550103",
            project_id=args.project_id,
            dry_run=True,
        )
        print(json.dumps(result, indent=2))

    elif args.user_phone and args.trade_phone:
        result = create_conference_call(
            user_phone=args.user_phone,
            trade_phone=args.trade_phone,
            project_id=args.project_id,
        )
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
