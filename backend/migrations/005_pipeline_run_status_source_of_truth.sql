-- Migration: 005_pipeline_run_status_source_of_truth
-- Purpose: Single source of truth for pipeline run status, stage timeline, and stuck-job reaping
-- Date: 2026-02-13
--
-- SUPERSEDED: The refresh_pipeline_run_status() function defined here has been
-- replaced by migration 010. This file is kept only for the ALTER TABLE and
-- trigger/reaper DDL. Do NOT re-apply the function definition from this file.

-- -----------------------------------------------------------------------------
-- 1) Add materialized run-status columns
-- -----------------------------------------------------------------------------
ALTER TABLE public.pipeline_runs
  ADD COLUMN IF NOT EXISTS jobs_queued integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS jobs_in_progress integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS jobs_succeeded integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS jobs_failed integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS jobs_total integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS stages jsonb NOT NULL DEFAULT '[]'::jsonb;


-- -----------------------------------------------------------------------------
-- 2) Single status computer for one run_id
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.refresh_pipeline_run_status(p_run_id text)
RETURNS void
LANGUAGE plpgsql
AS $$
declare
  v_listing_id integer;
  v_config jsonb;
  v_is_v5 boolean := false;
  v_v5_job_types text[] := array[
    'v5_fetch_listing_snapshot',
    'fetch_comparables',
    'v5_fetch_comparables_snapshot',
    'v5_cluster_target_photos',
    'v5_room_tags',
    'v5_generate_target_pir_slots',
    'v5_select_median_comparable',
    'v5_cluster_selected_comparable_photos',
    'v5_generate_selected_comparable_room_pirs',
    'v5_delta_slots_market_standard',
    'v5_work_items_market_standard',
    'v5_smart_m2',
    'v5_bcca_match',
    'v5_quant_plan',
    'v5_forage',
    'v5_boq_assembly',
    'v5_finalize',
    'v5_eli5',
    'v5_architect_report',
    'v5_room_images'
  ];
  v_stage_order text[] := array[
    'snapshot',
    'comparables',
    'clustering',
    'v5_room_tags',
    'v5_pir',
    'v5_select',
    'v5_comparables',
    'v5_delta',
    'v5_delta_review',
    'v5_decompose',
    'v5_smart_m2',
    'v5_bcca_match',
    'v5_quant_plan',
    'v5_forage',
    'v5_boq_assembly',
    'v5_finalize',
    'v5_eli5',
    'v5_architect_report',
    'v5_room_images_defurnish',
    'v5_room_images_prompt_generation',
    'v5_room_images_style_consistency',
    'v5_room_images_photo_generation'
  ];
  v_jobs_queued integer := 0;
  v_jobs_in_progress integer := 0;
  v_jobs_succeeded integer := 0;
  v_jobs_failed integer := 0;
  v_jobs_total integer := 0;
  v_stages jsonb := '[]'::jsonb;
  v_current_stage text := null;
  v_error_summary text := null;
  v_run_status text := 'queued';
