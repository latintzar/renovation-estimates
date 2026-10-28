-- Add provenance + reference fields for BOQ v3 (non-lossy, auditable)
alter table if exists public.boq_line_items
  add column if not exists room_id text,
  add column if not exists wall_id text,
  add column if not exists opening_id text,
  add column if not exists quantity_ref text,
  add column if not exists quantity_rule_id text,
  add column if not exists item_kind text,
  add column if not exists embedding_similarity real,
  add column if not exists embedding_top_k jsonb,
  add column if not exists provenance jsonb;

-- Update upsert RPC to accept new fields (preserve existing merge behavior).
create or replace function public.boq_line_items_upsert(rows jsonb)
returns integer
language plpgsql
as $$
declare
  inserted_count integer := 0;
begin
  with input_rows as (
    select * from jsonb_to_recordset(rows) as x(
      listing_id int,
      strategy_name text,
      dimension text,
      room_name text,
      scope_item_element text,
      bcca_code text,
      description text,
      quantity numeric,
      unit text,
      unit_price numeric,
      line_total numeric,
      labor_hours numeric,
      quantity_reasoning text,
      room_id text,
      wall_id text,
      opening_id text,
      quantity_ref text,
      quantity_rule_id text,
      item_kind text,
      embedding_similarity real,
      embedding_top_k jsonb,
      provenance jsonb
    )
  ), ins as (
    insert into public.boq_line_items (
      listing_id,
      strategy_name,
      dimension,
      room_name,
      scope_item_element,
      bcca_code,
      description,
      quantity,
      unit,
      unit_price,
      line_total,
      labor_hours,
      quantity_reasoning,
      room_id,
      wall_id,
      opening_id,
      quantity_ref,
      quantity_rule_id,
      item_kind,
      embedding_similarity,
      embedding_top_k,
      provenance
    )
    select
      listing_id,
      strategy_name,
      dimension,
      room_name,
      scope_item_element,
      bcca_code,
      description,
      quantity,
      unit,
      unit_price,
      line_total,
      labor_hours,
      quantity_reasoning,
      room_id,
      wall_id,
      opening_id,
      quantity_ref,
      quantity_rule_id,
      item_kind,
      embedding_similarity,
      embedding_top_k,
      provenance
    from input_rows
    on conflict (listing_id, strategy_name, dimension, room_name, bcca_code, description)
    do update set
      quantity = coalesce(public.boq_line_items.quantity, 0) + coalesce(excluded.quantity, 0),
      line_total = coalesce(public.boq_line_items.line_total, 0) + coalesce(excluded.line_total, 0),
      labor_hours = coalesce(public.boq_line_items.labor_hours, 0) + coalesce(excluded.labor_hours, 0),
      quantity_reasoning = left(
        case
          when excluded.quantity_reasoning is null or excluded.quantity_reasoning = '' then public.boq_line_items.quantity_reasoning
          when public.boq_line_items.quantity_reasoning is null or public.boq_line_items.quantity_reasoning = '' then excluded.quantity_reasoning
          else public.boq_line_items.quantity_reasoning || E'\n\n' || excluded.quantity_reasoning
        end,
        4000
      ),
      unit = coalesce(public.boq_line_items.unit, excluded.unit),
      unit_price = coalesce(public.boq_line_items.unit_price, excluded.unit_price),
      scope_item_element = coalesce(public.boq_line_items.scope_item_element, excluded.scope_item_element),
      room_id = coalesce(public.boq_line_items.room_id, excluded.room_id),
      wall_id = coalesce(public.boq_line_items.wall_id, excluded.wall_id),
      opening_id = coalesce(public.boq_line_items.opening_id, excluded.opening_id),
      quantity_ref = coalesce(public.boq_line_items.quantity_ref, excluded.quantity_ref),
      quantity_rule_id = coalesce(public.boq_line_items.quantity_rule_id, excluded.quantity_rule_id),
      item_kind = coalesce(public.boq_line_items.item_kind, excluded.item_kind),
      embedding_similarity = coalesce(public.boq_line_items.embedding_similarity, excluded.embedding_similarity),
      embedding_top_k = coalesce(public.boq_line_items.embedding_top_k, excluded.embedding_top_k),
      provenance = coalesce(public.boq_line_items.provenance, excluded.provenance)
    returning 1
  )
  select count(*) into inserted_count from ins;
  return inserted_count;
end;
$$;
