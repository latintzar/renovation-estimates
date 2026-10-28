#!/usr/bin/env python3
"""
Room Type Inference
====================

Handles messy room names from listings and infers structured room types.

Solves problems like:
- "Cocina-Comedor abierto" → kitchen, open_plan
- "Dormitorio principal con vestidor" → bedroom, primary, has_dressing
- "Baño 2" → bathroom, secondary
- "Office / Despacho" → office

This is critical for:
1. Quantity calculation (wet rooms need more waterproofing)
2. Variant selection (kitchen needs anti-mold paint)
3. Cost estimation (primary rooms vs secondary)
"""

from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import re


# =============================================================================
# ROOM TYPE KEYWORDS (Exhaustive for Spanish real estate listings)
# =============================================================================

ROOM_TYPE_KEYWORDS = {
    # === KITCHEN ===
    "kitchen": [
        "cocina", "kitchen", "cocineta", "kitchenette", "office cocina",
        "cocina americana", "cocina equipada", "cocina independiente"
    ],
    
    # === BATHROOM (full) ===
    "bathroom": [
        "baño", "bathroom", "cuarto de baño", "baño completo",
        "baño principal", "baño suite", "baño dormitorio"
    ],
    
    # === TOILET (half bath) ===
    "toilet": [
        "aseo", "wc", "aseo de cortesía", "medio baño", "lavabo",
        "aseo invitados", "servicio"
    ],
    
    # === BEDROOM ===
    "bedroom": [
        "dormitorio", "habitación", "bedroom", "cuarto", "alcoba",
        "dormitorio principal", "dormitorio doble", "dormitorio individual",
        "habitación doble", "habitación individual"
    ],
    
    # === LIVING ROOM ===
    "living": [
        "salón", "living", "sala", "sala de estar", "estancia",
        "salón principal", "living room", "cuarto de estar"
    ],
    
    # === DINING ROOM ===
    "dining": [
        "comedor", "dining", "zona de comedor", "comedor independiente"
    ],
    
    # === OFFICE ===
    "office": [
        "despacho", "office", "estudio", "oficina", "escritorio",
        "cuarto de trabajo", "zona de trabajo", "home office"
    ],
    
    # === HALLWAY ===
    "hallway": [
        "pasillo", "distribuidor", "hall", "entrada", "recibidor",
        "vestíbulo", "corredor", "galería"
    ],
    
    # === STORAGE ===
    "storage": [
        "trastero", "almacén", "despensa", "cuarto trastero",
        "storage", "armario empotrado", "cuarto de la plancha"
    ],
    
    # === DRESSING ROOM ===
    "dressing": [
        "vestidor", "dressing", "walk-in closet", "closet",
        "armario vestidor"
    ],
    
    # === LAUNDRY ===
    "laundry": [
        "lavadero", "cuarto de lavado", "lavandería", "tendedero",
        "zona de lavado", "galería lavadero"
    ],
    
    # === TERRACE/BALCONY ===
    "terrace": [
        "terraza", "balcón", "balconada", "solarium", "azotea",
        "terraza cubierta", "terraza descubierta", "patio"
    ],
    
    # === GARAGE ===
    "garage": [
        "garaje", "parking", "cochera", "plaza garaje",
        "aparcamiento", "garage"
    ],
    
    # === GARDEN ===
    "garden": [
        "jardín", "patio", "zona ajardinada", "garden",
        "parcela", "zona exterior"
    ],
    
    # === POOL ===
    "pool": [
        "piscina", "pool", "zona de piscina", "vaso de piscina"
    ],
    
    # === BASEMENT ===
    "basement": [
        "sótano", "bodega", "basement", "cueva",
        "planta baja", "semisótano"
    ],
    
    # === ATTIC ===
    "attic": [
        "buhardilla", "ático", "bajo cubierta", "attic",
        "altillo", "desván"
    ],
}


# =============================================================================
# ROOM CHARACTERISTICS KEYWORDS
# =============================================================================

