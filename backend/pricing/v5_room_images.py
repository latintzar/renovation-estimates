"""
V5 Room Images — before/after renovation renderings
====================================================

Generates before/after room images for the frontend BeforeAfterSlider.

The images are the visual version of the BOQ — editing the ORIGINAL photos
to show the renovation work. This proves it's legit: same room, same angle,
specific changes applied. No fantasy renders.

The delta narratives were generated from examining these same photos (via PIR).
Each narrative describes specific work on a specific element. This step
visualizes those narratives on the actual photos.

Pro gets:
  - ALL room photos (to understand the full space)
  - Delta narratives filtered to visible changes (specific materials/finishes)
  - ELI5 tagline + packages (what the buyer reads alongside the image)

Pro's job: look at the photo, understand what each element IS (wall vs railing,
door vs archway), apply each delta change to the correct element, clean the
room up, and leave everything else untouched.

Three-step process per room:
1. Flash picks the best photo (cheap)
2. Defurnish the chosen photo (remove clutter/furniture)
3. Pro sees the defurnished photo + delta + ELI5 → writes an editing prompt
4. Flash-image edits the defurnished photo

Cost: ~$0.02 pro prompt gen + ~$0.04 flash-image = ~$0.06 per room.

Input:  photo_clusters, BOQ aggregation, ELI5 summary, delta_slots
Output: v5_generated_images_market_standard (saved to unified_estimates)
"""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

CONCURRENCY = 10

# ── Slot → visual category mapping ──────────────────────────────────────
# Filters delta narratives to only the ones that produce VISIBLE changes.
# Invisible work (plumbing, electrical, waterproofing) maps to None.

_VISUAL_MAP = {
    "finishes.flooring": "flooring",
    "finishes.wall_finish": "walls",
    "finishes.wall_tiling": "walls",
    "finishes.ceiling_finish": "ceiling",
    "finishes.skirting": "flooring",
    "finishes.waterproofing": None,
    "finishes.joints_grout": None,
    "joinery.kitchen_cabinetry": "kitchen",
    "joinery.kitchen_worktops_splashback": "kitchen",
    "joinery.kitchen_appliance_integration": "kitchen",
    "joinery.bathroom_vanity": "bathroom_fixtures",
    "joinery.bath_vanity_storage": "bathroom_fixtures",
    "joinery.wardrobes": "furniture",
    "joinery.wardrobes_builtins": "furniture",
    "details.taps_mixers": "fixtures",
    "details.door_hardware": "fixtures",
    "details.electrical_trim": None,
    "details.sanitaryware": "bathroom_fixtures",
    "details.sanitary_fixtures": "bathroom_fixtures",
    "details.bathing_units": "bathroom_fixtures",
    "enclosure.windows": "windows",
    "enclosure.internal_doors": "doors",
    "enclosure.balcony_doors": "doors",
    "enclosure.shutters_blinds": "windows",
    "enclosure.sealing_air_tightness": None,
    "mep.lighting_points": "lighting",
    "mep.sockets_switches": None,
    "mep.electrical_circuits": None,
    "mep.plumbing_supply": None,
    "mep.plumbing_drain": None,
    "mep.gas_supply": None,
    "mep.hvac_terminals": "climate",
    "mep.hot_water_generator": None,
    "mep.ventilation_extraction": "kitchen",
    "mep.heating_emitters_controls": "climate",
    "shell.masonry_chases": None,
    "shell.openings_changes": None,
}

# Short labels for the "what stays" list
_CATEGORY_LABELS = {
    "flooring": "Flooring",
    "walls": "Walls",
    "ceiling": "Ceiling",
    "kitchen": "Kitchen",
    "bathroom_fixtures": "Bathroom fixtures",
    "fixtures": "Hardware & fittings",
    "furniture": "Built-in furniture",
    "windows": "Windows & shutters",
    "doors": "Doors",
    "lighting": "Lighting",
    "climate": "Climate units",
}

_ALL_VISUAL_CATEGORIES = list(_CATEGORY_LABELS.keys())


def _extract_visible_changes(
    delta_room: Optional[Dict[str, Any]],
) -> tuple[List[str], List[str]]:
    """
    From a delta room's slot_work_narratives, extract two lists:
      - visible_changes: the actual narrative texts for slots that produce
        visible changes (flooring, walls, kitchen, etc.)
      - unchanged_categories: category labels for things NOT changing

    The narratives are passed through as-is from the delta. They contain
    the specific materials and specs — that's the whole point.
    """
    if not delta_room or not isinstance(delta_room, dict):
        raise RuntimeError(
            "_extract_visible_changes: delta_room is missing or invalid. "
            "Cannot generate image without delta data."
        )

    narratives = delta_room.get("slot_work_narratives") or {}
    if not isinstance(narratives, dict):
        raise RuntimeError(
            f"_extract_visible_changes: slot_work_narratives is not a dict. "
            f"Got: {type(narratives).__name__}"
        )

    # Which categories have visible changes?
    changed_cats: set[str] = set()
    visible_lines: List[str] = []

    for slot_key, val in narratives.items():
        # Skip "no change" entries
        if isinstance(val, str):
            if val.strip().lower() in ("no change", "no_change", "sin cambio", "sin_cambio", ""):
                continue
            text = val.strip()
        elif isinstance(val, dict):
            action = str(val.get("action") or "").lower()
            if action in ("no_change", "no change", "sin_cambio", "sin cambio", ""):
                continue
            text = (val.get("narrative") or val.get("description") or "").strip()
        else:
            continue

        if not text:
            continue

        cat = _VISUAL_MAP.get(slot_key)
        if cat is None:
            continue  # invisible work

        changed_cats.add(cat)
        visible_lines.append(text)

    # What stays?
    unchanged = [
        _CATEGORY_LABELS[c] for c in _ALL_VISUAL_CATEGORIES
        if c not in changed_cats
    ]

    return visible_lines, unchanged


