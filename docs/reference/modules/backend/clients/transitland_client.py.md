# backend/clients/transitland_client.py

[Source](../../../../../backend/clients/transitland_client.py)

Transitland REST API Client ===========================

| Symbol | Kind | Source line |
|---|---|---|
| `RouteType` | ClassDef | [L38](../../../../../backend/clients/transitland_client.py#L38) |
| `TransitRoute` | ClassDef | [L68](../../../../../backend/clients/transitland_client.py#L68) |
| `ServiceInfo` | ClassDef | [L93](../../../../../backend/clients/transitland_client.py#L93) |
| `TransitStop` | ClassDef | [L104](../../../../../backend/clients/transitland_client.py#L104) |
| `TransitStop.__post_init__` | FunctionDef | [L124](../../../../../backend/clients/transitland_client.py#L124) |
| `TransitStop.route_names` | FunctionDef | [L129](../../../../../backend/clients/transitland_client.py#L129) |
| `TransitStop.is_metro` | FunctionDef | [L134](../../../../../backend/clients/transitland_client.py#L134) |
| `TransitStop.is_train` | FunctionDef | [L138](../../../../../backend/clients/transitland_client.py#L138) |
| `TransitStop.is_bus` | FunctionDef | [L142](../../../../../backend/clients/transitland_client.py#L142) |
| `TransitStop.is_tram` | FunctionDef | [L146](../../../../../backend/clients/transitland_client.py#L146) |
| `TransitStop.primary_type` | FunctionDef | [L150](../../../../../backend/clients/transitland_client.py#L150) |
| `TransitlandClient` | ClassDef | [L164](../../../../../backend/clients/transitland_client.py#L164) |
| `TransitlandClient.__init__` | FunctionDef | [L173](../../../../../backend/clients/transitland_client.py#L173) |
| `TransitlandClient.search_stops` | AsyncFunctionDef | [L181](../../../../../backend/clients/transitland_client.py#L181) |
| `TransitlandClient.search_metro_and_train` | AsyncFunctionDef | [L244](../../../../../backend/clients/transitland_client.py#L244) |
| `TransitlandClient.search_bus_and_tram` | AsyncFunctionDef | [L277](../../../../../backend/clients/transitland_client.py#L277) |
| `TransitlandClient.get_all_transit` | AsyncFunctionDef | [L309](../../../../../backend/clients/transitland_client.py#L309) |
| `TransitlandClient.get_accessible_lines` | AsyncFunctionDef | [L359](../../../../../backend/clients/transitland_client.py#L359) |
| `TransitlandClient._get_routes_with_actual_stops` | AsyncFunctionDef | [L470](../../../../../backend/clients/transitland_client.py#L470) |
| `TransitlandClient.get_routes_near_location` | AsyncFunctionDef | [L569](../../../../../backend/clients/transitland_client.py#L569) |
| `TransitlandClient.enrich_stop_with_routes` | AsyncFunctionDef | [L647](../../../../../backend/clients/transitland_client.py#L647) |
| `TransitlandClient._parse_stop` | FunctionDef | [L664](../../../../../backend/clients/transitland_client.py#L664) |
| `TransitlandClient._haversine_distance` | FunctionDef | [L690](../../../../../backend/clients/transitland_client.py#L690) |
| `TransitlandClient.to_dict` | FunctionDef | [L707](../../../../../backend/clients/transitland_client.py#L707) |
| `TransitlandClient.get_stop_departures` | AsyncFunctionDef | [L722](../../../../../backend/clients/transitland_client.py#L722) |
| `TransitlandClient._time_to_minutes` | FunctionDef | [L831](../../../../../backend/clients/transitland_client.py#L831) |
| `get_nearest_transit` | AsyncFunctionDef | [L843](../../../../../backend/clients/transitland_client.py#L843) |
