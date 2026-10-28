"""
WhatsApp Agent Tools (OpenClaw-inspired)
=======================================

Tools are explicit: the agent decides when to call them. We store tool history
alongside chat messages so the model can "see what it did" previously.

Design goals:
- Small, readable functions (no hidden magic)
- Fail loud on unexpected DB states (so we can debug)
- Reuse the proven V5 image pipeline helpers (defurnish/prompt-gen/style)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

import httpx

import database
from pipeline.gemini_client import (
    call_gemini,
    call_gemini_image,
    call_gemini_json,
    fetch_image_as_base64,
    fetch_images_batch,
)
from pricing.v5_room_images import (
    _IMAGE_GEN_PREAMBLE,
    _IMAGE_GEN_POSTAMBLE,
    _IMAGE_SYSTEM_INSTRUCTION,
    _build_scope_text,
    _defurnish_photo,
    _extract_visible_changes,
    _generate_prompt_for_photo,
    _parse_numbered_list_items,
    _pick_best_photo,
    _render_numbered_list_items,
    _style_consistency_patch_instructions,
)
from whatsapp.twilio_client import send_media

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# leo_tool registry (Phase 5: decorator-based tool registration)
# ---------------------------------------------------------------------------

_LEO_TOOLS: Dict[str, Callable[..., Any]] = {}
_LEO_TOOL_META: Dict[str, Dict[str, Any]] = {}


def leo_tool(
    *,
    name: str,
    description: str,
    requires: Optional[List[str]] = None,
    params: Optional[Dict[str, Any]] = None,
    required_params: Optional[List[str]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that self-registers a WhatsApp tool and its Gemini declaration.

    WHY THIS MATTERS:
    - Avoids having to edit multiple registries when adding a tool.
    - Lets the agent build tool declarations dynamically based on prerequisites.
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = str(name or "").strip()
        if not tool_name:
            raise ValueError("leo_tool: name is required")
        if tool_name in _LEO_TOOLS:
            raise ValueError(f"leo_tool: duplicate tool registration: {tool_name}")

        meta = {
            "name": tool_name,
            "description": str(description or "").strip(),
            "requires": [str(r).strip() for r in (requires or []) if isinstance(r, str) and str(r).strip()],
            "params": params or {"type": "object", "properties": {}},
            "required_params": [str(x).strip() for x in (required_params or []) if isinstance(x, str) and str(x).strip()],
        }

        setattr(fn, "_leo_tool_meta", meta)
        _LEO_TOOLS[tool_name] = fn
        _LEO_TOOL_META[tool_name] = meta
        return fn

    return _decorator


def get_tool_function(name: str) -> Optional[Callable[..., Any]]:
    """Return a tool callable by name (or None)."""
    return _LEO_TOOLS.get(str(name or "").strip())


def get_tool_declarations(*, capabilities: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Build Gemini function declarations for tools whose prerequisites are satisfied.

    capabilities: iterable of strings like:
      - listing_id
      - clusters
      - gla_opinion
      - smart_m2
      - has_any_vision
      - can_generate_vision
    """
    caps: Set[str] = {str(c).strip() for c in (capabilities or []) if isinstance(c, str) and str(c).strip()}

    decls: List[Dict[str, Any]] = []
    for tool_name, meta in sorted(_LEO_TOOL_META.items(), key=lambda kv: kv[0]):
        reqs = meta.get("requires") or []
        if any(r not in caps for r in reqs):
            continue

        parameters = meta.get("params") or {"type": "object", "properties": {}}
        if isinstance(parameters, dict):
            parameters = dict(parameters)
            req_params = meta.get("required_params") or []
            if req_params:
                parameters["required"] = list(req_params)

        decls.append(
            {
                "name": tool_name,
                "description": str(meta.get("description") or "").strip(),
                "parameters": parameters,
            }
        )

    return [{"function_declarations": decls}]


# ---------------------------------------------------------------------------
# Low-level DB helpers (Supabase PostgREST)
# ---------------------------------------------------------------------------

async def _get_rest() -> tuple[httpx.AsyncClient, str]:
    client = await database.get_client()
    base_url = database._get_base_url()
    if not base_url:
        raise RuntimeError("whatsapp.tools: missing Supabase REST base_url")
    return client, base_url


