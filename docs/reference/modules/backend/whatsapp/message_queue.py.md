# backend/whatsapp/message_queue.py

[Source](../../../../../backend/whatsapp/message_queue.py)

WhatsApp Message Queue (OpenClaw-inspired) =========================================

| Symbol | Kind | Source line |
|---|---|---|
| `_now_s` | FunctionDef | [L38](../../../../../backend/whatsapp/message_queue.py#L38) |
| `_env_int` | FunctionDef | [L42](../../../../../backend/whatsapp/message_queue.py#L42) |
| `BufferedMessage` | ClassDef | [L56](../../../../../backend/whatsapp/message_queue.py#L56) |
| `CoalescedTurn` | ClassDef | [L65](../../../../../backend/whatsapp/message_queue.py#L65) |
| `_looks_like_url` | FunctionDef | [L73](../../../../../backend/whatsapp/message_queue.py#L73) |
| `_has_media_kind` | FunctionDef | [L78](../../../../../backend/whatsapp/message_queue.py#L78) |
| `_inline_audio_part_from_media_items` | FunctionDef | [L95](../../../../../backend/whatsapp/message_queue.py#L95) |
| `_transcribe_voice_note` | AsyncFunctionDef | [L117](../../../../../backend/whatsapp/message_queue.py#L117) |
| `coalesce_messages` | AsyncFunctionDef | [L146](../../../../../backend/whatsapp/message_queue.py#L146) |
| `_coalesce_turns` | FunctionDef | [L191](../../../../../backend/whatsapp/message_queue.py#L191) |
| `SessionQueue` | ClassDef | [L212](../../../../../backend/whatsapp/message_queue.py#L212) |
| `SessionQueue.__init__` | FunctionDef | [L220](../../../../../backend/whatsapp/message_queue.py#L220) |
| `SessionQueue.enqueue` | AsyncFunctionDef | [L225](../../../../../backend/whatsapp/message_queue.py#L225) |
| `SessionQueue.drain_pending` | FunctionDef | [L238](../../../../../backend/whatsapp/message_queue.py#L238) |
| `SessionQueue._run_session` | AsyncFunctionDef | [L246](../../../../../backend/whatsapp/message_queue.py#L246) |
| `SessionQueue._run_turn` | AsyncFunctionDef | [L274](../../../../../backend/whatsapp/message_queue.py#L274) |
| `MessageBuffer` | ClassDef | [L289](../../../../../backend/whatsapp/message_queue.py#L289) |
| `MessageBuffer.__init__` | FunctionDef | [L292](../../../../../backend/whatsapp/message_queue.py#L292) |
| `MessageBuffer.push` | AsyncFunctionDef | [L298](../../../../../backend/whatsapp/message_queue.py#L298) |
| `MessageBuffer._debounce_wait_and_flush` | AsyncFunctionDef | [L345](../../../../../backend/whatsapp/message_queue.py#L345) |
| `MessageBuffer.flush` | AsyncFunctionDef | [L354](../../../../../backend/whatsapp/message_queue.py#L354) |
| `WhatsAppMessageQueue` | ClassDef | [L383](../../../../../backend/whatsapp/message_queue.py#L383) |
| `WhatsAppMessageQueue.__init__` | FunctionDef | [L384](../../../../../backend/whatsapp/message_queue.py#L384) |
| `WhatsAppMessageQueue.push` | AsyncFunctionDef | [L388](../../../../../backend/whatsapp/message_queue.py#L388) |
| `get_queue` | FunctionDef | [L395](../../../../../backend/whatsapp/message_queue.py#L395) |