begin
  select listing_id, coalesce(config, '{}'::jsonb)
  into v_listing_id, v_config
  from public.pipeline_runs
  where run_id = p_run_id;

  if not found then
    return;
  end if;

  v_is_v5 := coalesce(v_config->>'pipeline', '') = 'v5';

  with filtered_jobs as (
    select j.*
    from public.pipeline_jobs j
    where j.run_id = p_run_id
      and (
        (v_is_v5 and j.job_type = any(v_v5_job_types))
        or (not v_is_v5)
      )
  )
  select
    coalesce(sum(case when status = 'queued' then 1 else 0 end), 0)::integer,
    coalesce(sum(case when status = 'in_progress' then 1 else 0 end), 0)::integer,
    coalesce(sum(case when status = 'succeeded' then 1 else 0 end), 0)::integer,
    coalesce(sum(case when status = 'failed' then 1 else 0 end), 0)::integer,
    coalesce(count(*), 0)::integer
  into
    v_jobs_queued, v_jobs_in_progress, v_jobs_succeeded, v_jobs_failed, v_jobs_total
  from filtered_jobs;

  with filtered_jobs as (
    select j.*
    from public.pipeline_jobs j
    where j.run_id = p_run_id
      and (
        (v_is_v5 and j.job_type = any(v_v5_job_types))
        or (not v_is_v5)
      )
  )
  select j.error
  into v_error_summary
  from filtered_jobs j
  where j.status = 'failed'
    and j.error is not null
  order by coalesce(j.updated_at, j.created_at) desc
  limit 1;

  if v_is_v5 then
    with filtered_jobs as (
      select j.*
      from public.pipeline_jobs j
      where j.run_id = p_run_id
        and j.job_type = any(v_v5_job_types)
    ),
    real_stage_counts as (
      select
        j.stage::text as stage,
        sum(case when j.status = 'queued' then 1 else 0 end)::integer as queued,
        sum(case when j.status = 'in_progress' then 1 else 0 end)::integer as in_progress,
        sum(case when j.status = 'succeeded' then 1 else 0 end)::integer as succeeded,
        sum(case when j.status = 'failed' then 1 else 0 end)::integer as failed
      from filtered_jobs j
      group by j.stage
    ),
    delta_review as (
      select
        'v5_delta_review'::text as stage,
        0::integer as queued,
        0::integer as in_progress,
        case when exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = 'v5_delta_review_market_standard'
            and coalesce((ue.estimate_data->>'success')::boolean, false) = true
        ) then 1 else 0 end::integer as succeeded,
        case when exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = 'v5_delta_review_market_standard'
            and coalesce((ue.estimate_data->>'success')::boolean, false) = false
        ) then 1 else 0 end::integer as failed
    ),
    room_images_state as (
      select
        case
          when coalesce((select failed from real_stage_counts where stage = 'v5_room_images'), 0) > 0 then 'failed'
          when coalesce((select in_progress from real_stage_counts where stage = 'v5_room_images'), 0) > 0 then 'in_progress'
          when coalesce((select queued from real_stage_counts where stage = 'v5_room_images'), 0) > 0 then 'queued'
          when coalesce((select succeeded from real_stage_counts where stage = 'v5_room_images'), 0) > 0 then 'succeeded'
          else 'unknown'
        end::text as state
    ),
    room_artifacts as (
      select 1 as ord, 'v5_room_images_defurnish'::text as stage, 'v5_room_images_defurnish_market_standard'::text as artifact_key
      union all select 2, 'v5_room_images_prompt_generation', 'v5_room_images_prompt_gen_market_standard'
      union all select 3, 'v5_room_images_style_consistency', 'v5_room_images_style_consistency_market_standard'
      union all select 4, 'v5_room_images_photo_generation', 'v5_generated_images_market_standard'
    ),
    room_done as (
      select
        ra.ord,
        ra.stage,
        exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = ra.artifact_key
        ) as done
      from room_artifacts ra
    ),
    first_missing as (
      select min(ord)::integer as idx
      from room_done
      where done = false
    ),
    room_virtual_counts as (
      select
        rd.stage,
        case
          when rd.done then 0
          when ris.state = 'queued' then 1
          when fm.idx is not null and rd.ord > fm.idx then 1
          else 0
        end::integer as queued,
        case
          when rd.done then 0
          when ris.state = 'in_progress' and fm.idx = rd.ord then 1
          else 0
        end::integer as in_progress,
        case
          when rd.done or ris.state = 'succeeded' then 1
          else 0
        end::integer as succeeded,
        case
          when rd.done then 0
          when ris.state = 'failed' and fm.idx = rd.ord then 1
          else 0
        end::integer as failed
      from room_done rd
      cross join room_images_state ris
      cross join first_missing fm
    ),
    combined as (
      select stage, queued, in_progress, succeeded, failed from real_stage_counts
      union all
      select stage, queued, in_progress, succeeded, failed from delta_review
      union all
      select stage, queued, in_progress, succeeded, failed from room_virtual_counts
    ),
    combined_agg as (
      select
        stage,
        sum(queued)::integer as queued,
        sum(in_progress)::integer as in_progress,
        sum(succeeded)::integer as succeeded,
        sum(failed)::integer as failed
      from combined
      group by stage
    ),
    stage_order as (
      select so.stage, so.ord
      from unnest(v_stage_order) with ordinality as so(stage, ord)
      union all
      select ca.stage, 1000 + row_number() over (order by ca.stage)
      from combined_agg ca
      where not (ca.stage = any(v_stage_order))
    ),
    raw as (
      select
        so.ord,
        so.stage,
        coalesce(ca.queued, 0)::integer as queued,
        coalesce(ca.in_progress, 0)::integer as in_progress,
        coalesce(ca.succeeded, 0)::integer as succeeded,
        coalesce(ca.failed, 0)::integer as failed,
        case
          when coalesce(ca.failed, 0) > 0 then 'failed'
          when coalesce(ca.in_progress, 0) > 0 then 'in_progress'
          when coalesce(ca.queued, 0) > 0 then 'queued'
          when coalesce(ca.succeeded, 0) > 0 then 'succeeded'
          else 'unknown'
        end::text as status
      from stage_order so
      left join combined_agg ca on ca.stage = so.stage
      order by so.ord
    ),
    first_blocked as (
      select min(ord)::integer as ord
      from raw
      where status <> 'succeeded'
    ),
    normalized as (
      select
        r.ord,
        r.stage,
        case
          when fb.ord is not null and r.ord > fb.ord and r.status in ('succeeded', 'failed', 'in_progress')
            then greatest(1, r.queued)
          else r.queued
        end::integer as queued,
        case
          when fb.ord is not null and r.ord > fb.ord and r.status in ('succeeded', 'failed', 'in_progress')
            then 0
          else r.in_progress
        end::integer as in_progress,
        case
          when fb.ord is not null and r.ord > fb.ord and r.status in ('succeeded', 'failed', 'in_progress')
            then 0
          else r.succeeded
        end::integer as succeeded,
        case
          when fb.ord is not null and r.ord > fb.ord and r.status in ('succeeded', 'failed', 'in_progress')
            then 0
          else r.failed
        end::integer as failed
      from raw r
      cross join first_blocked fb
      order by r.ord
    ),
    normalized_first as (
      select min(ord)::integer as ord
      from normalized
      where not (succeeded > 0 and queued = 0 and in_progress = 0 and failed = 0)
    )
    select
      coalesce(
        jsonb_agg(
          jsonb_build_object(
            'stage', n.stage,
            'queued', n.queued,
            'in_progress', n.in_progress,
            'succeeded', n.succeeded,
            'failed', n.failed
          )
          order by n.ord
        ),
        '[]'::jsonb
      ),
      (
        select n.stage
        from normalized n
        join normalized_first nf on n.ord = nf.ord
      )
    into v_stages, v_current_stage
    from normalized n;
  else
    with filtered_jobs as (
      select j.*
      from public.pipeline_jobs j
      where j.run_id = p_run_id
    ),
    grouped as (
      select
        j.stage::text as stage,
        min(j.created_at) as first_created,
        sum(case when j.status = 'queued' then 1 else 0 end)::integer as queued,
        sum(case when j.status = 'in_progress' then 1 else 0 end)::integer as in_progress,
        sum(case when j.status = 'succeeded' then 1 else 0 end)::integer as succeeded,
        sum(case when j.status = 'failed' then 1 else 0 end)::integer as failed
      from filtered_jobs j
      group by j.stage
    ),
    ordered as (
      select
        g.stage,
        g.queued,
        g.in_progress,
        g.succeeded,
        g.failed
      from grouped g
      order by g.first_created asc, g.stage asc
    )
    select
      coalesce(
        jsonb_agg(
          jsonb_build_object(
            'stage', o.stage,
            'queued', o.queued,
            'in_progress', o.in_progress,
            'succeeded', o.succeeded,
            'failed', o.failed
          )
        ),
        '[]'::jsonb
      ),
      (
        select o.stage
        from ordered o
        where not (o.succeeded > 0 and o.queued = 0 and o.in_progress = 0 and o.failed = 0)
        limit 1
      )
    into v_stages, v_current_stage
    from ordered o;
  end if;

  if v_jobs_total = 0 then
    v_run_status := 'queued';
  elsif v_jobs_queued > 0 or v_jobs_in_progress > 0 then
    v_run_status := 'running';
  elsif v_jobs_failed > 0 then
    v_run_status := 'failed';
  else
    v_run_status := 'complete';
  end if;

  update public.pipeline_runs r
  set
    status = v_run_status,
    current_stage = v_current_stage,
    error_summary = case when v_run_status = 'failed' then v_error_summary else null end,
    jobs_queued = v_jobs_queued,
    jobs_in_progress = v_jobs_in_progress,
    jobs_succeeded = v_jobs_succeeded,
    jobs_failed = v_jobs_failed,
    jobs_total = v_jobs_total,
    stages = coalesce(v_stages, '[]'::jsonb),
    last_progress_at = now(),
    completed_at = case
      when v_run_status = 'complete' then coalesce(r.completed_at, now())
      else null
    end,
    updated_at = now()
  where r.run_id = p_run_id;
