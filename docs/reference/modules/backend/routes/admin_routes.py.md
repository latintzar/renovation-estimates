# backend/routes/admin_routes.py

[Source](../../../../../backend/routes/admin_routes.py)

Admin Routes — Pipeline Admin Dashboard ========================================

| Symbol | Kind | Source line |
|---|---|---|
| `RunSummary` | ClassDef | [L64](../../../../../backend/routes/admin_routes.py#L64) |
| `RunDetail` | ClassDef | [L83](../../../../../backend/routes/admin_routes.py#L83) |
| `LogEntry` | ClassDef | [L87](../../../../../backend/routes/admin_routes.py#L87) |
| `_enrich_run_with_jobs` | AsyncFunctionDef | [L103](../../../../../backend/routes/admin_routes.py#L103) |
| `list_runs` | AsyncFunctionDef | [L185](../../../../../backend/routes/admin_routes.py#L185) |
| `get_run_detail` | AsyncFunctionDef | [L247](../../../../../backend/routes/admin_routes.py#L247) |
| `get_run_logs` | AsyncFunctionDef | [L281](../../../../../backend/routes/admin_routes.py#L281) |
| `get_run_costs` | AsyncFunctionDef | [L371](../../../../../backend/routes/admin_routes.py#L371) |
| `get_run_costs._to_float` | FunctionDef | [L382](../../../../../backend/routes/admin_routes.py#L382) |
| `get_run_costs._compute_clean_run_timing` | AsyncFunctionDef | [L388](../../../../../backend/routes/admin_routes.py#L388) |
| `get_pipeline_version` | AsyncFunctionDef | [L533](../../../../../backend/routes/admin_routes.py#L533) |
| `list_listings` | AsyncFunctionDef | [L561](../../../../../backend/routes/admin_routes.py#L561) |
| `get_listing_detail` | AsyncFunctionDef | [L645](../../../../../backend/routes/admin_routes.py#L645) |
| `get_gla_detail` | AsyncFunctionDef | [L715](../../../../../backend/routes/admin_routes.py#L715) |
| `ClearFromStageRequest` | ClassDef | [L888](../../../../../backend/routes/admin_routes.py#L888) |
| `clear_from_stage` | AsyncFunctionDef | [L893](../../../../../backend/routes/admin_routes.py#L893) |
| `stop_listing` | AsyncFunctionDef | [L1401](../../../../../backend/routes/admin_routes.py#L1401) |
| `stop_all_pipelines` | AsyncFunctionDef | [L1450](../../../../../backend/routes/admin_routes.py#L1450) |
| `resume_all_pipelines` | AsyncFunctionDef | [L1490](../../../../../backend/routes/admin_routes.py#L1490) |
| `resume_listing` | AsyncFunctionDef | [L1532](../../../../../backend/routes/admin_routes.py#L1532) |
| `delete_listing` | AsyncFunctionDef | [L1588](../../../../../backend/routes/admin_routes.py#L1588) |
| `_delete_artifact` | AsyncFunctionDef | [L1689](../../../../../backend/routes/admin_routes.py#L1689) |
