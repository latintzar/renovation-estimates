# backend/routes/curation_v2.py

[Source](../../../../../backend/routes/curation_v2.py)

Place Curation V3 - Google-Powered Curation System ==================================================

| Symbol | Kind | Source line |
|---|---|---|
| `CuratedPlaceV2` | ClassDef | [L44](../../../../../backend/routes/curation_v2.py#L44) |
| `CuratedPlaceV2.to_dict` | FunctionDef | [L69](../../../../../backend/routes/curation_v2.py#L69) |
| `CuratedPlaceResponse` | ClassDef | [L74](../../../../../backend/routes/curation_v2.py#L74) |
| `CurationResponse` | ClassDef | [L105](../../../../../backend/routes/curation_v2.py#L105) |
| `TourGenerationResponse` | ClassDef | [L119](../../../../../backend/routes/curation_v2.py#L119) |
| `_verify_coordinates_with_google` | AsyncFunctionDef | [L162](../../../../../backend/routes/curation_v2.py#L162) |
| `_fetch_foursquare_places` | AsyncFunctionDef | [L251](../../../../../backend/routes/curation_v2.py#L251) |
| `_fetch_transit_stops` | AsyncFunctionDef | [L285](../../../../../backend/routes/curation_v2.py#L285) |
| `_save_curated_places` | AsyncFunctionDef | [L312](../../../../../backend/routes/curation_v2.py#L312) |
| `_cache_tiles_for_curation` | AsyncFunctionDef | [L369](../../../../../backend/routes/curation_v2.py#L369) |
| `curate_places` | AsyncFunctionDef | [L460](../../../../../backend/routes/curation_v2.py#L460) |
| `_get_curated_places_from_db` | AsyncFunctionDef | [L541](../../../../../backend/routes/curation_v2.py#L541) |
| `_place_to_response` | FunctionDef | [L581](../../../../../backend/routes/curation_v2.py#L581) |
| `_save_curated_places_v3` | AsyncFunctionDef | [L606](../../../../../backend/routes/curation_v2.py#L606) |
| `get_curated_places` | AsyncFunctionDef | [L693](../../../../../backend/routes/curation_v2.py#L693) |
| `get_stop_departures` | AsyncFunctionDef | [L769](../../../../../backend/routes/curation_v2.py#L769) |
| `get_transit_isochrone` | AsyncFunctionDef | [L824](../../../../../backend/routes/curation_v2.py#L824) |
| `get_isochrone_by_id` | AsyncFunctionDef | [L895](../../../../../backend/routes/curation_v2.py#L895) |
| `generate_tours_for_listing` | AsyncFunctionDef | [L929](../../../../../backend/routes/curation_v2.py#L929) |
| `generate_tours_for_listing.generate_tour_for_place` | AsyncFunctionDef | [L1024](../../../../../backend/routes/curation_v2.py#L1024) |