def _build_scope_text(
    delta_room: Optional[Dict[str, Any]],
) -> str:
    """
    Build the scope text directly from delta narratives.

    This is the data Pro uses to write the editing prompt. It contains:
    1. The visible change narratives (passed through from delta as-is)
    2. What stays unchanged (so Pro knows to leave those alone)

    No summaries, no budget tiers, no scale labels. Just the delta.
    """
    visible, unchanged = _extract_visible_changes(delta_room)

    parts: List[str] = []

    if not visible:
        return ""

    parts.append("What changes (from renovation scope):")
    for line in visible:
        parts.append(f"  - {line}")

    if unchanged:
        parts.append("")
        parts.append("What stays as-is:")
        for label in unchanged:
            parts.append(f"  - {label}")

    return "\n".join(parts)


# ── System instruction for the image model ───────────────────────────────
# This is the behavioral frame — geometry preservation rules that apply to
# every single image edit. Lives in systemInstruction, not the user prompt.

_IMAGE_SYSTEM_INSTRUCTION = (
    "You are an image editing model performing inpainting on room photos. "
    "You will receive a photo of a room and instructions to change specific "
    "surfaces and objects. Your job is to edit the photo IN PLACE.\n\n"
    "ABSOLUTE RULES:\n"
    "- Every wall edge, corner, door frame, window frame, and ceiling line "
    "must remain at the EXACT same pixel position as the input photo.\n"
    "- Do not zoom out, zoom in, or change the field of view.\n"
    "- Do not change the camera angle or perspective — this is the most important rule.\n"
    "- Do not change the room's proportions or dimensions.\n"
    "- Only change the APPEARANCE of surfaces — colors, textures, materials.\n"
    "- The output image must overlay perfectly on the input image with all "
    "structural edges aligned."
)

# ── User-prompt wrappers for every image-gen call ────────────────────────
# Keep these short — the geometry rules are in the system instruction now.

_IMAGE_GEN_PREAMBLE = (
    "Edit this photo. Change only the following:\n\n"
)

_IMAGE_GEN_POSTAMBLE = (
    "\n\nKeep everything else exactly as it is. "
    "Careful not to remove, nor move, doors and windows unless explicitly told to do so, "
    "since any of the renovation work being done would be to the materials/condition "
    "of those elements but unlikely to require removing them unless otherwise stated above. "
    "One photorealistic image, no text."
)

_DEFURNISH_PROMPT = (
    "Defurnish this room photo.\n\n"
    "Remove ALL movable items and clutter:\n"
    "- furniture (beds, sofas, chairs, tables), rugs, curtains/blinds, decor\n"
    "- personal items, bags, boxes, trash, cables\n"
    "- small appliances and countertop clutter\n"
    "- loose textiles (towels, bedding), random objects\n\n"
    "Leave ONLY the fixed structure:\n"
    "- walls, floor, ceiling, doors, windows, built-in cabinetry\n"
    "- radiators / fixed HVAC units, fixed lighting fixtures\n\n"
    "ABSOLUTE RULES:\n"
    "- Do NOT change materials, colors, or finishes.\n"
    "- Do NOT repaint, re-tile, or install new surfaces.\n"
    "- Do NOT change camera angle, zoom, or geometry.\n"
    "- Keep every wall edge/corner/window/door frame at the exact same pixel position.\n"
    "- Output one photorealistic image, no text."
)


async def _defurnish_photo(
    *,
    image: Dict[str, str],
    call_gemini_image: Any,
    room_id: str,
    room_name: str,
) -> Dict[str, str]:
    """
    Remove furniture/clutter from the chosen photo.

    WHY: Renovation edits look much cleaner when we first remove movable items.
    This step is strictly "cleanup/defurnish" — no renovation styling.
    """
    logger.info("v5_room_images: [defurnish] %s (%s)...", room_id, room_name)
    result = None
    for attempt in range(2):
        result = await call_gemini_image(
            prompt=_DEFURNISH_PROMPT,
            image_data=image["data"],
            image_mime_type=image.get("mime_type", "image/jpeg"),
            model="pro-image",
            temperature=0.1,
            system_instruction=_IMAGE_SYSTEM_INSTRUCTION,
        )
        if result.get("success") and result.get("image_data"):
            logger.info("v5_room_images: [defurnish] OK %s", room_id)
            return {"mime_type": "image/jpeg", "data": result["image_data"]}
        err = (result or {}).get("error", "unknown error")
        logger.warning("v5_room_images: [defurnish] retry %s (%s)", room_id, err)
        await asyncio.sleep(1)

    err = (result or {}).get("error", "unknown error")
    raise RuntimeError(f"v5_room_images: defurnish failed | room_id={room_id} | err={err}")


