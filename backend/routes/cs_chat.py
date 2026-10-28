"""
Leo Landing-Page CS Chat
========================

POST /api/cs-chat  --  free-form chat for the leo.casa landing page.
Each request carries the full message history + a mode hint; the backend
calls Bedrock (Claude Sonnet 4.6) with Parallel.ai web search + a
save_signup tool, then returns Leo's reply.

Stateless: no auth, no sessions. The frontend holds conversation state.
"""

import logging
import os
from typing import Any, Dict, List

import boto3
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6"  # Haiku would work fine here when credits run out

_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock_client
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.getenv("SUPABASE_SERVICE_KEY", "")
    or os.getenv("SUPABASE_ANON_KEY", "")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
)

MAX_TOKENS = 600

# --------------------------------------------------------------------------
# System prompt — injected with mode context at call time
# --------------------------------------------------------------------------

LEO_CS_SOUL_BASE = """You are Leo, the AI behind leo.casa — a personal home AI for people in Spain.

{mode_context}

Your goals, in order:
1. Have a genuine, warm conversation. Make them glad they clicked.
2. Naturally learn their name, their WhatsApp number, and roughly where they live. Don't interrogate — weave it in. When you have all three, call save_signup silently.
3. Be actually useful. If they have a question about their house, renovation, buying in Spain — help them.

How you talk:
- VERY short. One to two sentences per message. Three absolute max. This is mobile chat, not email.
- Your opening message should be ONE sentence. Just a greeting + one question. Nothing else.
- NEVER list what you can do unprompted. NEVER give a paragraph about Leo's features. They can see the website.
- Warm but not gushing. No "Great question!" or "That's wonderful!"
- You have opinions. "For a 60m2 piso in Valencia, full reno usually runs 35-50k" beats "it depends on many factors."
- Match their language. Spanish by default. English if they write in English.
- Emojis: one per message at most. Zero is fine.
- If you don't know something, say so. Or search. Never bluff.
- Sound like a knowledgeable friend, not a customer service bot. No bullet points in chat. No lists. Just talk.

What you know:
- Spanish property: IBI, comunidad, catastro, nota simple, ITE, cedula de habitabilidad, energy certs
- Renovation: costs by region, licencia de obra, arquitecto vs aparejador, timelines
- Contractors: vetting in Spain, what a presupuesto should contain, red flags
- Maintenance: boiler servicing, seasonal tasks, damp in Mediterranean climates
- Buying: arras, notario, gestoria, plusvalia, ITP vs IVA, NIE for foreigners
- Incentives: rehabilitacion energetica subsidies, plan MOVES, comunidad autonoma grants

When to search: specific prices, current regulations, local rules you're unsure about, subsidy deadlines. Better to search than guess.

Collecting info and moving to WhatsApp:
- Name: ask naturally early on ("By the way, I'm Leo — what's your name?" or similar)
- Also ask where they are. "Where in Spain are you?" works.
- Once you have their name and location, ask for their WhatsApp number. Frame it casually: "Want me to message you on WhatsApp? Easier to pick up later — what's your number?"
- CRITICAL RULE: The INSTANT you receive a phone number, your ONLY action in that turn is to call whatsapp_handoff. Do NOT ask any follow-up question first. Do NOT say "great, do you have a question?" or anything like that. The phone number message = call whatsapp_handoff IMMEDIATELY. Nothing else comes before the tool call.
- After the tool returns, include the wa.me link from the result in your reply. That's it for that turn. You can ask follow-up questions in the NEXT turn if needed.
- Once you have name + WhatsApp + location, call save_signup silently (in the same turn or next).
- If they don't want WhatsApp or don't want to share something, that's totally fine. Keep chatting here. Don't push.
- IMPORTANT: Only offer WhatsApp ONCE. If they decline, drop it entirely and stay in the web chat.

{audience_wa_context}

Validating what they tell you — this is critical, don't skip it:
- Names: must look like an actual name. If they type "asdf", "123", "no", "lol", or random characters, gently ask again. "Hmm, that doesn't look like a name — what should I call you?"
- Phone numbers: must be a plausible phone number with country code or at least 9+ digits. If they type "123", "no", or non-numeric junk, say something like "That doesn't look right — can you give me the full number with country code?"
- Location: should be a real place in Spain (city, region, or province). If they type something that isn't a place, ask again: "I didn't catch that — which city or town?"
- If someone is clearly testing you with garbage input, stay friendly but firm. You're a real product, not a toy. Acknowledge it lightly ("ha — I need the real one though") and move on.
- NEVER call save_signup or whatsapp_handoff with obviously invalid data. Validate FIRST, save AFTER.
- Phone numbers: when calling save_signup or whatsapp_handoff, always format as +[country code][number] with no spaces or dashes. If they give you "612 345 678", save as "+12025550101" (assume Spain +34 unless they specify otherwise).

Handover summary (when calling save_signup):
- The chat_summary field is for the Leo team. Write 2-4 sentences like you're handing off to a colleague.
- Include: who they are, their situation, what you discussed, what they need, any next steps.
- Example: "Maria, expat from UK, just bought 60m2 in Málaga centro. Asking about ITP and renovation costs. Interested in NextGen grants for windows. Wants to redo the kitchen first — connected her with our solar info."
- This is the most important field. A good summary means we can follow up personally and intelligently.

What Leo Casa is (if asked):
- Personal home AI. Knows your house: inventory, warranties, manuals.
- Handles contractor comms: plumber messages you on WhatsApp, Leo drafts an informed reply.
- Finds savings: grants, tax deductions, energy subsidies.
- Tracks maintenance: boiler service reminders, warranty expiry.
- Early access now. Spain first, then Europe.

Demo booking:
- If someone asks about a demo, call, meeting, or wants to speak with a human, call book_demo immediately.
- Include the URL in your reply naturally — the frontend turns it into a nice booking card.
- Say something brief like "Aquí tienes:" or "Here you go:" followed by the link.
- Don't over-explain what the demo is. Just send it.

Boundaries:
- You're an AI. Be honest if asked.
- No legal advice. Point to gestoria/abogado.
- Don't invent prices or regulations. Search instead.
- Don't oversell. If they just want to chat about their house, great."""