async def _select_single(
    *,
    table: str,
    filters: Dict[str, str],
    select: str,
) -> Optional[Dict[str, Any]]:
    client, base_url = await _get_rest()
    params = {k: v for k, v in (filters or {}).items()}
    params["select"] = select
    resp = await client.get(f"{base_url}/{table}", params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"whatsapp.tools: select failed | table={table} status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json()
    if not rows:
        return None
    if not isinstance(rows, list) or not isinstance(rows[0], dict):
        raise RuntimeError(f"whatsapp.tools: unexpected select response | table={table} type={type(rows).__name__}")
    return rows[0]


async def _insert_row(*, table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    client, base_url = await _get_rest()
    resp = await client.post(f"{base_url}/{table}", json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"whatsapp.tools: insert failed | table={table} status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json()
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return rows[0]
    return payload


async def _patch_rows(*, table: str, filters: Dict[str, str], payload: Dict[str, Any]) -> bool:
    client, base_url = await _get_rest()
    resp = await client.patch(f"{base_url}/{table}", params=filters, json=payload)
    return resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Project + Comms helpers (leo_projects, leo_tradespeople, leo_project_comms)
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    import re

    s2 = str(s or "").strip().lower()
    # Keep ASCII to avoid URL/email weirdness.
    s2 = s2.encode("ascii", errors="ignore").decode("ascii")
    s2 = re.sub(r"[^a-z0-9]+", "-", s2)
    s2 = re.sub(r"-{2,}", "-", s2).strip("-")
    return s2


def _normalize_e164(phone: str) -> str:
    p = str(phone or "").strip()
    if p.startswith("whatsapp:"):
        p = p.replace("whatsapp:", "", 1).strip()
    return p


def _extract_email_address(from_field: str) -> str:
    """
    Extract an email address from a From header-ish string like:
      - "Name <owner@example.invalid>"
      - "owner@example.invalid"
    """
    s = str(from_field or "").strip()
    if "<" in s and ">" in s:
        inner = s.split("<", 1)[1].split(">", 1)[0].strip()
        return inner
    return s


async def _get_latest_active_project_for_phone(phone: str) -> Optional[Dict[str, Any]]:
    client, base_url = await _get_rest()
    resp = await client.get(
        f"{base_url}/leo_projects",
        params={
            "phone_number": f"eq.{str(phone)}",
            "status": "eq.active",
            "select": "id,phone_number,listing_id,name,description,status,created_at",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(f"leo_projects select failed | status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json() or []
    return rows[0] if isinstance(rows, list) and rows else None


async def _get_tradesperson_by_id(tradesperson_id: str) -> Optional[Dict[str, Any]]:
    return await _select_single(
        table="leo_tradespeople",
        filters={"id": f"eq.{str(tradesperson_id)}"},
        select="id,project_id,name,email,phone,profile_summary,profile_data,outreach_status,created_at",
    )


async def _get_recent_tradespeople(*, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    client, base_url = await _get_rest()
    resp = await client.get(
        f"{base_url}/leo_tradespeople",
        params={
            "project_id": f"eq.{str(project_id)}",
            "select": "id,project_id,name,email,phone,outreach_status,created_at",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 200))),
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"leo_tradespeople select failed | project_id={project_id} status={resp.status_code} body={resp.text[:500]}"
        )
    rows = resp.json() or []
    if not isinstance(rows, list):
        raise RuntimeError("leo_tradespeople select: unexpected response type")
    return [r for r in rows if isinstance(r, dict)]


async def _log_project_comm(
    *,
    project_id: str,
    comm_type: str,
    tradesperson_id: Optional[str] = None,
    from_addr: Optional[str] = None,
    to_addr: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    call_sids: Optional[Dict[str, Any]] = None,
    recording_url: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "project_id": str(project_id),
        "type": str(comm_type),
        "tradesperson_id": str(tradesperson_id) if tradesperson_id else None,
        "from_addr": str(from_addr) if from_addr else None,
        "to_addr": str(to_addr) if to_addr else None,
        "subject": str(subject) if subject else None,
        "body": str(body) if body else None,
        "attachments": attachments or [],
        "call_sids": call_sids,
        "recording_url": recording_url,
    }
    # Strip None so we keep rows compact.
    payload = {k: v for k, v in payload.items() if v is not None}
    return await _insert_row(table="leo_project_comms", payload=payload)


# ---------------------------------------------------------------------------
# GLA storage helpers
# ---------------------------------------------------------------------------

async def _get_latest_image_version(*, listing_id: int, room_id: str, phone_number: Optional[str]) -> Optional[Dict[str, Any]]:
    client, base_url = await _get_rest()
    params: Dict[str, str] = {
        "listing_id": f"eq.{int(listing_id)}",
        "room_id": f"eq.{str(room_id)}",
        "select": "id,version,phone_number,slot_decisions,prompt_used,user_input,defurnished_data,image_data,created_at",
        "order": "version.desc",
        "limit": "1",
    }
    # phone_number is optional; if present we narrow for the active user.
    if phone_number:
        params["phone_number"] = f"eq.{str(phone_number)}"
    resp = await client.get(f"{base_url}/gla_image_versions", params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"whatsapp.tools: get_latest_image_version failed | status={resp.status_code} body={resp.text[:500]}")
    rows = resp.json() or []
    return rows[0] if isinstance(rows, list) and rows else None


async def _insert_image_version(
    *,
    listing_id: int,
    room_id: str,
    version: int,
    phone_number: Optional[str],
    slot_decisions: Dict[str, Any],
    prompt_used: str,
    user_input: Optional[str],
    defurnished_data: str,
    image_data: str,
) -> Dict[str, Any]:
    payload = {
        "listing_id": int(listing_id),
        "room_id": str(room_id),
        "version": int(version),
        "phone_number": str(phone_number) if phone_number else None,
        "slot_decisions": slot_decisions or {},
        "prompt_used": str(prompt_used),
        "user_input": (str(user_input).strip() if isinstance(user_input, str) else None),
        "defurnished_data": str(defurnished_data),
        "image_data": str(image_data),
    }
    return await _insert_row(table="gla_image_versions", payload=payload)


async def _get_latest_image_versions_for_listing(
    *,
    listing_id: int,
    phone_number: Optional[str],
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Best-effort fetch of recent gla_image_versions rows for a listing.

    WHY THIS MATTERS:
    - PostgREST doesn't give us a cheap "latest per room" group-by with our simple helpers.
    - For auto-consistency we just need a reasonable set of the newest prompts across rooms.
    """
    client, base_url = await _get_rest()
    params: Dict[str, str] = {
        "listing_id": f"eq.{int(listing_id)}",
        "select": "id,room_id,version,phone_number,slot_decisions,prompt_used,created_at",
        "order": "created_at.desc",
        "limit": str(max(1, min(int(limit), 1000))),
    }
    if phone_number:
        params["phone_number"] = f"eq.{str(phone_number)}"
    resp = await client.get(f"{base_url}/gla_image_versions", params=params)
    if resp.status_code != 200:
        raise RuntimeError(
            "whatsapp.tools: get_latest_image_versions_for_listing failed "
            f"| status={resp.status_code} body={resp.text[:500]}"
        )
    rows = resp.json() or []
    if not isinstance(rows, list):
        raise RuntimeError("whatsapp.tools: get_latest_image_versions_for_listing unexpected response type")
    return [r for r in rows if isinstance(r, dict)]


def _apply_style_patch_to_pro_list(*, pro_list: str, patch: Dict[str, Any]) -> tuple[str, int]:
    """
    Apply a single style-consistency patch dict to a numbered-list prompt.

    Returns: (patched_pro_list, applied_change_count)
    """
    items = _parse_numbered_list_items(str(pro_list or ""))
    if not items:
        return str(pro_list or "").strip(), 0

    change_count = 0

    replace_items = patch.get("replace_items") if isinstance(patch, dict) else None
    if isinstance(replace_items, list):
        for ri in replace_items:
            if not isinstance(ri, dict):
                continue
            try:
                item_index = int(ri.get("item_index"))
            except Exception:
                continue
            text = ri.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            idx0 = item_index - 1
            if 0 <= idx0 < len(items):
                if items[idx0].strip() != text.strip():
                    items[idx0] = text.strip()
                    change_count += 1

    insert_items = patch.get("insert_items_before_last") if isinstance(patch, dict) else None
    if isinstance(insert_items, list):
        inserts_clean = [str(x).strip() for x in insert_items if isinstance(x, str) and str(x).strip()]
        if inserts_clean:
            # Keep the camera/geometry rule as the final item.
            pos = max(len(items) - 1, 0)
            items = items[:pos] + inserts_clean + items[pos:]
            change_count += len(inserts_clean)

    patched = _render_numbered_list_items(items)
    return patched.strip() if patched else str(pro_list or "").strip(), change_count


async def _get_room_decisions(*, listing_id: int, room_id: str, phone_number: str) -> Optional[Dict[str, Any]]:
    return await _select_single(
        table="gla_room_decisions",
        filters={
            "listing_id": f"eq.{int(listing_id)}",
            "phone_number": f"eq.{str(phone_number)}",
            "room_id": f"eq.{str(room_id)}",
        },
        select="id,slot_decisions,cost_range_low,cost_range_high,approved,updated_at",
    )


async def _upsert_room_decisions(
    *,
    listing_id: int,
    room_id: str,
    phone_number: str,
    slot_decisions: Optional[Dict[str, Any]] = None,
    cost_range_low: Optional[float] = None,
    cost_range_high: Optional[float] = None,
) -> None:
    existing = await _get_room_decisions(listing_id=listing_id, room_id=room_id, phone_number=phone_number)
    if existing and existing.get("id"):
        filters = {"id": f"eq.{existing['id']}"}
        patch_payload: Dict[str, Any] = {}
        if slot_decisions is not None:
            patch_payload["slot_decisions"] = slot_decisions
        if cost_range_low is not None:
            patch_payload["cost_range_low"] = cost_range_low
        if cost_range_high is not None:
            patch_payload["cost_range_high"] = cost_range_high
        if patch_payload:
            ok = await _patch_rows(table="gla_room_decisions", filters=filters, payload=patch_payload)
            if not ok:
                raise RuntimeError(f"whatsapp.tools: failed to patch gla_room_decisions | listing_id={listing_id} room_id={room_id}")
        return

    payload: Dict[str, Any] = {
        "listing_id": int(listing_id),
        "phone_number": str(phone_number),
        "room_id": str(room_id),
        "slot_decisions": slot_decisions or {},
    }
    if cost_range_low is not None:
        payload["cost_range_low"] = cost_range_low
    if cost_range_high is not None:
        payload["cost_range_high"] = cost_range_high
    await _insert_row(table="gla_room_decisions", payload=payload)


def _extract_pro_list_from_prompt(prompt_used: str) -> str:
    s = (prompt_used or "").strip()
    if s.startswith(_IMAGE_GEN_PREAMBLE):
        s = s[len(_IMAGE_GEN_PREAMBLE):]
    if s.endswith(_IMAGE_GEN_POSTAMBLE):
        s = s[: -len(_IMAGE_GEN_POSTAMBLE)]
    return s.strip()


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

@leo_tool(
    name="create_project",
    description=(
        "Create a new renovation/project record for this WhatsApp user (project can exist without a listing). "
        "Returns a project_id which is also used to generate the project email inbox address."
    ),
    requires=[],
    params={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short human name for the project (e.g. 'Tatami bedroom', 'Fix blinds')"},
            "description": {"type": "string", "description": "Optional longer description / scope notes"},
        },
    },
    required_params=["name"],
)
async def create_project(
    *,
    name: str,
    description: Optional[str] = None,
    phone: str,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not phone:
        raise ValueError("create_project: missing phone")
    nm = str(name or "").strip()
    if not nm:
        raise ValueError("create_project: name is required")

    base = _slugify(nm) or _slugify(description or "") or "project"
    base = base[:40] if len(base) > 40 else base

    client, base_url = await _get_rest()
    payload_base: Dict[str, Any] = {
        "phone_number": str(phone),
        "listing_id": int(listing_id) if listing_id else None,
        "name": nm,
        "description": (str(description).strip() if isinstance(description, str) and description.strip() else None),
        "status": "active",
    }
    payload_base = {k: v for k, v in payload_base.items() if v is not None}

    last_err = ""
    for attempt in range(1, 30):
        pid = base if attempt == 1 else f"{base}-{attempt:02d}"
        payload = {**payload_base, "id": pid}
        resp = await client.post(f"{base_url}/leo_projects", json=payload)
        if resp.status_code in (200, 201):
            rows = resp.json() or []
            row = rows[0] if isinstance(rows, list) and rows else payload
            return {"ok": True, "project_id": row.get("id") or pid, "project": row}
        if resp.status_code == 409:
            last_err = resp.text[:200]
            continue
        last_err = f"{resp.status_code} {resp.text[:300]}"
        break

    raise RuntimeError(f"create_project: failed to insert after retries | last_err={last_err}")


@leo_tool(
    name="save_tradesperson",
    description="Save a tradesperson profile to the current project (name/email/phone + optional profile_data).",
    requires=["has_project"],
    params={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; defaults to your latest active project"},
            "name": {"type": "string", "description": "Tradesperson name"},
            "email": {"type": "string", "description": "Tradesperson email (optional)"},
            "phone": {"type": "string", "description": "Tradesperson phone (optional, E.164 preferred)"},
            "profile_summary": {"type": "string", "description": "Short synthesized summary (optional)"},
            "profile_data": {"type": "object", "description": "Full structured profile data (optional)"},
        },
    },
    required_params=["name"],
)
async def save_tradesperson(
    *,
    name: str,
    project_id: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    profile_summary: Optional[str] = None,
    profile_data: Optional[Dict[str, Any]] = None,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    nm = str(name or "").strip()
    if not nm:
        raise ValueError("save_tradesperson: name is required")

    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("save_tradesperson: missing project_id (no default project found)")

    payload: Dict[str, Any] = {
        "project_id": pid,
        "name": nm,
        "email": (str(email).strip() if isinstance(email, str) and email.strip() else None),
        "phone": (str(phone).strip() if isinstance(phone, str) and phone.strip() else None),
        "profile_summary": (str(profile_summary).strip() if isinstance(profile_summary, str) and profile_summary.strip() else None),
        "profile_data": profile_data or {},
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    row = await _insert_row(table="leo_tradespeople", payload=payload)
    return {"ok": True, "project_id": pid, "tradesperson_id": row.get("id"), "tradesperson": row}


@leo_tool(
    name="send_outreach_email",
    description=(
        "Send an outreach email to a tradesperson on the current project via Resend. "
        "Logs the outbound email to leo_project_comms and updates outreach_status."
    ),
    requires=["has_project", "has_tradesperson_email"],
    params={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; defaults to your latest active project"},
            "tradesperson_id": {"type": "string", "description": "Optional; if omitted, picks the most recent tradesperson with an email"},
            "subject": {"type": "string", "description": "Email subject"},
            "scope_description": {"type": "string", "description": "What we need done / scope details to send"},
            "user_name": {"type": "string", "description": "How to refer to the user in the email (optional)"},
            "reply_deadline_days": {"type": "integer", "description": "Soft reply deadline in days (optional)"},
            "dry_run": {"type": "boolean", "description": "If true, do not call Resend; just log what would be sent (testing only)"},
        },
    },
    required_params=["scope_description"],
)
async def send_outreach_email(
    *,
    scope_description: str,
    project_id: Optional[str] = None,
    tradesperson_id: Optional[str] = None,
    subject: Optional[str] = None,
    user_name: Optional[str] = None,
    reply_deadline_days: Optional[int] = None,
    dry_run: Optional[bool] = None,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("send_outreach_email: missing project_id (no default project found)")
    scope = str(scope_description or "").strip()
    if not scope:
        raise ValueError("send_outreach_email: scope_description is required")

    # Pick tradesperson.
    tp: Optional[Dict[str, Any]] = None
    if tradesperson_id:
        tp = await _get_tradesperson_by_id(str(tradesperson_id))
    if not tp:
        trades = await _get_recent_tradespeople(project_id=pid, limit=80)
        tp = next((t for t in trades if isinstance(t, dict) and isinstance(t.get("email"), str) and t.get("email").strip()), None)
    if not tp:
        raise RuntimeError("send_outreach_email: no tradesperson with an email found for this project")

    to_email = str(tp.get("email") or "").strip()
    trade_name = str(tp.get("name") or "there").strip()
    if not to_email:
        raise RuntimeError("send_outreach_email: chosen tradesperson has no email")

    # Subject default is intentionally short and clear (tradespeople read on mobile).
    subj = str(subject or "").strip() or f"Project inquiry: {pid}"

    from tools.leo_email_proxy import project_email as _project_email
    from_addr = _project_email(pid)

    if bool(dry_run):
        await _log_project_comm(
            project_id=pid,
            comm_type="email_out",
            tradesperson_id=str(tp.get("id") or ""),
            from_addr=from_addr,
            to_addr=to_email,
            subject=subj,
            body=f"DRY_RUN\n\n{scope}",
            attachments=[],
        )
        return {
            "ok": True,
            "dry_run": True,
            "project_id": pid,
            "tradesperson_id": str(tp.get("id") or "").strip(),
            "email": {
                "success": True,
                "email_id": "DRY_RUN",
                "from": from_addr,
                "to": to_email,
                "project_id": pid,
            },
        }

    from tools.leo_email_proxy import send_outreach as _send_outreach

    import asyncio

    result = await asyncio.to_thread(
        _send_outreach,
        pid,
        to_email,
        trade_name,
        subj,
        scope,
        str(user_name).strip() if isinstance(user_name, str) and user_name.strip() else "a client",
        int(reply_deadline_days) if isinstance(reply_deadline_days, int) and reply_deadline_days > 0 else 3,
    )
    if not isinstance(result, dict) or not result.get("success"):
        raise RuntimeError(f"send_outreach_email: send_outreach failed | result={result}")

    await _log_project_comm(
        project_id=pid,
        comm_type="email_out",
        tradesperson_id=str(tp.get("id") or ""),
        from_addr=str(result.get("from") or from_addr),
        to_addr=to_email,
        subject=subj,
        body=scope,
        attachments=[],
    )

    tp_id = str(tp.get("id") or "").strip()
    if tp_id:
        await _patch_rows(table="leo_tradespeople", filters={"id": f"eq.{tp_id}"}, payload={"outreach_status": "emailed"})

    return {"ok": True, "project_id": pid, "tradesperson_id": tp_id, "email": result}


@leo_tool(
    name="create_conference_call",
    description=(
        "Create a Twilio conference call connecting the user and a tradesperson for the current project. "
        "Logs the call metadata in leo_project_comms."
    ),
    requires=["has_project", "has_tradespeople"],
    params={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; defaults to your latest active project"},
            "tradesperson_id": {"type": "string", "description": "Optional; if omitted, picks the most recent tradesperson with a phone"},
            "dry_run": {"type": "boolean", "description": "If true, do not place calls (useful for testing)"},
            "record": {"type": "boolean", "description": "If true, record the conference (default true)"},
        },
    },
    required_params=[],
)
async def create_conference_call(
    *,
    project_id: Optional[str] = None,
    tradesperson_id: Optional[str] = None,
    dry_run: Optional[bool] = None,
    record: Optional[bool] = None,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("create_conference_call: missing project_id (no default project found)")

    # Load project to get user phone.
    project = await _select_single(
        table="leo_projects",
        filters={"id": f"eq.{pid}"},
        select="id,phone_number,name,status,created_at",
    )
    if not project:
        raise RuntimeError(f"create_conference_call: project not found | project_id={pid}")

    user_phone = _normalize_e164(str(project.get("phone_number") or ""))
    if not user_phone:
        raise RuntimeError("create_conference_call: project has no phone_number")

    # Pick tradesperson.
    tp: Optional[Dict[str, Any]] = None
    if tradesperson_id:
        tp = await _get_tradesperson_by_id(str(tradesperson_id))
    if not tp:
        trades = await _get_recent_tradespeople(project_id=pid, limit=80)
        tp = next((t for t in trades if isinstance(t, dict) and isinstance(t.get("phone"), str) and t.get("phone").strip()), None)
    if not tp:
        raise RuntimeError("create_conference_call: no tradesperson with a phone number found for this project")

    trade_phone = _normalize_e164(str(tp.get("phone") or ""))
    if not trade_phone:
        raise RuntimeError("create_conference_call: chosen tradesperson has no phone")

    # Determine call sequence number (best-effort).
    client, base_url = await _get_rest()
    resp = await client.get(
        f"{base_url}/leo_project_comms",
        params={"project_id": f"eq.{pid}", "type": "eq.call", "select": "id", "limit": "100"},
    )
    call_number = 1
    if resp.status_code == 200 and isinstance(resp.json(), list):
        call_number = len(resp.json()) + 1

    from tools.leo_conference_call import create_conference_call as _create_conf

    call_result = _create_conf(
        user_phone=user_phone,
        trade_phone=trade_phone,
        project_id=pid,
        call_number=int(call_number),
        record=True if record is None else bool(record),
        dry_run=bool(dry_run) if dry_run is not None else False,
    )
    if not isinstance(call_result, dict) or not call_result.get("conference_name"):
        raise RuntimeError(f"create_conference_call: underlying call failed | result={call_result}")

    tp_id = str(tp.get("id") or "").strip()
    await _log_project_comm(
        project_id=pid,
        comm_type="call",
        tradesperson_id=tp_id or None,
        from_addr=user_phone,
        to_addr=trade_phone,
        subject=f"Conference call: {call_result.get('conference_name')}",
        body=json.dumps(call_result, ensure_ascii=False),
        call_sids={
            "user_call_sid": call_result.get("user_call_sid"),
            "trade_call_sid": call_result.get("trade_call_sid"),
            "conference_name": call_result.get("conference_name"),
        },
    )

    return {"ok": True, "project_id": pid, "tradesperson_id": tp_id, "call": call_result}

@leo_tool(
    name="mark_debrief_done",
    description=(
        "Mark a call debrief as complete after you've discussed it with the user. "
        "Call this AFTER you've had the Gordon Ramsay debrief conversation about a recent call."
    ),
    requires=["has_project"],
    params={
        "type": "object",
        "properties": {
            "comm_id": {"type": "string", "description": "The comm_id from PENDING_CALL_DEBRIEF context"},
        },
    },
    required_params=["comm_id"],
)
async def mark_debrief_done(
    *,
    comm_id: str,
    phone: Optional[str] = None,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Mark a call debrief as done so Leo stops bringing it up."""
    cid = str(comm_id or "").strip()
    if not cid:
        raise ValueError("mark_debrief_done: missing comm_id")

    ok = await _patch_rows(
        table="leo_project_comms",
        filters={"id": f"eq.{cid}"},
        payload={"debrief_status": "done"},
    )
    if not ok:
        raise RuntimeError(f"mark_debrief_done: failed to update | comm_id={cid}")

    return {"ok": True, "comm_id": cid, "debrief_status": "done"}


@leo_tool(
    name="generate_room_vision",
    description=(
        "Generate a first after-image for a room (pick best photo, defurnish, prompt, render). "
        "IMPORTANT: room_id MUST be one of the exact values from ROOM_INVENTORY in the prompt. "
        "Only works for rooms that have both photos AND scope changes."
    ),
    requires=["listing_id", "can_generate_vision"],
    params={
        "type": "object",
        "properties": {
            "room_id": {"type": "string", "description": "Exact room_id from ROOM_INVENTORY (e.g. 'kitchen_1', 'bedroom_primary_1')"},
            "user_ideas": {"type": "string", "description": "Optional user preferences to incorporate into the vision"},
        },
    },
    required_params=["room_id"],
)
async def generate_room_vision(
    *,
    listing_id: int,
    room_id: str,
    user_ideas: Optional[str] = None,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a first "after" rendering for a room:
    pick photo → defurnish → pro prompt → flash-image render → store version.
    """
    if not listing_id:
        raise ValueError("generate_room_vision: missing listing_id")
    if not room_id:
        raise ValueError("generate_room_vision: missing room_id")

    clusters = await database.get_photo_clusters(int(listing_id))
    cluster = next((c for c in (clusters or []) if str(c.get("cluster_id") or "") == str(room_id)), None)
    if not (isinstance(cluster, dict) and isinstance(cluster.get("photo_urls"), list) and cluster.get("photo_urls")):
        raise RuntimeError(f"generate_room_vision: room cluster not found or empty | listing_id={listing_id} room_id={room_id}")

    # Pull slot opinions for this room (required for scope text).
    opinion = await database.get_unified_estimate(int(listing_id), "gla_opinion")
    if not (isinstance(opinion, dict) and isinstance(opinion.get("rooms"), list)):
        raise RuntimeError(f"generate_room_vision: missing gla_opinion | listing_id={listing_id}")
    room_op = next((r for r in opinion.get("rooms") or [] if isinstance(r, dict) and str(r.get("room_id") or "") == str(room_id)), None)
    slot_opinion = (room_op or {}).get("slot_opinion_narratives") or {}
    if not isinstance(slot_opinion, dict) or not slot_opinion:
        raise RuntimeError(f"generate_room_vision: missing slot_opinion_narratives | listing_id={listing_id} room_id={room_id}")

    # Allow the user to override/augment slot-level decisions for visual output.
    # Store these separately from opinion so iteration can evolve them.
    slot_decisions = dict(slot_opinion)
    if isinstance(user_ideas, str) and user_ideas.strip():
        # Small, explicit hook: add as a pseudo-slot so prompt-gen sees it.
        slot_decisions["_user_ideas"] = user_ideas.strip()

    # Build scope text using the proven V5 visual mapping (delta-like shape).
    delta_like = {"slot_work_narratives": slot_decisions}
    scope_text = _build_scope_text(delta_like)

    urls = [u for u in cluster.get("photo_urls") or [] if isinstance(u, str) and u.strip()]
    if not urls:
        raise RuntimeError(f"generate_room_vision: no photo urls | listing_id={listing_id} room_id={room_id}")

    room_name = str(cluster.get("room_type") or room_id)

    # Pick best photo from a small candidate set to keep cost/latency low.
    candidate_urls = urls[:6]
    fetched = await fetch_images_batch(candidate_urls)
    candidates = [
        (u, img)
        for u, img in zip(candidate_urls, fetched or [])
        if isinstance(img, dict) and img.get("data")
    ]
    chosen_url = candidate_urls[0]
    if len(candidates) >= 2:
        logger.info(
            "generate_room_vision: picking best photo | listing_id=%s room_id=%s candidates=%d",
            listing_id,
            room_id,
            len(candidates),
        )
        best_idx = await _pick_best_photo(
            room_name=room_name,
            photo_images=[img for _u, img in candidates],
            call_gemini_json=call_gemini_json,
        )
        chosen_url = candidates[int(best_idx)][0] if isinstance(best_idx, int) and 0 <= best_idx < len(candidates) else candidates[0][0]

    chosen_photo = await fetch_image_as_base64(chosen_url)
    if not (isinstance(chosen_photo, dict) and chosen_photo.get("data")):
        raise RuntimeError(f"generate_room_vision: failed to fetch chosen photo | url={chosen_url}")
    defurnished = await _defurnish_photo(
        room_id=str(room_id),
        room_name=room_name,
        photo=chosen_photo,
        call_gemini_image=call_gemini_image,
    )

    # Pro prompt generation (English list; image model prompt is wrapped).
    prompt, _pro_list = await _generate_prompt_for_photo(
        room_name=room_name,
        scope_text=scope_text,
        eli5_room=None,
        chosen_photo=defurnished,
        call_gemini=call_gemini,
    )

    # Phase 1: auto-consistency (best-effort, should not block generation).
    # If other rooms already have visions, run the style-consistency reviewer and patch this room's prompt list.
    try:
        recent_versions = await _get_latest_image_versions_for_listing(
            listing_id=int(listing_id),
            phone_number=phone,
            limit=200,
        )
        latest_by_room: Dict[str, Dict[str, Any]] = {}
        for row in recent_versions:
            rid = str(row.get("room_id") or "").strip()
            if not rid:
                continue
            # Rows are ordered newest-first; keep first.
            if rid not in latest_by_room:
                latest_by_room[rid] = row

        existing_room_ids = [rid for rid in latest_by_room.keys() if rid and rid != str(room_id)]
        if existing_room_ids:
            # Build lookups for nicer room_name labels.
            room_name_by_id: Dict[str, str] = {}
            try:
                for c in clusters or []:
                    if not isinstance(c, dict):
                        continue
                    cid = str(c.get("cluster_id") or "").strip()
                    rt = str(c.get("room_type") or "").strip()
                    if cid and rt:
                        room_name_by_id[cid] = rt
            except Exception:
                room_name_by_id = {}
            try:
                for r in (opinion.get("rooms") or []) if isinstance(opinion, dict) else []:
                    if not isinstance(r, dict):
                        continue
                    rid = str(r.get("room_id") or "").strip()
                    rt = str(r.get("room_type") or "").strip()
                    if rid and rt and rid not in room_name_by_id:
                        room_name_by_id[rid] = rt
            except Exception:
                pass

            rooms_for_review: List[Dict[str, Any]] = []
            # Existing rooms first (they define the style baseline).
            for rid in existing_room_ids[:8]:
                row = latest_by_room.get(rid) or {}
                prev_prompt = str(row.get("prompt_used") or "").strip()
                prev_list = _extract_pro_list_from_prompt(prev_prompt)
                if not prev_list:
                    continue
                slot_map = row.get("slot_decisions") if isinstance(row.get("slot_decisions"), dict) else {}
                visible, _unchanged = _extract_visible_changes({"slot_work_narratives": slot_map} if slot_map else {})
                rooms_for_review.append(
                    {
                        "room_id": rid,
                        "room_name": room_name_by_id.get(rid) or rid,
                        "eli5_tagline": "",
                        "visible_changes": visible or [],
                        "pro_list": prev_list,
                    }
                )

            # Add the new room as the last entry (patches target this prompt).
            visible_new, _unchanged_new = _extract_visible_changes({"slot_work_narratives": slot_decisions} if slot_decisions else {})
            rooms_for_review.append(
                {
                    "room_id": str(room_id),
                    "room_name": room_name_by_id.get(str(room_id)) or room_name,
                    "eli5_tagline": "",
                    "visible_changes": visible_new or [],
                    "pro_list": str(_pro_list or _extract_pro_list_from_prompt(prompt)),
                }
            )

            review = await _style_consistency_patch_instructions(
                listing_id=int(listing_id),
                rooms=rooms_for_review,
                call_gemini_json=call_gemini_json,
            )
            patches = review.get("patches") if isinstance(review, dict) else []
            patch_for_new = None
            if isinstance(patches, list):
                patch_for_new = next(
                    (p for p in patches if isinstance(p, dict) and str(p.get("room_id") or "") == str(room_id)),
                    None,
                )

            if patch_for_new:
                patched_list, applied = _apply_style_patch_to_pro_list(pro_list=str(_pro_list or ""), patch=patch_for_new)
                if applied > 0 and patched_list:
                    prompt = _IMAGE_GEN_PREAMBLE + patched_list + _IMAGE_GEN_POSTAMBLE
                    logger.info(
                        "Auto-consistency applied | listing_id=%s room_id=%s existing_rooms=%s patches=%d",
                        listing_id,
                        room_id,
                        ",".join(existing_room_ids[:8]),
                        applied,
                    )
    except Exception as exc:
        logger.warning(
            "generate_room_vision: auto-consistency failed (non-fatal) | listing_id=%s room_id=%s err=%s",
            listing_id,
            room_id,
            exc,
        )

    # Render (flash-image model alias is "pro-image" in our resolver).
    result = await call_gemini_image(
        prompt=prompt,
        image_data=defurnished["data"],
        image_mime_type=defurnished.get("mime_type") or "image/jpeg",
        model="pro-image",
        temperature=0.1,
        system_instruction=_IMAGE_SYSTEM_INSTRUCTION,
    )
    if not result.get("success") or not result.get("image_data"):
        raise RuntimeError(f"generate_room_vision: image render failed | err={result.get('error')}")

    latest = await _get_latest_image_version(listing_id=int(listing_id), room_id=str(room_id), phone_number=phone)
    next_version = int((latest or {}).get("version") or 0) + 1
    row = await _insert_image_version(
        listing_id=int(listing_id),
        room_id=str(room_id),
        version=next_version,
        phone_number=phone,
        slot_decisions=slot_decisions,
        prompt_used=prompt,
        user_input=user_ideas,
        defurnished_data=defurnished["data"],
        image_data=str(result["image_data"]),
    )

    # Persist decisions separately (for cost + future iterations).
    if phone:
        await _upsert_room_decisions(listing_id=int(listing_id), room_id=str(room_id), phone_number=str(phone), slot_decisions=slot_decisions)

    return {
        "ok": True,
        "listing_id": int(listing_id),
        "room_id": str(room_id),
        "version_id": row.get("id"),
        "version": next_version,
        "prompt_used": prompt,
        "image_data_base64": row.get("image_data"),
        "before_photo_url": chosen_url,
    }


@leo_tool(
    name="iterate_room_vision",
    description=(
        "Iterate a previously generated room vision by applying slot-level changes and re-rendering. "
        "Requires a previous version from generate_room_vision."
    ),
    requires=["listing_id", "has_any_vision"],
    params={
        "type": "object",
        "properties": {
            "room_id": {"type": "string", "description": "Exact room_id from ROOM_INVENTORY"},
            "version_id": {"type": "string", "description": "version_id returned by a previous generate_room_vision call"},
            "slot_changes": {"type": "string", "description": "JSON-encoded dict mapping slot names to new values, e.g. '{\"flooring\": \"oak parquet\", \"wall_color\": \"warm white\"}'"},
        },
    },
    required_params=["room_id", "version_id", "slot_changes"],
)
async def iterate_room_vision(
    *,
    listing_id: int,
    room_id: str,
    version_id: str,
    slot_changes: Dict[str, str],
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Iterate an existing vision by applying slot-level edits and re-rendering.

    "Edits, not rewrites": we keep the cached defurnished photo and we ask Pro to
    minimally adjust the prompt list to reflect the changed slots.
    """
    if not listing_id:
        raise ValueError("iterate_room_vision: missing listing_id")
    if not room_id:
        raise ValueError("iterate_room_vision: missing room_id")
    if not version_id:
        raise ValueError("iterate_room_vision: missing version_id")
    if not isinstance(slot_changes, dict) or not slot_changes:
        raise ValueError("iterate_room_vision: slot_changes must be a non-empty dict")

    prev = await _select_single(
        table="gla_image_versions",
        filters={"id": f"eq.{str(version_id)}"},
        select="id,listing_id,room_id,version,phone_number,slot_decisions,prompt_used,defurnished_data",
    )
    if not prev:
        raise RuntimeError(f"iterate_room_vision: version not found | version_id={version_id}")
    if int(prev.get("listing_id") or 0) != int(listing_id) or str(prev.get("room_id") or "") != str(room_id):
        raise RuntimeError("iterate_room_vision: version does not match listing_id/room_id")

    base_defurnished = prev.get("defurnished_data")
    if not isinstance(base_defurnished, str) or not base_defurnished.strip():
        raise RuntimeError("iterate_room_vision: missing cached defurnished_data")

    # Merge decisions (start from previous version's decisions).
    merged: Dict[str, Any] = dict(prev.get("slot_decisions") or {})
    for k, v in slot_changes.items():
        if not isinstance(k, str) or not k.strip():
            continue
        if not isinstance(v, str) or not v.strip():
            continue
        merged[k.strip()] = v.strip()

    # Update per-room decision store (best-effort consistency for costs, etc.)
    if phone:
        await _upsert_room_decisions(listing_id=int(listing_id), room_id=str(room_id), phone_number=str(phone), slot_decisions=merged)

    # Build updated scope text and do a minimal prompt update.
    scope_text = _build_scope_text({"slot_work_narratives": merged})
    prev_prompt = str(prev.get("prompt_used") or "").strip()
    prev_pro_list = _extract_pro_list_from_prompt(prev_prompt)

    patch_prompt = f"""
You previously wrote a numbered list of image-edit instructions for a room photo.
Now the user changed a few slot-level decisions. Your job is to UPDATE the numbered list
with MINIMAL edits. Keep the style, tone, and overall structure consistent.

WHY THIS MATTERS: If you rewrite everything, the outputs drift and feel inconsistent.

ROOM: {room_id}

PREVIOUS_LIST:
{prev_pro_list}

UPDATED_SCOPE (what should change / stay, derived from slot decisions):
{scope_text}

RULES:
- Output ONLY the updated numbered list (starting at 1.).
- Keep the last item as the geometry/camera rule (unchanged).
- Only change items that conflict with UPDATED_SCOPE.
""".strip()

    resp = await call_gemini(
        prompt=patch_prompt,
        model="pro",
        temperature=0.4,
        max_tokens=4000,
        use_spanish=False,
    )
    if not resp.success or not (resp.text or "").strip():
        raise RuntimeError(f"iterate_room_vision: prompt patch failed | err={resp.error}")

    new_pro_list = resp.text.strip()
    new_prompt = _IMAGE_GEN_PREAMBLE + new_pro_list + _IMAGE_GEN_POSTAMBLE

    render = await call_gemini_image(
        prompt=new_prompt,
        image_data=str(base_defurnished),
        image_mime_type="image/jpeg",
        model="pro-image",
        temperature=0.1,
        system_instruction=_IMAGE_SYSTEM_INSTRUCTION,
    )
    if not render.get("success") or not render.get("image_data"):
        raise RuntimeError(f"iterate_room_vision: image render failed | err={render.get('error')}")

    next_version = int(prev.get("version") or 0) + 1
    row = await _insert_image_version(
        listing_id=int(listing_id),
        room_id=str(room_id),
        version=next_version,
        phone_number=phone,
        slot_decisions=merged,
        prompt_used=new_prompt,
        user_input=None,
        defurnished_data=str(base_defurnished),
        image_data=str(render["image_data"]),
    )

    return {
        "ok": True,
        "listing_id": int(listing_id),
        "room_id": str(room_id),
        "previous_version_id": str(version_id),
        "version_id": row.get("id"),
        "version": next_version,
        "prompt_used": new_prompt,
        "image_data_base64": row.get("image_data"),
    }


@leo_tool(
    name="estimate_costs",
    description="Estimate renovation cost ranges per room (EUR low/high), based on GLA opinions + decisions + Smart M2.",
    requires=["listing_id", "gla_opinion", "smart_m2"],
    params={
        "type": "object",
        "properties": {
            "room_ids": {"type": "array", "items": {"type": "string"}},
        },
    },
    required_params=[],
)
async def estimate_costs(
    *,
    listing_id: int,
    room_ids: Optional[List[str]] = None,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimate per-room renovation costs (ranges) using one Pro call.

    No BCCA, no BOQ — this is a fast, honest advisor estimate with uncertainty.
    """
    if not listing_id:
        raise ValueError("estimate_costs: missing listing_id")

    listing = await database.get_listing(int(listing_id))
    if not listing:
        raise RuntimeError(f"estimate_costs: listing not found | listing_id={listing_id}")

    smart_m2 = await database.get_smart_m2(int(listing_id))
    if not smart_m2:
        raise RuntimeError(f"estimate_costs: missing smart_m2 | listing_id={listing_id}")

    opinion = await database.get_unified_estimate(int(listing_id), "gla_opinion")
    if not (isinstance(opinion, dict) and isinstance(opinion.get("rooms"), list)):
        raise RuntimeError(f"estimate_costs: missing gla_opinion | listing_id={listing_id}")

    rooms = [r for r in (opinion.get("rooms") or []) if isinstance(r, dict) and r.get("room_id")]
    if room_ids:
        want = {str(x) for x in room_ids if isinstance(x, str) and x.strip()}
        rooms = [r for r in rooms if str(r.get("room_id")) in want]
    if not rooms:
        raise RuntimeError("estimate_costs: no rooms to estimate")

    # Pull decisions (if present) for this phone/user — overrides opinion.
    decisions_by_room: Dict[str, Any] = {}
    if phone:
        for r in rooms:
            rid = str(r.get("room_id"))
            d = await _get_room_decisions(listing_id=int(listing_id), room_id=rid, phone_number=str(phone))
            if isinstance(d, dict) and isinstance(d.get("slot_decisions"), dict) and d.get("slot_decisions"):
                decisions_by_room[rid] = d["slot_decisions"]

    payload_for_llm: List[Dict[str, Any]] = []
    for r in rooms:
        rid = str(r.get("room_id"))
        payload_for_llm.append(
            {
                "room_id": rid,
                "room_type": str(r.get("room_type") or ""),
                "slot_opinion_narratives": r.get("slot_opinion_narratives") or {},
                "slot_decisions_override": decisions_by_room.get(rid) or {},
            }
        )

    prompt = f"""
You are an experienced renovation cost estimator in Spain.

Task: Estimate a realistic cost RANGE (low/high EUR) per room, based on:
- Leo's room slot opinions (what should/could be done)
- Optional user decisions overrides (if present)
- Smart M2 dimensions
- Listing context (city, type, year, etc.)

WHY THIS MATTERS: The user will use this to plan budget. Be honest about uncertainty.
Give ranges, not fake precision. If a room has mostly "no change", its cost should be low.

Return strict JSON:
{{
  "listing_id": <int>,
  "rooms": [
    {{"room_id": "string", "low_eur": <number>, "high_eur": <number>, "notes": "string"}}
  ],
  "total_low_eur": <number>,
  "total_high_eur": <number>
}}

LISTING:
{json.dumps({k: listing.get(k) for k in ["city","sqm","property_type","construction_year","price"] if k in listing}, ensure_ascii=False)}

SMART_M2:
{json.dumps(smart_m2, ensure_ascii=False)[:16000]}

ROOM_OPINIONS_AND_DECISIONS:
{json.dumps(payload_for_llm, ensure_ascii=False)[:16000]}
""".strip()

    schema = {
        "type": "object",
        "properties": {
            "listing_id": {"type": "integer"},
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "low_eur": {"type": "number"},
                        "high_eur": {"type": "number"},
                        "notes": {"type": "string"},
                    },
                    "required": ["room_id", "low_eur", "high_eur", "notes"],
                },
            },
            "total_low_eur": {"type": "number"},
            "total_high_eur": {"type": "number"},
        },
        "required": ["listing_id", "rooms", "total_low_eur", "total_high_eur"],
    }

    resp = await call_gemini(
        prompt=prompt,
        model="pro",
        temperature=0.2,
        max_tokens=8000,
        response_schema=schema,
        use_spanish=False,
    )
    if not resp.success or not (resp.text or "").strip():
        raise RuntimeError(f"estimate_costs: gemini failed | err={resp.error}")

    try:
        out = json.loads(resp.text)
    except Exception as exc:
        raise RuntimeError(f"estimate_costs: JSON parse failed | err={exc} raw={resp.text[:800]}") from exc

    # Persist per-room ranges for this phone/user.
    if phone and isinstance(out, dict) and isinstance(out.get("rooms"), list):
        for r in out.get("rooms") or []:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("room_id") or "").strip()
            if not rid:
                continue
            low = r.get("low_eur")
            high = r.get("high_eur")
            try:
                low_f = float(low)
                high_f = float(high)
            except Exception:
                continue
            await _upsert_room_decisions(
                listing_id=int(listing_id),
                room_id=rid,
                phone_number=str(phone),
                cost_range_low=low_f,
                cost_range_high=high_f,
            )

    return {"ok": True, "estimate": out}


@leo_tool(
    name="send_room_photos",
    description=(
        "Send the clustered room photos to the user via WhatsApp so they can see what you are referencing. "
        "IMPORTANT: room_id MUST be an exact value from ROOM_INVENTORY."
    ),
    requires=["listing_id", "clusters"],
    params={
        "type": "object",
        "properties": {
            "room_id": {"type": "string", "description": "Exact room_id from ROOM_INVENTORY"},
        },
    },
    required_params=["room_id"],
)
async def send_room_photos(
    *,
    listing_id: int,
    room_id: str,
    phone: str,
) -> Dict[str, Any]:
    """Send room photo URLs to WhatsApp as media messages."""
    if not phone:
        raise ValueError("send_room_photos: missing phone")
    if not listing_id:
        raise ValueError("send_room_photos: missing listing_id")
    if not room_id:
        raise ValueError("send_room_photos: missing room_id")

    clusters = await database.get_photo_clusters(int(listing_id))
    cluster = next((c for c in (clusters or []) if str(c.get("cluster_id") or "") == str(room_id)), None)
    urls = [u for u in ((cluster or {}).get("photo_urls") or []) if isinstance(u, str) and u.strip()]
    if not urls:
        raise RuntimeError(f"send_room_photos: no urls | listing_id={listing_id} room_id={room_id}")

    caption = f"Fotos de {room_id} (para que veas lo que estoy viendo):"
    # WhatsApp reliability: limit media count per message.
    chunk_size = 5
    sent = 0
    for i in range(0, len(urls), chunk_size):
        send_media(str(phone), caption if i == 0 else "", urls[i:i + chunk_size])
        sent += len(urls[i:i + chunk_size])

    return {"ok": True, "sent": sent, "room_id": str(room_id)}


@leo_tool(
    name="style_consistency_check",
    description=(
        "Review multiple room prompts and return patch instructions to keep style consistent across rooms. "
        "All room_ids MUST be exact values from ROOM_INVENTORY."
    ),
    requires=["listing_id", "has_any_vision"],
    params={
        "type": "object",
        "properties": {
            "room_ids": {"type": "array", "items": {"type": "string"}, "description": "Array of exact room_ids from ROOM_INVENTORY"},
        },
    },
    required_params=["room_ids"],
)
async def style_consistency_check(
    *,
    listing_id: int,
    room_ids: List[str],
) -> Dict[str, Any]:
    """
    Review prompts across rooms and return patch instructions for consistency.

    This does not mutate stored prompts; it returns patches the agent can apply
    via iteration (or by generating new versions).
    """
    if not listing_id:
        raise ValueError("style_consistency_check: missing listing_id")
    room_ids_clean = [str(r).strip() for r in (room_ids or []) if isinstance(r, str) and str(r).strip()]
    if len(room_ids_clean) < 2:
        return {"ok": True, "patches": [], "note": "need at least 2 rooms for consistency check"}

    opinion = await database.get_unified_estimate(int(listing_id), "gla_opinion")
    rooms_op = (opinion or {}).get("rooms") if isinstance(opinion, dict) else None
    if not isinstance(rooms_op, list):
        raise RuntimeError("style_consistency_check: missing gla_opinion.rooms")
    opinion_by_room = {str(r.get("room_id")): r for r in rooms_op if isinstance(r, dict) and r.get("room_id")}

    # Load latest prompt per room (any phone_number).
    rooms_for_review: List[Dict[str, Any]] = []
    for rid in room_ids_clean:
        latest = await _get_latest_image_version(listing_id=int(listing_id), room_id=rid, phone_number=None)
        if not latest or not (latest.get("prompt_used") or "").strip():
            continue
        op_room = opinion_by_room.get(rid) or {}
        slot_map = (op_room.get("slot_opinion_narratives") or {}) if isinstance(op_room, dict) else {}
        visible, _unchanged = _extract_visible_changes({"slot_work_narratives": slot_map} if isinstance(slot_map, dict) else {})

        pro_list = _extract_pro_list_from_prompt(str(latest.get("prompt_used") or ""))
        rooms_for_review.append(
            {
                "room_id": rid,
                "room_name": str((op_room or {}).get("room_type") or rid),
                "eli5_tagline": "",
                "visible_changes": visible,
                "pro_list": pro_list,
            }
        )

    if len(rooms_for_review) < 2:
        return {"ok": True, "patches": [], "note": "not enough rooms with prompts"}

    review = await _style_consistency_patch_instructions(
        listing_id=int(listing_id),
        rooms=rooms_for_review,
        call_gemini_json=call_gemini_json,
    )
    return {"ok": True, **(review or {"patches": []})}


@leo_tool(
    name="get_room_analysis",
    description=(
        "Fetch all analysis artifacts for a room (PIR, opinion, decisions, Smart M2, photo URLs, latest image version). "
        "IMPORTANT: room_id MUST be an exact value from ROOM_INVENTORY."
    ),
    requires=["listing_id"],
    params={
        "type": "object",
        "properties": {
            "room_id": {"type": "string", "description": "Exact room_id from ROOM_INVENTORY"},
        },
    },
    required_params=["room_id"],
)
async def get_room_analysis(
    *,
    listing_id: int,
    room_id: str,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure data retrieval for the agent (no side effects)."""
    if not listing_id:
        raise ValueError("get_room_analysis: missing listing_id")
    if not room_id:
        raise ValueError("get_room_analysis: missing room_id")

    pir = await database.get_unified_estimate(int(listing_id), "v5_pir_target")
    opinion = await database.get_unified_estimate(int(listing_id), "gla_opinion")
    clusters = await database.get_photo_clusters(int(listing_id))
    smart_m2 = await database.get_smart_m2(int(listing_id))

    cluster = next((c for c in (clusters or []) if str(c.get("cluster_id") or "") == str(room_id)), None)
    room_pir = None
    if isinstance(pir, dict):
        room_pir = next((r for r in (pir.get("rooms") or []) if isinstance(r, dict) and str(r.get("room_id") or "") == str(room_id)), None)
    room_op = None
    if isinstance(opinion, dict):
        room_op = next((r for r in (opinion.get("rooms") or []) if isinstance(r, dict) and str(r.get("room_id") or "") == str(room_id)), None)

    decisions = None
    if phone:
        decisions = await _get_room_decisions(listing_id=int(listing_id), room_id=str(room_id), phone_number=str(phone))

    latest_img = await _get_latest_image_version(listing_id=int(listing_id), room_id=str(room_id), phone_number=phone)

    return {
        "ok": True,
        "listing_id": int(listing_id),
        "room_id": str(room_id),
        "cluster": cluster,
        "pir": room_pir,
        "opinion": room_op,
        "smart_m2": smart_m2,
        "decisions": decisions,
        "latest_image_version": {k: latest_img.get(k) for k in ["id", "version", "prompt_used", "created_at"]} if isinstance(latest_img, dict) else None,
    }


@leo_tool(
    name="save_memory",
    description="Save a stable user preference/fact to memory (budget band, style, hates marble, etc.).",
    requires=[],
    params={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "content": {"type": "string"},
        },
    },
    required_params=["key", "content"],
)
async def save_memory(
    *,
    key: str,
    content: str,
    phone: str,
    listing_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Save a user preference/fact to whatsapp_user_profiles.memory_summary.
    """
    if not phone:
        raise ValueError("save_memory: missing phone")
    k = str(key or "").strip()
    c = str(content or "").strip()
    if not k or not c:
        raise ValueError("save_memory: key/content required")

    profile = await _select_single(
        table="whatsapp_user_profiles",
        filters={"phone_number": f"eq.{str(phone)}"},
        select="phone_number,memory_summary",
    )
    existing = str((profile or {}).get("memory_summary") or "").strip()
    line = f"- {k}: {c}"
    next_mem = (existing + "\n" + line).strip() if existing else line
    # Basic safety: keep memory compact.
    next_mem = next_mem[:1200]

    if profile and profile.get("phone_number"):
        ok = await _patch_rows(
            table="whatsapp_user_profiles",
            filters={"phone_number": f"eq.{str(phone)}"},
            payload={"memory_summary": next_mem},
        )
        if not ok:
            raise RuntimeError("save_memory: failed to patch whatsapp_user_profiles")
    else:
        await _insert_row(
            table="whatsapp_user_profiles",
            payload={"phone_number": str(phone), "memory_summary": next_mem, "last_listing_id": int(listing_id) if listing_id else None},
        )

    return {"ok": True, "saved": line}


@leo_tool(
    name="recall_memory",
    description="Recall previously saved user memory relevant to the current conversation.",
    requires=[],
    params={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
    },
    required_params=["query"],
)
async def recall_memory(
    *,
    query: str,
    phone: str,
) -> Dict[str, Any]:
    """Return the stored memory summary (best-effort simple retrieval)."""
    if not phone:
        raise ValueError("recall_memory: missing phone")
    q = str(query or "").strip().lower()
    profile = await _select_single(
        table="whatsapp_user_profiles",
        filters={"phone_number": f"eq.{str(phone)}"},
        select="phone_number,memory_summary",
    )
    mem = str((profile or {}).get("memory_summary") or "").strip()
    if not mem:
        return {"ok": True, "memory": "", "matches": []}

    matches: List[str] = []
    if q:
        for line in mem.splitlines():
            if q in line.lower():
                matches.append(line.strip())

    return {"ok": True, "memory": mem, "matches": matches}


# ---------------------------------------------------------------------------
# Gemini tool declarations
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS: List[Dict[str, Any]] = get_tool_declarations(
    capabilities=[
        "listing_id",
        "clusters",
        "gla_opinion",
        "smart_m2",
        "has_any_vision",
        "can_generate_vision",
    ]
)

TOOL_CONFIG: Dict[str, Any] = {
    "function_calling_config": {"mode": "AUTO"},
}

