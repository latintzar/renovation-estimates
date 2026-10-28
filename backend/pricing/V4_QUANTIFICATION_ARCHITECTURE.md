# V4 — Agentic Quantification + Foraging Smart M2 (Design + Implementation Plan)

## Goal

Make BOQ quantities behave like a QS working from drawings:
- First decide **WHAT** work item we’re pricing (BCCA code + unit).
- Then decide **HOW** to measure it in this property (measurement method + formula).
- Then **forage** the needed measurement signals from floorplan/photos in a targeted way.
- Then compute quantity deterministically and price it (qty × unit_price, + labor hours).

**Critical constraint:** Every measurement signal should be **provable from a floorplan** when available, and otherwise **provable from photos** or explicitly marked as **defaulted/assumed** with conservative fallback rules.

### Floorplan-first policy (explicit)

- If a **floorplan exists**, the system must treat it as the **primary authority** for “count-like” and “layout-like” signals (openings, fixtures, MEP points where diagrammed).
- If a **floorplan does not exist**, the system may use **photos** for a limited subset of signals where visibility makes sense (openings, radiators, sanitary ware, visible boiler/panel, countertop runs).
- If a signal is **not reliably provable** without a floorplan, it must be either:
  - **not requested** by the Quantification Planner, or
  - requested with an explicit **default rule** (and it must be marked `defaulted=true` with clear notes).

## Why V3 isn’t enough

V3 forces the worklist generator to choose `quantity_ref` from TAKEOFF_MENU. This is robust, but it creates two failure modes:
- For some work items (notably electrical points), the true QS measurement is a **count primitive** that Smart M2 doesn’t provide, so the LLM picks area proxies (m²) which can be “valid” but conceptually wrong.
- Matching BCCA code/unit and quantification are coupled too early.

V4 separates concerns:
1) scope packages per room
2) BCCA match → unit
3) quantification plan → required signals + formula
4) smart m2 forage → signals (with provenance)
5) deterministic compute + pricing

## V4 Pipeline Overview (Diagram)

```
StrategySpec (narrative per room × dimension)
        |
        v
V4 Worklist (room-level scope packages; no quantity_ref)
        |
        v
BCCA Match (embeddings over rich candidate text)
=> chooses: {bcca_code, unit, unit_price, labor_hours_per_unit, full_desc}
        |
        v
Quantification Planner (LLM, per dimension)
=> outputs per (room_id, work_item_id):
   - required_signals[]   (from measurement catalog)
   - formula_ast          (deterministic expression referencing signals)
   - provability guidance (floorplan-first, photo fallback, default rules)
        |
        v
Smart M2 Forage (LLM, per room)
=> extracts/estimates required_signals from floorplan/photos
   + returns provenance: confidence, evidence pointers, defaulted flags
        |
        v
Deterministic BOQ Assembly
=> quantity = eval(formula_ast, signals)
=> line_total = quantity * unit_price
=> labor_hours = quantity * labor_hours_per_unit
```

## New Concepts

### Measurement Catalog (V4)

Replace TAKEOFF_MENU-as-strings with a typed “catalog” of possible signals that can exist in any dwelling.

Each signal specifies:
- `signal_id`
- `unit_family`: one of `m2 | ml | ud | m3`
- `provable_from`: `floorplan | photos | either | not_reliably_provable`
- `fallback_rule`: deterministic conservative fallback if not provable (only allowed when explicitly permitted)
- `notes`: how a QS would interpret it

Examples (not exhaustive):
- `room_floor_area_m2`
- `room_ceiling_area_m2`
- `room_wall_net_area_m2`
- `opening_count_by_type(door|window|balcony_door)`
- `opening_area_total_m2_by_type(...)`
- `countertop_run_ml`
- `wardrobe_run_ml`
- `radiator_count_ud`
- `boiler_count_ud`
- `sanitary_set_count_ud`
- `light_point_count_ud` (**floorplan-first**; photos fallback if visible; else defaulted)
- `socket_count_ud` (**floorplan-first**)
- `switch_count_ud` (**floorplan-first**)

### Quantification Plan (V4)

For each room work item, the planner outputs:
- `required_signals[]`: list of signal_ids from the catalog
- `formula_ast`: a deterministic expression using only:
  - `SIGNAL(signal_id)`
  - numeric constants
  - `+ - * /`
  - `MIN/MAX` (optional)
  - `CEIL/FLOOR` (optional)