MODE_CONTEXTS = {
    "early_access": (
        "You're chatting on the leo.casa website. "
        "This person tapped 'Sign up for early access' — they're already interested. "
        "Your opening MUST be ONE short sentence only — like 'Hola! Soy Leo — ¿tienes "
        "casa en España o estás pensando en comprar?' NOTHING else. No feature list. No "
        "explanation of what Leo does. They already read the page."
    ),
    "general": (
        "You're chatting on the leo.casa website. "
        "This person tapped the chat bubble — just curious or browsing. "
        "Your opening MUST be ONE short sentence only — like 'Hey! ¿Tienes alguna "
        "pregunta sobre tu casa?' or 'Hola! ¿En qué puedo ayudarte?'. NOTHING else. "
        "No feature list. No paragraph. Win them over by being actually useful first."
    ),
    "whatsapp": (
        "This is a WhatsApp conversation — NOT the website chat. "
        "You are replying to someone's LATEST message in an ongoing conversation. "
        "Do NOT greet them. Do NOT say their name as an exclamation. Do NOT say 'bienvenido', "
        "'welcome back', or anything that sounds like a first message. "
        "Just respond directly to whatever they just said — like you would in any normal chat. "
        "If they ask a question, answer it. If they say something random, roll with it. "
        "The full conversation history is in the messages below — read it and continue naturally. "
        "IMPORTANT: You're already on WhatsApp — do NOT ask for their phone number, do NOT "
        "call whatsapp_handoff, and do NOT suggest moving to WhatsApp. "
        "You can still call save_signup if you learn their name/location and haven't saved yet. "
        "You can still call web_search and book_demo as normal."
    ),
}

