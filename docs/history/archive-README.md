Historical specification at source commit4dca5f9b. [Current setup](../setup.md) and [release status](../../RELEASE-STATUS.md) record this derivative’s verified scope.

# puedo_casa (monorepo)

This repository contains the current `lean-mvp/` app plus supporting docs and utilities.

## Repo layout (high level)

- **`lean-mvp/`**: main product app (Next.js frontend + Python/FastAPI backend + Supabase).
- **`docs/`**: current documentation (start at `docs/README.md`).
- **`mcp-send-email/`**: email MCP utility package.

---

## Queue-based Renovation / BOQ pipeline (enqueue + workers)

The renovation pipeline (including BOQ) is implemented as a **DB-backed job queue** using **Supabase Postgres RPC**.

### Pipeline architecture (listing → post-BOQ)

Terminology note:
- **“v2”** in code (e.g. `v2_scheduler.py`, `run_v2_pipeline.py`) is an **internal codename** for the **comparable-based renovation options pipeline** (target + comparable PIRs → strategies → delta scopes → BOQ → post-BOQ). It does **not** imply we’re actively maintaining multiple versions of the product pipeline.

At a high level, the V2 pipeline is a **job graph** that starts from a `listing_id` and produces:

- clustered photos + PIRs (target + comparables)
- a strategy selection
- delta scopes per strategy
- BOQ line items + aggregated BOQ per strategy
- post-BOQ enhancements per strategy

The job graph is defined in `lean-mvp/backend/pricing/v2_scheduler.py` and executed by `lean-mvp/backend/workers/pipeline_worker.py` + `lean-mvp/backend/workers/handlers.py`.

**Job graph (conceptual)**

```text
enqueue_v2_run(listing_id)
  ├─ clustering:        cluster_target_photos
  ├─ pir:              generate_target_pir
  ├─ comparable_cache: cache_comparable_images           (fanout per comparable)
  ├─ comparable_cluster: cluster_comparable_photos       (fanout per comparable)
  ├─ pir:              generate_comparable_pir           (fanout per comparable)
  ├─ strategy:         strategy_selection
  ├─ delta_scopes:     delta_scopes
  ├─ boq_llm:          boq_enqueue_scope_jobs
  │    └─ boq_llm_scope_item                             (fanout per scope item)
  │         └─ boq_write_items                           (writes line items)
  ├─ boq_finalize:     boq_finalize_all
  │    └─ boq_finalize_strategy                          (fanout per strategy; aggregates BOQ)
  └─ post_boq:         post_boq_enqueue_all
       └─ post_boq_strategy                              (fanout per strategy; post-processing)
```

**Why queue-based?**

- lets long-running BOQ runs complete without keeping an HTTP request open
- can scale by running more worker processes / machines
- supports idempotency and retries

### What exists (source of truth in code)

- **Scheduler (job graph)**: `lean-mvp/backend/pricing/v2_scheduler.py`
  - Enqueues a full run (clustering → PIR → strategy → delta scopes → BOQ fanout → finalize → post-BOQ)
- **Enqueue script**: `lean-mvp/backend/scripts/enqueue_v2_pipeline_run.py`
- **Worker process**: `lean-mvp/backend/workers/pipeline_worker.py`
  - Polls and claims jobs via RPC
  - Renews job locks via a heartbeat while running
- **Job handlers + throttles**: `lean-mvp/backend/workers/handlers.py`
  - Contains the process-wide semaphores (Gemini/DB/storage throttles)

### Queue primitives (RPC calls)

The backend uses these Supabase RPC functions (see usage in `lean-mvp/backend/database.py`):

- `enqueue_pipeline_job`
- `claim_pipeline_jobs`
- `ack_pipeline_job`
- `fail_pipeline_job`
- `extend_pipeline_job_lock`
- `pipeline_job_counts` (aggregation)

### How to enqueue a pipeline run

From the repo root:

```bash
cd /root/puedo_casa/lean-mvp/backend
python scripts/enqueue_v2_pipeline_run.py --listing-id 12
```

This will create a `run_id` and enqueue the job graph for that listing.

### How to run workers

From the repo root:

```bash
cd /root/puedo_casa/lean-mvp/backend
python workers/pipeline_worker.py --poll-seconds 1 --limit 1 --lock-seconds 300
```

Notes:

- **Scaling**: run multiple worker processes (and/or multiple machines). Each worker process claims jobs independently.
- **Throughput knob**: `--limit` controls how many jobs a single worker claims per poll. It defaults to `1` to avoid job hoarding.
- **Critical concurrency detail**: throttles like `GEMINI_FLASH_SEMAPHORE` in `lean-mvp/backend/workers/handlers.py` are **per-process**. If you start N worker processes, your effective Gemini concurrency scales by ~N unless you enforce a global limiter.

### Monitoring a run (foreground)

If you want a simple “watch the queue” loop that prints counts until completion:

```bash
cd /root/puedo_casa/lean-mvp/backend
python scripts/run_v2_pipeline.py --listing-id 12
```