- `units`: must be consistent with the BCCA unit
- `provability`: per signal, whether floorplan or photos should be used, and when defaulting is allowed

No “free numeric quantities” are permitted unless they are derived from signals + declared ops.

### Smart M2 Forage (V4)

Smart M2 becomes targeted:
- It is given only the signals required for a room, plus evidence sources:
  - floorplan (if available)
  - room photos
  - prior smart_m2 baseline geometry (optional)
- It returns signal values with provenance:
  - `value`, `unit_family`
  - `confidence`
  - `evidence`: `{source: floorplan|photo, indices/refs}`
  - `defaulted: true/false`
  - `notes`

## Data Contracts (Schemas)

### V4 Worklist (room-level)

- `strategy_name`
- `dimensions` → per dimension:
  - `room_blocks[]`:
    - `room_id`
    - `scope_packages[]`:
      - `work_item_id`
      - `work_description` (Spanish, BCCA-ish noun phrase; may be compact)
      - `target_element` (optional)
      - `source_scope_refs` (optional pointers into StrategySpec / delta scope)

### V4 BCCA Matches (per room work item)

- `work_item_id`, `room_id`, `dimension`
- `bcca_code`
- `unit` (from BCCA)
- `unit_price`
- `labor_hours_per_unit`
- `bcca_desc_100`
- `bcca_full_desc`
- `embedding_similarity`
- `top_k` (audit)

### V4 Quantification Plan

- `work_item_id`, `room_id`, `dimension`
- `required_signals[]`
- `formula_ast`
- `unit_family` (must match BCCA unit family)
- `notes` (short, for audit only)

### V4 Signals Store (per listing)

Persist per room:
- `room_id`
- `signals`: `{signal_id: {value, unit_family, confidence, evidence, defaulted, notes}}`

## Deterministic Compute

A deterministic evaluator:
- validates all referenced signals exist
- checks unit family consistency
- computes the numeric quantity

## Implementation Plan (Changelog)

## Implementation Checklist (do in this order)

This section is intentionally “do-this-next” so it’s unambiguous.

### Milestone 0 — Pipeline health (must be green before V4)

- [x] Ensure `workers/handlers.py` imports cleanly (no indentation/syntax errors).

### Milestone 1 — Contracts (catalog + schemas)

- [ ] Add `pricing/measurement_catalog_v4.py`
  - Define canonical `signal_id`s
  - Define `unit_family` per signal
  - Define `provable_from` policy per signal (`floorplan|photos|either|not_reliably_provable`)
  - Define whether defaulting is permitted, and what deterministic default rule applies
- [ ] Add `pricing/schemas/gemini_schemas_v4.py`
  - V4 Worklist schema (room-level scope packages; no quantity refs)
  - V4 Quantification Plan schema (signals + formula AST)
  - V4 Smart M2 Forage schema (signals with provenance)
  - (Optional) V4 BCCA match audit schema

**Acceptance criteria:**
- Schemas are strict and reject unknown fields (fail-loud).
- Every `signal_id` referenced by V4 schemas must exist in `measurement_catalog_v4.py`.

### Milestone 2 — Deterministic quantity evaluator

- [ ] Add `pricing/quantity_formula_v4.py`
  - Validate `formula_ast` shape and allowed operators
  - Extract referenced `signal_id`s
  - Evaluate deterministically given `{signal_id -> value}`
  - Validate final `unit_family` matches the matched BCCA unit family

**Acceptance criteria:**
- If a signal is missing, raise an exception with context (work_item_id, room_id, missing signal_id).
- If the formula uses an unsupported op, raise immediately.
- If the computed quantity is negative/NaN/inf, raise immediately.

### Milestone 3 — V4 Quantification Planner (LLM step)

- [ ] Add `pricing/v4_quantification_planner.py`
  - Input: (dimension) StrategySpec + V4 Worklist room items + BCCA matches + Measurement Catalog + “floorplan availability” flags
  - Output: V4 Quantification Plan
  - Hard rule: planner cannot output raw quantities; must output `formula_ast` referencing signals.

**Acceptance criteria:**
- Planner never requests `provable_from=floorplan` signals when floorplan is missing, unless it also declares a default rule and marks it defaultable.
- Planner outputs plans at **room-level** (room_id scoped).

