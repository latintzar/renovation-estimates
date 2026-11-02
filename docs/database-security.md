# Database access boundaries

The sample app uses its local authored workspace. New connected installations use the [fresh database](fresh-database.md), whose native backend tables and RPCs are service-role only. The retained migration sequence records the historical schema and its earlier access policies.

## Forward policy hardening

Apply the dated `202611010001_` migration after reconciling the existing schema in your own database. Review the target tables and their role grants first. This source change has not been applied to a hosted customer database.

Due-diligence records are serviced through the backend role. Listing comparable tables keep their separately declared public SELECT policies while mutations require `service_role`. Property intelligence/gap reports keep the original authenticated shared-read contract; their service writes are explicitly scoped to `service_role`. This does not invent a per-household join for a shared property research table.

## Acceptance

Run `python3 tools/test-database-policies.py` with Docker available. The security regression script replays the forward migration against synthetic fixtures matching the affected historical policies in an isolated PostgreSQL instance with synthetic roles and records. It verifies anonymous denial, own-user profile isolation, service writes and intended shared reads. This tests the stated policies and idempotent hardening; it is separate from a complete empty-database bootstrap or proof of an existing hosted Supabase configuration. A recipient should test two authenticated households plus `anon` and its backend service role against the reconciled schema.

Keep the service-role credential in the private backend. A browser anon key identifies a public client; authorization comes from the actual database grants, row policies and authenticated ownership checks.
