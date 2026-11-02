# Fresh database

Create a Supabase project for your own Estimate installation and install the PostgreSQL client tools (`psql`). Save your project's Postgres connection URI in a private file through hidden terminal input:

```sh
python3 tools/runtime-env.py configure \
  --file "$HOME/.config/leo-estimates/database.env" --capability database-admin
python3 tools/runtime-env.py run \
  --file "$HOME/.config/leo-estimates/database.env" -- \
  python3 tools/bootstrap-database.py
python3 tools/runtime-env.py run \
  --file "$HOME/.config/leo-estimates/database.env" -- \
  python3 tools/bootstrap-database.py --apply
```

The first bootstrap command checks local inputs; `--apply` installs [db/bootstrap.sql](../db/bootstrap.sql) in one transaction. It uses libpq's environment input so the connection URI stays outside command arguments and output. TLS is required by default; an explicit connection-URI SSL setting selects your own local test configuration. The SQL checks for Supabase's auth schema and an empty application schema before writing. You can also run the same SQL through your project's SQL editor.

Then save your project URL and server service-role key through the [private runtime configuration](setup.md#private-runtime-file). Start the backend on loopback and connect the frontend to that backend. The native frontend reads through FastAPI; the fresh database grants its application tables, sequences and RPCs to `service_role`. Keep that credential in the backend runtime file.

## What gets installed

| Area | Tables and functions | Source contract |
|---|---|---|
| Property inputs | `listings`, `listing_photos`, market/comparable tables and photo clusters | `backend/database.py` listing/comparable methods |
| Durable work | `pipeline_runs`, `pipeline_jobs`, `pipeline_job_events` | Enqueue, worker, progress and admin routes |
| Queue operations | `claim_pipeline_jobs`, `pipeline_job_counts`, status refresh, backfill and stuck-job reaping | `backend/database.py`, `backend/workers/pipeline_worker.py` |
| Analysis and estimates | Property-intelligence variants, `smart_m2`, `unified_estimates`, checkpoints and retained earlier analysis tables | Current persistence methods and versioned research DDL |
| Costing | `boq_line_items`, its batch merge RPC, `pipeline_cost_tracking`, Gemini usage log and cost view | The original deterministic assembler and run-cost reporting |

The current backend uses a text `run_id`; the earlier base schema also has a UUID `id`. Both remain available. Job IDs are UUIDs, idempotency keys are unique, and each run keeps its original listing reference. PIR variants use `(listing_id, pir_type)` and estimates use `(listing_id, package_type)`.

The queue claims available jobs with `FOR UPDATE SKIP LOCKED`, records the worker and lease, and increments attempts. The retained Python worker checks V5/GLA predecessors. Heartbeats extend a running lease; the original reaper fails an abandoned job so an operator can inspect and explicitly retry it. Future, cancelled, succeeded and exhausted jobs stay outside new claims.

## Reproduce the schema

```sh
python3 tools/build-database-bootstrap.py --check
python3 tools/test-database-bootstrap.py
```

The second command needs Docker and `postgres:16-alpine`. It starts a uniquely named database with its network disabled and synthetic Supabase roles, then removes that database. It verifies a fresh install, refusal to overwrite an existing application, disjoint concurrent claims, idempotent enqueue, availability/lease/cancellation, original status aggregation, BOQ accumulation and service-only access. It also executes the released Python persistence functions with a local SQL-backed request recorder to check their actual JSON fields. This is SQL/client-contract verification; your Supabase project's PostgREST, authentication, storage and provider integrations get their own acceptance checks.

[db/bootstrap/sources.json](../db/bootstrap/sources.json) records every input SHA and application order. The assembly preserves dated migration files, selects the later comparable definition and adds the missing current contracts in [current-contracts.sql](../db/bootstrap/current-contracts.sql). After changing an input, run `python3 tools/build-database-bootstrap.py` and repeat the database test. Existing installations use reviewed forward migrations against their actual schema.

## Connected acceptance

Use your own listing and permitted photographs, install your construction price book and regenerate the matching embeddings, then run a single owned pipeline through acquisition, planning, measured quantities and report persistence. Verify the worker can stop, retry and resume its run. Optional communications, retailer/WhatsApp services, GLA image tooling and historical experiments retain their separate configuration/schema contracts. This bootstrap covers the native Estimate persistence and queue; it supplies the missing installation contract rather than certifying every archived integration.
