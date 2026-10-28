-- 010b_gemini_call_log_clear_history
--
-- WHY THIS MATTERS:
-- Admin clear-from-stage reruns jobs in the SAME run_id. If we keep per-call cost rows,
-- a rerun would otherwise accumulate costs from multiple attempts.
--
-- Approach:
-- - Mark downstream call-log rows as cleared with a per-run sequence number.
-- - Exclude cleared rows from the default run totals.
-- - Keep cleared totals available as a per-clear breakdown.

create table if not exists public.gemini_clear_events (
  id bigserial primary key,
  listing_id bigint not null,
  run_id text not null,
  clear_seq integer not null,
  from_stage text not null,
  stages jsonb,
  note text,
  created_at timestamptz not null default now()
);

create unique index if not exists gemini_clear_events_run_seq_uidx
  on public.gemini_clear_events(run_id, clear_seq);

create index if not exists gemini_clear_events_listing_run_idx
  on public.gemini_clear_events(listing_id, run_id);

alter table public.gemini_call_log
  add column if not exists cleared_seq integer,
  add column if not exists cleared_at timestamptz,
  add column if not exists cleared_from_stage text;

create index if not exists gemini_call_log_run_cleared_idx
  on public.gemini_call_log(run_id, cleared_seq);

create or replace view public.gemini_run_costs_v1 as
with active as (
  select *
  from public.gemini_call_log
  where cleared_seq is null
),
active_totals as (
  select
    listing_id,
    run_id,
    count(*)::int as total_calls,
    coalesce(sum(prompt_tokens), 0)::bigint as total_input_tokens,
    coalesce(sum(output_tokens + thinking_tokens), 0)::bigint as total_output_tokens,
    coalesce(sum(cost_regular), 0)::numeric(12,6) as total_cost_regular,
    coalesce(sum(cost_cached), 0)::numeric(12,6) as total_cost_cached,
    min(created_at) as first_call_at,
    max(created_at) as last_call_at
  from active
  group by listing_id, run_id
),
active_stage_rollup as (
  select
    listing_id,
    run_id,
    stage,
    count(*)::int as calls,
    coalesce(sum(prompt_tokens), 0)::bigint as input_tokens,
    coalesce(sum(output_tokens), 0)::bigint as output_tokens,
    coalesce(sum(thinking_tokens), 0)::bigint as thinking_tokens,
    coalesce(sum(cost_regular), 0)::numeric(12,6) as cost_regular,
    coalesce(sum(cost_cached), 0)::numeric(12,6) as cost_cached
  from active
  group by listing_id, run_id, stage
),
active_model_rollup as (
  select
    listing_id,
    run_id,
    model,
    count(*)::int as calls,
    coalesce(sum(prompt_tokens), 0)::bigint as input_tokens,
    coalesce(sum(output_tokens), 0)::bigint as output_tokens,
    coalesce(sum(thinking_tokens), 0)::bigint as thinking_tokens,
    coalesce(sum(cost_regular), 0)::numeric(12,6) as cost_regular,
    coalesce(sum(cost_cached), 0)::numeric(12,6) as cost_cached
  from active
  group by listing_id, run_id, model
),
cleared_rollup as (
  select
    listing_id,
    run_id,
    cleared_seq,
    min(cleared_from_stage) as from_stage,
    min(cleared_at) as cleared_at,
    count(*)::int as calls,
    coalesce(sum(prompt_tokens), 0)::bigint as input_tokens,
    coalesce(sum(output_tokens + thinking_tokens), 0)::bigint as output_tokens,
    coalesce(sum(cost_regular), 0)::numeric(12,6) as cost_regular,
    coalesce(sum(cost_cached), 0)::numeric(12,6) as cost_cached
  from public.gemini_call_log
  where cleared_seq is not null
  group by listing_id, run_id, cleared_seq
)
select
  t.listing_id,
  t.run_id,
  t.total_calls,
  t.total_input_tokens,
  t.total_output_tokens,
  t.total_cost_regular,
  t.total_cost_cached,
  coalesce(
    (
      select jsonb_object_agg(
        s.stage,
        jsonb_build_object(
          'calls', s.calls,
          'input_tokens', s.input_tokens,
          'output_tokens', s.output_tokens,
          'thinking_tokens', s.thinking_tokens,
          'cost_regular', s.cost_regular,
          'cost_cached', s.cost_cached
        )
      )
      from active_stage_rollup s
      where s.listing_id = t.listing_id and s.run_id = t.run_id
    ),
    '{}'::jsonb
  ) as by_stage,
  coalesce(
    (
      select jsonb_object_agg(
        m.model,
        jsonb_build_object(
          'calls', m.calls,
          'input_tokens', m.input_tokens,
          'output_tokens', m.output_tokens,
          'thinking_tokens', m.thinking_tokens,
          'cost_regular', m.cost_regular,
          'cost_cached', m.cost_cached
        )
      )
      from active_model_rollup m
      where m.listing_id = t.listing_id and m.run_id = t.run_id
    ),
    '{}'::jsonb
  ) as by_model,
  t.first_call_at,
  t.last_call_at,
  coalesce(
    (
      select jsonb_object_agg(
        cr.cleared_seq::text,
        jsonb_build_object(
          'from_stage', cr.from_stage,
          'cleared_at', cr.cleared_at,
          'calls', cr.calls,
          'input_tokens', cr.input_tokens,
          'output_tokens', cr.output_tokens,
          'cost_regular', cr.cost_regular,
          'cost_cached', cr.cost_cached
        )
      )
      from cleared_rollup cr
      where cr.listing_id = t.listing_id and cr.run_id = t.run_id
    ),
    '{}'::jsonb
  ) as cleared_costs
from active_totals t;

