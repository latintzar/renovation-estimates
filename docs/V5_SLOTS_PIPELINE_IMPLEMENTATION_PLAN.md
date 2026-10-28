Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## V5 Implementation Plan — Slot-first pipeline (Room Tags + Slots → PIR → Strategy → Delta → Decompose → BCCA → V4 Tail)

This plan upgrades the pipeline end-to-end so renovation scope becomes **slot-complete**, **room-aware**, and **catalog-matchable**, while keeping **quant planning + foraging + costing/timing + post-BOQ unchanged**.

Constraints:
- **One narrative per slot** (no extra structured attributes in PIR V5).
- **No structural engineering** scope in V5.
- Listing 12 is used only for **smoke tests** after implementation.

---

### Execution protocol (undisturbed runs + review gate)

This work is executed as two undisturbed runs, followed by a gated cleanup phase:

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

### V4 (current) vs V5 (target) — side-by-side

```text
V4 (CURRENT end-to-end)                                  V5 (TARGET end-to-end)
───────────────────────────────────────────               ───────────────────────────────────────────
Listing → photos + metadata                               Listing → photos + metadata
        |                                                         |
Photo clustering (open-ish labels)                         Constrained clustering (canonical room types)
        |                                                         |
Target PIR (per cluster, 6 dims narratives)                Room tags (per cluster: room_type/environment/combined_types)
Comparable PIR (whole-home, 6 dims narratives)             Comparable PIR V5 (whole-home, slot schema from tags)
        |                                                  Target PIR V5 (per cluster, slot schema from protocol)
Strategy selection (from PIR narratives)                           |
        |                                                         v
Delta scope (narrative deltas by 6 dims)                   Strategy selection V5 (slot targets per tier)
        |                                                         |
Worklist generation (LLM writes BCCA-ish items)                     v
        |                                                  Delta V5 (per room × slot one-liners)
BCCA match (embeddings)                                            |
        |                                                           v
Quant plan → forage → deterministic BOQ                      Decompose V5 (cheap LLM → BCCA-matchable work items)
                                                             BCCA match → V4 tail (UNCHANGED)
```

---

### Architecture diagram (V5)

```text
Comparable listings (no clustering)                  Target listing (needs clustering)
  - Casafari tags + all photos                         - all photos
                |                                               |
      tag→schema(decide slots)                         constrained clustering (room types)
                |                                               |
                v                                               v
Comparable PIR V5 (whole-home, slot schema)         Canonical room clusters V5
  - 1 narrative per slot                              - labels: bathroom_full_1, kitchen_1, ...
  - “typical bathroom/kitchen” slots                  - open-plan clusters: combined_types[]
                |                                               |
                +----------------------+------------------------+
                                       v
Target PIR V5 (per cluster, slot schema)
  - 1 narrative per slot per room
                                       |
                                       v
Strategy selection V5 (slot targets per tier)
  - conservative / market_standard / top_of_market
  - expressed in slot vocabulary
                                       |
                                       v
Delta V5 (per room × slots)
  - for each relevant slot: one-liner “work needed”
                                       |
                                       v
Work-item decomposition V5 (cheap LLM)
  - slot one-liners → BCCA-matchable work_items[]
                                       |
                                       v
BCCA match (embeddings)
                                       |
                                       v
V4 tail (UNCHANGED)
  - quant plan → forage → deterministic BOQ → post-BOQ
```

---

### Repo hygiene rule (keep the repo clean)

We will **not** defer cleanup to the end. For each milestone:
- Add the new V5 path.
- Wire it into the pipeline behind a clear switch/key.
- Run the milestone’s smoke test(s).
- **Immediately remove/retire the superseded code path** if it is no longer referenced.

This keeps the repo clean while still being safe (git history is the rollback).

---

### Implementation tracking (tick-off)

Use this checklist as the single source of truth while implementing.

