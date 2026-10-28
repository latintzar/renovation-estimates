# Setup

## Synthetic estimate

Python 3.12 and the NumPy/Pydantic closure in `requirements-first-result.txt` are enough for the first result. Run the README commands. The calculation tool creates its own private temporary directory, synthetic SQLite price book, estimate rows and JSON receipt. Its Python socket fence blocks network attempts. The real calculation modules are checked against their archived Git blobs before execution.

The SQLite sink implements the assembler's `save_boq_line_items_batch` seam. Supabase remains the application's durable store. [Architecture](architecture.md).

## Interface

Use Node 22.12 or later. From `frontend`, run `npm ci`, `npm run typecheck`, `npm run build`, then `npm run start`. Development uses `npm run dev`. Both servers bind to 127.0.0.1:3002. Root navigation opens `/listings` on any installation hostname. The `/first-estimate` entry connects the original report component to the actual synthetic calculation fixture. Regenerate/check it with `python3 tools/export-first-result.py --check`. The archived report applies its own fixed overhead/margin/tax arithmetic; those displayed percentages are part of this synthetic interface example, rather than a real project’s tax determination.

`BACKEND_URL` selects the server-side FastAPI origin; its local default is `http://localhost:8000`. `NEXT_PUBLIC_SITE_URL` controls installation metadata. `NEXT_PUBLIC_MAPBOX_TOKEN` enables the existing map component with the recipient's public browser token. Playfair Display and Source Sans3 are self-hosted with their OFL notices; font provenance is in `frontend/public/fonts/provenance.json`.

The listing importer requires the backend and its data contracts. The local calculation proof is independently usable while those integrations are commissioned.

## Private runtime file

Choose an absolute path outside the source checkout, in a directory with mode 0700. The helper writes a file with mode 0600. In a private terminal:

```sh
python3 tools/runtime-env.py configure \
  --file /absolute/private/estimates/runtime.env --capability database
python3 tools/runtime-env.py configure \
  --file /absolute/private/estimates/runtime.env --capability gemini
python3 tools/runtime-env.py doctor \
  --file /absolute/private/estimates/runtime.env
```

Supported groups are database, gemini, comparables, scraping, places, vertex, frontend and optional communications. Enter secret values through the hidden prompt. Doctor reports configured field names and presence; it performs zero provider calls.

The runner supplies the selected file, strips inherited provider credentials and disables ambient AWS home profiles/cloud metadata. It treats values as data and executes an argument array:

```sh
python3 tools/runtime-env.py run \
  --file /absolute/private/estimates/runtime.env -- \
  .venv/bin/python -m uvicorn main:app --app-dir backend \
  --host 127.0.0.1 --port 8000
```

Install `backend/requirements.txt` into a separate virtual environment for the complete historical backend import closure. Its optional communications/research code remains separate from the Estimate entry's mounted routes. [Providers](providers.md) maps each capability to configuration and source.

## Supabase and queue artifacts

The native application uses Supabase REST tables and Postgres RPCs. `db/001_schema.sql` is the original base schema. `supabase/migrations` and `backend/migrations` retain subsequent versioned changes; `supabase/migrations_legacy` records older copies. Their duplicate numbers and historical assumptions require reconciliation against a newly owned empty project, rather than running every file lexically.

The archived code implements pipeline runs/jobs, job claims, acknowledgement, retry, lease extension and status aggregation. The archive lacks the original base `pipeline_jobs`/`claim_pipeline_jobs` DDL. Fresh queue installation and worker recovery therefore remain an explicit integration task. The original cloud tables were retired; archived customer-row dumps stay private. This release supplies source and the proved deterministic result, with this schema gap recorded.

Use a recipient-owned Supabase URL and server service-role credential. Keep the service role on the server. Set up the owned schema, storage permissions and application access control before importing recipient data or starting a worker. Preserve the worker's lease/predecessor/idempotency semantics when completing the missing bootstrap. The retained API/admin routes were trusted local tools; public hosting needs application authorization and provider limits.

## Reference-data regeneration

The first result uses synthetic rates. A full V5 run needs an owned construction price database, compatible index and dimension metadata, plus the matching embeddings and full labor index named by `backend/pricing/bcca_embedding_matcher.py`. The current loader's four f32/metadata files and full labor index are absent from the archived tree. The differently named older array is a historical artifact, rather than a verified replacement.

With licensed recipient inputs, `backend/pricing/scripts/build_bcca_embedding_index_full.py` and `build_bcca_dimension_artifacts_v1.py` provide the original regeneration path. That path uses the recipient's embedding provider. Regeneration, full queue setup, listing acquisition, model analysis and actual account acceptance require measured verification after those resources are commissioned.

On a constrained verification host, ESTIMATES_BUILD_CACHE=0 disables only generated Webpack filesystem caching. The application and locked dependencies are unchanged. Normal installs/builds use the default cache.


For frontend-specific settings, use a separate private file with the frontend group:

```sh
python3 tools/runtime-env.py run \
  --file /absolute/private/estimates/frontend.env -- \
  npm --prefix frontend run dev
```

The example file at repository root contains supported field names and empty values.
The selected-file runner keeps empty cloud fields from reopening ambient account discovery.

The report adapter adds an authored flooring category to the two synthetic finish items. Prices, quantities, labor hours and line totals come directly from the original calculation receipt.
