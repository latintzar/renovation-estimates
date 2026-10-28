"""
Legacy Tour Generator - ARCHIVED (Not for Production Use)
=========================================================

⚠️  THIS FILE IS NOT USED IN PRODUCTION.
⚠️  It exists only as a reference for potential architectural changes.
⚠️  Do NOT import this in production code.

This is a Python port of the original tour generation logic from gamepad-streetview.html.
Preserved in case we need to revert from Gemini-based generation or adapt the algorithm.

Original source: Leo/random stuff/gamepad-streetview.html
Extracted: December 2024

Key Components:
1. Camera state machine
2. Motion primitives (survey, glance, examine, etc.)
3. Establish scene patterns (both-ways, spin, glance-spin, etc.)
4. Beat-based tour generation (big-sweep, zoom-examine, look-up, etc.)
5. Real-time sway for handheld feel

Manual Testing Only:
    python -m backend.services.tour_generator_legacy

This generates heading/pitch/zoom keyframes compatible with:
- Google Street View Dynamic
- Custom panorama viewer with cached tiles
"""

import random
import math
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field

# ========================================
# CONSTANTS
# ========================================

NEUTRAL_PITCH = {'min': 5, 'max': 15}


# ========================================
# UTILITY FUNCTIONS
# ========================================

def rand(min_val: float, max_val: float) -> float:
    """Random float between min and max."""
    return random.uniform(min_val, max_val)


def rand_int(min_val: int, max_val: int) -> int:
    """Random integer between min and max (inclusive)."""
    return random.randint(min_val, max_val)


def rand_choice(choices: list):
    """Random choice from list."""
    return random.choice(choices)


def normalize_angle(angle: float) -> float:
    """Normalize angle to 0-360 range."""
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle


# ========================================
# KEYFRAME DATA STRUCTURE
# ========================================

@dataclass
class Keyframe:
    time: float  # milliseconds
    heading: float  # 0-360 degrees
    pitch: float  # -60 to 60 degrees
    zoom: float  # 0.5 to 3


@dataclass
class TourProgram:
    id: str
    name: str
    duration: float  # total duration in ms
    keyframes: List[Keyframe] = field(default_factory=list)


# ========================================
# CAMERA STATE MACHINE
# ========================================

class Camera:
    """
    Single source of truth for camera state.
    All motion flows through here.
    """
    
    def __init__(self):
        self.H = 0.0  # Heading (degrees)
        self.P = 0.0  # Pitch (degrees)
        self.Z = 1.0  # Zoom level
        self.keyframes: List[Keyframe] = []
        self.time = 0.0
    
    def reset(self, heading: float, pitch: float = 8.0, zoom: float = 1.0):
        """Reset camera for new tour."""
        self.H = normalize_angle(heading)
        self.P = pitch
        self.Z = zoom
        self.keyframes = []
        self.time = 0.0
    
    def state(self) -> Dict:
        """Get current state."""
        return {'heading': self.H, 'pitch': self.P, 'zoom': self.Z}
    
    def mark(self):
        """Add keyframe at current state."""
        self.keyframes.append(Keyframe(
            time=self.time,
            heading=self.H,
            pitch=max(-60, min(60, self.P)),
            zoom=max(0.5, min(3, self.Z))
        ))
    
    def move_to(self, target_h: float, target_p: float, target_z: float, 
                duration: float, easing: str = 'smooth'):
        """
        Smoothly move to new state.
        This is the ONLY way to change camera state.
        """
        STEP_MS = 150  # Coarser granularity prevents micro-jitter
        steps = max(3, math.ceil(duration / STEP_MS))
        
        start_h = self.H
        start_p = self.P
        start_z = self.Z
        
        # Calculate shortest heading path
        target_h = normalize_angle(target_h)
        h_diff = target_h - start_h
        if h_diff > 180:
            h_diff -= 360
        if h_diff < -180:
            h_diff += 360
        
        # SMILE DIP: During large horizontal sweeps, humans naturally dip pitch
        is_large_sweep = abs(h_diff) > 40
        smile_dip_amount = min(6, abs(h_diff) * 0.05) if is_large_sweep else 0
        
        for i in range(steps + 1):
            p = i / steps
            
            # Easing functions
            if easing == 'snap':  # Quick start, slow end
                t = 1 - pow(1 - p, 3)
            elif easing == 'drift':  # Very slow, dreamy
                t = p * p * (3 - 2 * p)
            elif easing == 'linear':
                t = p
            else:  # smooth ease-in-out
                t = 2 * p * p if p < 0.5 else 1 - pow(-2 * p + 2, 2) / 2
            
            # Apply smile dip: sinusoidal dip in middle of sweep
            smile_dip = smile_dip_amount * math.sin(p * math.pi)
            
            self.H = normalize_angle(start_h + h_diff * t)
            self.P = start_p + (target_p - start_p) * t - smile_dip
            self.Z = start_z + (target_z - start_z) * t
            self.time += duration / steps
            self.mark()
    
    def hold(self, duration: float):
        """Hold at current position."""
        STEP_MS = 100
        steps = max(2, math.ceil(duration / STEP_MS))
        
        for i in range(steps + 1):
            self.time += duration / steps
            self.mark()
    
    def get_program(self, name: str) -> TourProgram:
        """Get final program."""
        return TourProgram(
            id=f"{int(self.time)}_{random.random()}",
            name=name,
            duration=self.time,
            keyframes=self.keyframes.copy()
        )