async def _pick_best_photo(
    *,
    room_name: str,
    photo_images: List[Dict[str, str]],
    call_gemini_json: Any,
) -> int:
    """
    Flash picks the best photo for editing. Cheap and fast.
    Returns 0-indexed photo index.
    """
    n = len(photo_images)
    if n <= 1:
        return 0

    result = await call_gemini_json(
        prompt=(
            f"You have {n} photos of a **{room_name}** (numbered 1 to {n}). "
            f"Pick the ONE photo that shows the most of the room with a clear, "
            f"straight-on angle and good lighting. Avoid extreme angles, "
            f"close-ups, or very dark photos. Return just the number."
        ),
        model="flash",
        temperature=0.3,
        images=photo_images,
        response_schema={
            "type": "integer",
            "description": "1-indexed number of the best photo",
        },
    )

    if isinstance(result, int) and 1 <= result <= n:
        return result - 1
    logger.warning("_pick_best_photo: bad result=%s, defaulting to 0", result)
    return 0


async def _generate_prompt_for_photo(
    *,
    room_name: str,
    scope_text: str,
    eli5_room: Optional[Dict[str, Any]],
    chosen_photo: Dict[str, str],
    call_gemini: Any,
) -> tuple[str, str]:
    """
    Pro sees the SINGLE photo that will be edited + delta scope + ELI5 context
    → writes inpainting instructions.

    Pro only sees the exact photo the image model will edit. This keeps its
    reasoning focused on what's actually in frame — no distraction from other
    angles of the same room.
    """

    # ── Build the ELI5 section (what the buyer reads) ─────────────────────
    eli5_section = ""
    if eli5_room and isinstance(eli5_room, dict):
        tagline = eli5_room.get("tagline") or ""
        packages = eli5_room.get("packages") or []
        pkg_lines = []
        for pkg in packages:
            if isinstance(pkg, dict) and pkg.get("name"):
                cost = pkg.get("cost", 0)
                pkg_lines.append(f"  • {pkg['name']} — EUR {cost:,.0f}")
        if tagline or pkg_lines:
            eli5_section = f"║ Tagline: {tagline}\n"
            if pkg_lines:
                eli5_section += "║ Packages:\n" + "\n".join(pkg_lines)

    # ── Assemble the structured prompt ────────────────────────────────────
    meta_prompt = (
        f"You are a renovation architect looking at this photo of a **{room_name}** "
        f"that is about to be renovated. This is the exact photo that will be "
        f"edited — study it carefully.\n\n"
        f"Your job: write a numbered list of specific changes to make to this "
        f"photo so it shows the room after renovation. Be vivid — describe "
        f"textures, colors, and finishes in detail so an image model can render "
        f"them accurately. Also explicitly note any structural elements "
        f"(railings, beams, archways) that must stay untouched.\n\n"
    )

    if eli5_section:
        meta_prompt += (
            f"╔══ WHAT THE BUYER READS ══════════════════════════════════════\n"
            f"{eli5_section}\n"
            f"╚═════════════════════════════════════════════════════════════\n"
            f"The buyer sees this text alongside your image. The image must\n"
            f"match what they read.\n\n"
        )

    meta_prompt += (
        f"╔══ RENOVATION SCOPE (from delta analysis) ════════════════════\n"
        f"║ These narratives were generated by examining these exact\n"
        f"║ photos. Each one describes specific work on a specific\n"
        f"║ element — a wall, a floor, a fixture. Not everything.\n"
        f"╠════════════════════════════════════════════════════════════════\n"
        f"{scope_text}\n"
        f"╚═════════════════════════════════════════════════════════════\n\n"
        f"╔══ HOW TO THINK ABOUT THIS ═══════════════════════════════════\n"
        f"║\n"
        f"║ 1. INVENTORY the photo. Look at it carefully and mentally\n"
        f"║    list EVERY visible element: walls, floor, ceiling, doors,\n"
        f"║    windows, railings, beams, fixtures, lamps, pipes, switches,\n"
        f"║    stains, clutter, furniture — everything you can see.\n"
        f"║\n"
        f"║ 2. MATCH each element to the scope. For each thing in your\n"
        f"║    inventory, ask: does the scope say to change it? If yes,\n"
        f"║    write a change instruction with the specific materials\n"
        f"║    and finishes from the narrative. \"Pintar paramentos\n"
        f"║    verticales\" means paint the solid walls — NOT a railing,\n"
        f"║    NOT an opening, NOT a beam. Apply each change to the\n"
        f"║    RIGHT element.\n"
        f"║\n"
        f"║ 3. UNDERSTAND HOW THE IMAGE MODEL READS YOUR WORDS.\n"
        f"║    You're writing for a model that edits photos. It has\n"
        f"║    quirks you need to work around:\n"
        f"║\n"
        f"║    • SURFACES: It's lazy about texture. If you write\n"
        f"║      \"paint white,\" it overlays thin white on the existing\n"
        f"║      rough texture and the old surface bleeds through.\n"
        f"║      We've seen galería walls with heavy stucco where\n"
        f"║      \"paint smooth white\" left the bumps fully visible.\n"
        f"║      What works: describe the END STATE vividly — the\n"
        f"║      smoothness, the uniformity, the absence of what was\n"
        f"║      there before. The worse the surface, the more vivid.\n"
        f"║\n"
        f"║    • LIKE-FOR-LIKE REPLACEMENTS MUST LOOK DIFFERENT.\n"
        f"║      If the scope implies tile→tile, paint→paint, or similar\n"
        f"║      category replacements, do NOT be subtle. Specify a deliberate\n"
        f"║      new tone/color/format that will read as a clear change vs the\n"
        f"║      original photo (while staying faithful to the scope intent).\n"
        f"║      WHY THIS MATTERS: the before/after slider loses credibility if\n"
        f"║      finishes look almost identical.\n"
        f"║\n"
        f"║    • GEOMETRY: It tends to enlarge rooms, zoom out, and\n"
        f"║      shift walls when it reads spatial language. Words like\n"
        f"║      \"spacious,\" \"open,\" \"extending,\" \"airy\" make it\n"
        f"║      redraw the room larger. Even \"floor extending to all\n"
        f"║      edges\" can trigger this. Stick to describing WHAT\n"
        f"║      each surface looks like, never how the room feels.\n"
        f"║      This matters enormously — the output goes into a\n"
        f"║      before/after slider and if corners don't align\n"
        f"║      pixel-for-pixel, the whole tool loses credibility.\n"
        f"║\n"
        f"║    • STRUCTURAL ELEMENTS: It fills in gaps. If you change\n"
        f"║      a wall next to a railing without mentioning the\n"
        f"║      railing, it replaces the railing with more wall.\n"
        f"║      We've seen this happen with a galería railing that\n"
        f"║      became a solid wall. Anything structural that ISN'T\n"
        f"║      changing needs an explicit \"keep\" item.\n"
        f"║\n"
        f"║ 4. CLEAN UP with common sense. A renovation leaves the\n"
        f"║    room move-in ready. Ask yourself for each element you\n"
        f"║    see: would this survive a renovation? Old dusty lamp\n"
        f"║    above a newly tiled bathroom? No — swap it for\n"
        f"║    something clean and modern. Stained ceiling above\n"
        f"║    fresh white walls? Obviously repaint it. Yellowed\n"
        f"║    sockets next to new skirting? Replace them. Every\n"
        f"║    element should look like it belongs in the same era\n"
        f"║    as the renovation work.\n"
        f"║\n"
        f"║ 5. SECOND LOOK. Review your list against the photo one\n"
        f"║    more time. Imagine walking into this room after all\n"
        f"║    your changes. Scan left to right, floor to ceiling.\n"
        f"║    Does anything still look old, dirty, or forgotten?\n"
        f"║    A dirty patch on a wall you didn't mention? A grimy\n"
        f"║    fixture you skipped? Add items until the renovation\n"
        f"║    looks COMPLETE — not half-finished.\n"
        f"║\n"
        f"║ 6. STYLE COHERENCE ACROSS ROOMS.\n"
        f"║    The home must feel like ONE coherent renovation, not a collage.\n"
        f"║    Keep a consistent design language across rooms (floor tone,\n"
        f"║    wall finish family, metal finishes, wood tone, lighting temperature)\n"
        f"║    as implied by the scope. Do NOT invent a different style.\n"
        f"║\n"
        f"║    If the scope implies a REPLACEMENT of a visible element (for example\n"
        f"║    windows/frames, doors, shutters/blinds, radiators/AC units, fixtures),\n"
        f"║    pick a clearly different but well-suited color/material for that\n"
        f"║    element so the change is obvious in the after image. The choice must\n"
        f"║    remain faithful to the renovation intent described in the scope.\n"
        f"║\n"
        f"╚═════════════════════════════════════════════════════════════\n\n"
        f"╔══ OUTPUT FORMAT ═════════════════════════════════════════════\n"
        f"║ Write a numbered list of changes to make to THIS photo.\n"
        f"║ Each item: \"Change [element you see] to [rich description].\"\n"
        f"║\n"
        f"║ Be DESCRIPTIVE — textures, colors, finishes, quality.\n"
        f"║ The image model needs vivid detail to render correctly.\n"
        f"║\n"
        f"║ GOOD example:\n"
        f"║   1. Replace the old speckled terrazzo floor with smooth,\n"
        f"║      continuous grey microcement — matte finish, no joints,\n"
        f"║      flowing seamlessly to every wall edge.\n"
        f"║   2. Paint all walls smooth bright white, removing every\n"
        f"║      stain, crack, and rough patch — pristine, even finish.\n"
        f"║   3. The metal railing along the right side stays exactly\n"
        f"║      as it is — do not cover, fill in, or replace it.\n"
        f"║\n"
        f"║ BAD example (scene description — causes room distortion):\n"
        f"║   \"A modern room with grey floors and white walls.\"\n"
        f"║\n"
        f"║ Rules:\n"
        f"║ - Each change targets ONE element visible in the photo\n"
        f"║ - Use specific materials/colors/textures from the scope\n"
        f"║ - IMPORTANT: if a structural element (railing, beam, arch,\n"
        f"║   opening, column) sits NEAR something you're changing,\n"
        f"║   add an explicit item saying it stays unchanged. The image\n"
        f"║   model will fill it in or cover it otherwise.\n"
        f"║ - Your LAST numbered item must ALWAYS be:\n"
        f"║   \"Keep the camera position, zoom level, and all wall,\n"
        f"║   corner, ceiling, and floor edge positions identical to\n"
        f"║   the original photo.\"\n"
        f"╚═════════════════════════════════════════════════════════════"
    )

    response = await call_gemini(
        prompt=meta_prompt,
        model="pro",
        temperature=0.7,
        images=[chosen_photo],
        use_spanish=False,
    )

    if not response.success or not response.text or not response.text.strip():
        raise RuntimeError(
            f"_generate_prompt_for_photo: Pro returned empty result "
            f"for {room_name}. response={response!r}"
        )

    pro_list = response.text.strip()
    final_prompt = _IMAGE_GEN_PREAMBLE + pro_list + _IMAGE_GEN_POSTAMBLE
    return final_prompt, pro_list


