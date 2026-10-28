# backend/pipeline/gemini_client.py

[Source](../../../../../backend/pipeline/gemini_client.py)

Gemini Client for Lean MVP Pipeline (using google-generativeai SDK) ===================================================================

| Symbol | Kind | Source line |
|---|---|---|
| `set_gemini_tracking_context` | FunctionDef | [L43](../../../../../backend/pipeline/gemini_client.py#L43) |
| `clear_gemini_tracking_context` | FunctionDef | [L57](../../../../../backend/pipeline/gemini_client.py#L57) |
| `_usage_metadata_to_dict` | FunctionDef | [L63](../../../../../backend/pipeline/gemini_client.py#L63) |
| `_usage_metadata_to_dict._safe_default` | FunctionDef | [L104](../../../../../backend/pipeline/gemini_client.py#L104) |
| `_get_usage_int` | FunctionDef | [L128](../../../../../backend/pipeline/gemini_client.py#L128) |
| `TokenTracker` | ClassDef | [L144](../../../../../backend/pipeline/gemini_client.py#L144) |
| `TokenTracker.__init__` | FunctionDef | [L333](../../../../../backend/pipeline/gemini_client.py#L333) |
| `TokenTracker.get_instance` | FunctionDef | [L337](../../../../../backend/pipeline/gemini_client.py#L337) |
| `TokenTracker.reset` | FunctionDef | [L342](../../../../../backend/pipeline/gemini_client.py#L342) |
| `TokenTracker.set_stage` | FunctionDef | [L356](../../../../../backend/pipeline/gemini_client.py#L356) |
| `TokenTracker.track` | FunctionDef | [L362](../../../../../backend/pipeline/gemini_client.py#L362) |
| `TokenTracker.report` | FunctionDef | [L513](../../../../../backend/pipeline/gemini_client.py#L513) |
| `TokenTracker.log_summary` | FunctionDef | [L559](../../../../../backend/pipeline/gemini_client.py#L559) |
| `TokenTracker.log_stage_progress` | FunctionDef | [L618](../../../../../backend/pipeline/gemini_client.py#L618) |
| `_validate_gemini_pricing_tables` | FunctionDef | [L659](../../../../../backend/pipeline/gemini_client.py#L659) |
| `get_token_tracker` | FunctionDef | [L697](../../../../../backend/pipeline/gemini_client.py#L697) |
| `_is_rate_limit_error` | FunctionDef | [L713](../../../../../backend/pipeline/gemini_client.py#L713) |
| `_compress_to_jpeg` | FunctionDef | [L719](../../../../../backend/pipeline/gemini_client.py#L719) |
| `get_api_key` | FunctionDef | [L769](../../../../../backend/pipeline/gemini_client.py#L769) |
| `GeminiResponse` | ClassDef | [L778](../../../../../backend/pipeline/gemini_client.py#L778) |
| `call_gemini` | AsyncFunctionDef | [L796](../../../../../backend/pipeline/gemini_client.py#L796) |
| `_call_gemini_single` | AsyncFunctionDef | [L869](../../../../../backend/pipeline/gemini_client.py#L869) |
| `_call_gemini_single._keepalive` | AsyncFunctionDef | [L968](../../../../../backend/pipeline/gemini_client.py#L968) |
| `_call_gemini_single._args_to_dict` | FunctionDef | [L1015](../../../../../backend/pipeline/gemini_client.py#L1015) |
| `call_gemini_json` | AsyncFunctionDef | [L1255](../../../../../backend/pipeline/gemini_client.py#L1255) |
| `fetch_image_as_base64` | AsyncFunctionDef | [L1303](../../../../../backend/pipeline/gemini_client.py#L1303) |
| `_guess_mime_type_from_path` | FunctionDef | [L1369](../../../../../backend/pipeline/gemini_client.py#L1369) |
| `fetch_image_source_as_base64` | AsyncFunctionDef | [L1382](../../../../../backend/pipeline/gemini_client.py#L1382) |
| `fetch_images_batch` | AsyncFunctionDef | [L1410](../../../../../backend/pipeline/gemini_client.py#L1410) |
| `fetch_images_batch.fetch_with_semaphore` | AsyncFunctionDef | [L1420](../../../../../backend/pipeline/gemini_client.py#L1420) |
| `call_gemini_image` | AsyncFunctionDef | [L1430](../../../../../backend/pipeline/gemini_client.py#L1430) |
