"""
API Clients for Place Curation
==============================

- foursquare_client: Grocery, lifestyle, hospital, local_special POIs ($15/1000)
- transitland_client: Metro, bus, train stops from GTFS ($1/1000)
- overture_client: Parks, beaches, green spaces (FREE!)
- streetview_client: Google Street View tiles
- google_places_client: Coordinate verification ($17/1000) - Find Place API
"""

from .foursquare_client import FoursquareClient
from .transitland_client import TransitlandClient
from .streetview_client import StreetViewClient
from .overture_client import OvertureClient
from .google_places_client import GooglePlacesClient, verify_poi_coordinates

__all__ = [
    'FoursquareClient', 
    'TransitlandClient', 
    'StreetViewClient', 
    'OvertureClient',
    'GooglePlacesClient',
    'verify_poi_coordinates',
]