### Milestone 4 — Targeted Smart M2 Forage (LLM step)

- [ ] Add `pipeline/steps/smart_m2.py` helper: `get_smart_m2_forage_prompt_v4(...)`
  - Input: required_signals + (room photos) + (floorplan image if exists)
  - Output: only requested signals, with provenance and defaulted flags
- [ ] Add persistence hook in DB/unified_estimates:
  - `v4_measurement_signals_{strategy}` (or listing-level, but keyed by strategy for reproducibility)

**Acceptance criteria:**
- If floorplan exists, the forage step must reference it for count-like signals (and include evidence).
- If a signal is not provable and no default rule exists, the forage step must fail (not silently skip).

### Milestone 5 — BOQ assembly (deterministic)

- [ ] Add `pricing/v4_boq_assembler.py`
  - Input: BCCA matches + V4 Quantification Plan + signals store
  - Output: line items written to `boq_line_items` with per-room granularity preserved

**Acceptance criteria:**
- Every priced line item records: work_item_id, room_id, bcca_code, unit, unit_price, quantity, formula_ast, signals_used, defaulted_any.
- No room merging bugs (room_id preserved in DB write).

### Milestone 6 — Smoke test + audit report

- [ ] Add `scripts/smoke_v4_quantification.py`
  - listing_id=12
  - run exactly 1 strategy + 1 dimension end-to-end
  - emit a markdown report with:
    - work item → BCCA match (topK) → signals → formula → qty → € total

**Acceptance criteria:**
- Script exits non-zero on any missing prerequisites (StrategySpec, Worklist, Smart M2, PIR).
- Output markdown is deterministic and audit-friendly.

### Milestone 7 — Rollout plan

- Run V4 side-by-side with V3 for listing 12, compare:
  - “count-ish” items (ud) that were incorrectly measured by m² in V3
  - top outliers by € and by labor hours
  - percentage of defaulted signals

### 1) Schemas
- Add V4 schemas in `pricing/schemas/gemini_schemas_v4.py`:
  - `V4_WORKLIST_SCHEMA`
  - `V4_BCCA_MATCH_SCHEMA`
  - `V4_QUANTIFICATION_PLAN_SCHEMA`
  - `V4_SMART_M2_FORAGE_SCHEMA`

### 2) Measurement Catalog
- Add `pricing/measurement_catalog_v4.py` with typed catalog entries.
- Include provability flags and default rules.

### 3) New Pipeline Handlers
Implement handlers in `workers/handlers.py`:
- `handle_v4_worklist` (StrategySpec → room scope packages)
- `handle_v4_bcca_match` (scope packages → BCCA code/unit/price)
- `handle_v4_quantification_plan` (per dimension → required_signals + formula_ast)
- `handle_v4_smart_m2_forage` (per room → fill signals)
- `handle_v4_boq_assemble` (deterministic eval + writes `boq_line_items`)

### 4) Smart M2 Forage Prompt
- Add `pipeline/steps/smart_m2.py` helper: `get_smart_m2_forage_prompt(room, required_signals, listing_context)`
- Output should be strictly limited to requested signals.
- Floorplan-first rule: if floorplan is available, it must be used for count-like signals.

### 5) Storage
Add new storage key(s) in unified_estimates:
- `v4_measurement_signals_{strategy}` (or listing-level `v4_measurement_signals`)
- `v4_quantification_plan_{strategy}`
- `v4_bcca_matches_{strategy}`
- `v4_boq_{strategy}` (or continue using `boq_line_items` + `dimension="v4"`)

### 6) Smoke Tests
Add scripts:
- `scripts/smoke_v4_quantification.py`:
  - listing_id=12
  - run ONE strategy + ONE dimension end-to-end
  - assert:
    - every work item has a BCCA match
    - every plan formula evaluates with available signals
    - no defaulted signals when floorplan exists (if floorplan provided)
    - outputs deterministic quantities and non-zero pricing

### 7) Rollout
- Implement V4 alongside V3 (do not delete V3).
- Run on listing 12 only.
- Compare:
  - number of “count-ish” items priced by m² in V3 vs V4
  - top cost outliers
  - labor hours coverage

## Open Questions (to finalize before coding)
- Floorplan availability detection: where is floorplan stored and how do we access it per listing?
- Which signals are allowed to be defaulted without floorplan?
- Cost controls: max signals per room, max LLM calls per dimension.