# Global camera instance
_camera = Camera()


# ========================================
# MOTION PRIMITIVES
# ========================================

class Motion:
    """
    Atomic camera movements - the vocabulary.
    These compose into higher-level beats.
    """
    
    @staticmethod
    def survey(direction: Literal['left', 'right'], magnitude: float = 60):
        """Slow pan to look in a direction."""
        target_h = _camera.H + (-magnitude if direction == 'left' else magnitude)
        pitch_var = rand(-3, 5)
        _camera.move_to(target_h, _camera.P + pitch_var, _camera.Z, rand(1800, 2400), 'drift')
    
    @staticmethod
    def glance(direction: Literal['left', 'right'], magnitude: float = 30):
        """Quick look - smoothed (no micro-pause)."""
        dir_mult = -1 if direction == 'left' else 1
        target_h = _camera.H + dir_mult * magnitude
        pitch_bump = rand(-2, 3)
        _camera.move_to(target_h, _camera.P + pitch_bump, _camera.Z, rand(900, 1200), 'smooth')
    
    @staticmethod
    def examine(zoom_level: float = 1.4, hold_time: float = 800):
        """Zoom in/out - smoothed (continuous arc)."""
        drift = rand(-4, 4)
        pitch_up = rand(2, 5)
        # Smooth zoom in
        _camera.move_to(_camera.H + drift, _camera.P + pitch_up, zoom_level, rand(1000, 1400), 'smooth')
        # Smooth pull back
        _camera.move_to(_camera.H + drift + rand(-6, 6), _camera.P, 1, rand(1000, 1400), 'smooth')
    
    @staticmethod
    def skyward():
        """Look up - smoothed (continuous arc)."""
        drift = rand(-12, 12)
        up_pitch = rand(20, 30)
        _camera.move_to(_camera.H + drift, up_pitch, _camera.Z, rand(900, 1200), 'smooth')
        _camera.move_to(_camera.H + drift + rand(-10, 10), rand(4, 10), _camera.Z, rand(1000, 1400), 'smooth')
    
    @staticmethod
    def groundward():
        """Look down - smoothed (continuous arc)."""
        drift = rand(-15, 15)
        down_pitch = rand(-15, -6)
        _camera.move_to(_camera.H + drift, down_pitch, _camera.Z, rand(900, 1200), 'smooth')
        _camera.move_to(_camera.H + drift + rand(-8, 8), rand(4, 10), _camera.Z, rand(1000, 1400), 'smooth')
    
    @staticmethod
    def staged_turn(total_angle: float):
        """Organic curve turn (not staccato)."""
        pitch_wander = rand(-4, 4)
        _camera.move_to(_camera.H + total_angle * 0.6, _camera.P + pitch_wander, _camera.Z, rand(1000, 1400), 'smooth')
        _camera.move_to(_camera.H + total_angle * 0.4, _camera.P - pitch_wander/2, _camera.Z, rand(900, 1200), 'smooth')
    
    @staticmethod
    def discover(direction: Literal['left', 'right'], magnitude: float = 40):
        """Turn as if noticing - one confident movement."""
        dir_mult = -1 if direction == 'left' else 1
        _camera.move_to(_camera.H + dir_mult * magnitude, _camera.P + rand(0, 3), _camera.Z, rand(1100, 1500), 'smooth')
    
    @staticmethod
    def breathe(duration: float = 1000):
        """Subtle movement."""
        _camera.move_to(
            _camera.H + rand(-3, 3),
            _camera.P + rand(-2, 2),
            _camera.Z + rand(-0.03, 0.03),
            duration,
            'drift'
        )
    
    @staticmethod
    def settle():
        """Gentle arrival moment."""
        _camera.move_to(_camera.H + rand(-3, 3), _camera.P + rand(-2, 2), _camera.Z, rand(800, 1100), 'drift')


