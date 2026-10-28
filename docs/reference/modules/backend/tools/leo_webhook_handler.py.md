# backend/tools/leo_webhook_handler.py

[Source](../../../../../backend/tools/leo_webhook_handler.py)

Leo Webhook Handler — processes inbound emails and routes to WhatsApp.

| Symbol | Kind | Source line |
|---|---|---|
| `_load_env` | FunctionDef | [L33](../../../../../backend/tools/leo_webhook_handler.py#L33) |
| `_get_resend_webhook_secret` | FunctionDef | [L50](../../../../../backend/tools/leo_webhook_handler.py#L50) |
| `_get_email_domain` | FunctionDef | [L63](../../../../../backend/tools/leo_webhook_handler.py#L63) |
| `verify_signature` | FunctionDef | [L68](../../../../../backend/tools/leo_webhook_handler.py#L68) |
| `extract_project_id` | FunctionDef | [L79](../../../../../backend/tools/leo_webhook_handler.py#L79) |
| `send_whatsapp` | FunctionDef | [L91](../../../../../backend/tools/leo_webhook_handler.py#L91) |
| `format_email_summary` | FunctionDef | [L130](../../../../../backend/tools/leo_webhook_handler.py#L130) |
| `handle_email_received` | FunctionDef | [L165](../../../../../backend/tools/leo_webhook_handler.py#L165) |
| `handle_webhook` | FunctionDef | [L212](../../../../../backend/tools/leo_webhook_handler.py#L212) |
| `simulate_from_webhook_site` | FunctionDef | [L231](../../../../../backend/tools/leo_webhook_handler.py#L231) |