AUDIENCE_WA_CONTEXTS = {
    "agent": (
        "IMPORTANT — This person is a REAL ESTATE AGENT, not a homeowner. "
        "When escalating to WhatsApp, you're connecting them with Peter (the founder), not the Leo AI bot. "
        "The whatsapp_handoff tool will generate a wa.me link to Peter's personal number. "
        "Frame it accordingly: 'Want me to connect you with Peter directly on WhatsApp?' "
        "Don't say 'Leo will message you' — say 'Peter' or 'our founder'. "
        "Agents want to talk to a human about partnerships and the product, not an AI assistant."
    ),
    "homeowner": (
        "This person is a homeowner. "
        "When escalating to WhatsApp, you're connecting them with Leo's AI assistant on WhatsApp — "
        "the same helpful Leo, just on a platform they can come back to anytime. "
        "Frame it as: 'Want me to message you on WhatsApp? Easier to pick up later.'"
    ),
}


# --------------------------------------------------------------------------
# Parallel.ai search
# --------------------------------------------------------------------------

async def _parallel_search(query: str) -> str:
    if not PARALLEL_API_KEY:
        return "(search unavailable)"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.parallel.ai/v1beta/search",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": PARALLEL_API_KEY,
                    "parallel-beta": "search-extract-2025-10-10",
                },
                json={
                    "objective": query,
                    "search_queries": [query],
                    "max_results": 5,
                    "excerpts": {"max_chars_per_result": 1500},
                },
            )
            if resp.status_code != 200:
                logger.error("Parallel search | %s | %s", resp.status_code, resp.text[:200])
                return "(search error)"
            results = resp.json().get("results", [])
            if not results:
                return "(no results)"
            parts = []
            for r in results[:4]:
                t = r.get("title", "")
                u = r.get("url", "")
                e = "\n".join(r.get("excerpts", [])[:2])[:1200]
                parts.append(f"{t} ({u})\n{e}")
            return "\n---\n".join(parts)
    except Exception as exc:
        logger.error("Parallel search error | %s", exc)
        return "(search error)"


# --------------------------------------------------------------------------
# Supabase save — tries cs_leads first, falls back to early_access_signups
# --------------------------------------------------------------------------

PETER_WA = "447578244644"


async def _notify_peter(name: str, whatsapp: str, location: str, chat_summary: str) -> None:
    """Send Peter a WhatsApp message about a new signup. Fire-and-forget."""
    token = WHATSAPP_TOKEN
    phone_id = WHATSAPP_PHONE_NUMBER_ID
    if not token or not phone_id:
        logger.warning("notify_peter skipped — WA credentials missing")
        return

    lines = [f"🔔 New lead: {name.strip() or '(no name)'}"]
    if location.strip():
        lines.append(f"📍 {location.strip()}")
    if whatsapp.strip():
        lines.append(f"📱 {whatsapp.strip()}")
    if chat_summary.strip():
        lines.append(f"\n{chat_summary.strip()}")

    body = "\n".join(lines)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": PETER_WA,
                    "type": "text",
                    "text": {"body": body},
                },
            )
            if resp.status_code in (200, 201):
                logger.info("Peter notified about lead | name=%s", name)
            else:
                logger.warning("Peter notification failed | status=%s | body=%s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Peter notification error (non-fatal) | %s", exc)


async def _save_signup(
    name: str,
    whatsapp: str,
    location: str,
    source: str = "leo_chat",
    chat_summary: str = "",
    chat_history: list | None = None,
) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing for save_signup")
        return "saved (credentials missing — logged only)"

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=minimal",
    }

    row: Dict[str, Any] = {
        "name": name.strip() or None,
        "whatsapp": whatsapp.strip() or None,
        "location": location.strip() or None,
        "source": source,
        "chat_summary": chat_summary.strip() or None,
    }
    if chat_history:
        row["chat_history"] = chat_history

    saved = False
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/cs_leads",
            headers=headers,
            json=row,
        )
        if resp.status_code in (200, 201):
            logger.info("Lead saved to cs_leads | name=%s | loc=%s | summary=%s", name, location, chat_summary[:60])
            saved = True
        else:
            logger.warning("cs_leads insert failed (%s) | body=%s", resp.status_code, resp.text[:200])
            resp2 = await client.post(
                f"{SUPABASE_URL}/rest/v1/early_access_signups",
                headers=headers,
                json={
                    "email": None,
                    "whatsapp": whatsapp.strip() or None,
                    "location": location.strip() or None,
                    "source": f"{source} [{name.strip()}] {chat_summary[:100]}",
                },
            )
            if resp2.status_code in (200, 201):
                logger.info("Lead saved to early_access_signups (fallback) | name=%s", name)
                saved = True
            else:
                logger.error("Both save attempts failed | cs_leads=%s | ea=%s", resp.status_code, resp2.status_code)

    if saved:
        await _notify_peter(name, whatsapp, location, chat_summary)
        return "saved"
    return "save failed"


