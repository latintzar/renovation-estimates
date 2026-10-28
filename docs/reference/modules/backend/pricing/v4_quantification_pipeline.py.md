# backend/pricing/v4_quantification_pipeline.py

[Source](../../../../../backend/pricing/v4_quantification_pipeline.py)

V4 Quantification Pipeline (Full Implementation) ================================================

| Symbol | Kind | Source line |
|---|---|---|
| `_load_bcca_whole_dwelling_denylist_v1` | FunctionDef | [L50](../../../../../backend/pricing/v4_quantification_pipeline.py#L50) |
| `_is_whole_dwelling_bcca_item` | FunctionDef | [L73](../../../../../backend/pricing/v4_quantification_pipeline.py#L73) |
| `_require` | FunctionDef | [L115](../../../../../backend/pricing/v4_quantification_pipeline.py#L115) |
| `_extract_floorplan_urls` | FunctionDef | [L121](../../../../../backend/pricing/v4_quantification_pipeline.py#L121) |
| `_room_photo_urls_by_id` | FunctionDef | [L142](../../../../../backend/pricing/v4_quantification_pipeline.py#L142) |
| `_unit_family` | FunctionDef | [L159](../../../../../backend/pricing/v4_quantification_pipeline.py#L159) |
| `_safe_float` | FunctionDef | [L177](../../../../../backend/pricing/v4_quantification_pipeline.py#L177) |
| `_extract_listing_sqm` | FunctionDef | [L187](../../../../../backend/pricing/v4_quantification_pipeline.py#L187) |
| `_extract_room_estimated_m2_from_smart_m2` | FunctionDef | [L219](../../../../../backend/pricing/v4_quantification_pipeline.py#L219) |
| `_get_repo_root` | FunctionDef | [L235](../../../../../backend/pricing/v4_quantification_pipeline.py#L235) |
| `_get_default_bcca_matcher` | FunctionDef | [L239](../../../../../backend/pricing/v4_quantification_pipeline.py#L239) |
| `_get_repo_root_data_dir` | FunctionDef | [L250](../../../../../backend/pricing/v4_quantification_pipeline.py#L250) |
| `_load_bcca_codes_by_dimension_v1` | FunctionDef | [L256](../../../../../backend/pricing/v4_quantification_pipeline.py#L256) |
| `_dimension_scoped_matcher` | FunctionDef | [L277](../../../../../backend/pricing/v4_quantification_pipeline.py#L277) |
| `_safe_get` | FunctionDef | [L292](../../../../../backend/pricing/v4_quantification_pipeline.py#L292) |
| `_prefill_signals_from_smart_m2` | FunctionDef | [L307](../../../../../backend/pricing/v4_quantification_pipeline.py#L307) |
| `build_v4_worklist_prompt` | FunctionDef | [L360](../../../../../backend/pricing/v4_quantification_pipeline.py#L360) |
| `build_v4_quant_planner_prompt` | FunctionDef | [L459](../../../../../backend/pricing/v4_quantification_pipeline.py#L459) |
| `build_v4_quant_planner_prompt._compact_match` | FunctionDef | [L479](../../../../../backend/pricing/v4_quantification_pipeline.py#L479) |
| `build_v4_forage_prompt` | FunctionDef | [L599](../../../../../backend/pricing/v4_quantification_pipeline.py#L599) |
| `generate_v4_worklist_for_dimension` | AsyncFunctionDef | [L679](../../../../../backend/pricing/v4_quantification_pipeline.py#L679) |
| `_rerank_bcca_candidates_flash_lite` | AsyncFunctionDef | [L712](../../../../../backend/pricing/v4_quantification_pipeline.py#L712) |
| `match_v4_bcca` | AsyncFunctionDef | [L788](../../../../../backend/pricing/v4_quantification_pipeline.py#L788) |
| `match_v4_bcca._build_bcca_query_packet` | FunctionDef | [L799](../../../../../backend/pricing/v4_quantification_pipeline.py#L799) |
| `match_v4_bcca._desc_low` | FunctionDef | [L880](../../../../../backend/pricing/v4_quantification_pipeline.py#L880) |
| `match_v4_bcca._is_entry_door_item` | FunctionDef | [L883](../../../../../backend/pricing/v4_quantification_pipeline.py#L883) |
| `match_v4_bcca._rerank_one` | AsyncFunctionDef | [L912](../../../../../backend/pricing/v4_quantification_pipeline.py#L912) |
| `_plans_validate_or_raise` | FunctionDef | [L979](../../../../../backend/pricing/v4_quantification_pipeline.py#L979) |
| `_plans_validate_or_raise._normalize_formula_ast` | FunctionDef | [L1004](../../../../../backend/pricing/v4_quantification_pipeline.py#L1004) |
| `_plans_validate_or_raise._normalize_formula_ast._infer_family` | FunctionDef | [L1014](../../../../../backend/pricing/v4_quantification_pipeline.py#L1014) |
| `_plans_validate_or_raise._infer_formula_unit_family` | FunctionDef | [L1097](../../../../../backend/pricing/v4_quantification_pipeline.py#L1097) |
| `_plans_validate_or_raise._collect_signal_ids` | FunctionDef | [L1132](../../../../../backend/pricing/v4_quantification_pipeline.py#L1132) |
| `_plans_validate_or_raise._infer_unit_family_from_signal_id` | FunctionDef | [L1178](../../../../../backend/pricing/v4_quantification_pipeline.py#L1178) |
| `generate_v4_quant_plan` | AsyncFunctionDef | [L1211](../../../../../backend/pricing/v4_quantification_pipeline.py#L1211) |
| `generate_v4_quant_plan._run_once` | AsyncFunctionDef | [L1239](../../../../../backend/pricing/v4_quantification_pipeline.py#L1239) |
| `generate_v4_quant_plan._run_once._collect_plan_issues` | FunctionDef | [L1261](../../../../../backend/pricing/v4_quantification_pipeline.py#L1261) |
| `generate_v4_quant_plan._run_once._filter_worklist_dim` | FunctionDef | [L1335](../../../../../backend/pricing/v4_quantification_pipeline.py#L1335) |
| `generate_v4_quant_plan._run_room` | AsyncFunctionDef | [L1459](../../../../../backend/pricing/v4_quantification_pipeline.py#L1459) |
| `forage_v4_signals_for_room` | AsyncFunctionDef | [L1498](../../../../../backend/pricing/v4_quantification_pipeline.py#L1498) |
| `build_v4_zero_rescue_prompt` | FunctionDef | [L1610](../../../../../backend/pricing/v4_quantification_pipeline.py#L1610) |
| `resolve_zero_signals_for_room` | AsyncFunctionDef | [L1692](../../../../../backend/pricing/v4_quantification_pipeline.py#L1692) |
| `run_v4_for_strategy` | AsyncFunctionDef | [L1798](../../../../../backend/pricing/v4_quantification_pipeline.py#L1798) |
| `run_v4_for_strategy._load_signals_payload_into_store` | FunctionDef | [L1861](../../../../../backend/pricing/v4_quantification_pipeline.py#L1861) |
| `run_v4_for_strategy._checkpoint_signals` | AsyncFunctionDef | [L1911](../../../../../backend/pricing/v4_quantification_pipeline.py#L1911) |
| `run_v4_for_strategy._prepare_dimension` | AsyncFunctionDef | [L1945](../../../../../backend/pricing/v4_quantification_pipeline.py#L1945) |
| `run_v4_for_strategy._prepare_dimension._collect_signal_ids` | FunctionDef | [L2026](../../../../../backend/pricing/v4_quantification_pipeline.py#L2026) |
| `run_v4_for_strategy._prepare_dimension._infer_unit_family_from_signal_id` | FunctionDef | [L2044](../../../../../backend/pricing/v4_quantification_pipeline.py#L2044) |
| `run_v4_for_strategy._forage_room_once` | AsyncFunctionDef | [L2109](../../../../../backend/pricing/v4_quantification_pipeline.py#L2109) |
| `run_v4_for_strategy._assemble_dimension` | AsyncFunctionDef | [L2151](../../../../../backend/pricing/v4_quantification_pipeline.py#L2151) |
| `_cap_quantity` | FunctionDef | [L2224](../../../../../backend/pricing/v4_quantification_pipeline.py#L2224) |
| `assemble_v4_boq` | AsyncFunctionDef | [L2292](../../../../../backend/pricing/v4_quantification_pipeline.py#L2292) |
| `assemble_v4_boq._collect_signal_ids` | FunctionDef | [L2345](../../../../../backend/pricing/v4_quantification_pipeline.py#L2345) |
| `assemble_v4_boq._infer_unit_family_from_signal_id` | FunctionDef | [L2363](../../../../../backend/pricing/v4_quantification_pipeline.py#L2363) |
| `_worklist_dim_from_flat_items` | FunctionDef | [L2444](../../../../../backend/pricing/v4_quantification_pipeline.py#L2444) |
| `_ensure_smart_m2` | AsyncFunctionDef | [L2480](../../../../../backend/pricing/v4_quantification_pipeline.py#L2480) |
| `_ensure_smart_m2._OrchestratorShim` | ClassDef | [L2540](../../../../../backend/pricing/v4_quantification_pipeline.py#L2540) |
| `_ensure_smart_m2._OrchestratorShim.__init__` | FunctionDef | [L2542](../../../../../backend/pricing/v4_quantification_pipeline.py#L2542) |
| `run_v4_tail_from_v5_work_items` | AsyncFunctionDef | [L2563](../../../../../backend/pricing/v4_quantification_pipeline.py#L2563) |
| `run_v4_tail_from_v5_work_items._load_signals_payload_into_store` | FunctionDef | [L2631](../../../../../backend/pricing/v4_quantification_pipeline.py#L2631) |
| `run_v4_tail_from_v5_work_items._checkpoint_signals` | AsyncFunctionDef | [L2669](../../../../../backend/pricing/v4_quantification_pipeline.py#L2669) |
| `run_v4_tail_from_v5_work_items._prepare_dimension` | AsyncFunctionDef | [L2698](../../../../../backend/pricing/v4_quantification_pipeline.py#L2698) |
| `run_v4_tail_from_v5_work_items._prepare_dimension._collect_signal_ids` | FunctionDef | [L2747](../../../../../backend/pricing/v4_quantification_pipeline.py#L2747) |
| `run_v4_tail_from_v5_work_items._prepare_dimension._infer_unit_family_from_signal_id` | FunctionDef | [L2765](../../../../../backend/pricing/v4_quantification_pipeline.py#L2765) |
| `run_v4_tail_from_v5_work_items._forage_room_once` | AsyncFunctionDef | [L2803](../../../../../backend/pricing/v4_quantification_pipeline.py#L2803) |
| `run_v4_tail_from_v5_work_items._zero_rescue_room` | AsyncFunctionDef | [L2874](../../../../../backend/pricing/v4_quantification_pipeline.py#L2874) |
| `run_v4_tail_from_v5_work_items._assemble_dimension` | AsyncFunctionDef | [L2952](../../../../../backend/pricing/v4_quantification_pipeline.py#L2952) |