# ========================================
# DIRECTION TRACKING
# ========================================

# Tracks which way we've been moving to prevent zigzag
_last_move_dir = 0  # -1 = left, +1 = right, 0 = neutral


def _reset_direction():
    global _last_move_dir
    _last_move_dir = 0


def _update_direction(direction: int):
    global _last_move_dir
    _last_move_dir = direction


# ========================================
# ESTABLISH SCENE
# ========================================

def establish_scene(is_property: bool):
    """
    Orient the viewer before focusing on details.
    
    Property tours: ALWAYS look both ways first.
    Nearby tours: Quick variety patterns.
    """
    global _last_move_dir
    
    if is_property:
        # Property: GUARANTEED both-ways, sometimes with enhancement
        enhanced = random.random() < 0.3
        if enhanced:
            variant = f"both-ways-then-{rand_choice(['spin', 'ground-spin'])}"
        else:
            variant = 'both-ways'
    else:
        # Nearby: variety for quick context
        variant = rand_choice(['both-ways', 'glance-spin', 'quick-glance'])
    
    neutral_p = rand(NEUTRAL_PITCH['min'], NEUTRAL_PITCH['max'])
    
    if variant == 'both-ways':
        start_h = _camera.H
        _camera.move_to(start_h - rand(50, 80), neutral_p + rand(-2, 2), _camera.Z, rand(1000, 1400), 'smooth')
        _camera.move_to(start_h + rand(60, 100), neutral_p + rand(-1, 3), _camera.Z, rand(1400, 1900), 'smooth')
        _camera.move_to(start_h + rand(-15, 25), neutral_p, _camera.Z, rand(900, 1200), 'smooth')
        _last_move_dir = 1
    
    elif variant == 'spin':
        spin_dir = -1 if random.random() < 0.5 else 1
        spin_amount = rand(240, 320)
        _camera.move_to(_camera.H + spin_dir * spin_amount * 0.5, neutral_p + rand(-2, 4), _camera.Z, rand(2000, 2600), 'smooth')
        _camera.move_to(_camera.H + spin_dir * spin_amount * 0.5, neutral_p, _camera.Z, rand(1800, 2400), 'smooth')
        _last_move_dir = spin_dir
    
    elif variant == 'glance-spin':
        glance_dir = -1 if random.random() < 0.5 else 1
        _camera.move_to(_camera.H + glance_dir * rand(35, 55), neutral_p, _camera.Z, rand(900, 1200), 'smooth')
        _camera.move_to(_camera.H - glance_dir * rand(100, 150), neutral_p + rand(-2, 2), _camera.Z, rand(1600, 2100), 'smooth')
        _last_move_dir = -glance_dir
    
    elif variant == 'ground-spin':
        spin_dir = -1 if random.random() < 0.5 else 1
        _camera.move_to(_camera.H + spin_dir * rand(70, 110), rand(-8, 0), _camera.Z, rand(1400, 1800), 'smooth')
        _camera.move_to(_camera.H + spin_dir * rand(25, 45), neutral_p + rand(0, 4), _camera.Z, rand(1200, 1600), 'smooth')
        _last_move_dir = spin_dir
    
    elif variant == 'quick-glance':
        dir_mult = -1 if random.random() < 0.5 else 1
        _camera.move_to(_camera.H + dir_mult * rand(40, 70), neutral_p, _camera.Z, rand(1000, 1400), 'smooth')
        _camera.move_to(_camera.H - dir_mult * rand(15, 30), neutral_p, _camera.Z, rand(800, 1100), 'smooth')
        _last_move_dir = -dir_mult
    
    elif variant == 'both-ways-then-spin':
        start_h = _camera.H
        _camera.move_to(start_h - rand(45, 65), neutral_p, _camera.Z, rand(1000, 1300), 'smooth')
        _camera.move_to(start_h + rand(50, 80), neutral_p + rand(-1, 2), _camera.Z, rand(1200, 1600), 'smooth')
        spin_dir = -1 if random.random() < 0.5 else 1
        _camera.move_to(_camera.H + spin_dir * rand(160, 220), neutral_p + rand(-2, 4), _camera.Z, rand(2000, 2600), 'smooth')
        _last_move_dir = spin_dir
    
    elif variant == 'both-ways-then-ground-spin':
        start_h = _camera.H
        _camera.move_to(start_h - rand(45, 65), neutral_p, _camera.Z, rand(1000, 1300), 'smooth')
        _camera.move_to(start_h + rand(50, 80), neutral_p + rand(-1, 2), _camera.Z, rand(1200, 1600), 'smooth')
        spin_dir = -1 if random.random() < 0.5 else 1
        _camera.move_to(_camera.H + spin_dir * rand(60, 90), rand(-6, 2), _camera.Z, rand(1300, 1700), 'smooth')
        _camera.move_to(_camera.H + spin_dir * rand(20, 35), neutral_p, _camera.Z, rand(1000, 1300), 'smooth')
        _last_move_dir = spin_dir


