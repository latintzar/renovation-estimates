# backend/whatsapp/tools.py

[Source](../../../../../backend/whatsapp/tools.py)

WhatsApp Agent Tools (OpenClaw-inspired) =======================================

| Symbol | Kind | Source line |
|---|---|---|
| `leo_tool` | FunctionDef | [L56](../../../../../backend/whatsapp/tools.py#L56) |
| `leo_tool._decorator` | FunctionDef | [L72](../../../../../backend/whatsapp/tools.py#L72) |
| `get_tool_function` | FunctionDef | [L95](../../../../../backend/whatsapp/tools.py#L95) |
| `get_tool_declarations` | FunctionDef | [L100](../../../../../backend/whatsapp/tools.py#L100) |
| `_get_rest` | AsyncFunctionDef | [L142](../../../../../backend/whatsapp/tools.py#L142) |
| `_select_single` | AsyncFunctionDef | [L150](../../../../../backend/whatsapp/tools.py#L150) |
| `_insert_row` | AsyncFunctionDef | [L170](../../../../../backend/whatsapp/tools.py#L170) |
| `_patch_rows` | AsyncFunctionDef | [L181](../../../../../backend/whatsapp/tools.py#L181) |
| `_slugify` | FunctionDef | [L191](../../../../../backend/whatsapp/tools.py#L191) |
| `_normalize_e164` | FunctionDef | [L202](../../../../../backend/whatsapp/tools.py#L202) |
| `_extract_email_address` | FunctionDef | [L209](../../../../../backend/whatsapp/tools.py#L209) |
| `_get_latest_active_project_for_phone` | AsyncFunctionDef | [L222](../../../../../backend/whatsapp/tools.py#L222) |
| `_get_tradesperson_by_id` | AsyncFunctionDef | [L240](../../../../../backend/whatsapp/tools.py#L240) |
| `_get_recent_tradespeople` | AsyncFunctionDef | [L248](../../../../../backend/whatsapp/tools.py#L248) |
| `_log_project_comm` | AsyncFunctionDef | [L269](../../../../../backend/whatsapp/tools.py#L269) |
| `_get_latest_image_version` | AsyncFunctionDef | [L303](../../../../../backend/whatsapp/tools.py#L303) |
| `_insert_image_version` | AsyncFunctionDef | [L322](../../../../../backend/whatsapp/tools.py#L322) |
| `_get_latest_image_versions_for_listing` | AsyncFunctionDef | [L348](../../../../../backend/whatsapp/tools.py#L348) |
| `_apply_style_patch_to_pro_list` | FunctionDef | [L382](../../../../../backend/whatsapp/tools.py#L382) |
| `_get_room_decisions` | AsyncFunctionDef | [L425](../../../../../backend/whatsapp/tools.py#L425) |
| `_upsert_room_decisions` | AsyncFunctionDef | [L437](../../../../../backend/whatsapp/tools.py#L437) |
| `_extract_pro_list_from_prompt` | FunctionDef | [L475](../../../../../backend/whatsapp/tools.py#L475) |
| `create_project` | AsyncFunctionDef | [L504](../../../../../backend/whatsapp/tools.py#L504) |
| `save_tradesperson` | AsyncFunctionDef | [L565](../../../../../backend/whatsapp/tools.py#L565) |
| `send_outreach_email` | AsyncFunctionDef | [L618](../../../../../backend/whatsapp/tools.py#L618) |
| `create_conference_call` | AsyncFunctionDef | [L735](../../../../../backend/whatsapp/tools.py#L735) |
| `mark_debrief_done` | AsyncFunctionDef | [L830](../../../../../backend/whatsapp/tools.py#L830) |
| `generate_room_vision` | AsyncFunctionDef | [L869](../../../../../backend/whatsapp/tools.py#L869) |
| `iterate_room_vision` | AsyncFunctionDef | [L1123](../../../../../backend/whatsapp/tools.py#L1123) |
| `estimate_costs` | AsyncFunctionDef | [L1260](../../../../../backend/whatsapp/tools.py#L1260) |
| `send_room_photos` | AsyncFunctionDef | [L1426](../../../../../backend/whatsapp/tools.py#L1426) |
| `style_consistency_check` | AsyncFunctionDef | [L1472](../../../../../backend/whatsapp/tools.py#L1472) |
| `get_room_analysis` | AsyncFunctionDef | [L1542](../../../../../backend/whatsapp/tools.py#L1542) |
| `save_memory` | AsyncFunctionDef | [L1599](../../../../../backend/whatsapp/tools.py#L1599) |
| `recall_memory` | AsyncFunctionDef | [L1656](../../../../../backend/whatsapp/tools.py#L1656) |
