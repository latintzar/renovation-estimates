"""
Gemini Tour Generator
=====================

Uses Gemini to analyze Street View panoramas
and generate cinematic tour sequences with friendly captions.
"""

import os
import json
import logging
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Gemini config - Use Google AI Studio key
GEMINI_MODEL = "gemini-2.5-flash"  # Fast + reliable for tour generation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)


@dataclass
class TourAction:
    """A single action in the tour sequence."""
    heading: float
    pitch: float
    fov: float
    duration: float
    caption: Optional[str] = None


@dataclass
class TourSequence:
    """Complete tour sequence for a location."""
    pano_id: str
    location_type: str
    total_duration: float
    actions: List[TourAction]


class TourGenerator:
    """Generates cinematic tours using Gemini vision."""
    
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
    
    async def generate_tour(
        self,
        panorama_image: bytes,
        location_type: str,
        location_name: str,
        property_heading: float = 0,
        pano_id: str = "",
        place_info: Optional[Dict[str, Any]] = None,
        distance_meters: Optional[float] = None,
        walking_minutes: Optional[float] = None,
    ) -> TourSequence:
        """Generate a tour sequence for a panorama."""
        
        # Build context
        spot_context = f"This is {location_name}"
        if location_type != "property":
            spot_context += f", a {location_type}"
            if distance_meters:
                spot_context += f" ({int(distance_meters)}m"
                if walking_minutes:
                    spot_context += f", {walking_minutes:.0f} min walk"
                spot_context += " from the property)"
        
        # Build prompt
        prompt = f"""You are creating a cinematic Street View tour.

Context: {spot_context}

Your Role: Like a friend showing someone around. Calm, observational, NOT sell-y.

Panorama: 360° equirectangular. Heading 0°=front, 90°=right, 180°=back.

Requirements:
1. Start with an establishing shot
2. Point out 2-3 interesting things
3. End looking toward heading {int(property_heading or 0)}°
4. Total duration: 6-10 seconds
5. Captions: 5-12 words, factual observations

Output JSON only:
{{"actions": [{{"heading": 45, "pitch": 5, "fov": 80, "duration": 2.0, "caption": "Wide street"}}]}}"""
        
        # Encode image
        image_b64 = base64.b64encode(panorama_image).decode("utf-8")
        
        try:
            response = self.model.generate_content([
                {"mime_type": "image/png", "data": image_b64},
                prompt
            ])
            
            actions = self._parse_response(response.text, property_heading)
            total_duration = sum(a.duration for a in actions)
            
            return TourSequence(
                pano_id=pano_id,
                location_type=location_type,
                total_duration=total_duration,
                actions=actions
            )
            
        except Exception as e:
            logger.error(f"Gemini tour generation failed: {e}")
            raise  # No fallback - Gemini only!
    
    def _parse_response(self, response_text: str, fallback_heading: float) -> List[TourAction]:
        """Parse Gemini's JSON response into TourActions."""
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            data = json.loads(text)
            actions = []
            
            for action_data in data.get("actions", []):
                actions.append(TourAction(
                    heading=float(action_data.get("heading", 0)),
                    pitch=float(action_data.get("pitch", 0)),
                    fov=float(action_data.get("fov", 75)),
                    duration=float(action_data.get("duration", 2.0)),
                    caption=action_data.get("caption"),
                ))
            
            if not actions:
                return self._fallback_actions(fallback_heading)
            
            return actions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return self._fallback_actions(fallback_heading)
    
    def _fallback_actions(self, property_heading: float) -> List[TourAction]:
        """Generate fallback tour actions."""
        return [
            TourAction(heading=0, pitch=5, fov=85, duration=2.0, caption="Looking around..."),
            TourAction(heading=90, pitch=0, fov=75, duration=2.0, caption="To the right..."),
            TourAction(heading=180, pitch=0, fov=75, duration=2.0, caption="Behind us..."),
            TourAction(heading=property_heading, pitch=0, fov=70, duration=2.0, caption="Back this way"),
        ]
    
    def _fallback_tour(self, pano_id: str, location_type: str, property_heading: float) -> TourSequence:
        """Generate a complete fallback tour."""
        actions = self._fallback_actions(property_heading)
        return TourSequence(
            pano_id=pano_id,
            location_type=location_type,
            total_duration=sum(a.duration for a in actions),
            actions=actions
        )
    
    def sequence_to_dict(self, sequence: TourSequence) -> Dict[str, Any]:
        """Convert TourSequence to dict for JSON storage."""
        return {
            "pano_id": sequence.pano_id,
            "location_type": sequence.location_type,
            "total_duration": sequence.total_duration,
            "actions": [asdict(a) for a in sequence.actions]
        }
    
    def dict_to_sequence(self, data: Dict[str, Any]) -> TourSequence:
        """Convert dict back to TourSequence."""
        actions = [TourAction(**action_data) for action_data in data.get("actions", [])]
        return TourSequence(
            pano_id=data.get("pano_id", ""),
            location_type=data.get("location_type", "unknown"),
            total_duration=data.get("total_duration", 0),
            actions=actions
        )
