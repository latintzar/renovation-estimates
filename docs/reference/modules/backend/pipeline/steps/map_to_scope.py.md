# backend/pipeline/steps/map_to_scope.py

[Source](../../../../../../backend/pipeline/steps/map_to_scope.py)

========================================================= PHASE 2: SCOPE MAPPER ========================================================= Maps detected conditions from Phase 1 to remedial task scopes.

| Symbol | Kind | Source line |
|---|---|---|
| `ScopeTask` | ClassDef | [L44](../../../../../../backend/pipeline/steps/map_to_scope.py#L44) |
| `PackageScopeResult` | ClassDef | [L62](../../../../../../backend/pipeline/steps/map_to_scope.py#L62) |
| `PackageScopeResult.task_count` | FunctionDef | [L71](../../../../../../backend/pipeline/steps/map_to_scope.py#L71) |
| `PackageScopeResult.systems_covered` | FunctionDef | [L75](../../../../../../backend/pipeline/steps/map_to_scope.py#L75) |
| `run_ps2_package_scopes` | AsyncFunctionDef | [L83](../../../../../../backend/pipeline/steps/map_to_scope.py#L83) |
| `_parse_tasks` | FunctionDef | [L246](../../../../../../backend/pipeline/steps/map_to_scope.py#L246) |
| `_group_tasks_by_room` | FunctionDef | [L273](../../../../../../backend/pipeline/steps/map_to_scope.py#L273) |
| `_save_empty_scopes` | AsyncFunctionDef | [L291](../../../../../../backend/pipeline/steps/map_to_scope.py#L291) |
