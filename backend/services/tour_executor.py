"""
Tour Executor - Baked-in Cinematic Behaviors
============================================

Converts Gemini's tile-based tour sequences into executable keyframes
with cinematic polish: sway, shake, arc, easing, timing.

Gemini says: "focus on x3_y1", "sweep from x2 to x5"
Executor outputs: Smooth keyframe animations with natural camera feel

Output format is compatible with:
- Custom panorama viewer (preferred)
- Google Street View Dynamic (if needed)
"""

import math
import random
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Tile grid configuration (Zoom Level 3)
TILES_HORIZONTAL = 8
TILES_VERTICAL = 4
DEGREES_PER_COLUMN = 360 / TILES_HORIZONTAL  # 45°

# Pitch mapping for rows
ROW_PITCH = {
    0: 60,    # y0: sky/ceiling
    1: 15,    # y1: upper horizon
    2: -10,   # y2: lower horizon/storefronts
    3: -45,   # y3: ground/street
}

# Timing (milliseconds)
KEYFRAME_INTERVAL = 100  # 10 FPS for smooth playback

# Default durations
DURATIONS = {
    "establish": 2500,
    "focus": 2500,
    "sweep": 2000,  # Base, scales with distance
    "glance": 1200,
}

# Cinematic behaviors
BEHAVIORS = {
    "focus": {
        "zoom": 1.1,
        "sway_amplitude": 2,  # ±2° heading sway
        "sway_period": 3000,
        "pitch_drift": 1,  # ±1° subtle pitch movement
    },
    "sweep": {
        "arc_pitch_dip": 5,  # Dip 5° at midpoint
        "speed_deg_per_sec": 30,
        "easing": "ease-in-out",
    },
    "glance": {
        "duration": 800,
        "return_duration": 400,
        "easing": "ease-out",
    },
    "establish": {
        "look_angle": 60,  # How far to look each way
        "duration_per_direction": 800,
    },
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Keyframe:
    """A single keyframe in the tour animation."""
    time_ms: int
    heading: float
    pitch: float
    zoom: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": self.time_ms,
            "h": round(self.heading, 1),
            "p": round(self.pitch, 1),
            "z": round(self.zoom, 2),
        }


@dataclass
class TourProgram:
    """Complete tour program with keyframes."""
    pano_id: str
    location_type: str
    location_name: str
    keyframes: List[Keyframe] = field(default_factory=list)
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pano_id": self.pano_id,
            "location_type": self.location_type,
            "location_name": self.location_name,
            "duration_ms": self.duration_ms,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def tile_to_heading(column: int) -> float:
    """Convert tile column to heading angle (center of tile)."""
    return (column * DEGREES_PER_COLUMN) + (DEGREES_PER_COLUMN / 2)


def tile_to_pitch(row: int) -> float:
    """Convert tile row to pitch angle."""
    return ROW_PITCH.get(row, 0)


def parse_tile_ref(tile_ref: str) -> tuple[int, int]:
    """Parse tile reference like 'x3_y1' into (column, row)."""
    parts = tile_ref.lower().replace("x", "").replace("y", "").split("_")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 1  # Default to x0_y1


def normalize_heading(h: float) -> float:
    """Normalize heading to 0-360 range."""
    while h < 0:
        h += 360
    while h >= 360:
        h -= 360
    return h