# ========================================
# BEAT GENERATION
# ========================================

def generate_creative_sequence(is_property: bool, building_context: Optional[Dict] = None) -> List[str]:
    """
    Generate a sequence of cinematic beats.
    
    Property tours: 3-4 beats for thorough exploration.
    Nearby tours: 2-3 beats for quick context.
    """
    count = rand_int(3, 4) if is_property else rand_int(2, 3)
    
    # Check if we should include look-up
    include_look_up = building_context is None or building_context.get('suggested_look_up', True)
    
    property_vocabulary = [
        'big-sweep', 'glance', 'zoom-examine', 'zoom-examine',
        'zoom-while-pan', 'zoom-while-pan', 'look-down', 'pitch-while-pan'
    ]
    
    nearby_vocabulary = [
        'big-sweep', 'glance', 'zoom-examine',
        'zoom-while-pan', 'survey-pan'
    ]
    
    if include_look_up:
        property_vocabulary.append('look-up')
        nearby_vocabulary.append('look-up')
    
    vocabulary = property_vocabulary if is_property else nearby_vocabulary
    
    beats = []
    last = None
    
    for _ in range(count):
        choices = [v for v in vocabulary if v != last]
        
        if last == 'big-sweep':
            choices = [v for v in choices if v != 'big-sweep']
        
        pitch_beats = ['look-up', 'pitch-while-pan', 'look-down']
        if last in pitch_beats:
            choices = [v for v in choices if v not in pitch_beats]
        
        beat = rand_choice(choices)
        beats.append(beat)
        last = beat
    
    return beats