- [ ] Milestone 0 implemented
- [ ] Milestone 0 tested (static validation)
- [ ] Milestone 1 implemented
- [ ] Milestone 1 tested (listing 12 clustering)
- [ ] Milestone 2 implemented
- [ ] Milestone 2 tested (listing 12 room tags)
- [ ] Milestone 3 implemented
- [ ] Milestone 3 tested (at least 1 comparable)
- [ ] Milestone 4 implemented
- [ ] Milestone 4 tested (listing 12 target PIR per room)
- [ ] Milestone 5 implemented
- [ ] Milestone 5 tested (listing 12 tier targets)
- [ ] Milestone 6 implemented
- [ ] Milestone 6 tested (listing 12 delta per room × slot)
- [ ] Milestone 7 implemented
- [ ] Milestone 7 tested (listing 12 decomposition → matchable work items)
- [ ] Milestone 8 implemented
- [ ] Milestone 8 tested (listing 12 end-to-end 1 strategy)
- [ ] Milestone 9 implemented (KG + legacy cleanup)
- [ ] Milestone 9 tested (no pipeline dependency on deleted code)

---

### What’s NEW (V5)

- **Canonical room type allowlist for clustering** (incl. open-plan + studio labels).
- **Room tags V5** persisted per cluster:
  - `room_type`, `environment`, `traits`, `combined_types`, confidence + evidence refs.
- **Slot schemas** used everywhere (same slot universe across PIR/strategy/delta).
- **Comparable PIR V5 (whole-home)**:
  - schema decided by Casafari tags (no clustering).
  - outputs “typical room” narratives per slot.
- **Target PIR V5 (room-by-room)**:
  - schema decided by room tags/protocol for each cluster.
  - outputs 1 narrative per slot per cluster.
- **Delta V5 (per room × slots)**:
  - outputs 1 one-liner per slot describing work required to reach tier target.
- **Decomposition V5**:
  - cheap LLM turns slot one-liners into **BCCA-matchable** work items (still room-scoped).

---

### What gets REFACTORED (keep, but rewire)

- **Clustering step**: switch from open-ended room names to constrained canonical labels.
- **`pricing/pir_generator.py`**:
  - split into: comparable PIR V5 (whole-home) + target PIR V5 (per room cluster).
  - keep: caching, image handling, persistence patterns.
- **`pricing/strategy_selector.py`**:
  - consume V5 PIR slot narratives (comparable + target) and output tier targets in slots.
- **`pricing/delta_scope_generator.py`**:
  - output per-room slot one-liners (instead of the current narrative-heavy delta structures).
- **Upstream-to-V4 glue**:
  - replace the “V4 worklist generator” entry with “V5 decomposition output” feeding into BCCA matching + the existing V4 quantification flow.

---

### What gets DEPRECATED/DELETED (as requested)

#### Deprecate KG from runtime/prompt context (V5)
- Remove KG context injection from prompts and decision-making once V5 is green.
- Keep files temporarily until V5 smoke tests pass, then delete.

Candidates to remove after V5 is stable:
- `backend/pricing/hybrid_renovation_graph.json`
- `backend/pricing/flatten_kg.py`
- `backend/pricing/enrich_kg_quantity_guidance.py`
- `backend/pricing/kg_context.yaml`
- Any KG traversal utilities only used to expand task chains

#### Delete-and-remake (recommended)
These are better as clean V5 contracts rather than mutating existing V2/V3 outputs:
- PIR output schema(s) for V5 (new files / new keys)
- Delta output schema for V5 (slot-first)

---

## Implementation milestones (do in order)

### Milestone 0 — Lock the V5 vocab + protocols (no pipeline behavior change)

Deliverables:
- Canonical room type allowlist (for clustering)
- Slot universe (GSO slots)
- Room-type → slot protocol mapping (complete)

Sources already drafted:
- `docs/ROOM_TAGS_SLOTS_GSO_V1.md`
- `docs/SLOTS_BY_ROOM_TYPE_V1.md`

Acceptance:
- Every canonical room type has a protocol.
- Open-plan and studio are defined via union rules.
- Home-level slots have a deterministic host-room policy.

---

### Milestone 1 — Constrained clustering V5 (target listings)

Goal:
- Make clustering output deterministic and canonical: `bathroom_full_1`, `kitchen_1`, etc.

Work:
- Update/extend clustering step to accept:
  - allowed room type labels
  - numbering rule for multiples
  - open-plan labels as valid outputs

Acceptance:
- Listing 12 produces canonical clusters with stable labels.
- Open-plan clusters produce `combined_types[]` tags (even if approximate).

---

### Milestone 2 — Room tags V5 (target clusters)

Goal:
- Attach tags that drive slot schema selection deterministically.

Work:
- Implement `room_tags_v5` builder:
  - inputs: canonical cluster label, cluster photos, any detected openings/features
  - outputs: `room_type`, `environment`, traits, `combined_types`, confidence + evidence refs

