-- 009_gemini_call_log_and_run_costs_view
--
-- WHY THIS MATTERS:
-- We want to measure the ACTUAL tokens sent/received from Gemini for every call.
-- That requires persisting per-call usage_metadata (source of truth), and deriving
-- totals from those rows (not from logs or in-memory counters that can race/reset).

create table if not exists public.gemini_call_log (
  id bigserial primary key,
  listing_id bigint not null,
  run_id text not null,
  job_id text,
  stage text not null,
  job_type text,
  model text not null,

  has_images boolean not null default false,
  pricing_tier text not null default 'standard', -- 'standard' | 'long'
  pricing_mode text not null default 'regular',  -- 'regular' | 'cached' (informational)

  prompt_tokens integer not null,
  output_tokens integer not null,
  thinking_tokens integer not null default 0,
  total_tokens integer not null,

  cost_regular numeric(12,6) not null,
  cost_cached numeric(12,6) not null,

  usage_metadata jsonb,
  request_meta jsonb,

  created_at timestamptz not null default now()
);

create index if not exists gemini_call_log_listing_run_idx
  on public.gemini_call_log(listing_id, run_id);

create index if not exists gemini_call_log_run_stage_idx
  on public.gemini_call_log(run_id, stage);

create index if not exists gemini_call_log_run_model_idx
  on public.gemini_call_log(run_id, model);

-- Aggregated, queryable source-of-truth for run costs.
-- PostgREST can select from this view directly.
create or replace view public.gemini_run_costs_v1 as
with totals as (
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
  from public.gemini_call_log
  group by listing_id, run_id
),
stage_rollup as (
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
  from public.gemini_call_log
  group by listing_id, run_id, stage
),
model_rollup as (
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
  from public.gemini_call_log
  group by listing_id, run_id, model
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
      from stage_rollup s
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
      from model_rollup m
      where m.listing_id = t.listing_id and m.run_id = t.run_id
    ),
    '{}'::jsonb
  ) as by_model,
  t.first_call_at,
  t.last_call_at
from totals t;

-- NOTE:
-- This view is later extended to support clear-from-stage reruns by excluding cleared rows
-- and adding a cleared_costs breakdown (see migration 010b).