end;
$$;


-- -----------------------------------------------------------------------------
-- 3) Trigger wrapper on pipeline_jobs mutations
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public._pipeline_jobs_refresh_run_status_trg()
RETURNS trigger
LANGUAGE plpgsql
AS $$
declare
  v_run_id text;
begin
  v_run_id := coalesce(new.run_id, old.run_id);
  if v_run_id is not null then
    perform public.refresh_pipeline_run_status(v_run_id);
  end if;

  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;

drop trigger if exists pipeline_jobs_refresh_run_status on public.pipeline_jobs;
create trigger pipeline_jobs_refresh_run_status
after insert or update or delete
on public.pipeline_jobs
for each row
execute function public._pipeline_jobs_refresh_run_status_trg();


-- -----------------------------------------------------------------------------
-- 4) Stuck-job reaper
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reap_stuck_pipeline_jobs(
  p_stale_seconds integer default 600,
  p_heartbeat_grace_seconds integer default 300,
  p_limit integer default 100
)
RETURNS integer
LANGUAGE plpgsql
AS $$
declare
  v_count integer := 0;
begin
  with stale as (
    select j.id
    from public.pipeline_jobs j
    where j.status = 'in_progress'
      and j.locked_until is not null
      and j.locked_until < (now() - make_interval(secs => greatest(0, coalesce(p_stale_seconds, 600))))
      and coalesce(j.last_heartbeat_at, j.started_at, j.updated_at, j.created_at)
            < (now() - make_interval(secs => greatest(0, coalesce(p_heartbeat_grace_seconds, 300))))
    order by j.locked_until asc
    limit greatest(1, coalesce(p_limit, 100))
  )
  update public.pipeline_jobs j
  set
    status = 'failed',
    error = 'Worker heartbeat expired (stuck in_progress reaped)',
    error_context = jsonb_build_object(
      'reason', 'heartbeat_expired',
      'reaped_at', now(),
      'stale_seconds', p_stale_seconds,
      'heartbeat_grace_seconds', p_heartbeat_grace_seconds
    ),
    locked_by = null,
    locked_until = null,
    finished_at = now(),
    updated_at = now()
  from stale s
  where j.id = s.id;

  get diagnostics v_count = row_count;
  return coalesce(v_count, 0);
end;
$$;


-- -----------------------------------------------------------------------------
-- 5) Backfill helper + initial backfill
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.backfill_pipeline_run_statuses(p_limit integer default null)
RETURNS integer
LANGUAGE plpgsql
AS $$
declare
  r record;
  v_count integer := 0;
begin
  for r in
    select pr.run_id
    from public.pipeline_runs pr
    order by pr.created_at desc
    limit case when p_limit is null then 2147483647 else greatest(1, p_limit) end
  loop
    perform public.refresh_pipeline_run_status(r.run_id);
    v_count := v_count + 1;
  end loop;
  return v_count;
end;
$$;

select public.backfill_pipeline_run_statuses(null);

