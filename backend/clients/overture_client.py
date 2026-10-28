"""
Overture Maps Client (via AWS Athena)
=====================================

FREE data source for nature places (parks, beaches, forests, lakes, rivers).
Uses AWS Athena to query Overture's cross-account Glue catalog.

Same approach as Leo/backend/tools/tools_athena.py

PRIORITY ORDER (highest to lowest):
1. 🏖️ Beach/Coast (water) - Rare, lifestyle-defining
2. 🌊 Lake/Lagoon (water) - Water frontage is premium
3. 🌲 Forest/Nature Reserve (land_use) - Natural escape
4. 🌳 Large Park ≥20,000 m² (land_use) - Significant green space
5. 🏞️ River (water) - Waterfront walk

REQUIRES: AWS credentials + Athena access

Cost: ~$0.005 per GB scanned (effectively FREE)
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

import boto3

# Load environment
backend_root = Path(__file__).parent.parent
pass  # Recipient runtime supplies its explicit private environment.
pass  # Recipient runtime supplies its explicit private environment.

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Athena MUST run in us-west-2 to access Overture Glue catalog
AWS_REGION = "us-west-2"
ATHENA_OUTPUT_LOCATION = os.getenv(
    "ATHENA_OUTPUT_LOCATION",
    "s3://puedo-casa-athena-results/queries/"
)

# Overture Maps cross-account Glue catalog
OVERTURE_CATALOG = "overture"
OVERTURE_DATABASE = "release"
OVERTURE_RELEASE = os.getenv("OVERTURE_RELEASE", "v2025_12_17_0")
OVERTURE_TABLE = f"{OVERTURE_CATALOG}.{OVERTURE_DATABASE}.{OVERTURE_RELEASE}"

# Meters per degree at equator
METERS_PER_DEGREE = 111319

# Park size thresholds (m²)
MIN_LARGE_PARK_M2 = 20000   # ~2 hectares - Priority 4
MIN_MEDIUM_PARK_M2 = 10000  # ~1 hectare - Priority 6 fallback  
MIN_SMALL_PARK_M2 = 5000    # ~0.5 hectare (1 football field) - Priority 7 last resort


@dataclass
class OverturePlace:
    """Place result from Overture."""
    id: str
    name: str
    lat: float
    lng: float
    category: str  # beach, lake, forest, park, river
    nature_type: str  # Overture class (bay, lake, forest, park, river, etc.)
    area_m2: Optional[float] = None
    distance_m: int = 0
    source: str = "overture"
    priority: int = 99  # Lower = higher priority


class OvertureClient:
    """
    Client for querying Overture Maps via AWS Athena.
    """
    
    def __init__(self):
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Athena client."""
        if self._client is None:
            self._client = boto3.client("athena", region_name=AWS_REGION)
            logger.info(f"[Overture] ✅ Athena client initialized (region={AWS_REGION})")
        return self._client
    
    def _run_query(self, sql: str, timeout_seconds: int = 60) -> List[Dict]:
        """Execute Athena query and return results."""
        client = self._get_client()
        
        # Start query execution
        response = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={
                "Catalog": OVERTURE_CATALOG,
                "Database": OVERTURE_DATABASE,
            },
            ResultConfiguration={
                "OutputLocation": ATHENA_OUTPUT_LOCATION,
            },
        )
        
        query_execution_id = response["QueryExecutionId"]
        
        # Poll for completion
        start_time = time.time()
        while True:
            status = client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status["QueryExecution"]["Status"]["State"]
            
            if state == "SUCCEEDED":
                break
            elif state in ["FAILED", "CANCELLED"]:
                reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
                logger.error(f"[Overture] ❌ Query {state}: {reason}")
                return []
            
            if time.time() - start_time > timeout_seconds:
                logger.error(f"[Overture] ❌ Query timeout after {timeout_seconds}s")
                return []
            
            time.sleep(0.5)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Parse results (skip header row)
        rows = results["ResultSet"]["Rows"]
        if len(rows) < 2:
            return []
        
        # Get column names from header
        columns = [col["VarCharValue"] for col in rows[0]["Data"]]
        
        # Parse data rows
        data = []
        for row in rows[1:]:
            values = [col.get("VarCharValue", "") for col in row["Data"]]
            data.append(dict(zip(columns, values)))
        
        return data

    # =========================================================================
    # PRIORITY 1: Beach/Coast
    # Beach = land_use.beach_resort
    # Coast = water.(bay|sea|ocean|lagoon)
    # =========================================================================
    
    async def _search_beach(self, lat: float, lng: float, radius_deg: float) -> List[OverturePlace]:
        """Search for beaches (land_use) and coastal water (bay/sea/ocean)."""
        
        # First: Search for beach_resort in land_use
        sql_beach = f"""
        SELECT 
            id,
            names.primary AS name,
            'beach_resort' AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Area(ST_GeomFromBinary(geometry)) * {METERS_PER_DEGREE} * {METERS_PER_DEGREE} * COS(RADIANS({lat})) AS area_m2,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'land_use'
          AND class = 'beach_resort'
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql_beach)
        if results:
            return [self._parse_land_result(r, "Beach", 1) for r in results]
        
        # Second: Search for coastal water (bay, sea, ocean, lagoon)
        sql_coast = f"""
        SELECT 
            id,
            names.primary AS name,
            class AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'water'
          AND class IN ('bay', 'sea', 'ocean', 'lagoon')
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql_coast)
        return [self._parse_water_result(r, "Coast", 1) for r in results]

    # =========================================================================
    # PRIORITY 2: Lake/Lagoon (water)
    # =========================================================================
    
    async def _search_lake(self, lat: float, lng: float, radius_deg: float) -> List[OverturePlace]:
        """Search for lakes, lagoons, reservoirs."""
        sql = f"""
        SELECT 
            id,
            names.primary AS name,
            class AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'water'
          AND class IN ('lake', 'lagoon', 'reservoir')
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql)
        return [self._parse_water_result(r, "Lake", 2) for r in results]

    # =========================================================================
    # PRIORITY 3: Forest/Nature Reserve (land_use)
    # =========================================================================
    
    async def _search_forest(self, lat: float, lng: float, radius_deg: float) -> List[OverturePlace]:
        """Search for forests, nature reserves."""
        sql = f"""
        SELECT 
            id,
            names.primary AS name,
            class AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Area(ST_GeomFromBinary(geometry)) * {METERS_PER_DEGREE} * {METERS_PER_DEGREE} * COS(RADIANS({lat})) AS area_m2,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'land_use'
          AND class IN ('forest', 'nature_reserve', 'national_park', 'wilderness_area', 'protected')
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql)
        return [self._parse_land_result(r, "Forest", 3) for r in results]

    # =========================================================================
    # PRIORITY 4/6/7: Park (land_use) - with size thresholds
    # =========================================================================
    
    async def _search_park(
        self, 
        lat: float, 
        lng: float, 
        radius_deg: float,
        min_area_m2: int = MIN_LARGE_PARK_M2,
        priority: int = 4,
        label: str = "Large Park"
    ) -> List[OverturePlace]:
        """Search for parks above a minimum area threshold."""
        sql = f"""
        SELECT 
            id,
            names.primary AS name,
            class AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Area(ST_GeomFromBinary(geometry)) * {METERS_PER_DEGREE} * {METERS_PER_DEGREE} * COS(RADIANS({lat})) AS area_m2,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'land_use'
          AND class IN ('park', 'state_park', 'recreation_ground')
          AND ST_Area(ST_GeomFromBinary(geometry)) * {METERS_PER_DEGREE} * {METERS_PER_DEGREE} * COS(RADIANS({lat})) >= {min_area_m2}
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql)
        return [self._parse_land_result(r, label, priority) for r in results]

    # =========================================================================
    # PRIORITY 5: River (water) - LAST RESORT
    # Only 'river' class (not streams), must be NAMED (significant rivers have names)
    # =========================================================================
    
    async def _search_river(self, lat: float, lng: float, radius_deg: float) -> List[OverturePlace]:
        """Search for significant NAMED rivers only (not streams or unnamed creeks)."""
        sql = f"""
        SELECT 
            id,
            names.primary AS name,
            class AS nature_type,
            ST_Y(ST_Centroid(ST_GeomFromBinary(geometry))) AS lat,
            ST_X(ST_Centroid(ST_GeomFromBinary(geometry))) AS lng,
            ST_Distance(ST_Point({lng}, {lat}), ST_Centroid(ST_GeomFromBinary(geometry))) * {METERS_PER_DEGREE} AS distance_m
        FROM {OVERTURE_TABLE}
        WHERE theme = 'base' AND type = 'water'
          AND class = 'river'
          AND names.primary IS NOT NULL
          AND names.primary != ''
          AND bbox.xmin >= {lng - radius_deg}
          AND bbox.xmax <= {lng + radius_deg}
          AND bbox.ymin >= {lat - radius_deg}
          AND bbox.ymax <= {lat + radius_deg}
        ORDER BY distance_m
        LIMIT 1
        """
        results = self._run_query(sql)
        return [self._parse_water_result(r, "River", 5) for r in results]

    # =========================================================================
    # RESULT PARSERS
    # =========================================================================
    
    def _parse_water_result(self, row: Dict, category: str, priority: int) -> OverturePlace:
        """Parse water query result."""
        return OverturePlace(
            id=row.get("id", ""),
            name=row.get("name") or category,
            category=category,
            nature_type=row.get("nature_type", ""),
            lat=float(row.get("lat", 0)),
            lng=float(row.get("lng", 0)),
            area_m2=None,  # Water features don't have meaningful area
            distance_m=int(float(row.get("distance_m", 0))),
            priority=priority,
        )
    
    def _parse_land_result(self, row: Dict, category: str, priority: int) -> OverturePlace:
        """Parse land_use query result."""
        return OverturePlace(
            id=row.get("id", ""),
            name=row.get("name") or category,
            category=category,
            nature_type=row.get("nature_type", ""),
            lat=float(row.get("lat", 0)),
            lng=float(row.get("lng", 0)),
            area_m2=float(row.get("area_m2", 0)) if row.get("area_m2") else None,
            distance_m=int(float(row.get("distance_m", 0))),
            priority=priority,
        )

    # =========================================================================
    # MAIN SEARCH - Priority-based
    # =========================================================================
    
    async def search_nature(
        self,
        lat: float,
        lng: float,
        radius_m: int = 2000,
    ) -> Optional[OverturePlace]:
        """
        Search for nature features with priority ordering.
        
        Priority:
        1. Beach/Coast - Rare, lifestyle-defining
        2. Lake/Lagoon - Water frontage is premium
        3. Forest/Nature Reserve - Natural escape
        4. Large Park (≥20,000 m²) - Significant green space
        5. Named River - Waterfront walk
        6. Medium Park (≥10,000 m²) - Fallback green space
        7. Small Park (≥5,000 m²) - Last resort, still a decent park
        
        Returns the FIRST match in priority order, or None.
        """
        radius_deg = radius_m / METERS_PER_DEGREE
        
        # Priority 1: Beach/Coast
        logger.info(f"[Overture] 🏖️ P1: Searching beach/coast...")
        results = await self._search_beach(lat, lng, radius_deg)
        if results:
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({results[0].nature_type})")
            return results[0]
        
        # Priority 2: Lake/Lagoon
        logger.info(f"[Overture] 🌊 P2: Searching lake/lagoon...")
        results = await self._search_lake(lat, lng, radius_deg)
        if results:
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({results[0].nature_type})")
            return results[0]
        
        # Priority 3: Forest/Nature Reserve
        logger.info(f"[Overture] 🌲 P3: Searching forest/nature...")
        results = await self._search_forest(lat, lng, radius_deg)
        if results:
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({results[0].nature_type})")
            return results[0]
        
        # Priority 4: Large Park (≥20,000 m²)
        logger.info(f"[Overture] 🌳 P4: Searching large park (≥{MIN_LARGE_PARK_M2:,} m²)...")
        results = await self._search_park(lat, lng, radius_deg, min_area_m2=MIN_LARGE_PARK_M2, priority=4, label="Large Park")
        if results:
            area_str = f"{results[0].area_m2:,.0f} m²" if results[0].area_m2 else "unknown"
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({area_str})")
            return results[0]
        
        # Priority 5: Named River
        logger.info(f"[Overture] 🏞️ P5: Searching named river...")
        results = await self._search_river(lat, lng, radius_deg)
        if results:
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({results[0].nature_type})")
            return results[0]
        
        # Priority 6: Medium Park (≥10,000 m²) - fallback
        logger.info(f"[Overture] 🌳 P6: Searching medium park (≥{MIN_MEDIUM_PARK_M2:,} m²)...")
        results = await self._search_park(lat, lng, radius_deg, min_area_m2=MIN_MEDIUM_PARK_M2, priority=6, label="Medium Park")
        if results:
            area_str = f"{results[0].area_m2:,.0f} m²" if results[0].area_m2 else "unknown"
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({area_str})")
            return results[0]
        
        # Priority 7: Small Park (≥5,000 m²) - last resort
        logger.info(f"[Overture] 🌳 P7: Searching small park (≥{MIN_SMALL_PARK_M2:,} m²)...")
        results = await self._search_park(lat, lng, radius_deg, min_area_m2=MIN_SMALL_PARK_M2, priority=7, label="Small Park")
        if results:
            area_str = f"{results[0].area_m2:,.0f} m²" if results[0].area_m2 else "unknown"
            logger.info(f"[Overture] ✅ Found: {results[0].name} ({area_str})")
            return results[0]
        
        logger.info(f"[Overture] ⚪ No nature (beach/lake/forest/park/river) within {radius_m}m")
        return None

    def to_dict(self, place: OverturePlace) -> Dict[str, Any]:
        """Convert OverturePlace to dictionary for storage."""
        return {
            "source": "overture",
            "source_id": place.id,
            "name": place.name,
            "lat": place.lat,
            "lng": place.lng,
            "category": place.category,
            "nature_type": place.nature_type,
            "distance_m": place.distance_m,
            "area_m2": place.area_m2,
            "priority": place.priority,
        }


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def search_nature(lat: float, lng: float, radius: int = 2000) -> Optional[OverturePlace]:
    """
    Search for nature features with priority ordering (FREE via Overture/Athena).
    
    Priority: Beach > Lake > Forest > Large Park > Named River > Medium Park > Small Park
    
    Park thresholds:
    - Large: ≥20,000 m² (~2 hectares)
    - Medium: ≥10,000 m² (~1 hectare) - fallback
    - Small: ≥5,000 m² (~0.5 hectare) - last resort
    
    Returns the highest-priority nature feature found, or None.
    """
    client = OvertureClient()
    return await client.search_nature(lat, lng, radius_m=radius)