def execute_beat(beat: str, is_property: bool = True):
    """
    Execute a single cinematic beat.
    Each beat is a complete camera movement.
    """
    global _last_move_dir
    
    hold_mult = 1.0 if is_property else 0.5
    pitch_pan_reduction = max(0.5, 1 - abs(_camera.P) / 80)
    
    if beat == 'big-sweep':
        if _last_move_dir == 0:
            dir_mult = -1 if random.random() < 0.5 else 1
        else:
            dir_mult = _last_move_dir if random.random() < 0.7 else -_last_move_dir
        
        pitch_drift = _camera.P + rand(-6, 6)
        sweep_mag = rand(50, 80) * pitch_pan_reduction
        _camera.move_to(_camera.H + dir_mult * sweep_mag, pitch_drift, _camera.Z, rand(2200, 3000), 'drift')
        _last_move_dir = dir_mult
    
    elif beat == 'glance':
        if _last_move_dir == 0:
            dir_mult = -1 if random.random() < 0.5 else 1
        else:
            dir_mult = _last_move_dir if random.random() < 0.9 else -_last_move_dir
        
        pitch_drift = _camera.P + rand(-5, 5)
        glance_mag = rand(25, 40) * pitch_pan_reduction
        _camera.move_to(_camera.H + dir_mult * glance_mag, pitch_drift, _camera.Z, rand(1600, 2200), 'smooth')
        _last_move_dir = dir_mult
    
    elif beat == 'survey-pan':
        if _last_move_dir == 0:
            dir_mult = -1 if random.random() < 0.5 else 1
        else:
            dir_mult = _last_move_dir if random.random() < 0.75 else -_last_move_dir
        
        pitch_drift = _camera.P + rand(-6, 6)
        survey_mag = rand(55, 85) * pitch_pan_reduction
        _camera.move_to(_camera.H + dir_mult * survey_mag, pitch_drift, _camera.Z, rand(2400, 3200), 'drift')
        _last_move_dir = dir_mult
    
    elif beat == 'zoom-examine':
        drift = rand(-15, 15)
        pitch_up = _camera.P + rand(3, 8)
        zoom_level = rand(1.35, 1.55)
        _camera.move_to(_camera.H + drift, pitch_up, zoom_level, rand(1000, 1400), 'smooth')
        _camera.move_to(_camera.H + rand(-20, 20), pitch_up + rand(-5, 5), zoom_level, rand(800, 1100), 'drift')
        _camera.move_to(_camera.H + rand(-10, 10), _camera.P + rand(-4, 4), 1, rand(900, 1200), 'smooth')
    
    elif beat == 'look-down':
        drift = rand(-20, 20)
        down_pitch = rand(-18, -8)
        _camera.move_to(_camera.H + drift, down_pitch, _camera.Z, rand(1000, 1400), 'smooth')
        _camera.move_to(_camera.H + rand(-15, 15), rand(2, 10), _camera.Z, rand(900, 1200), 'smooth')
    
    elif beat == 'look-up':
        drift = rand(-15, 15)
        up_pitch = rand(22, 35)
        _camera.move_to(_camera.H + drift, up_pitch, _camera.Z, rand(900, 1200), 'smooth')
        _camera.move_to(_camera.H + rand(-20, 20), rand(5, 12), _camera.Z, rand(800, 1100), 'smooth')
    
    elif beat == 'linger':
        _camera.move_to(
            _camera.H + rand(-20, 20),
            _camera.P + rand(-8, 8),
            _camera.Z + rand(-0.08, 0.08),
            rand(2000, 2800),
            'drift'
        )
    
    elif beat == 'zoom-while-pan':
        if _last_move_dir == 0:
            dir_mult = -1 if random.random() < 0.5 else 1
        else:
            dir_mult = _last_move_dir if random.random() < 0.8 else -_last_move_dir
        
        pitch_drift = _camera.P + rand(2, 8)
        _camera.move_to(_camera.H + dir_mult * rand(30, 50), pitch_drift, rand(1.25, 1.45), rand(1400, 1800), 'smooth')
        _camera.move_to(_camera.H + dir_mult * rand(15, 25), _camera.P + rand(-4, 4), 1, rand(1000, 1400), 'smooth')
        _last_move_dir = dir_mult
    
    elif beat == 'pitch-while-pan':
        if _last_move_dir == 0:
            dir_mult = -1 if random.random() < 0.5 else 1
        else:
            dir_mult = _last_move_dir if random.random() < 0.8 else -_last_move_dir
        
        go_up = random.random() < 0.6
        target_pitch = rand(18, 28) if go_up else rand(-15, -6)
        _camera.move_to(_camera.H + dir_mult * rand(35, 55), target_pitch, _camera.Z, rand(1400, 1900), 'smooth')
        _camera.move_to(_camera.H + dir_mult * rand(15, 25), rand(3, 12), _camera.Z, rand(900, 1200), 'smooth')
        _last_move_dir = dir_mult


