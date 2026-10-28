Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## Pipeline V5 — Implementation Plan (Strict, Single Strategy = Market Standard)

This replaces prior “multi-version” plans. We implement V5 as if from scratch:

- **One strategy**: `market_standard` only.
- **Slots everywhere**: room_type → fixed slot list; PIR/delta always produce one value per slot.
- **No KG** in runtime context.
- **V4 tail unchanged** (match → quant plan → forage → BOQ), consumed directly from V5 work items (no adapter artifacts).

---

## Execution protocol (undisturbed runs + review gate)

This plan is executed as two undisturbed runs, followed by a gated cleanup phase.

- **Part A — Build-to-testing (autonomous coding; no expensive smokes yet)**  
  Implement missing stages, prompts, and strict schemas so the pipeline is ready to test end-to-end.

- **Part B — Testing/Debugging run (listing 12 only; foreground; until MD output)**  
  Run smokes in order in a continuous foreground session (bounded `timeout` slices if needed). On failure: fix immediately and rerun the same smoke. Every smoke writes a markdown report.

- **Review gate (stop + wait)**  
  After the markdown outputs exist, perform a structured review and then **stop** for an explicit user go/no-go decision before proceeding to any deletions/cleanup.

Enforcement artifacts (already present in this repo):
- Project skill: `.cursor/skills/v5-undisturbed-runs/SKILL.md`
- Project subagent: `.cursor/agents/pipeline-test-runner.md`

---

### The only architecture we build (V5)

```text
Listing (target) (photos + listing info)
  -> V5 constrained clustering (canonical room types)                [TARGET photos only]
  -> V5 room tags                                                    [deterministic]
  -> V5 target PIR                                                   [parallel: 1 call per room; 1 sentence per slot]

Listing (comparables) (listing info + photos)
  -> Fetch comparables                                                [uses target listing info]
  -> Infer comparable "room plan" from listing info/features           [NO comparable photo clustering]
  -> V5 comparable PIR                                                [parallel: 1 call per comparable; ALL photos; 1 sentence per slot]
  -> Comparable selector (market_standard reference)                   [pick 1 comparable]

Merge
  -> V5 market targets (slot targets for market_standard)              [uses target PIR + selected comparable PIR]
  -> V5 delta (per room × slot narratives; "no change" or 3–5 sentences)
  -> V5 decomposition (per room × dimension; dimension-scoped BCCA vocab menu)
  -> V4 tail (unchanged): BCCA match → quant plan → forage → BOQ (dimension-scoped embedding pools, prebuilt)
```

---

## Repository organization (do this first)

Create a clean V5 boundary so the code doesn’t sprawl:

- `lean-mvp/backend/pricing/v5/`
  - `room_types.py`
  - `slots.py`
  - `schemas.py`
  - `prompts/`
  - `clustering.py` (wraps `pipeline/steps/cluster_photos_v5.py` if you keep it there)
  - `pir.py`
  - `delta.py`
  - `decompose.py`
  - `to_v4_adapter.py`
  - `orchestrator.py`
- `lean-mvp/backend/scripts/` smoke scripts: `smoke_v5_*.py`

Rule: V5 stages must import from `pricing.v5.*`, not from scattered legacy modules.

---

## Strategy simplification (remove 3-tier logic)

We delete the idea of “strategy selection” for V5:
- No conservative / top_of_market.
- No anchoring to comparable IDs.
- Only: **market standard**.

We still may use comparables, but only to define a single target standard.

---

## Milestones (strict order, delete-as-you-replace)

### Discipline inside Part A (Build → Smoke → Cement)

For every milestone in Part A, do these three steps in order:

1) **BUILD**: implement the stage code + schema + prompt.
2) **SMOKE**: run the stage as a standalone foreground smoke on **listing 12** only, writing a markdown report.
3) **CEMENT**: once it passes, wire it into the V5 orchestrator and retire any superseded wiring.

**Development cost constraint (smokes on listing 12):** to keep iteration cheap, smoke tests may reuse already-fetched comparables and/or cached comparable PIR artifacts for listing 12. This is **not** the intended production architecture: for new listings, we **do** generate comparable PIRs (1 call per comparable, using all comparable photos, no clustering).

**Audit requirement (new):** Every RUN step must write a **markdown report** to disk so outputs can be reviewed. The report should include:
- counts (rooms / slots / items)
- a small sample (first room or first tier)
- the persisted key(s)

**Legacy deletion guardrail:** Do not delete/disable legacy V2/V3 routes/handlers during Part A. Full legacy cleanup happens only after Part B’s review gate (see “Part C” below).

### Milestone 0 — Move/normalize existing V5 building blocks into `pricing/v5/`

Goal:
- Consolidate without changing behavior.

Work:
- Relocate current V5 modules (room types, slots, schemas, prompts, PIR, delta, decomposition) into the V5 package.
- Update imports so V5 uses its own package boundary.
- Keep a minimal compatibility layer if needed for temporary imports.

Smoke:
- `python -m py_compile` for all V5 modules.

Cleanup:
- Delete old duplicated V5 files after migration.

---

### Milestone 1 — V5 clustering end-to-end (listing → `v5_clusters`)

Goal:
- Constrained clustering produces canonical room types + numbering.

Work:
- Implement `pricing/v5/clustering.py` wrapper that:
  - loads listing photos
  - calls constrained clustering
  - persists `v5_clusters`

Smoke:
- `scripts/smoke_v5_clustering.py --listing-id 12`

 Cement:
 - Add Stage B to `pricing/v5/orchestrator.py` (runs before PIR).
 - Ensure no V5 path reads legacy clusters.

