# backend/tools/leo_call_transcriber.py

[Source](../../../../../backend/tools/leo_call_transcriber.py)

Leo Call Transcriber — Local Whisper + AWS Speaker Segments ============================================================

| Symbol | Kind | Source line |
|---|---|---|
| `_load_env` | FunctionDef | [L55](../../../../../backend/tools/leo_call_transcriber.py#L55) |
| `_get_twilio_auth` | FunctionDef | [L71](../../../../../backend/tools/leo_call_transcriber.py#L71) |
| `_get_aws_config` | FunctionDef | [L80](../../../../../backend/tools/leo_call_transcriber.py#L80) |
| `download_recording` | FunctionDef | [L94](../../../../../backend/tools/leo_call_transcriber.py#L94) |
| `convert_to_wav` | FunctionDef | [L129](../../../../../backend/tools/leo_call_transcriber.py#L129) |
| `run_whisper` | FunctionDef | [L150](../../../../../backend/tools/leo_call_transcriber.py#L150) |
| `upload_to_s3` | FunctionDef | [L196](../../../../../backend/tools/leo_call_transcriber.py#L196) |
| `start_aws_transcribe` | FunctionDef | [L216](../../../../../backend/tools/leo_call_transcriber.py#L216) |
| `poll_aws_transcribe` | FunctionDef | [L250](../../../../../backend/tools/leo_call_transcriber.py#L250) |
| `extract_aws_speaker_segments` | FunctionDef | [L322](../../../../../backend/tools/leo_call_transcriber.py#L322) |
| `stitch_transcripts` | FunctionDef | [L363](../../../../../backend/tools/leo_call_transcriber.py#L363) |
| `format_transcript_clean` | FunctionDef | [L424](../../../../../backend/tools/leo_call_transcriber.py#L424) |
| `generate_highlights` | AsyncFunctionDef | [L453](../../../../../backend/tools/leo_call_transcriber.py#L453) |
| `process_recording` | AsyncFunctionDef | [L536](../../../../../backend/tools/leo_call_transcriber.py#L536) |
| `_main` | AsyncFunctionDef | [L659](../../../../../backend/tools/leo_call_transcriber.py#L659) |