def _parse_numbered_list_items(text: str) -> List[str]:
    """
    Parse a simple "1. ... 2. ..." list into item strings.
    If parsing fails, return the whole text as a single item.
    """
    import re

    if not text or not text.strip():
        return []

    # Split on "N." at line starts.
    chunks = re.split(r"(?m)^\s*\d+\.\s+", text.strip())
    chunks = [c.strip() for c in chunks if c.strip()]
    if not chunks:
        return [text.strip()]
    return chunks


def _render_numbered_list_items(items: List[str]) -> str:
    return "\n".join([f"{i+1}. {t.strip()}" for i, t in enumerate(items) if t.strip()])


async def _style_consistency_patch_instructions(
    *,
    listing_id: int,
    rooms: List[Dict[str, Any]],
    call_gemini_json: Any,
) -> Dict[str, Any]:
    """
    Single Pro call that reviews per-room prompt lists and returns PATCH instructions.

    Hard requirement: this must be best-effort and never block image generation.
    It must NEVER raise. If the LLM fails or returns invalid output, return an empty patch set.
    """
    if not rooms:
        return {"patches": []}

    # Keep context compact: send only the numbered list (not the full wrapper prompt).
    room_blocks: List[str] = []
    for r in rooms:
        room_blocks.append(
            "\n".join(
                [
                    f"ROOM_ID: {r.get('room_id')}",
                    f"ROOM_NAME: {r.get('room_name')}",
                    f"ELI5_TAGLINE: {str(r.get('eli5_tagline') or '').strip()}",
                    "DELTA_VISIBLE_CHANGES:",
                    *(f"- {x}" for x in (r.get("visible_changes") or [])),
                    "CURRENT_PROMPT_LIST:",
                    str(r.get("pro_list") or "").strip(),
                ]
            )
        )

    reviewer_prompt = (
        "You are reviewing renovation image-edit prompts for multiple rooms of ONE home.\n\n"
        "Goal: enforce cross-room stylistic consistency so the after-images look like a single coherent renovation.\n"
        "You must be faithful to the intent in DELTA_VISIBLE_CHANGES. Do not contradict delta.\n\n"
        "You will receive, for each room:\n"
        "- DELTA_VISIBLE_CHANGES (the renovation intent)\n"
        "- CURRENT_PROMPT_LIST (a numbered list of edits)\n\n"
        "Task:\n"
        "- Identify stylistic inconsistencies across rooms (floor tone/material family, wall finish family, metal finishes,\n"
        "  wood tone, lighting temperature, window/door frame finish language).\n"
        "- When delta implies a finish replacement within the same category (tile→tile, paint→paint), make sure the prompt\n"
        "  language is explicit enough that the after image will read as a clear change (tone/color/format/pattern), while\n"
        "  staying faithful to DELTA_VISIBLE_CHANGES. Do not invent beyond delta — only add minimal specificity that is\n"
        "  already implied by delta words (e.g., 'tonos tierra', 'beige y marrón', 'aluminio blanco', 'madera oscura').\n"
        "- Output PATCH instructions that are surgical: change as little as possible.\n"
        "- Do not rewrite whole prompts. Only specify exact item replacements or insertions.\n"
        "- The last item about keeping camera/geometry must remain as the last item.\n"
        "- Consider what materials make sense in different rooms, from the materials that are mentioned in the prompts already — "
        "for example, unlikely that hardwood would make sense in a bathroom unless specifically stated.\n\n"
        "Output strict JSON with this shape:\n"
        "{\n"
        '  "patches": [\n'
        "    {\n"
        '      "room_id": "string",\n'
        '      "replace_items": [{"item_index": 1, "text": "..." }],\n'
        '      "insert_items_before_last": ["...", "..."]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- item_index is 1-based.\n"
        "- replace_items must only touch items that create inconsistency; keep everything else.\n"
        "- insert_items_before_last is for global coherence reminders that need to appear in that room.\n\n"
        "ROOMS:\n"
        + "\n\n---\n\n".join(room_blocks)
    )

    # Single Pro call (as requested). This must never block the pipeline.
    try:
        result = await call_gemini_json(
            prompt=reviewer_prompt,
            model="pro",
            temperature=0.2,
            # Give it plenty of output budget without going unbounded.
            max_tokens=16384,
            response_schema={
                "type": "object",
                "properties": {
                    "patches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "room_id": {"type": "string"},
                                "replace_items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "item_index": {"type": "integer"},
                                            "text": {"type": "string"},
                                        },
                                        "required": ["item_index", "text"],
                                    },
                                },
                                "insert_items_before_last": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["room_id", "replace_items", "insert_items_before_last"],
                        },
                    }
                },
                "required": ["patches"],
            },
        )
        if isinstance(result, dict) and isinstance(result.get("patches"), list):
            return result
    except Exception as e:
        logger.warning(
            "v5_room_images: style consistency reviewer failed (non-blocking) | listing_id=%s | err=%s",
            listing_id,
            e,
        )

    return {"patches": []}


