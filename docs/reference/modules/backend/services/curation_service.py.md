# backend/services/curation_service.py

[Source](../../../../../backend/services/curation_service.py)

Place Curation Service V3 =========================

| Symbol | Kind | Source line |
|---|---|---|
| `point_in_isochrone` | FunctionDef | [L60](../../../../../backend/services/curation_service.py#L60) |
| `_point_in_polygon` | FunctionDef | [L102](../../../../../backend/services/curation_service.py#L102) |
| `CuratedPlaceV2` | ClassDef | [L155](../../../../../backend/services/curation_service.py#L155) |
| `CuratedPlaceV2.to_dict` | FunctionDef | [L198](../../../../../backend/services/curation_service.py#L198) |
| `calculate_walking_time` | FunctionDef | [L233](../../../../../backend/services/curation_service.py#L233) |
| `calculate_travel_times` | FunctionDef | [L254](../../../../../backend/services/curation_service.py#L254) |
| `calculate_heading` | FunctionDef | [L274](../../../../../backend/services/curation_service.py#L274) |
| `haversine_distance` | FunctionDef | [L287](../../../../../backend/services/curation_service.py#L287) |
| `CurationService` | ClassDef | [L305](../../../../../backend/services/curation_service.py#L305) |
| `CurationService.__init__` | FunctionDef | [L319](../../../../../backend/services/curation_service.py#L319) |
| `CurationService.curate_places` | AsyncFunctionDef | [L330](../../../../../backend/services/curation_service.py#L330) |
| `CurationService._mark_empty_slot` | FunctionDef | [L466](../../../../../backend/services/curation_service.py#L466) |
| `CurationService._curate_grocery` | AsyncFunctionDef | [L476](../../../../../backend/services/curation_service.py#L476) |
| `CurationService._curate_transit` | AsyncFunctionDef | [L554](../../../../../backend/services/curation_service.py#L554) |
| `CurationService._curate_transit.filter_by_isochrone` | FunctionDef | [L587](../../../../../backend/services/curation_service.py#L587) |
| `CurationService._build_routes_with_stations` | AsyncFunctionDef | [L655](../../../../../backend/services/curation_service.py#L655) |
| `CurationService._transit_to_curated_v2` | FunctionDef | [L758](../../../../../backend/services/curation_service.py#L758) |
| `CurationService._curate_late_night` | AsyncFunctionDef | [L793](../../../../../backend/services/curation_service.py#L793) |
| `CurationService._curate_street_activity` | AsyncFunctionDef | [L832](../../../../../backend/services/curation_service.py#L832) |
| `CurationService._curate_hospital` | AsyncFunctionDef | [L880](../../../../../backend/services/curation_service.py#L880) |
| `CurationService._curate_gas_station` | AsyncFunctionDef | [L919](../../../../../backend/services/curation_service.py#L919) |
| `CurationService._curate_local_special` | AsyncFunctionDef | [L943](../../../../../backend/services/curation_service.py#L943) |
| `CurationService._enrich_with_streetview` | AsyncFunctionDef | [L987](../../../../../backend/services/curation_service.py#L987) |
| `CurationService._is_quality_google_place` | FunctionDef | [L1019](../../../../../backend/services/curation_service.py#L1019) |
| `CurationService._google_to_curated` | FunctionDef | [L1032](../../../../../backend/services/curation_service.py#L1032) |
| `CurationService._google_type_to_category` | FunctionDef | [L1068](../../../../../backend/services/curation_service.py#L1068) |
| `curate_places_for_listing` | AsyncFunctionDef | [L1102](../../../../../backend/services/curation_service.py#L1102) |