CHARACTERISTIC_KEYWORDS = {
    # Layout
    "open_plan": ["abierto", "open", "americano", "integrado", "unido", "comunicado"],
    "independent": ["independiente", "separado", "cerrado"],
    "combined": ["comedor", "cocina", "office", "-", "/"],
    
    # Hierarchy
    "primary": ["principal", "master", "suite", "1", "grande"],
    "secondary": ["secundario", "2", "3", "4", "pequeño", "auxiliar"],
    "guest": ["invitados", "guest", "visitas"],
    "children": ["niños", "infantil", "kids", "juvenil"],
    
    # Features
    "has_shower": ["ducha", "plato ducha", "shower"],
    "has_bathtub": ["bañera", "bathtub", "jacuzzi", "hidromasaje"],
    "has_dressing": ["vestidor", "dressing", "walk-in"],
    "has_terrace": ["terraza", "balcón"],
    "has_window": ["ventana", "exterior", "luminoso"],
    "interior": ["interior", "sin ventana", "oscuro"],
    
    # Condition
    "equipped": ["equipado", "amueblado", "completo"],
    "to_renovate": ["reformar", "a reformar", "para reformar"],
    "renovated": ["reformado", "nuevo", "recién"],
    
    # Size
    "large": ["grande", "amplio", "espacioso", "xl"],
    "small": ["pequeño", "reducido", "compacto"],
    "double": ["doble", "matrimonio"],
    "single": ["individual", "single", "sencillo"],
}


# =============================================================================
# ROOM ENVIRONMENT MAPPING (for variant selection)
# =============================================================================

ROOM_ENVIRONMENTS = {
    "kitchen": "wet",
    "bathroom": "wet",
    "toilet": "wet",
    "laundry": "wet",
    "pool": "wet",
    "basement": "wet",  # Often humidity issues
    
    "bedroom": "dry",
    "living": "dry",
    "dining": "dry",
    "office": "dry",
    "hallway": "dry",
    "storage": "dry",
    "dressing": "dry",
    "attic": "dry",
    
    "terrace": "exterior",
    "garden": "exterior",
    "garage": "exterior",
}


# =============================================================================
# ROOM TYPE INFERENCE FUNCTION
# =============================================================================

@dataclass
class RoomInfo:
    """Structured room information."""
    original_name: str
    primary_type: str
    environment: str  # wet, dry, exterior
    characteristics: List[str]
    is_combined: bool  # e.g., kitchen-dining
    combined_types: List[str]  # e.g., ["kitchen", "dining"]
    confidence: float  # 0-1


def infer_room_type(room_name: str) -> RoomInfo:
    """
    Infer room type and characteristics from messy room name.
    
    Args:
        room_name: Raw room name from listing (e.g., "Cocina-Comedor abierto")
    
    Returns:
        RoomInfo with structured type, environment, and characteristics
    
    Examples:
        >>> infer_room_type("Cocina-Comedor abierto")
        RoomInfo(primary_type="kitchen", environment="wet", 
                 characteristics=["open_plan", "combined"],
                 is_combined=True, combined_types=["kitchen", "dining"])
        
        >>> infer_room_type("Dormitorio principal con vestidor")
        RoomInfo(primary_type="bedroom", environment="dry",
                 characteristics=["primary", "has_dressing"],
                 is_combined=False, combined_types=[])
    """
    room_lower = room_name.lower().strip()
    
    # Find all matching room types
    matched_types = []
    for room_type, keywords in ROOM_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in room_lower:
                matched_types.append((room_type, len(kw)))  # (type, match_length)
                break
    
    # Sort by match length (longer = more specific)
    matched_types.sort(key=lambda x: x[1], reverse=True)
    
    # Determine primary type
    if matched_types:
        primary_type = matched_types[0][0]
        confidence = 0.9
    else:
        primary_type = "general"
        confidence = 0.3
    
    # Check if combined room
    combined_types = list(set([t[0] for t in matched_types[:3]]))
    is_combined = len(combined_types) > 1
    
    # Infer characteristics
    characteristics = []
    for char_name, keywords in CHARACTERISTIC_KEYWORDS.items():
        if any(kw in room_lower for kw in keywords):
            characteristics.append(char_name)
    
    # Mark as combined if detected
    if is_combined:
        characteristics.append("combined")
    
    # Determine environment (prioritize wettest room type for combined)
    environment = "dry"
    for t in combined_types:
        env = ROOM_ENVIRONMENTS.get(t, "dry")
        if env == "wet":
            environment = "wet"
            break
        elif env == "exterior":
            environment = "exterior"
    
    if not combined_types:
        environment = ROOM_ENVIRONMENTS.get(primary_type, "dry")
    
    return RoomInfo(
        original_name=room_name,
        primary_type=primary_type,
        environment=environment,
        characteristics=characteristics,
        is_combined=is_combined,
        combined_types=combined_types if is_combined else [],
        confidence=confidence
    )


