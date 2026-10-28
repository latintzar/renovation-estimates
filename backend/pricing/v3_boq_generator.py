import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple, DefaultDict
from collections import defaultdict

from .quantity_resolver import resolve_quantity_ref
from .bcca_embedding_matcher import BccaEmbeddingMatcher

logger = logging.getLogger(__name__)


def _extract_cost_components(worklist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts worklist payloads with either:
    - { room_blocks: [ { room_id, cost_components: [...] } ] }
    - { worklist_items: [ { bcca_description, unit, rooms: [ {room_id, quantity_ref}, ... ] } ] }
    - { cost_components: [...] }
    """
    if not worklist or not isinstance(worklist, dict):
        raise RuntimeError("v3_boq_generator: invalid worklist payload")

    if "room_blocks" in worklist:
        blocks = worklist.get("room_blocks") or []
        if not isinstance(blocks, list):
            raise RuntimeError("v3_boq_generator: room_blocks must be a list")
        items: List[Dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            for item in block.get("cost_components") or []:
                if isinstance(item, dict):
                    items.append(item)
        return items

    if "worklist_items" in worklist:
        worklist_items = worklist.get("worklist_items") or []
        if not isinstance(worklist_items, list):
            raise RuntimeError("v3_boq_generator: worklist_items must be a list")
        items: List[Dict[str, Any]] = []
        for wi in worklist_items:
            if not isinstance(wi, dict):
                continue
            rooms = wi.get("rooms") or []
            if not isinstance(rooms, list):
                continue
            for r in rooms:
                if not isinstance(r, dict):
                    continue
                items.append(
                    {
                        "room_id": r.get("room_id"),
                        "quantity_ref": r.get("quantity_ref"),
                        "unit": wi.get("unit"),
                        "bcca_description": wi.get("bcca_description"),
                        # preserve dimension if present, else caller can override later
                        "dimension": wi.get("dimension"),
                    }
                )
        return items

    items = worklist.get("cost_components") or []
    if not isinstance(items, list):
        raise RuntimeError("v3_boq_generator: cost_components must be a list")
    return [i for i in items if isinstance(i, dict)]


def _require_fields(item: Dict[str, Any], required: Iterable[str]) -> None:
    for key in required:
        if item.get(key) in (None, "", []):
            raise RuntimeError(f"v3_boq_generator: missing required field | key={key} | item={item}")


async def generate_boq_v3(
    *,
    listing_id: int,
    strategy_name: str,
    worklist_payload: Dict[str, Any],
    db: Any,
    matcher: BccaEmbeddingMatcher,
    embed_text_fn: Optional[Any] = None,
    embed_texts_fn: Optional[Any] = None,
) -> int:
    """
    Deterministic BOQ generation from a BCCA worklist.
    This function does NOT call LLMs. It expects:
    - Smart M2 data present in DB
    - Worklist with quantity_ref per item
    - Embedding matcher + embedding function (Vertex) for BCCA lookup
    """
    if embed_text_fn is None:
        raise RuntimeError("v3_boq_generator: embed_text_fn is required (no LLM calls, but embeddings are needed)")

    smart_m2 = await db.get_smart_m2(listing_id)
    if smart_m2 is None:
        raise RuntimeError(f"v3_boq_generator: missing Smart M2 | listing_id={listing_id}")
    rooms = smart_m2.get("rooms") or []

    items = _extract_cost_components(worklist_payload)
    if not items:
        raise RuntimeError(f"v3_boq_generator: empty worklist | listing_id={listing_id} strategy={strategy_name}")

    rows: List[Dict[str, Any]] = []
    # Embed unique descriptions (much cheaper + deterministic) then reuse per item.
    desc_to_embedding: Dict[str, Any] = {}
    unique_desc = []
    for item in items:
        desc = (item.get("bcca_description") or "").strip()
        if desc and desc not in desc_to_embedding:
            desc_to_embedding[desc] = None
            unique_desc.append(desc)

    # Embed in bulk when possible (much cheaper than per-item calls).
    if callable(embed_texts_fn):
        embs = embed_texts_fn(unique_desc)
        for d, e in zip(unique_desc, embs):
            desc_to_embedding[d] = e
    else:
        for d in unique_desc:
            e = embed_text_fn(d)
            if hasattr(e, "__await__"):
                e = await e
            desc_to_embedding[d] = e

    for item in items:
        _require_fields(item, ["room_id", "bcca_description", "quantity_ref", "unit"])

        qty, qty_prov = resolve_quantity_ref(item["quantity_ref"], rooms)
        description = item["bcca_description"]
        unit = item["unit"]

        query_embedding = desc_to_embedding.get(description)
        if query_embedding is None:
            query_embedding = embed_text_fn(description)
            if hasattr(query_embedding, "__await__"):
                query_embedding = await query_embedding

        matches = matcher.match(query_embedding, unit=unit, top_k=5, min_similarity=0.45)
        best_score, best = matches[0]

        unit_price = float(best.get("price") or 0)
        line_total = qty * unit_price
        hours_per_unit = best.get("labor_hours_per_unit")
        labor_hours = None
        if hours_per_unit is not None:
            try:
                labor_hours = float(hours_per_unit) * float(qty)
            except Exception:
                labor_hours = None

        rows.append(
            {
                "listing_id": listing_id,
                "strategy_name": strategy_name,
                "dimension": item.get("dimension") or "v3",
                "room_name": item.get("room_name") or item.get("room_id"),
                "scope_item_element": item.get("element") or item.get("scope_item_element"),
                "bcca_code": best.get("code"),
                "description": best.get("description") or description,
                "quantity": qty,
                "unit": unit,
                "unit_price": unit_price,
                "line_total": line_total,
                "labor_hours": labor_hours,
                "quantity_reasoning": item.get("quantity_reasoning"),
                "room_id": item.get("room_id"),
                "wall_id": item.get("wall_id"),
                "opening_id": item.get("opening_id"),
                "quantity_ref": item.get("quantity_ref"),
                "quantity_rule_id": item.get("quantity_rule_id"),
                "item_kind": item.get("item_kind"),
                "embedding_similarity": best_score,
                "embedding_top_k": [
                    {"score": float(score), "code": m.get("code"), "unit": m.get("unit")} for score, m in matches
                ],
                "provenance": {
                    "quantity": qty_prov,
                    "worklist_item": item,
                },
            }
        )

    # Persist in batches *per room_name* to preserve per-room granularity.
    # WHY: database.py de-dupes within a batch on (listing_id, strategy_name, dimension, room_name, bcca_code, description).
    # If we write everything with room_name="all", we incorrectly merge identical work across different rooms.
    rows_by_room: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        rn = str(r.get("room_name") or r.get("room_id") or "unknown").strip() or "unknown"
        rows_by_room[rn].append(r)

    saved_total = 0
    for room_name, room_rows in rows_by_room.items():
        saved = await db.save_boq_line_items_batch(
            listing_id=listing_id,
            strategy_name=strategy_name,
            dimension="v3",
            room_name=room_name,
            items=room_rows,
        )
        saved_total += int(saved)

    return int(saved_total)
