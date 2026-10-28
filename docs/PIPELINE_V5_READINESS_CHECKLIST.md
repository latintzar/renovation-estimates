Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## Pipeline V5 — Readiness Checklist (DEPRECATED)

This document is **no longer required** as a post-BOQ “definition of done” gate.

We keep it only as an optional reference while we implement V5 via:
- `docs/PIPELINE_V5_IMPLEMENTATION_PLAN_SINGLE_STRATEGY.md` (milestones + Build → Run → Cement)
- the per-stage smoke reports written during RUN steps

V5 principle: treat this as if built from scratch.
- **One pipeline version**: V5.
- **One strategy**: `market_standard` only.
- **Slot-first everywhere**: clustering → PIR → delta → decompose → match → V4 tail.

---

### Naming + structure sanity (non-negotiable)

- [ ] **Single V5 module boundary exists** (no scattered “v5_*.py” across random folders).
  - Recommended: `lean-mvp/backend/pricing/v5/` as the single package.
- [ ] **Single V5 prompt registry exists**:
  - `lean-mvp/backend/pricing/v5/prompts/`
- [ ] **Single V5 schema module exists**:
  - `lean-mvp/backend/pricing/v5/schemas.py` (or `pricing/schemas/gemini_schemas_v5.py` but referenced only by V5)
- [ ] **Single V5 orchestrator exists**:
  - one entrypoint: `run_v5(listing_id, force=False, until_stage=None)`
- [ ] **No “multi-version” orchestrator logic** (no implicit fallbacks to V4/V3 upstream).

---

### Stage-by-stage readiness (artifacts + smoke slices)

For each stage below, readiness requires:
1) the stage runs in isolation (foreground script)
2) output is persisted under stable keys
3) output shape matches schema
4) logs show counts + sample rows
5) a markdown report is written to disk for review

#### Stage A — Input fetch (listing photos + listing tags)
- [ ] Fetch listing + photos reliably.
- [ ] Output persisted (optional) as `v5_listing_snapshot`.
- [ ] Smoke: `scripts/smoke_v5_fetch_listing.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_fetch_listing_<id>.md`

#### Stage B — Constrained clustering (canonical room types)
- [ ] Uses canonical allowlist (including open-plan/studio).
- [ ] Produces clusters labeled `room_type_N` with stable numbering.
- [ ] Persists `v5_clusters`.
- [ ] Smoke: `scripts/smoke_v5_clustering.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_clustering_<id>.md`

#### Stage C — Room tags (derived tags for protocols)
- [ ] Derives `room_type`, `environment`, `combined_types`, traits, confidence/evidence.
- [ ] Persists `v5_room_tags`.
- [ ] Smoke: `scripts/smoke_v5_room_tags.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_room_tags_<id>.md`

#### Stage D — Target PIR (per room, fixed slots, 1 narrative per slot)
- [ ] For each cluster: selects fixed slot list from room_type protocol.
- [ ] Enforces exactly one sentence per slot (string).
- [ ] Persists `v5_pir_target`.
- [ ] Smoke (one room): `scripts/smoke_v5_pir_target_room.py --listing-id <id> --room-id <rid>`
- [ ] Smoke (all rooms): `scripts/smoke_v5_pir_target_all_rooms.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_pir_target_listing_<id>.md`

#### Stage E — Comparable target definition (single strategy)
V5 runs only `market_standard`. Strategy selection is removed.

- [ ] We have a “market standard target” object expressed in slots:
  - either from comparables (whole-home PIR) or from a policy baseline.
- [ ] Persists `v5_market_standard_targets`.

#### Stage F — Delta (per room × slot one-liners)
- [ ] For each room: produces one-liner per slot: “no change” or “work needed”.
- [ ] Persists `v5_delta_slots_market_standard`.
- [ ] Smoke: `scripts/smoke_v5_delta_slots.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_delta_slots_<id>.md`

#### Stage G — Decomposition (slot one-liners → matchable work items)
- [ ] Decomposes each slot one-liner into 0–N work items.
- [ ] Persists `v5_work_items_market_standard`.
- [ ] Smoke: `scripts/smoke_v5_decompose_work_items.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_decompose_work_items_<id>.md`

#### Stage H — Adapter to V4 tail (temporary compatibility)
- [ ] Writes `v4_worklist_market_standard_<dimension>` from V5 work items.
- [ ] Runs V4 tail unchanged (match → quant plan → forage → BOQ).
- [ ] Smoke: `scripts/smoke_v5_to_v4_tail.py --listing-id <id>`
 - [ ] Report: `backend/reports/smoke_v5_to_v4_tail_<id>.md`

---

### Global quality gates

- [ ] **Cost guardrails**: explicit caps for photos per call and max tokens per call.
- [ ] **No silent omissions**: slot lists are deterministic; PIR/delta must return values for every slot.
- [ ] **Replayability**: rerun from any stage using persisted artifacts; no re-sending photos unless required.
- [ ] **Clean repo**: delete superseded orchestration paths immediately after replacement passes smoketests.

---

### Definition of “V5 is ready”

V5 is “ready” when:
- Listing 12 end-to-end produces a stable BOQ using **only** the V5 upstream path and a single strategy (`market_standard`), and
- every smoke script passes, and
- there is one orchestrator entrypoint used by the app.