def ease_in_out(t: float) -> float:
    """Ease-in-out interpolation (smoothstep)."""
    return t * t * (3 - 2 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


# =============================================================================
# TOUR EXECUTOR
# =============================================================================

class TourExecutor:
    """
    Converts tour sequences into executable keyframes.
    
    Usage:
        executor = TourExecutor()
        program = executor.execute(sequence_dict)
        keyframes = program.to_dict()["keyframes"]
    """
    
    def __init__(self, starting_heading: float = 0):
        self.current_heading = starting_heading
        self.current_pitch = 0
        self.current_zoom = 1.0
        self.current_time = 0
        self.keyframes: List[Keyframe] = []
    
    def execute(self, sequence: Dict[str, Any]) -> TourProgram:
        """
        Execute a tour sequence and generate keyframes.
        
        Args:
            sequence: Dict from TourGenerator.sequence_to_dict()
            
        Returns:
            TourProgram with all keyframes
        """
        # Initialize from property direction
        prop_dir = sequence.get("property_direction", "x0")
        if prop_dir.startswith("x"):
            prop_col = int(prop_dir[1])
            self.current_heading = tile_to_heading(prop_col)
        
        self.current_pitch = 0
        self.current_zoom = 1.0
        self.current_time = 0
        self.keyframes = []
        
        # Add initial keyframe
        self._add_keyframe()
        
        # Execute each action
        for action in sequence.get("actions", []):
            self._execute_action(action)
        
        # Add final settle
        self._settle(500)
        
        return TourProgram(
            pano_id=sequence.get("pano_id", ""),
            location_type=sequence.get("location_type", ""),
            location_name=sequence.get("location_name", ""),
            keyframes=self.keyframes,
            duration_ms=self.current_time,
        )
    
    def _add_keyframe(self):
        """Add a keyframe at current state."""
        self.keyframes.append(Keyframe(
            time_ms=self.current_time,
            heading=normalize_heading(self.current_heading),
            pitch=self.current_pitch,
            zoom=self.current_zoom,
        ))
    
    def _execute_action(self, action: Dict):
        """Execute a single tour action."""
        action_type = action.get("action", "focus")
        
        if action_type == "establish":
            self._establish()
        elif action_type == "focus":
            self._focus(action)
        elif action_type == "sweep":
            self._sweep(action)
        elif action_type == "glance":
            self._glance(action)
        else:
            logger.warning(f"Unknown action type: {action_type}")
    
    def _establish(self):
        """Execute establish action: look both ways to orient."""
        behavior = BEHAVIORS["establish"]
        look_angle = behavior["look_angle"]
        duration = behavior["duration_per_direction"]
        
        # Start heading
        start_h = self.current_heading
        
        # Look left
        self._animate_to(
            heading=start_h - look_angle,
            pitch=random.uniform(-5, 5),
            zoom=1.0,
            duration=duration,
        )
        
        # Pause briefly
        self.current_time += 200
        self._add_keyframe()
        
        # Sweep right (through center)
        self._animate_to(
            heading=start_h + look_angle,
            pitch=random.uniform(-5, 5),
            zoom=1.0,
            duration=duration * 1.5,  # Longer for the full sweep
        )
        
        # Return to center
        self._animate_to(
            heading=start_h,
            pitch=0,
            zoom=1.0,
            duration=duration * 0.7,
        )
    
    def _focus(self, action: Dict):
        """Execute focus action: hold on specific tiles with gentle movement."""
        tiles = action.get("tiles", ["x0_y1"])
        behavior = BEHAVIORS["focus"]
        duration = DURATIONS["focus"]
        
        # Get target from first tile
        if tiles:
            col, row = parse_tile_ref(tiles[0])
        else:
            col, row = 0, 1
        
        target_h = tile_to_heading(col)
        target_p = tile_to_pitch(row)
        
        # Animate to target
        self._animate_to(
            heading=target_h,
            pitch=target_p,
            zoom=behavior["zoom"],
            duration=800,
        )
        
        # Hold with gentle sway
        self._hold_with_sway(
            duration=duration,
            sway_amplitude=behavior["sway_amplitude"],
            pitch_drift=behavior["pitch_drift"],
        )
        
        # Ease zoom back
        self._animate_to(
            heading=self.current_heading,
            pitch=self.current_pitch,
            zoom=1.0,
            duration=400,
        )
    
    def _sweep(self, action: Dict):
        """Execute sweep action: smooth pan across columns."""
        from_col = action.get("from_column", 0)
        to_col = action.get("to_column", 4)
        behavior = BEHAVIORS["sweep"]
        
        from_h = tile_to_heading(from_col)
        to_h = tile_to_heading(to_col)
        
        # Calculate duration based on distance
        angle_delta = abs(to_h - from_h)
        if angle_delta > 180:
            angle_delta = 360 - angle_delta
        
        duration = int((angle_delta / behavior["speed_deg_per_sec"]) * 1000)
        duration = max(duration, 1000)  # Minimum 1 second
        
        # Move to start if needed
        if abs(self.current_heading - from_h) > 10:
            self._animate_to(
                heading=from_h,
                pitch=random.uniform(-5, 5),
                zoom=1.0,
                duration=600,
            )
        
        # Execute sweep with arc
        self._sweep_with_arc(
            from_h=from_h,
            to_h=to_h,
            duration=duration,
            arc_dip=behavior["arc_pitch_dip"],
        )
    
    def _glance(self, action: Dict):
        """Execute glance action: quick look and return."""
        column = action.get("column", 0)
        behavior = BEHAVIORS["glance"]
        
        target_h = tile_to_heading(column)
        start_h = self.current_heading
        start_p = self.current_pitch
        
        # Quick look
        self._animate_to(
            heading=target_h,
            pitch=random.uniform(-10, 10),
            zoom=1.0,
            duration=behavior["duration"],
        )
        
        # Brief pause
        self.current_time += 150
        self._add_keyframe()
        
        # Return
        self._animate_to(
            heading=start_h,
            pitch=start_p,
            zoom=1.0,
            duration=behavior["return_duration"],
        )
    
    def _animate_to(
        self,
        heading: float,
        pitch: float,
        zoom: float,
        duration: int,
    ):
        """Animate camera to target position."""
        start_h = self.current_heading
        start_p = self.current_pitch
        start_z = self.current_zoom
        
        steps = int(max(duration // KEYFRAME_INTERVAL, 1))
        
        for i in range(1, steps + 1):
            t = ease_in_out(i / steps)
            
            self.current_heading = lerp(start_h, heading, t)
            self.current_pitch = lerp(start_p, pitch, t)
            self.current_zoom = lerp(start_z, zoom, t)
            self.current_time += KEYFRAME_INTERVAL
            
            self._add_keyframe()
    
    def _sweep_with_arc(
        self,
        from_h: float,
        to_h: float,
        duration: int,
        arc_dip: float,
    ):
        """Execute sweep with pitch arc for natural feel."""
        start_p = self.current_pitch
        
        steps = int(max(duration // KEYFRAME_INTERVAL, 1))
        
        for i in range(1, steps + 1):
            t = i / steps
            eased_t = ease_in_out(t)
            
            # Heading interpolation
            self.current_heading = lerp(from_h, to_h, eased_t)
            
            # Arc: dip down at midpoint, return at end
            arc_factor = math.sin(t * math.pi)  # 0 → 1 → 0
            self.current_pitch = start_p - (arc_dip * arc_factor)
            
            self.current_time += KEYFRAME_INTERVAL
            self._add_keyframe()
    
    def _hold_with_sway(
        self,
        duration: int,
        sway_amplitude: float,
        pitch_drift: float,
    ):
        """Hold position with gentle sway."""
        base_h = self.current_heading
        base_p = self.current_pitch
        
        steps = int(max(duration // KEYFRAME_INTERVAL, 1))
        
        for i in range(steps):
            t = i / steps
            
            # Gentle sinusoidal sway
            sway = sway_amplitude * math.sin(t * math.pi * 2)
            drift = pitch_drift * math.sin(t * math.pi * 3)
            
            self.current_heading = base_h + sway
            self.current_pitch = base_p + drift
            self.current_time += KEYFRAME_INTERVAL
            
            self._add_keyframe()
    
    def _settle(self, duration: int):
        """Final settling movement."""
        # Gentle return to neutral pitch
        self._animate_to(
            heading=self.current_heading,
            pitch=0,
            zoom=1.0,
            duration=duration,
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def execute_tour_sequence(
    sequence: Dict[str, Any],
    starting_heading: float = 0,
) -> Dict[str, Any]:
    """
    Execute a tour sequence and return keyframes.
    
    This is the main entry point for the story route.
    """
    executor = TourExecutor(starting_heading)
    program = executor.execute(sequence)
    return program.to_dict()