def match_room_to_smart_m2(
    room_name: str,
    smart_m2_rooms: List[Dict]
) -> Optional[Dict]:
    """
    Find the best matching Smart M2 room for a task's source room.
    
    Uses fuzzy matching to handle variations in naming.
    
    Args:
        room_name: Room name from gap analysis (e.g., "cocina")
        smart_m2_rooms: List of room dicts from Smart M2 
                        [{"room_name": "Cocina", "m2": 12, "height_m": 2.5}, ...]
    
    Returns:
        Best matching room dict, or None if no match
    """
    if not smart_m2_rooms:
        return None
    
    room_lower = room_name.lower().strip()
    
    # Direct match
    for room in smart_m2_rooms:
        if room.get("room_name", "").lower().strip() == room_lower:
            return room
    
    # Partial match
    for room in smart_m2_rooms:
        smart_name = room.get("room_name", "").lower().strip()
        if room_lower in smart_name or smart_name in room_lower:
            return room
    
    # Type-based match
    room_info = infer_room_type(room_name)
    for room in smart_m2_rooms:
        smart_info = infer_room_type(room.get("room_name", ""))
        if smart_info.primary_type == room_info.primary_type:
            return room
    
    return None


def get_room_dimensions(
    room_name: str,
    smart_m2_rooms: List[Dict],
    default_m2: float = 10.0,
    default_height: float = 2.5
) -> Dict:
    """
    Get dimensions for a room, falling back to defaults.
    
    Args:
        room_name: Room name
        smart_m2_rooms: Smart M2 data
        default_m2: Default floor area if no match
        default_height: Default height if no match
    
    Returns:
        Dict with m2, height, perimeter, wall_area
    """
    room = match_room_to_smart_m2(room_name, smart_m2_rooms)
    
    if room:
        m2 = room.get("m2", default_m2)
        height = room.get("height_m", default_height)
    else:
        m2 = default_m2
        height = default_height
    
    # Calculate derived dimensions
    perimeter = 4 * (m2 ** 0.5)  # Approximate square
    wall_area = perimeter * height
    
    return {
        "m2": m2,
        "height": height,
        "perimeter": round(perimeter, 2),
        "wall_area": round(wall_area, 2),
        "matched": room is not None
    }


# =============================================================================
# QUANTITY FACTOR EXTRACTION
# =============================================================================

def get_quantity_factors(
    room_name: str,
    smart_m2_rooms: List[Dict],
    property_total_m2: float = 100.0
) -> Dict:
    """
    Extract all factors needed for quantity reasoning.
    
    Returns comprehensive context for Gemini to reason about quantities.
    """
    room_info = infer_room_type(room_name)
    dims = get_room_dimensions(room_name, smart_m2_rooms)
    
    # Count rooms of each type in the property
    room_type_counts = {}
    for r in smart_m2_rooms:
        info = infer_room_type(r.get("room_name", ""))
        room_type_counts[info.primary_type] = room_type_counts.get(info.primary_type, 0) + 1
    
    return {
        # Room identity
        "room_name": room_name,
        "room_type": room_info.primary_type,
        "environment": room_info.environment,
        "characteristics": room_info.characteristics,
        "is_combined": room_info.is_combined,
        
        # Room dimensions
        "room_m2": dims["m2"],
        "room_height": dims["height"],
        "room_perimeter": dims["perimeter"],
        "room_wall_area": dims["wall_area"],
        
        # Property context
        "property_total_m2": property_total_m2,
        "total_rooms": len(smart_m2_rooms),
        "room_type_counts": room_type_counts,
        
        # Special flags
        "is_wet_room": room_info.environment == "wet",
        "is_exterior": room_info.environment == "exterior",
        "is_primary": "primary" in room_info.characteristics,
        "is_open_plan": "open_plan" in room_info.characteristics,
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test cases
    test_rooms = [
        "Cocina-Comedor abierto",
        "Dormitorio principal con vestidor",
        "Baño 2",
        "Office / Despacho",
        "Salón grande",
        "Aseo de cortesía",
        "Terraza cubierta",
        "Lavadero",
        "Habitación individual",
        "Cuarto de baño completo",
    ]
    
    print("=" * 70)
    print("ROOM TYPE INFERENCE TEST")
    print("=" * 70)
    
    for room in test_rooms:
        info = infer_room_type(room)
        print(f"\n'{room}':")
        print(f"  Type: {info.primary_type}")
        print(f"  Environment: {info.environment}")
        print(f"  Characteristics: {info.characteristics}")
        print(f"  Combined: {info.is_combined} → {info.combined_types}")
        print(f"  Confidence: {info.confidence:.0%}")