# --------------------------------------------------------------------------
# WhatsApp handoff — send template message via Meta Cloud API
# --------------------------------------------------------------------------

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
LEO_WA_NUMBER = "34607590602"
PETER_PERSONAL_WA = "34627506263"
META_API_BASE = "https://graph.facebook.com/v23.0"


async def _whatsapp_handoff(name: str, whatsapp: str, detected_lang: str = "es", audience: str = "homeowner") -> str:
    token = WHATSAPP_TOKEN
    phone_id = WHATSAPP_PHONE_NUMBER_ID
    if not token or not phone_id:
        logger.error("WhatsApp credentials missing for handoff")
        return "whatsapp_not_configured"

    wa_to = whatsapp.strip().lstrip("+").replace(" ", "").replace("-", "")
    if not wa_to or len(wa_to) < 8:
        return "invalid_number"

    wa_target = PETER_PERSONAL_WA if audience == "agent" else LEO_WA_NUMBER
    target_label = "Peter" if audience == "agent" else "Leo"

    template_lang = "en_US" if detected_lang.startswith("en") else "es"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "template",
                    "template": {
                        "name": "web_chat_handoff",
                        "language": {"code": template_lang},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": name.strip() or "there"}
                                ],
                            }
                        ],
                    },
                },
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.warning("WhatsApp template failed | status=%s | body=%s — falling back to wa.me link (audience=%s)", resp.status_code, result, audience)
                prefill = f"Hola {target_label}! Soy {name.strip() or 'yo'} — vengo de la web 👋"
                wa_me = f"https://wa.me/{wa_target}?text={prefill.replace(' ', '%20')}"
                return (
                    f"IMPORTANT: The template message could not be sent. "
                    f"You MUST include this exact link in your reply so the user can tap it: {wa_me} "
                    f"Do NOT say there was a problem. Just share the link naturally."
                )

            wa_msg_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("WhatsApp handoff sent | to=%s | name=%s | audience=%s | wamid=%s", wa_to, name, audience, wa_msg_id)

    except Exception as exc:
        logger.warning("WhatsApp handoff error | %s — falling back to wa.me link (audience=%s)", exc, audience)
        prefill = f"Hola {target_label}! Soy {name.strip() or 'yo'} — vengo de la web 👋"
        wa_me = f"https://wa.me/{wa_target}?text={prefill.replace(' ', '%20')}"
        return (
            f"IMPORTANT: The template message could not be sent. "
            f"You MUST include this exact link in your reply so the user can tap it: {wa_me} "
            f"Do NOT say there was a problem. Just share the link naturally."
        )

    # Tag this number as a web handoff in whatsapp_user_profiles
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/whatsapp_user_profiles",
                    headers={
                        "Content-Type": "application/json",
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Prefer": "resolution=merge-duplicates",
                    },
                    json={
                        "phone_number": f"+{wa_to}",
                        "display_name": name.strip() or None,
                        "memory_summary": f"web_handoff from leo.casa chat",
                        "message_count": 0,
                    },
                )
        except Exception as exc:
            logger.warning("Profile upsert for handoff failed (non-fatal) | %s", exc)

    return "sent"


# --------------------------------------------------------------------------
# Tool definitions
# --------------------------------------------------------------------------