Acceptance:
- Listing 12 clusters all have room tags.
- `open_plan_*` clusters get `combined_types` populated.

---

### Milestone 3 — Comparable PIR V5 (whole-home)

Goal:
- No clustering for comparables; choose schema from Casafari tags.

Work:
- Add new comparable PIR function:
  - chooses which “typical rooms” exist (counts optional) from Casafari tags
  - emits 1 narrative per slot for:
    - typical kitchen, typical bathroom, typical bedroom, typical living, typical exterior (if any)
  - keeps outputs intentionally “fuzzy” but slot-complete at the home level

Acceptance:
- For a comparable, PIR V5 always emits all slots required by the inferred home composition.

---

### Milestone 4 — Target PIR V5 (per room cluster)

Goal:
- Generate a slot-complete room-by-room PIR for the target listing.

Work:
- For each cluster:
  - select its protocol from `SLOTS_BY_ROOM_TYPE_V1`
  - call LLM with the room photos and require exactly 1 narrative sentence per slot

Acceptance:
- Every required slot has exactly one narrative sentence per room.
- No extra prose blocks outside slots.

---

### Milestone 5 — Strategy selection V5 (slot targets per tier)

Goal:
- Produce tier targets expressed in the same slot vocabulary.

Work:
- Replace old strategy selector inputs with:
  - comparable PIR V5 (whole-home slot narratives)
  - target PIR V5 (room slot narratives)
- Output:
  - per tier: slot-level “target state” (still 1 narrative per slot), at:
    - home-level + room-type archetype level (not per specific room yet)

Acceptance:
- Tier targets are monotonic (top_of_market >= market_standard >= conservative).
- Targets cover all slots required by the home composition.

---

### Milestone 6 — Delta V5 (per room × slots)

Goal:
- Convert tier targets into per-room action one-liners per slot.

Work:
- For each target room cluster:
  - compute relevant slots from protocol (including open-plan union)
  - compare target room slot narrative vs tier target slot narrative
  - output 1 one-liner per slot: “what needs to be done”
- Provide optional framing guidance to LLM:
  - “transformation vs hygiene” as thinking aid only (not a hard schema)

Acceptance:
- Every relevant slot for every room yields one one-liner (can be “no change”).

---

### Milestone 7 — Decomposition V5 (slot one-liners → BCCA-matchable work items)

Goal:
- Convert slot one-liners into 1..N work items that match the pricing catalog.

Work:
- Cheap model (Gemini Flash):
  - input: room_id, dimension, slot_id, one-liner
  - output: list of `work_items[]` (short BCCA-ish descriptions)

Acceptance:
- Each non-no-op slot produces at least one work item.
- Work item strings are short and matchable (construction-noun phrasing).

---

### Milestone 8 — BCCA match + V4 tail unchanged

Goal:
- Feed V5 work items into existing V4 BCCA match + quant plan + forage + BOQ.

Work:
- Adapter layer:
  - construct the V4 worklist structure from V5 work items (or bypass V4 worklist generation entirely if the downstream expects only work item lists).

Acceptance:
- End-to-end pricing runs for listing 12 for at least one strategy.

---

### Milestone 9 — Cleanup

Goal:
- After V5 smoke tests pass, remove unused legacy paths and KG.

Work:
- Remove KG context usage and delete KG-only files/modules (see above).
- Archive/deprecate old PIR and delta generation paths if no longer used.

Acceptance:
- All pipeline stages still run cleanly without KG assets.

---

## Smoke test plan (listing 12)

Required smoke tests after implementation:

1) **Clustering V5**
- produces canonical room types + numbering
- open-plan cluster case handled if present

2) **Room tags V5**
- every cluster gets tags, environment, and combined_types when needed

3) **Target PIR V5**
- per cluster: returns 1 narrative per required slot

4) **Comparable PIR V5**
- whole-home: returns slot-complete narratives based on Casafari tags

5) **Strategy selection V5**
- outputs tier targets per slot (home + archetype)

6) **Delta V5**
- per target room: produces one-liner per slot

7) **Decomposition V5**
- produces BCCA-matchable work items

8) **Existing V4 tail**
- BCCA match + quant plan + forage + BOQ completes without changes to quant/forage/cost/post-BOQ

