# backend/whatsapp/agent.py

[Source](../../../../../backend/whatsapp/agent.py)

WhatsApp Agent ==============

| Symbol | Kind | Source line |
|---|---|---|
| `_save_conversation` | AsyncFunctionDef | [L126](../../../../../backend/whatsapp/agent.py#L126) |
| `_update_conversation` | AsyncFunctionDef | [L171](../../../../../backend/whatsapp/agent.py#L171) |
| `_get_processing_conversation_for_listing` | AsyncFunctionDef | [L190](../../../../../backend/whatsapp/agent.py#L190) |
| `_upsert_user_profile` | AsyncFunctionDef | [L217](../../../../../backend/whatsapp/agent.py#L217) |
| `_get_user_profile` | AsyncFunctionDef | [L244](../../../../../backend/whatsapp/agent.py#L244) |
| `_update_user_profile` | AsyncFunctionDef | [L261](../../../../../backend/whatsapp/agent.py#L261) |
| `_append_message` | AsyncFunctionDef | [L276](../../../../../backend/whatsapp/agent.py#L276) |
| `_get_recent_messages` | AsyncFunctionDef | [L324](../../../../../backend/whatsapp/agent.py#L324) |
| `_get_latest_listing_for_phone` | AsyncFunctionDef | [L349](../../../../../backend/whatsapp/agent.py#L349) |
| `_get_latest_active_project_for_phone` | AsyncFunctionDef | [L391](../../../../../backend/whatsapp/agent.py#L391) |
| `_get_pending_call_debriefs` | AsyncFunctionDef | [L430](../../../../../backend/whatsapp/agent.py#L430) |
| `_mark_debrief_done` | AsyncFunctionDef | [L471](../../../../../backend/whatsapp/agent.py#L471) |
| `_get_tradespeople_for_project` | AsyncFunctionDef | [L489](../../../../../backend/whatsapp/agent.py#L489) |
| `extract_listing_url` | FunctionDef | [L526](../../../../../backend/whatsapp/agent.py#L526) |
| `_is_social_url` | FunctionDef | [L562](../../../../../backend/whatsapp/agent.py#L562) |
| `_fetch_social_preview_media_item` | AsyncFunctionDef | [L570](../../../../../backend/whatsapp/agent.py#L570) |
| `_collapse_url_spaces` | FunctionDef | [L647](../../../../../backend/whatsapp/agent.py#L647) |
| `handle_inbound` | AsyncFunctionDef | [L677](../../../../../backend/whatsapp/agent.py#L677) |
| `run_coalesced_turn` | AsyncFunctionDef | [L849](../../../../../backend/whatsapp/agent.py#L849) |
| `_truncate` | FunctionDef | [L891](../../../../../backend/whatsapp/agent.py#L891) |
| `_handle_chat` | AsyncFunctionDef | [L898](../../../../../backend/whatsapp/agent.py#L898) |
| `_handle_chat._fast_reply_if_trivial` | FunctionDef | [L916](../../../../../backend/whatsapp/agent.py#L916) |
| `_handle_chat._fetch_as_b64` | AsyncFunctionDef | [L947](../../../../../backend/whatsapp/agent.py#L947) |
| `_handle_chat._msg_line` | FunctionDef | [L1193](../../../../../backend/whatsapp/agent.py#L1193) |
| `_handle_chat._compute_capabilities` | FunctionDef | [L1242](../../../../../backend/whatsapp/agent.py#L1242) |
| `_handle_chat._build_tool_declarations` | FunctionDef | [L1320](../../../../../backend/whatsapp/agent.py#L1320) |
| `_handle_chat._execute_tool` | AsyncFunctionDef | [L1325](../../../../../backend/whatsapp/agent.py#L1325) |
| `_handle_chat._build_room_inventory` | FunctionDef | [L1383](../../../../../backend/whatsapp/agent.py#L1383) |
| `_handle_chat._build_debrief_block` | FunctionDef | [L1469](../../../../../backend/whatsapp/agent.py#L1469) |
| `_handle_chat._build_prompt` | FunctionDef | [L1515](../../../../../backend/whatsapp/agent.py#L1515) |
| `handle_pipeline_complete` | AsyncFunctionDef | [L1750](../../../../../backend/whatsapp/agent.py#L1750) |