# ========================================
# PUBLIC API
# ========================================

def generate_tour(
    target_heading: float,
    tour_type: str = 'default',
    name: str = 'Tour',
    building_context: Optional[Dict] = None
) -> TourProgram:
    """
    Generate a complete tour program.
    
    Args:
        target_heading: Initial heading to face (0-360 degrees)
        tour_type: 'property' for thorough exploration, anything else for quick
        name: Name for the tour
        building_context: Optional dict with 'suggested_look_up' boolean
        
    Returns:
        TourProgram with keyframes ready for playback
    """
    is_property = tour_type == 'property'
    
    # Reset direction tracking
    _reset_direction()
    
    # Initialize camera
    _camera.reset(target_heading, rand(NEUTRAL_PITCH['min'], NEUTRAL_PITCH['max']), 1)
    
    # Opening shot: gentle drift
    _camera.move_to(
        _camera.H + rand(-6, 6),
        _camera.P + rand(-2, 3),
        _camera.Z,
        rand(1600, 2200),
        'drift'
    )
    
    # Sometimes do a gentle zoom
    if random.random() < 0.6:
        zoom_drift = rand(-5, 5)
        _camera.move_to(_camera.H + zoom_drift, _camera.P + rand(2, 5), rand(1.2, 1.35), rand(1200, 1600), 'smooth')
        neutral_p = rand(NEUTRAL_PITCH['min'], NEUTRAL_PITCH['max'])
        _camera.move_to(_camera.H + zoom_drift + rand(-4, 4), neutral_p, 1, rand(1100, 1500), 'smooth')
    
    # Establish scene
    establish_scene(is_property)
    
    # Generate and execute beats
    beats = generate_creative_sequence(is_property, building_context)
    for beat in beats:
        execute_beat(beat, is_property)
    
    return _camera.get_program(name)


def generate_nearby_place_tour(
    target_heading: float,
    place_name: str,
    place_type: str = 'default',
    building_context: Optional[Dict] = None
) -> TourProgram:
    """
    Generate a tour for a nearby place (quicker, less thorough).
    
    Args:
        target_heading: Heading toward the place (0-360 degrees)
        place_name: Name of the place (used as tour name)
        place_type: Type hint (cafe, restaurant, park, etc.)
        building_context: Optional building context
        
    Returns:
        TourProgram with keyframes
    """
    type_map = {
        'cafe': 'cafe', 'coffee': 'cafe',
        'restaurant': 'restaurant', 'food': 'restaurant',
        'park': 'park', 'garden': 'park',
        'gym': 'default', 'supermarket': 'default', 'pharmacy': 'default'
    }
    
    tour_type = type_map.get(place_type.lower() if place_type else '', 'default')
    
    return generate_tour(
        target_heading=target_heading,
        tour_type=tour_type,
        name=place_name,
        building_context=building_context
    )


# ========================================
# REAL-TIME SWAY (for playback overlay)
# ========================================

