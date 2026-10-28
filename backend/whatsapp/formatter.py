"""
WhatsApp Message Formatter
===========================

Reads V5 pipeline outputs (ELI5, BOQ aggregation, generated images) from
unified_estimates and formats them into WhatsApp-friendly messages.

WHY THIS MATTERS: WhatsApp has a ~4096 character limit per message and
users want a scannable summary, not a wall of text. This module produces
a concise, well-structured summary plus image URLs that Twilio can fetch.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FormattedResult:
    """Complete formatted output ready for WhatsApp delivery."""
    summary_text: str           # Main text message (~500-1500 chars)
    image_urls: List[str]       # Publicly-accessible URLs for after-images
    image_captions: List[str]   # One caption per image
    error: Optional[str] = None


def format_pipeline_results(
    listing_id: int,
    eli5: Optional[Dict[str, Any]],
    boq_agg: Optional[Dict[str, Any]],
    generated_images: Optional[Dict[str, Any]],
    listing: Optional[Dict[str, Any]],
    public_base_url: str,
) -> FormattedResult:
    """
    Format V5 pipeline results into WhatsApp messages.

    Args:
        listing_id:       The listing ID
        eli5:             v5_eli5_market_standard from unified_estimates
        boq_agg:          v2_market_standard from unified_estimates
        generated_images: v5_generated_images_market_standard from unified_estimates
        listing:          Raw listing data (for address, price, etc.)
        public_base_url:  Public URL base for image serving (e.g. https://abc123.ngrok.io)

    Returns:
        FormattedResult with summary text and image URLs
    """
    if not eli5 and not boq_agg:
        return FormattedResult(
            summary_text="Sorry, the analysis did not produce results for this listing. Please try again.",
            image_urls=[],
            image_captions=[],
            error="no_data",
        )

    # ── Extract key numbers ───────────────────────────────────────────────
    prop_summary = (eli5 or {}).get("property_summary", {})
    concept = (eli5 or {}).get("concept", {})
    timeline = (eli5 or {}).get("timeline", {})
    rooms = (eli5 or {}).get("rooms", [])

    address = prop_summary.get("address") or _listing_address(listing) or f"Listing {listing_id}"
    total_cost = float(prop_summary.get("total_cost") or (boq_agg or {}).get("grand_total_with_iva") or 0)
    total_weeks = int(timeline.get("total_weeks") or prop_summary.get("total_weeks") or 0)
    asking_price = float((listing or {}).get("price_eur") or (listing or {}).get("price") or 0)

    intro_before = concept.get("intro_before", "")
    intro_after = concept.get("intro_after", "")

    # ── Build summary text ────────────────────────────────────────────────
    lines = []
    lines.append(f"*Renovation estimate for {address}*")
    lines.append("")

    if intro_before and intro_after:
        lines.append(f"Before: {intro_before}")
        lines.append(f"After: {intro_after}")
        lines.append("")

    # Cost headline
    lines.append(f"*Total cost: EUR {total_cost:,.0f}* (incl. IVA)")
    if total_weeks:
        lines.append(f"Timeline: ~{total_weeks} weeks")

    # Value uplift estimate (rough: renovation should add ~1.5x its cost)
    if asking_price > 0 and total_cost > 0:
        estimated_after_value = asking_price + (total_cost * 1.5)
        uplift_pct = ((estimated_after_value - asking_price) / asking_price) * 100
        lines.append(
            f"Estimated value uplift: +{uplift_pct:.0f}% "
            f"(from EUR {asking_price:,.0f} to ~EUR {estimated_after_value:,.0f})"
        )

    lines.append("")

    # Room breakdown
    if rooms:
        lines.append("*Key work:*")
        for room in rooms[:6]:  # Cap at 6 rooms for readability
            room_name = room.get("room_name", "Room")
            cost = float(room.get("cost") or 0)
            tagline = room.get("tagline", "")

            # Truncate tagline for WhatsApp readability
            if len(tagline) > 100:
                tagline = tagline[:97] + "..."

            lines.append(f"- *{room_name}* (EUR {cost:,.0f}): {tagline}")

        if len(rooms) > 6:
            lines.append(f"  ... and {len(rooms) - 6} more rooms")

        lines.append("")

    # Timeline summary
    timeline_summary = timeline.get("summary", "")
    if timeline_summary:
        lines.append(f"*Timeline:* {timeline_summary}")
        lines.append("")

    summary_text = "\n".join(lines).strip()

    # ── Image URLs ────────────────────────────────────────────────────────
    image_urls: List[str] = []
    image_captions: List[str] = []

    if generated_images and isinstance(generated_images, dict):
        images = generated_images.get("generated_images") or []
        for idx, img in enumerate(images):
            if not isinstance(img, dict):
                continue
            # Only include images that were successfully generated
            if not img.get("after_data"):
                continue

            # Build URL to the image-serving endpoint
            url = f"{public_base_url.rstrip('/')}/api/listings/{listing_id}/generated-images/{idx}"
            image_urls.append(url)

            room_name = img.get("room_name") or img.get("room_id") or f"Room {idx + 1}"
            image_captions.append(f"After: {room_name}")

            # Cap at 4 images (WhatsApp best practice)
            if len(image_urls) >= 4:
                break

    return FormattedResult(
        summary_text=summary_text,
        image_urls=image_urls,
        image_captions=image_captions,
    )


def _listing_address(listing: Optional[Dict[str, Any]]) -> Optional[str]:
    """Best-effort address extraction from listing data."""
    if not listing:
        return None
    return (
        listing.get("title")
        or listing.get("address")
        or listing.get("city")
        or None
    )
