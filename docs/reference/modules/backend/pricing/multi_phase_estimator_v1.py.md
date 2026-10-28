# backend/pricing/multi_phase_estimator_v1.py

[Source](../../../../../backend/pricing/multi_phase_estimator_v1.py)

V2 Multi-Phase Estimation Orchestrator - Post-BOQ Phases ========================================================

| Symbol | Kind | Source line |
|---|---|---|
| `sanitize_gemini_json` | FunctionDef | [L56](../../../../../backend/pricing/multi_phase_estimator_v1.py#L56) |
| `sanitize_gemini_json.truncate_decimal` | FunctionDef | [L68](../../../../../backend/pricing/multi_phase_estimator_v1.py#L68) |
| `MultiPhaseEstimatorV1` | ClassDef | [L187](../../../../../backend/pricing/multi_phase_estimator_v1.py#L187) |
| `MultiPhaseEstimatorV1.__init__` | FunctionDef | [L210](../../../../../backend/pricing/multi_phase_estimator_v1.py#L210) |
| `MultiPhaseEstimatorV1.estimate` | AsyncFunctionDef | [L254](../../../../../backend/pricing/multi_phase_estimator_v1.py#L254) |
| `MultiPhaseEstimatorV1._build_room_photos_from_canonical` | FunctionDef | [L408](../../../../../backend/pricing/multi_phase_estimator_v1.py#L408) |
| `MultiPhaseEstimatorV1._execute_phase_1_boq` | AsyncFunctionDef | [L442](../../../../../backend/pricing/multi_phase_estimator_v1.py#L442) |
| `MultiPhaseEstimatorV1._execute_phase_3_peer_review` | AsyncFunctionDef | [L546](../../../../../backend/pricing/multi_phase_estimator_v1.py#L546) |
| `MultiPhaseEstimatorV1._apply_review_plan` | FunctionDef | [L666](../../../../../backend/pricing/multi_phase_estimator_v1.py#L666) |
| `MultiPhaseEstimatorV1._build_phase_3_output` | FunctionDef | [L770](../../../../../backend/pricing/multi_phase_estimator_v1.py#L770) |
| `MultiPhaseEstimatorV1._assess_cost_per_sqm` | FunctionDef | [L817](../../../../../backend/pricing/multi_phase_estimator_v1.py#L817) |
| `MultiPhaseEstimatorV1._execute_phase_4_rendering_prompts` | AsyncFunctionDef | [L836](../../../../../backend/pricing/multi_phase_estimator_v1.py#L836) |
| `MultiPhaseEstimatorV1.generate_rendering_prompts` | AsyncFunctionDef | [L849](../../../../../backend/pricing/multi_phase_estimator_v1.py#L849) |
| `MultiPhaseEstimatorV1._build_phase_4_prompt` | FunctionDef | [L971](../../../../../backend/pricing/multi_phase_estimator_v1.py#L971) |
| `MultiPhaseEstimatorV1._execute_phase_5_image_generation` | AsyncFunctionDef | [L1026](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1026) |
| `MultiPhaseEstimatorV1.generate_images` | AsyncFunctionDef | [L1039](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1039) |
| `MultiPhaseEstimatorV1._execute_phase_7_eli5_summaries` | AsyncFunctionDef | [L1204](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1204) |
| `MultiPhaseEstimatorV1.generate_eli5_summaries` | AsyncFunctionDef | [L1215](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1215) |
| `MultiPhaseEstimatorV1._execute_phase_8_architect_report` | AsyncFunctionDef | [L1335](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1335) |
| `MultiPhaseEstimatorV1.generate_architect_report` | AsyncFunctionDef | [L1346](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1346) |
| `MultiPhaseEstimatorV1._build_cached_context` | FunctionDef | [L1482](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1482) |
| `MultiPhaseEstimatorV1._build_canonical_rooms_section` | FunctionDef | [L1644](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1644) |
| `MultiPhaseEstimatorV1._build_smart_m2_section` | FunctionDef | [L1670](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1670) |
| `MultiPhaseEstimatorV1._init_price_lookups` | FunctionDef | [L1708](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1708) |
| `MultiPhaseEstimatorV1._load_file` | FunctionDef | [L1729](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1729) |
| `MultiPhaseEstimatorV1._load_json` | FunctionDef | [L1739](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1739) |
| `MultiPhaseEstimatorV1._call_gemini_with_retry` | AsyncFunctionDef | [L1757](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1757) |
| `MultiPhaseEstimatorV1._parse_json_response` | FunctionDef | [L1815](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1815) |
| `MultiPhaseEstimatorV1._build_unified_estimate` | FunctionDef | [L1857](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1857) |
| `MultiPhaseEstimatorV1._log_banner` | FunctionDef | [L1961](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1961) |
| `MultiPhaseEstimatorV1._log_separator` | FunctionDef | [L1968](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1968) |
| `MultiPhaseEstimatorV1._log_phase_start` | FunctionDef | [L1972](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1972) |
| `MultiPhaseEstimatorV1.get_phase_output` | FunctionDef | [L1983](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1983) |
| `MultiPhaseEstimatorV1.get_all_phase_outputs` | FunctionDef | [L1987](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1987) |
| `MultiPhaseEstimatorV1.get_current_items` | FunctionDef | [L1991](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1991) |
| `MultiPhaseEstimatorV1.get_checkpoints_completed` | FunctionDef | [L1995](../../../../../backend/pricing/multi_phase_estimator_v1.py#L1995) |