def get_realtime_sway(elapsed_ms: float, current_zoom: float = 1, current_pitch: float = 0) -> Dict:
    """
    Calculate handheld camera sway for a given timestamp.
    Apply this ON TOP of keyframe interpolation during playback.
    
    Args:
        elapsed_ms: Time since tour started
        current_zoom: Current zoom level (affects damping)
        current_pitch: Current pitch (affects damping)
        
    Returns:
        Dict with heading, pitch, zoom offsets to ADD to base values
    """
    t = elapsed_ms / 1000
    
    # Reduce shake when zoomed in
    zoom_dampen = 1 / max(1, current_zoom * 0.8)
    
    # Reduce shake at extreme pitch
    pitch_dampen = 1 - abs(current_pitch) / 120
    
    dampen = max(0.3, zoom_dampen * pitch_dampen)
    
    # Layer 1: Organic sway (slow, wide, breathing)
    sway_h = math.sin(t * 0.5) * 7.0 + math.sin(t * 0.9 + 1.5) * 4.5 + math.sin(t * 0.3 + 3.0) * 2.5
    sway_p = math.sin(t * 0.6 + 0.8) * 4.5 + math.sin(t * 1.1 + 2.2) * 2.5
    sway_z = math.sin(t * 0.4 + 1.0) * 0.04
    
    # Layer 2: Movement sway (medium frequency)
    move_h = math.sin(t * 1.7 + 0.5) * 2.0 + math.sin(t * 2.3 + 1.2) * 1.5
    move_p = math.sin(t * 1.9 + 0.8) * 1.5 + math.sin(t * 2.7 + 1.5) * 1.0
    
    # Layer 3: Subtle shake (reduced)
    shake_h = (math.sin(t * 3.7) * 0.25 + math.sin(t * 5.3 + 0.7) * 0.15) * dampen
    shake_p = (math.sin(t * 4.1 + 0.5) * 0.2 + math.sin(t * 6.7 + 1.1) * 0.1) * dampen
    shake_z = (math.sin(t * 2.9 + 0.3) * 0.004) * dampen
    
    return {
        'heading': sway_h + move_h + shake_h,
        'pitch': sway_p + move_p + shake_p,
        'zoom': sway_z + shake_z
    }


# ========================================
# CONVERSION TO TILE-BASED
# ========================================

def keyframes_to_tile_sequence(keyframes: List[Keyframe]) -> List[Dict]:
    """
    Convert heading-based keyframes to tile-based sequence.
    For use with custom panorama viewer.
    
    At Zoom 3: tile x = floor(heading / 45)
    """
    tile_seq = []
    
    for kf in keyframes:
        tile_x = int(kf.heading / 45) % 8
        tile_y = 1 if kf.pitch > 0 else 2  # Upper or lower horizon
        
        tile_seq.append({
            'time': kf.time,
            'tile': f'x{tile_x}_y{tile_y}',
            'heading': kf.heading,
            'pitch': kf.pitch,
            'zoom': kf.zoom
        })
    
    return tile_seq


# ========================================
# SERIALIZATION
# ========================================

def program_to_dict(program: TourProgram) -> Dict:
    """Convert TourProgram to JSON-serializable dict."""
    return {
        'id': program.id,
        'name': program.name,
        'duration': program.duration,
        'keyframes': [
            {
                'time': kf.time,
                'heading': kf.heading,
                'pitch': kf.pitch,
                'zoom': kf.zoom
            }
            for kf in program.keyframes
        ]
    }


def dict_to_program(data: Dict) -> TourProgram:
    """Convert dict back to TourProgram."""
    return TourProgram(
        id=data['id'],
        name=data['name'],
        duration=data['duration'],
        keyframes=[
            Keyframe(
                time=kf['time'],
                heading=kf['heading'],
                pitch=kf['pitch'],
                zoom=kf['zoom']
            )
            for kf in data['keyframes']
        ]
    )


# ========================================
# TEST
# ========================================

if __name__ == '__main__':
    # Test property tour
    print("Generating property tour...")
    property_tour = generate_tour(
        target_heading=135,
        tour_type='property',
        name='Test Property'
    )
    print(f"  Duration: {property_tour.duration:.0f}ms")
    print(f"  Keyframes: {len(property_tour.keyframes)}")
    
    # Test nearby tour
    print("\nGenerating nearby tour...")
    nearby_tour = generate_nearby_place_tour(
        target_heading=90,
        place_name='Mercadona',
        place_type='grocery'
    )
    print(f"  Duration: {nearby_tour.duration:.0f}ms")
    print(f"  Keyframes: {len(nearby_tour.keyframes)}")
    
    # Test serialization
    print("\nTesting serialization...")
    data = program_to_dict(property_tour)
    restored = dict_to_program(data)
    print(f"  Original keyframes: {len(property_tour.keyframes)}")
    print(f"  Restored keyframes: {len(restored.keyframes)}")
    
    # Test tile conversion
    print("\nTesting tile conversion...")
    tiles = keyframes_to_tile_sequence(property_tour.keyframes[:5])
    for t in tiles:
        print(f"  {t['time']:.0f}ms: {t['tile']} (h={t['heading']:.1f}°)")
    
    print("\n✅ Legacy tour generator working!")

