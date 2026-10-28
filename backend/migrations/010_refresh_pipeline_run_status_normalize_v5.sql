-- Migration 010: Normalize V5 stage statuses (no downstream "running" flashes)
--
-- WHAT THIS FIXES
-- - Downstream stages briefly showing "running" when a worker claims a job out of order
-- - Delta Review showing "running" while Delta is still running
-- - Room-images sub-stages (prompt gen/style/photo gen) showing green based on old artifacts
-- - Cancelled runs incorrectly showing as "complete" (status now becomes "stopped")
--
-- WHY THIS MATTERS
-- `claim_pipeline_jobs()` can claim any queued job (global queue ordering), and the worker may
-- immediately requeue jobs whose predecessor isn't ready. Without normalization, the run's
-- materialized `stages` JSON will reflect those transient claims and the UI will flicker.
--
-- Source of truth is Postgres function `public.refresh_pipeline_run_status(p_run_id text)`.
-- This migration keeps repo SQL in sync with the deployed Supabase function.

begin;

create or replace function public.refresh_pipeline_run_status(p_run_id text)
returns void
language plpgsql
security definer
as $$
declare
  v_run record;
  v_is_v5 boolean := false;
  v_listing_id integer := null;
  v_run_created_at timestamptz := null;

  v_jobs_queued integer := 0;
  v_jobs_in_progress integer := 0;
  v_jobs_succeeded integer := 0;
  v_jobs_failed integer := 0;
  v_jobs_cancelled integer := 0;
  v_jobs_total integer := 0;

  v_stages jsonb := '[]'::jsonb;
  v_current_stage text := null;
  v_run_status text := null;
  v_error_summary text := null;

  -- Keep in sync with backend stage registry ordering.
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
    'v5_room_images',
    'v5_room_images_defurnish',
    'v5_room_images_prompt_generation',
    'v5_room_images_style_consistency',
    'v5_room_images_photo_generation'
  ];

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
begin
  select *
  into v_run
  from public.pipeline_runs
  where run_id = p_run_id
  limit 1;

  if not found then
    return;
  end if;

  v_listing_id := v_run.listing_id;
  v_is_v5 := coalesce((v_run.config->>'pipeline') = 'v5', false);
  v_run_created_at := v_run.created_at;

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
    delta_stage as (
      select
        coalesce((select queued from real_stage_counts where stage = 'v5_delta'), 0)::integer as queued,
        coalesce((select in_progress from real_stage_counts where stage = 'v5_delta'), 0)::integer as in_progress,
        coalesce((select succeeded from real_stage_counts where stage = 'v5_delta'), 0)::integer as succeeded,
        coalesce((select failed from real_stage_counts where stage = 'v5_delta'), 0)::integer as failed
    ),
    delta_review_exists as (
      select
        exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = 'v5_delta_review_market_standard'
            and coalesce(ue.generated_at, ue.updated_at) >= v_run_created_at
        ) as exists_any,
        exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = 'v5_delta_review_market_standard'
            and coalesce(ue.generated_at, ue.updated_at) >= v_run_created_at
            and coalesce((ue.estimate_data->>'success')::boolean, false) = true
        ) as success_true,
        exists (
          select 1
          from public.unified_estimates ue
          where ue.listing_id = v_listing_id
            and ue.package_type = 'v5_delta_review_market_standard'
            and coalesce(ue.generated_at, ue.updated_at) >= v_run_created_at
            and coalesce((ue.estimate_data->>'success')::boolean, false) = false
        ) as success_false
    ),
    delta_review as (
      select
        'v5_delta_review'::text as stage,
        case
          when dre.exists_any then 0
          when ds.succeeded > 0 then 0
          else ds.queued
        end::integer as queued,
        -- Mirrors delta while missing artifact (normalized later so it never appears concurrently running).
        case
          when dre.exists_any then 0
          when ds.succeeded > 0 then 0
          else ds.in_progress
        end::integer as in_progress,
        case
          when dre.exists_any and dre.success_true then 1
          else 0
        end::integer as succeeded,
        case
          when dre.exists_any and dre.success_false then 1
          when not dre.exists_any and ds.succeeded > 0 then 1
          else 0
        end::integer as failed
      from delta_stage ds
      cross join delta_review_exists dre
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
      union all select 2, 'v5_room_images_prompt_generation', 'v5_room_images_prompt_generation_market_standard'
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
            and coalesce(ue.generated_at, ue.updated_at) >= v_run_created_at
        ) as done
      from room_artifacts ra
    ),
    first_missing as (
      select min(ord)::integer as idx
      from room_done
      where done = false
    ),
    room_virtual_counts as (
      -- Virtual sub-stage status derived from parent v5_room_images state + artifacts.
      -- CRITICAL: when parent is 'unknown' (= cancelled or missing from status buckets),
      -- all sub-stages must be all-zeros (grey) — NOT queued.
      select
        rd.stage,
        case
          when rd.done then 0
          when ris.state = 'unknown' then 0
          when ris.state = 'queued' then 1
          when fm.idx is not null and rd.ord >= fm.idx then 1
          else 0
        end::integer as queued,
        case
          when rd.done then 0
          when ris.state = 'unknown' then 0
          when ris.state = 'in_progress' and fm.idx = rd.ord then 1
          else 0
        end::integer as in_progress,
        case
          when rd.done or ris.state = 'succeeded' then 1
          else 0
        end::integer as succeeded,
        case
          when rd.done then 0
          when ris.state = 'unknown' then 0
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

  if v_is_v5 then
    select
      sum(case when j.status = 'queued' then 1 else 0 end)::integer,
      sum(case when j.status = 'in_progress' then 1 else 0 end)::integer,
      sum(case when j.status = 'succeeded' then 1 else 0 end)::integer,
      sum(case when j.status = 'failed' then 1 else 0 end)::integer,
      sum(case when j.status = 'cancelled' then 1 else 0 end)::integer,
      count(*)::integer
    into v_jobs_queued, v_jobs_in_progress, v_jobs_succeeded, v_jobs_failed, v_jobs_cancelled, v_jobs_total
    from public.pipeline_jobs j
    where j.run_id = p_run_id
      and j.job_type = any(v_v5_job_types);
  else
    select
      sum(case when j.status = 'queued' then 1 else 0 end)::integer,
      sum(case when j.status = 'in_progress' then 1 else 0 end)::integer,
      sum(case when j.status = 'succeeded' then 1 else 0 end)::integer,
      sum(case when j.status = 'failed' then 1 else 0 end)::integer,
      sum(case when j.status = 'cancelled' then 1 else 0 end)::integer,
      count(*)::integer
    into v_jobs_queued, v_jobs_in_progress, v_jobs_succeeded, v_jobs_failed, v_jobs_cancelled, v_jobs_total
    from public.pipeline_jobs j
    where j.run_id = p_run_id;
  end if;

  if v_jobs_total = 0 then
    v_run_status := 'queued';
  elsif v_jobs_queued > 0 or v_jobs_in_progress > 0 then
    v_run_status := 'running';
  elsif v_jobs_cancelled > 0 then
    v_run_status := 'stopped';
  elsif v_jobs_failed > 0 then
    v_run_status := 'failed';
  else
    v_run_status := 'complete';
  end if;

  if v_jobs_failed > 0 then
    select j.error
    into v_error_summary
    from public.pipeline_jobs j
    where j.run_id = p_run_id
      and j.status = 'failed'
      and j.error is not null
    order by coalesce(j.updated_at, j.created_at) desc
    limit 1;
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

commit;