Cleanup:
- Ensure the app/orchestrator will call V5 clustering, not the legacy open-ended version.

---

### Milestone 2 — Room tags (`v5_room_tags`)

Goal:
- Deterministic room tags derived from clusters.

Work:
- Implement room tags builder:
  - `room_type`, `environment`, `combined_types`, traits, evidence/confidence
- Persist `v5_room_tags`

Smoke:
- `scripts/smoke_v5_room_tags.py --listing-id 12`

 Cement:
 - Add Stage C to the orchestrator after clustering.

---

### Milestone 3 — Target PIR V5 (`v5_pir_target`)

Goal:
- For each room cluster, run PIR with the fixed slot list for that room_type.

Work:
- Implement PIR target runner:
  - per room: 1 sentence per slot
  - visibility handled by “not visible + assumption” sentence (prompt-enforced)
- Persist `v5_pir_target`

Smoke:
- `scripts/smoke_v5_pir_target_room.py --listing-id 12 --room-id <rid>`
- `scripts/smoke_v5_pir_target_all_rooms.py --listing-id 12`

 Cement:
 - Add Stage D to orchestrator. Persist per-room PIR payload and reuse on reruns.

Cleanup:
- Stop using legacy target PIR generation in any V5 path.

---

### Milestone 4 — Market targets (`v5_market_standard_targets`)

Goal:
- Define the *one* target standard in slots.

Two acceptable V5 implementations (pick one and ship):

**Option A: Comparable-driven**
- Production: fetch comparables, infer comparable room plan from comparable listing info/features (**no comparable photo clustering**), then generate comparable PIRs (1 call per comparable, ALL photos, 1 sentence per slot), then select the market_standard reference.
- Development: for listing 12 smokes, it is acceptable to reuse cached comparable PIR artifacts to control cost.
- Synthesize one market-standard slot target set from (target PIR + selected comparable PIR).

**Option B: Policy baseline**
- If comparables are not reliable/available, define market targets as policy templates per room archetype + slot.

Work:
- Persist `v5_market_standard_targets`.

Smoke:

 Cement:
 - Add Stage E to orchestrator. Targets must be persisted and reused.

---

### Milestone 5 — Delta (`v5_delta_slots_market_standard`)

Goal:
- Per room × slot: `"no change"` or a **3–5 sentence** work narrative.

Work:
- Generate delta by comparing:
  - target PIR slot narrative (current)
  - market target slot narrative (desired)
- Persist `v5_delta_slots_market_standard`

Smoke:
- `scripts/smoke_v5_delta_slots.py --listing-id 12`

 Cement:
 - Add Stage F to orchestrator. Delta must be persisted and reused.

---

### Milestone 6 — Decomposition (`v5_work_items_market_standard`)

Goal:
- Convert each non-“no change” slot narrative into catalog-matchable work items.

Work:
- Decompose per (room, dimension) so the prompt can enforce **dimension-scoped BCCA vocabulary**.
- Persist a flat list of work items

Smoke:
- `scripts/smoke_v5_decompose_work_items.py --listing-id 12`

 Cement:
 - Add Stage G to orchestrator. Decomposition must be cached per room×dimension.

---

### Milestone 7 — V4 tail run directly from V5 work items (no adapter artifacts)

Goal:
- Feed V5 work items into V4 tail without changing quant/forage/BOQ logic.

Work:
- Do **NOT** write any intermediate `v4_worklist_*` artifacts.
- Call V4 tail using V5 work items directly (in-memory worklist view only):
  - BCCA match → quant plan → forage → BOQ
  - Suggested entrypoint: `pricing.v4_quantification_pipeline.run_v4_tail_from_v5_work_items(...)`

Smoke:
- `scripts/smoke_v5_to_v4_tail.py --listing-id 12`

 Cement:
 - Add Stage H to orchestrator to invoke the V4 tail from V5 work items (no adapter stage).

Cleanup:
- Remove any remaining “bridge” paths that bypass V5 clustering/tags.

---

### Milestone 8 — Single orchestrator + app wiring

Goal:
- The app has **one** orchestrator path for pricing a listing: V5.

Work:
- Add a single V5 orchestrator entrypoint used by the worker/job system.
- Ensure no other pipeline version is used for renovation pricing.

Smoke:
- One command that runs the full pipeline for listing 12 and prints all artifact keys.

Cleanup:
- Delete/disable legacy job handlers that are not used by V5.

---

## Part B — Smoke test run (listing 12 only) + review gate

After Part A milestones are complete, run the full smoke suite for listing 12 in order, producing markdown reports:

- `scripts/smoke_v5_clustering.py`
- `scripts/smoke_v5_room_tags.py`
- `scripts/smoke_v5_pir_target_*` (room + all-rooms)
- comparable fetch/plan/PIR/selector smokes (as implemented)
- `scripts/smoke_v5_delta_slots.py`
- `scripts/smoke_v5_decompose_work_items.py`
- `scripts/smoke_v5_to_v4_tail.py`

Then produce (or point to) a final end-to-end markdown report that includes:
- counts (rooms / slots / items)
- selected comparable summary (if comparable-driven)
- delta sample excerpts
- top mismatches sample from BCCA match (if available)
- BOQ totals

Finally, perform a structured quality review and **stop** for the user’s go/no-go decision.

---

## Part C — Delete legacy (only after user approves post-review)

After the review gate go-ahead:
- Delete/disable V2/V3 pipeline routes and unreachable handlers.
- Remove legacy strategy selection / delta scopes / KG runtime plumbing that is no longer used.
- Keep only shared infra needed by V5 (DB, queue worker, Casafari client, etc.).

