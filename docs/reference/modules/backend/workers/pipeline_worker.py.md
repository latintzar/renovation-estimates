# backend/workers/pipeline_worker.py

[Source](../../../../../backend/workers/pipeline_worker.py)

| Symbol | Kind | Source line |
|---|---|---|
| `BlockedByPredecessor` | ClassDef | [L35](../../../../../backend/workers/pipeline_worker.py#L35) |
| `_PipelineDbLogHandler` | ClassDef | [L73](../../../../../backend/workers/pipeline_worker.py#L73) |
| `_PipelineDbLogHandler.__init__` | FunctionDef | [L74](../../../../../backend/workers/pipeline_worker.py#L74) |
| `_PipelineDbLogHandler.emit` | FunctionDef | [L78](../../../../../backend/workers/pipeline_worker.py#L78) |
| `_emit_progress_event` | AsyncFunctionDef | [L99](../../../../../backend/workers/pipeline_worker.py#L99) |
| `_stall_watchdog` | AsyncFunctionDef | [L120](../../../../../backend/workers/pipeline_worker.py#L120) |
| `_cancel_watchdog` | AsyncFunctionDef | [L175](../../../../../backend/workers/pipeline_worker.py#L175) |
| `_flush_job_logs_to_db` | AsyncFunctionDef | [L232](../../../../../backend/workers/pipeline_worker.py#L232) |
| `_job_log_streamer` | AsyncFunctionDef | [L267](../../../../../backend/workers/pipeline_worker.py#L267) |
| `_worker_id` | FunctionDef | [L284](../../../../../backend/workers/pipeline_worker.py#L284) |
| `_handle_noop` | AsyncFunctionDef | [L290](../../../../../backend/workers/pipeline_worker.py#L290) |
| `_dispatch` | AsyncFunctionDef | [L294](../../../../../backend/workers/pipeline_worker.py#L294) |
| `_heartbeat_loop` | AsyncFunctionDef | [L300](../../../../../backend/workers/pipeline_worker.py#L300) |
| `_run_loop` | AsyncFunctionDef | [L326](../../../../../backend/workers/pipeline_worker.py#L326) |
| `_run_loop._iso_utc_after` | FunctionDef | [L347](../../../../../backend/workers/pipeline_worker.py#L347) |
| `_run_loop._block_if_predecessor_not_ready` | AsyncFunctionDef | [L350](../../../../../backend/workers/pipeline_worker.py#L350) |
| `_run_loop._process_one` | AsyncFunctionDef | [L422](../../../../../backend/workers/pipeline_worker.py#L422) |
| `main` | FunctionDef | [L746](../../../../../backend/workers/pipeline_worker.py#L746) |