async def generate_v5_room_images(
    *,
    listing_id: int,
    strategy_name: str,
    photo_clusters: List[Dict[str, Any]],
    boq_aggregation: Dict[str, Any],
    eli5: Optional[Dict[str, Any]],
    delta_slots: Optional[Dict[str, Any]],
    db: Any,
    call_gemini_image: Any,
    call_gemini_json: Any,
    call_gemini: Any,
) -> Dict[str, Any]:
    """
    Generate before/after room images for the frontend carousel.

    Picks the top rooms by BOQ cost, builds transformation prompts from
    V5 data, and calls gemini-2.5-flash-image for each.

    Returns the images dict and saves to unified_estimates.
    """
    line_items = boq_aggregation.get("line_items") or []
    if not line_items:
        raise RuntimeError(f"v5_room_images: no line items | listing_id={listing_id}")

    if not photo_clusters:
        raise RuntimeError(f"v5_room_images: no photo_clusters | listing_id={listing_id}")

    # ── Group data by room ────────────────────────────────────────────────────
    # BOQ items by room
    boq_by_room: Dict[str, List[Dict[str, Any]]] = {}
    room_costs: Dict[str, float] = {}
    for item in line_items:
        rid = str(item.get("room_id") or item.get("room_name") or "general").strip()
        boq_by_room.setdefault(rid, []).append(item)
        room_costs[rid] = room_costs.get(rid, 0) + float(item.get("line_total") or 0)

    # ELI5 rooms by room_id
    eli5_by_room: Dict[str, Dict[str, Any]] = {}
    if eli5 and isinstance(eli5, dict):
        for room in eli5.get("rooms") or []:
            if isinstance(room, dict):
                rid = str(room.get("room_id") or "").strip()
                if rid:
                    eli5_by_room[rid] = room

    # Delta rooms by room_id
    delta_by_room: Dict[str, Dict[str, Any]] = {}
    if delta_slots and isinstance(delta_slots, dict):
        for room in delta_slots.get("rooms") or []:
            if isinstance(room, dict):
                rid = str(room.get("room_id") or "").strip()
                if rid:
                    delta_by_room[rid] = room

    # Photo clusters by cluster_id → ALL photo URLs per room
    photos_by_room: Dict[str, Dict[str, Any]] = {}
    for cluster in photo_clusters:
        if not isinstance(cluster, dict):
            continue
        cid = str(cluster.get("cluster_id") or "").strip()
        rt = str(cluster.get("room_type") or "").strip()
        urls = [u for u in (cluster.get("photo_urls") or []) if isinstance(u, str) and u.strip()]
        if not cid or not urls:
            continue
        # Skip non-room clusters
        if rt in ("floorplan", "street_view", "views_outlook", "exterior", "building"):
            continue
        photos_by_room[cid] = {
            "room_id": cid,
            "room_type": rt,
            "photo_url": urls[0],       # Primary photo (the one we edit)
            "all_urls": urls,            # All photos of this room (for reference)
        }

    # ── Select rooms (must have photos and delta, sorted by BOQ cost) ───────
    eligible = [
        rid for rid, _ in sorted(room_costs.items(), key=lambda x: -x[1])
        if rid in photos_by_room and rid not in ("general", "shared")
    ]

    if not eligible:
        logger.warning("v5_room_images: no eligible rooms with photos | listing_id=%s", listing_id)
        return {"generated_images": [], "images_generated": 0, "images_failed": 0}

    logger.info(
        "v5_room_images: generating %d images | listing_id=%s | rooms=%s",
        len(eligible), listing_id, eligible,
    )

    # ── Generate images (concurrent, semaphore-limited) ─────────────────────
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _prepare_one(rid: str) -> Dict[str, Any]:
        """Pick photo → defurnish → pro prompt (no image edit yet)."""
        photo_info = photos_by_room[rid]
        all_urls = photo_info.get("all_urls") or [photo_info["photo_url"]]
        room_type = photo_info["room_type"]
        eli5_room = eli5_by_room.get(rid)
        delta_room = delta_by_room.get(rid)

        room_name = (eli5_room or {}).get("room_name") or room_type or rid

        if not delta_room:
            logger.info(
                "v5_room_images: [skip] %s (%s) — no delta data, skipping image generation",
                rid, room_name,
            )
            return {
                "room_id": rid, "room_name": room_name,
                "before_url": (photo_info.get("all_urls") or [photo_info["photo_url"]])[0],
                "after_data": None,
                "skipped": True,
                "error": f"No delta data for room {rid} ({room_name})",
            }

        scope_text = _build_scope_text(delta_room)
        visible, unchanged = _extract_visible_changes(delta_room)

        logger.info(
            "v5_room_images: [scope] %s (%s) | visible_changes=%d | unchanged=%d",
            rid, room_name, len(visible), len(unchanged),
        )

        if not visible:
            logger.info(
                "v5_room_images: [skip] %s (%s) — no visible changes (only non-visual work like plumbing/electrical), skipping image generation",
                rid, room_name,
            )
            return {
                "room_id": rid, "room_name": room_name,
                "before_url": (photo_info.get("all_urls") or [photo_info["photo_url"]])[0],
                "after_data": None,
                "skipped": True,
                "error": f"No visible changes for room {rid} ({room_name}) — only non-visual work",
            }

        async with sem:
            # ── Fetch ALL photos for this room ────────────────────────────────
            all_images: List[Dict[str, str]] = []
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    for url in all_urls:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            logger.warning("v5_room_images: HTTP %d fetching %s", resp.status_code, url[:60])
                            continue
                        all_images.append({
                            "data": base64.b64encode(resp.content).decode(),
                            "mime_type": resp.headers.get("content-type", "image/jpeg"),
                        })
            except Exception as e:
                logger.error("v5_room_images: failed to fetch photos for %s: %s", rid, e)
                return {
                    "room_id": rid, "room_name": room_name,
                    "before_url": all_urls[0], "after_data": None,
                    "error": f"Failed to fetch photos: {e}",
                }

            if not all_images:
                return {
                    "room_id": rid, "room_name": room_name,
                    "before_url": all_urls[0], "after_data": None,
                    "error": "All photo fetches failed",
                }

            # ── Step 1: Flash picks the best photo (cheap) ───────────────────
            best_idx = 0
            if len(all_images) > 1:
                try:
                    best_idx = await _pick_best_photo(
                        room_name=room_name,
                        photo_images=all_images,
                        call_gemini_json=call_gemini_json,
                    )
                    logger.info("v5_room_images: [pick] %s → photo %d/%d", rid, best_idx + 1, len(all_images))
                except Exception as e:
                    logger.warning("v5_room_images: [pick] FAIL %s: %s — using first", rid, e)

            chosen_image = all_images[best_idx]
            chosen_url = all_urls[best_idx] if best_idx < len(all_urls) else all_urls[0]

            # ── Step 2: Defurnish chosen photo ───────────────────────────────
            try:
                defurnished_image = await _defurnish_photo(
                    image=chosen_image,
                    call_gemini_image=call_gemini_image,
                    room_id=rid,
                    room_name=room_name,
                )
            except Exception as e:
                logger.error("v5_room_images: [defurnish] FAIL %s (%s): %s", rid, room_name, e)
                return {
                    "room_id": rid,
                    "room_name": room_name,
                    "before_url": chosen_url,
                    "after_data": None,
                    "error": str(e),
                }

            # NOTE: prompt generation is a distinct progress step; do it after all defurnish is done.
            return {
                "room_id": rid,
                "room_name": room_name,
                "room_type": room_type,
                "before_url": chosen_url,
                "before_data": chosen_image["data"],
                "defurnished_image": defurnished_image,
                # Context for prompt generation (next phase)
                "scope_text": scope_text,
                "eli5_room": eli5_room,
                "delta_room": delta_room,
                # Context for style consistency reviewer
                "visible_changes": visible,
                "eli5_tagline": ((eli5_room or {}).get("tagline") or "").strip(),
            }

    async def _render_one(prep: Dict[str, Any]) -> Dict[str, Any]:
        """Flash-image edits the defurnished photo using (possibly patched) prompt."""
        rid = prep["room_id"]
        room_name = prep["room_name"]
        prompt = prep["prompt"]
        defurnished_image = prep["defurnished_image"]

        logger.info("v5_room_images: [image-gen] %s (%s)...", rid, room_name)
        try:
            result = None
            for attempt in range(2):
                result = await call_gemini_image(
                    prompt=prompt,
                    image_data=defurnished_image["data"],
                    image_mime_type=defurnished_image["mime_type"],
                    model="pro-image",
                    temperature=0.1,
                    system_instruction=_IMAGE_SYSTEM_INSTRUCTION,
                )
                if result.get("success") and result.get("image_data"):
                    break
                error_msg = result.get("error", "")
                if "text instead of image" in error_msg and attempt == 0:
                    logger.warning("v5_room_images: retry %s (got text, retrying)...", rid)
                    await asyncio.sleep(1)
                else:
                    break

            if result and result.get("success") and result.get("image_data"):
                logger.info("v5_room_images: OK %s (%s)", rid, room_name)
                return {
                    "room_id": rid,
                    "room_name": room_name,
                    "before_url": prep.get("before_url"),
                    "before_data": prep.get("before_data"),
                    "defurnished_data": defurnished_image["data"],
                    "after_data": result["image_data"],
                    "transformation_prompt": prompt,
                }
            else:
                error = (result or {}).get("error", "unknown error")
                logger.error("v5_room_images: FAIL %s: %s", rid, error)
                return {
                    "room_id": rid,
                    "room_name": room_name,
                    "before_url": prep.get("before_url"),
                    "after_data": None,
                    "error": error,
                }
        except Exception as e:
            logger.error("v5_room_images: exception for %s: %s", rid, e)
            return {
                "room_id": rid,
                "room_name": room_name,
                "before_url": prep.get("before_url"),
                "after_data": None,
                "error": str(e),
            }

    async def _save_progress_artifact(key: str, payload: Dict[str, Any]) -> None:
        """
        Best-effort progress artifact save for status tracking.

        WHY THIS MATTERS:
        This job contains multiple internal phases (defurnish, prompt-gen,
        style consistency, image generation). Persisting small checkpoint artifacts lets
        admin + reno tab show them as distinct progress steps.
        """
        try:
            ok = await db.save_unified_estimate(listing_id, key, payload)
            if not ok:
                logger.warning("v5_room_images: progress artifact save returned false | key=%s listing_id=%s", key, listing_id)
        except Exception as exc:
            logger.warning(
                "v5_room_images: progress artifact save failed (non-fatal) | key=%s listing_id=%s | %s: %s",
                key,
                listing_id,
                type(exc).__name__,
                exc,
            )

    async def _prompt_gen_one(prep: Dict[str, Any]) -> Dict[str, Any]:
        """Pro sees defurnished photo + delta scope (+ ELI5) → writes a prompt list."""
        rid = str(prep.get("room_id") or "").strip()
        room_name = str(prep.get("room_name") or "").strip()
        defurnished_image = prep.get("defurnished_image")
        if not rid or not isinstance(defurnished_image, dict) or not defurnished_image.get("data"):
            return prep

        logger.info("v5_room_images: [prompt-gen] %s (%s)", rid, room_name)
        prompt, pro_list = await _generate_prompt_for_photo(
            room_name=room_name,
            scope_text=str(prep.get("scope_text") or "").strip(),
            eli5_room=prep.get("eli5_room"),
            chosen_photo=defurnished_image,
            call_gemini=call_gemini,
        )
        prep["prompt"] = prompt
        prep["pro_list"] = pro_list
        logger.info("v5_room_images: [prompt-gen] OK %s → %d chars", rid, len(prompt))
        return prep

    # Phase A1: pick best photo + defurnish for all rooms.
    defurnished = await asyncio.gather(*[_prepare_one(rid) for rid in eligible])
    await _save_progress_artifact(
        f"v5_room_images_defurnish_{strategy_name}",
        {
            "listing_id": int(listing_id),
            "strategy_name": str(strategy_name),
            "schema_version": "v5_room_images_defurnish_v1",
            "created_at": datetime.utcnow().isoformat(),
            "counts": {
                "rooms_total": len(eligible),
                "rooms_ok": sum(1 for r in defurnished if isinstance(r, dict) and r.get("defurnished_image")),
                "rooms_failed": sum(1 for r in defurnished if isinstance(r, dict) and r.get("error")),
            },
            "room_ids": list(eligible),
        },
    )

    # Phase A2: prompt generation for all rooms (uses defurnished photos).
    prepared = await asyncio.gather(*[_prompt_gen_one(r) for r in defurnished if isinstance(r, dict)])
    await _save_progress_artifact(
        f"v5_room_images_prompt_generation_{strategy_name}",
        {
            "listing_id": int(listing_id),
            "strategy_name": str(strategy_name),
            "schema_version": "v5_room_images_prompt_gen_v1",
            "created_at": datetime.utcnow().isoformat(),
            "counts": {
                "rooms_total": len(eligible),
                "rooms_with_prompts": sum(1 for r in prepared if isinstance(r, dict) and r.get("prompt") and r.get("pro_list")),
            },
            "room_ids": list(eligible),
        },
    )

    # Phase B: single Pro consistency reviewer → apply surgical patches to per-room prompt lists.
    style_success = False
    style_error: Optional[str] = None
    style_patches: List[Dict[str, Any]] = []
    try:
        good_rooms = [r for r in prepared if isinstance(r, dict) and r.get("prompt") and r.get("pro_list")]
        review = await _style_consistency_patch_instructions(
            listing_id=listing_id,
            rooms=good_rooms,
            call_gemini_json=call_gemini_json,
        )
        style_patches = [p for p in (review.get("patches") or []) if isinstance(p, dict)]
        style_success = True
        patch_map: Dict[str, Dict[str, Any]] = {}
        for p in (review.get("patches") or []):
            if isinstance(p, dict) and p.get("room_id"):
                patch_map[str(p["room_id"])] = p

        for r in good_rooms:
            rid = str(r.get("room_id"))
            patch = patch_map.get(rid) or {}
            replace_items = patch.get("replace_items") or []
            insert_items = patch.get("insert_items_before_last") or []
            if not replace_items and not insert_items:
                continue

            items = _parse_numbered_list_items(str(r.get("pro_list") or ""))
            if not items:
                continue

            # Preserve the last geometry item as last.
            last = items[-1]
            body = items[:-1]

            # Replace requested items (1-based indices over full list including last).
            for ri in replace_items:
                if not isinstance(ri, dict):
                    continue
                idx = int(ri.get("item_index") or 0)
                txt = str(ri.get("text") or "").strip()
                if idx <= 0 or not txt:
                    continue
                # If it targets the last item, ignore (must remain).
                if idx == len(items):
                    continue
                # Apply to body index (0-based).
                if 1 <= idx <= len(body):
                    body[idx - 1] = txt

            # Insert new coherence items right before last.
            for t in insert_items:
                if isinstance(t, str) and t.strip():
                    body.append(t.strip())

            new_list = _render_numbered_list_items(body + [last])
            r["pro_list"] = new_list
            r["prompt"] = _IMAGE_GEN_PREAMBLE + new_list + _IMAGE_GEN_POSTAMBLE

            logger.info("v5_room_images: [style] patched prompt list | listing_id=%s | room_id=%s", listing_id, rid)
    except Exception as e:
        style_success = False
        style_error = f"{type(e).__name__}: {e}"
        logger.warning("v5_room_images: style consistency pass failed (non-blocking) | listing_id=%s | err=%s", listing_id, e)

    await _save_progress_artifact(
        f"v5_room_images_style_consistency_{strategy_name}",
        {
            "listing_id": int(listing_id),
            "strategy_name": str(strategy_name),
            "schema_version": "v5_room_images_style_consistency_v1",
            "created_at": datetime.utcnow().isoformat(),
            "success": bool(style_success),
            "error": style_error,
            "counts": {
                "rooms_reviewed": sum(1 for r in prepared if isinstance(r, dict) and r.get("prompt") and r.get("pro_list")),
                "patch_rooms": len([p for p in style_patches if p.get("room_id")]),
                "patches_total": len(style_patches),
            },
            "patches": style_patches,
        },
    )

    # Phase C: render images using (possibly patched) prompts.
    generated_images = await asyncio.gather(*[_render_one(r) for r in prepared if isinstance(r, dict) and r.get("prompt")])
    images_ok = sum(1 for r in generated_images if r.get("after_data"))
    images_fail = len(generated_images) - images_ok

    # ── Save ──────────────────────────────────────────────────────────────────
    output = {
        "generated_images": generated_images,
        "images_generated": images_ok,
        "images_failed": images_fail,
        "schema_version": "v5_generated_images_v1",
    }

    img_key = f"v5_generated_images_{strategy_name}"
    ok = await db.save_unified_estimate(listing_id, img_key, output)
    if not ok:
        raise RuntimeError(f"v5_room_images: save failed | key={img_key} listing_id={listing_id}")

    logger.info(
        "v5_room_images: done | listing_id=%s | ok=%d fail=%d",
        listing_id, images_ok, images_fail,
    )
    return output