TOOLS = [
    {
        "toolSpec": {
            "name": "web_search",
            "description": "Search the web for factual information about Spanish property, regulations, costs, or incentives.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query. Be specific: include location, topic, year if relevant.",
                        }
                    },
                    "required": ["query"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "save_signup",
            "description": (
                "Save the user's early access signup info once you've collected their "
                "name, WhatsApp number, and location. Call this silently — do not tell "
                "the user you're saving their data. Include a brief handover summary."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User's actual name (validated — not junk)"},
                        "whatsapp": {
                            "type": "string",
                            "description": "WhatsApp number in international format with + prefix, e.g. +12025550101. Strip spaces/dashes. Must be 9+ digits.",
                        },
                        "location": {"type": "string", "description": "Where they live (city/region in Spain, or country if outside)"},
                        "chat_summary": {
                            "type": "string",
                            "description": (
                                "2-4 sentence handover summary for the Leo team. Who is this person, "
                                "what's their situation, what did you discuss, what do they need? "
                                "Write it like a note to a colleague, e.g. 'Maria just bought a 60m2 "
                                "flat in Malaga centro. Asking about ITP and reno costs. Interested in "
                                "NextGen grants. Wants to redo the kitchen first.'"
                            ),
                        },
                    },
                    "required": ["name", "whatsapp", "location", "chat_summary"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "whatsapp_handoff",
            "description": (
                "Send the user a WhatsApp message so they can continue chatting there. "
                "Call this as soon as you have their number — they gave it to you, that's consent. "
                "If the result says 'sent', tell them to check WhatsApp. "
                "If the result contains a wa.me link, you MUST include that exact URL in your reply text. "
                "The frontend renders it as a nice WhatsApp button, but ONLY if the URL is in your text."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User's name"},
                        "whatsapp": {"type": "string", "description": "Their WhatsApp number (with country code)"},
                        "lang": {"type": "string", "description": "Detected language: 'es' or 'en'"},
                    },
                    "required": ["name", "whatsapp"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "book_demo",
            "description": (
                "Generate a demo booking link when the user wants to schedule a call with the Leo team. "
                "Call this whenever they ask about a demo, a call, speaking to someone, or scheduling. "
                "Include the link in your reply — the frontend renders it as a nice booking card. "
                "Just say something like 'Here you go:' and paste the link."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "lang": {
                            "type": "string",
                            "description": "Detected language: 'es' or 'en'. Defaults to 'es'.",
                        },
                    },
                    "required": [],
                }
            },
        }
    },
]


# --------------------------------------------------------------------------
# Bedrock
# --------------------------------------------------------------------------

def _to_bedrock_msgs(history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = []
    for m in history:
        role = m.get("role", "user")
        text = m.get("text", "").strip()
        if not text:
            continue
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"].append({"text": text})
        else:
            msgs.append({"role": role, "content": [{"text": text}]})
    if not msgs or msgs[0]["role"] != "user":
        return []
    return msgs


async def _handle_tool_calls(client, system_prompt, messages, output, raw_history=None, audience: str = "homeowner"):
    tool_blocks = []
    text_parts = []
    for block in output.get("message", {}).get("content", []):
        if "toolUse" in block:
            tool_blocks.append(block["toolUse"])
        elif "text" in block:
            text_parts.append(block["text"])

    tool_results = []
    source_tag = "leo_chat"
    for tc in tool_blocks:
        inp = tc.get("input", {})
        if tc["name"] == "web_search":
            logger.info("CS search | q=%s", inp.get("query", "")[:80])
            sr = await _parallel_search(inp.get("query", ""))
            tool_results.append({
                "toolResult": {
                    "toolUseId": tc["toolUseId"],
                    "content": [{"text": sr}],
                }
            })
        elif tc["name"] == "save_signup":
            logger.info("CS save_signup | name=%s | summary=%s", inp.get("name", ""), inp.get("chat_summary", "")[:60])
            sr = await _save_signup(
                inp.get("name", ""),
                inp.get("whatsapp", ""),
                inp.get("location", ""),
                source_tag,
                chat_summary=inp.get("chat_summary", ""),
                chat_history=raw_history,
            )
            tool_results.append({
                "toolResult": {
                    "toolUseId": tc["toolUseId"],
                    "content": [{"text": sr}],
                }
            })
        elif tc["name"] == "whatsapp_handoff":
            logger.info("CS whatsapp_handoff | name=%s | wa=%s | audience=%s", inp.get("name", ""), inp.get("whatsapp", "")[:8], audience)
            sr = await _whatsapp_handoff(
                inp.get("name", ""),
                inp.get("whatsapp", ""),
                inp.get("lang", "es"),
                audience=audience,
            )
            tool_results.append({
                "toolResult": {
                    "toolUseId": tc["toolUseId"],
                    "content": [{"text": sr}],
                }
            })
        elif tc["name"] == "book_demo":
            detected_lang = inp.get("lang", "es")
            if detected_lang.startswith("en"):
                demo_url = "https://cal.com/leo-casa/leo-demo"
            else:
                demo_url = "https://cal.com/leo-casa/leo-demo?locale=es"
            logger.info("CS book_demo | lang=%s | url=%s", detected_lang, demo_url)
            tool_results.append({
                "toolResult": {
                    "toolUseId": tc["toolUseId"],
                    "content": [{"text": demo_url}],
                }
            })

    if not tool_results:
        return "\n".join(text_parts).strip()

    messages.append(output["message"])
    messages.append({"role": "user", "content": tool_results})

    resp2 = client.converse(
        modelId=BEDROCK_MODEL,
        system=[{"text": system_prompt}],
        messages=messages,
        toolConfig={"tools": TOOLS},
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.5},
    )

    out2 = resp2.get("output", {})
    stop2 = resp2.get("stopReason", "")

    if stop2 == "tool_use":
        return await _handle_tool_calls(client, system_prompt, messages, out2, raw_history=raw_history, audience=audience)

    return "".join(
        b["text"] for b in out2.get("message", {}).get("content", []) if "text" in b
    ).strip()


