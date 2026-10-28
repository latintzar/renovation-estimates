# backend/pricing/v5_strategy_delta_decompose.py

[Source](../../../../../backend/pricing/v5_strategy_delta_decompose.py)

V5 Strategy Targets, Delta Slots, and Work-item Decomposition.

| Symbol | Kind | Source line |
|---|---|---|
| `_clean_json_text` | FunctionDef | [L26](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L26) |
| `_safe_json_loads` | FunctionDef | [L40](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L40) |
| `generate_v5_strategy_targets` | AsyncFunctionDef | [L65](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L65) |
| `generate_v5_delta_for_room` | AsyncFunctionDef | [L91](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L91) |
| `generate_v5_delta_for_room._strip_fences` | FunctionDef | [L102](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L102) |
| `generate_v5_delta_for_room._fallback_one_liner` | FunctionDef | [L112](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L112) |
| `generate_v5_delta_for_room._is_valid_one_liner` | FunctionDef | [L122](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L122) |
| `_normalize_delta_text` | FunctionDef | [L226](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L226) |
| `apply_v5_delta_cross_room_patches` | FunctionDef | [L230](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L230) |
| `review_v5_delta_slots_cross_room` | AsyncFunctionDef | [L302](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L302) |
| `_slot_id_to_dimension` | FunctionDef | [L354](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L354) |
| `decompose_v5_slot_one_liner` | AsyncFunctionDef | [L371](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L371) |
| `decompose_v5_room_dimension` | AsyncFunctionDef | [L417](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L417) |
| `decompose_v5_room_all_dimensions` | AsyncFunctionDef | [L479](../../../../../backend/pricing/v5_strategy_delta_decompose.py#L479) |
