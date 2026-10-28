Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## Pipeline changelog — Room Tags + Slots (GSO) V1

This is the most direct, minimal change-set to evolve the existing pipeline toward **gap-proof completeness** without blowing up call count.

---

### What stays the same (important)

- **6 dimensions remain** as the top-level structure (`V2_DIMENSIONS`).
- **V4 stays**: worklist → embeddings match to BCCA → quant plan → forage → deterministic BOQ.
- **Embeddings stay**: still the right primitive for candidate retrieval in a large catalog.
- **Strategy tiers stay**: `conservative`, `market_standard`, `top_of_market`.

---

### What changes (V1)

#### 1) Add “Room Tags” as a persisted artifact

- **New artifact**: `room_tags_v1` (per listing)
- **Purpose**: attach canonical room meaning to clusters so we can apply slot rules deterministically.
- **Implementation suggestion**
  - Leverage `pricing/room_inference.py` where textual room names exist.
  - Add a fallback “image-based room typing” prompt only for clusters with low-confidence tags.

**New unified_estimate keys**
- `v1_room_tags` (or `v4_room_tags` if you want to align with V4 naming)

#### 2) Add “Slot Plan” per strategy (the completeness checklist)

- **New artifact**: `slot_plan_v1` (per listing × strategy)
- **Purpose**: for each `(room, dimension)`, list required slots and whether the slot is `DELTA` vs `BASELINE`.
- **Rules**:
  - Slot applicability is deterministic from room tags (wet/dry/exterior + room_type + openings/features).
  - Slot state is decided from strategy spec delta vs baseline; baseline can be reused upward across tiers.

**New unified_estimate keys**
- `v1_slot_plan_{strategy}`

#### 3) Change the worklist prompt to be “slot-complete” (not open-ended prose)

Current V4 worklist prompt asks for room-level scope packages per dimension from narrative.

V1 change:
- Include the **slots list** for that dimension and require the output to either:
  - produce ≥1 scope package per required slot, or
  - explicitly mark slot as “no-op baseline” (if that’s allowed policy)

**Where**
- `backend/pricing/v4_quantification_pipeline.py` → `build_v4_worklist_prompt(...)`

**Schema change (recommended)**
- Extend `V4_SCOPE_PACKAGE_SCHEMA` with:
  - `slot_id` (string; enum = V1 slots for that dimension)
  - `slot_state` (`DELTA|BASELINE`)
  - `assumption_level` (optional)

**Where**
- `backend/pricing/schemas/gemini_schemas_v4.py`

#### 4) Add a deterministic “slot coverage validator” before BCCA matching

- **Purpose**: fail loud if any required slot is missing in the worklist for a room.
- **Where**
  - Add to `backend/pricing/worklist_validator.py` (or add a new validator module)

**Validator checks**
- For each required slot instance: ≥1 scope package with that `slot_id`
- Every scope package has `slot_id`, `room_id`, `dimension`

#### 5) BCCA matching becomes “slot-filtered retrieval”

V1 change:
- For each scope package, use `slot_id` to narrow candidate retrieval.
  - Either filter by a precomputed allowed BCCA family list for the slot, or
  - run retrieval and then rerank with slot-aware penalties.

**Where**
- `backend/pricing/bcca_embedding_matcher.py` (add optional filters)
- `backend/pricing/v4_quantification_pipeline.py` (pass slot_id into match step)

**New config (region adapter)**
- `slot_id → allowed BCCA families/codes` mapping file
  - Start coarse; tighten iteratively.

#### 6) Quantification planner and foraging remain unchanged in call count

No new call explosion required:
- Planner stays per dimension.
- Forage stays per room.

Slots improve **correctness** by stabilizing *what* gets matched, not by increasing LLM calls.

---

### Migration plan (smallest shippable steps)

#### Step A — Persist room tags (no downstream change yet)
- Output `v1_room_tags` and inspect on listing 12.

#### Step B — Generate slot plan (no worklist change yet)
- Output `v1_slot_plan_{strategy}` for listing 12.
- Build a simple report: required slots count by room/dimension.

#### Step C — Enforce slot coverage in worklist output
- Update worklist prompt + schema to include `slot_id`.
- Add validator that fails on missing slot coverage.

#### Step D — Slot-filter BCCA matching (quality boost)
- Use `slot_id` to restrict candidate pool.

---

### Why this reduces “patchiness”

- Before: “Generate a worklist” is open-ended; omissions are silent.
- After: every required slot must appear; omissions become deterministic failures with targeted repair surface area.

---

### Notes about comparables (avoid clustering if you want)

V1 doesn’t require clustering comparables.
- You can keep comparable PIR as property-level.
- Use it to set strategy targets and global finish levels.

Only cluster comparables if you later need room-by-room deltas with high precision.