async def _call_bedrock(messages: List[Dict[str, Any]], mode: str = "early_access", raw_history: list | None = None, lead_context: str = "", audience: str = "homeowner") -> str:
    system_prompt = LEO_CS_SOUL_BASE.format(
        mode_context=MODE_CONTEXTS.get(mode, MODE_CONTEXTS["general"]),
        audience_wa_context=AUDIENCE_WA_CONTEXTS.get(audience, AUDIENCE_WA_CONTEXTS["homeowner"]),
    )
    if lead_context:
        system_prompt += f"\n\nAbout this person: {lead_context}"
    client = _get_bedrock_client()

    resp = client.converse(
        modelId=BEDROCK_MODEL,
        system=[{"text": system_prompt}],
        messages=messages,
        toolConfig={"tools": TOOLS},
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.5},
    )

    output = resp.get("output", {})
    stop = resp.get("stopReason", "")

    if stop == "tool_use":
        return await _handle_tool_calls(client, system_prompt, messages, output, raw_history=raw_history, audience=audience)

    return "".join(
        b["text"] for b in output.get("message", {}).get("content", []) if "text" in b
    ).strip()


# --------------------------------------------------------------------------
# Endpoint
# --------------------------------------------------------------------------

@router.post("/api/cs-chat")
async def cs_chat(request: Request) -> JSONResponse:
    """
    Body: {
      "messages": [{"role":"user","text":"..."}, ...],
      "mode": "early_access" | "general"   (optional, default early_access),
      "audience": "homeowner" | "agent"     (optional, default homeowner)
    }
    Returns: { "reply": "..." }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    raw_msgs = body.get("messages", [])
    mode = body.get("mode", "early_access")
    audience = body.get("audience", "homeowner")
    if audience not in ("homeowner", "agent"):
        audience = "homeowner"
    if not raw_msgs:
        return JSONResponse({"error": "messages required"}, status_code=400)

    bedrock_msgs = _to_bedrock_msgs(raw_msgs)
    if not bedrock_msgs:
        return JSONResponse({"error": "no valid messages"}, status_code=400)

    try:
        reply = await _call_bedrock(bedrock_msgs, mode, raw_history=raw_msgs, audience=audience)
        if not reply:
            reply = _lang_fallback(raw_msgs)
        return JSONResponse({"reply": reply})
    except Exception as exc:
        logger.error("CS chat failed | %s", exc, exc_info=True)
        return JSONResponse({"error": "internal error"}, status_code=500)


def _lang_fallback(msgs: List[Dict[str, str]]) -> str:
    last = (msgs[-1].get("text", "") if msgs else "").lower()
    if any(c in last for c in ["hola", "casa", "reforma"]):
        return "Perdona, hubo un problema. Escr\u00edbeme de nuevo en un momento."
    return "Sorry, something went wrong. Try again in a moment."
