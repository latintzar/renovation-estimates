Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Implementation Plan: Bracket Analysis Modal

> **Goal**: When user clicks "Analyse" on a bracket above asking price, show a full-screen modal with scope, pricing, timeline, images, and export functionality.

---

## Table of Contents

1. [Current State](#current-state)
2. [Target State](#target-state)
3. [Implementation Phases](#implementation-phases)
4. [Phase 1: Backend Pipeline](#phase-1-backend-pipeline)
5. [Phase 2: Frontend Modal](#phase-2-frontend-modal)
6. [Phase 3: Export & Share](#phase-3-export--share)
7. [Phase 4: Testing & Polish](#phase-4-testing--polish)

---

## Current State

### What Works ✅
- Casafari API client (`backend/clients/casafari_client.py`)
- Database tables (`listing_market_stats`, `listing_comparables`, `listing_bracket_analyses`)
- API endpoints in `backend/routes/renovation.py`:
  - `GET /{id}/comparables/brackets` - Fetch market data
  - `POST /{id}/comparables/brackets` - Run Casafari search
  - `POST /{id}/comparables/analyse` - Run bracket analysis (PLACEHOLDER)
- `ComparablesCard.tsx` with state machine and "Analyse All" button

### What's Placeholder ⚠️
- `/analyse` endpoint returns **heuristic** pricing, not real KGEstimator
- No **scope of work** from verify_rules/assess_uniclass
- No **Gemini timeline** synthesis
- No **V1-V4 image** pipeline wired up
- No **modal UI** for bracket details
- No **export PDF** or **share link**

---

## Target State

```
User clicks "Analyse All"
         ↓
┌─────────────────────────────────────────────────────────┐
│ POST /api/renovation/{id}/comparables/analyse           │
│                                                         │
│ For each bracket above asking:                          │
│   1. Get detected_conditions from DB (verify_rules)     │
│   2. Get visible_elements from DB (assess_uniclass)     │
│   3. Build scope of work items                          │
│   4. Call KGEstimator → BCCA line items + pricing       │
│   5. Call Gemini → timeline phases                      │
│   6. Call V1-V4 → before/after images                   │
│   7. Save to listing_bracket_analyses                   │
└─────────────────────────────────────────────────────────┘
         ↓
Frontend shows RenovationOptionCard (collapsed)
         ↓
User taps card → Full-screen modal opens
         ↓
┌─────────────────────────────────────────────────────────┐
│ Modal shows:                                            │
│   • THE MATH (asking + reno = investment vs target)     │
│   • BEFORE/AFTER slider                                 │
│   • SCOPE with room thumbnails                          │
│   • TIMELINE Gantt                                      │
│   • COMPARABLES carousel                                │
│   • Sticky share icon → Share Link / Export PDF         │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

| Phase | Description | Est. Time |
|-------|-------------|-----------|
| 1 | Backend: Wire up real pipeline | 4-6 hours |
| 2 | Frontend: Build modal UI | 3-4 hours |
| 3 | Export & Share functionality | 2-3 hours |
| 4 | Testing & polish | 2 hours |

---

## Phase 1: Backend Pipeline

### 1.1 Get Detected Conditions from DB

The listing should already have `verify_rules` and `assess_uniclass` results from the photo analysis pipeline.

**Files involved:**
- `backend/routes/renovation.py` - `/analyse` endpoint
- `backend/db.py` - Database queries

**Tasks:**
- [ ] Query `room_rule_verifications` for listing
- [ ] Query `room_uniclass_assessments` for listing
- [ ] Filter to `status = 'confirmed'` (issues detected)
- [ ] Build scope items from detected conditions

```python
# In renovation.py analyse_bracket()

# Get detected issues from verify_rules
rule_verifications = await db.supabase.table('room_rule_verifications') \
    .select('*') \
    .eq('listing_id', listing_id) \
    .eq('status', 'confirmed') \
    .execute()

# Get element conditions from assess_uniclass
uniclass_assessments = await db.supabase.table('room_uniclass_assessments') \
    .select('*') \
    .eq('listing_id', listing_id) \
    .execute()
```

### 1.2 Build Scope of Work

Map detected conditions to renovation tasks with BCCA keywords.

**Files involved:**
- `backend/pipeline/rules_engine_v2.json` - Has `bcca_keyword` per rule
- Create: `backend/pipeline/scope_builder.py`

**Tasks:**
- [ ] Create `scope_builder.py` module
- [ ] Load rules_engine_v2.json
- [ ] For each confirmed rule violation → add remedial action to scope
- [ ] For each poor-condition uniclass element → add upgrade to scope
- [ ] Return list of scope items with `bcca_keyword`, `category`, `room`

```python
# backend/pipeline/scope_builder.py

def build_scope_from_analysis(
    rule_verifications: List[dict],
    uniclass_assessments: List[dict],
    rules_engine: dict
) -> List[ScopeItem]:
    """
    Convert detected conditions into scope of work items.
    
    Returns list of:
    {
        "id": "ELEC_REBT_001",
        "description": "Full electrical rewiring",
        "bcca_keyword": "instalación eléctrica vivienda completa",
        "category": "ELECTRICAL",
        "room": "general",
        "priority": "critical"
    }
    """
```

### 1.3 Integrate KGEstimator

Replace heuristic pricing with real KGEstimator.

**Files involved:**
- `experiments/renovation_costing/kg_estimator.py` - The estimator
- `backend/routes/renovation.py` - Integration point

**Tasks:**
- [ ] Copy/move KGEstimator to `backend/pricing/kg_estimator.py`
- [ ] Create wrapper function `price_scope_items(items, sqm)`
- [ ] Return structured BoQ with line items, PEM, overhead, IVA
- [ ] Handle missing BCCA matches gracefully

```python
# In renovation.py analyse_bracket()

from backend.pricing.kg_estimator import price_scope_items

# Price the scope
boq = await price_scope_items(
    scope_items=scope_items,
    floor_area_m2=listing.get('m2_built', 100),
    rooms=listing.get('rooms', [])
)

# boq = {
#     "line_items": [...],
#     "categories": {"ELECTRICAL": 12163, "PLUMBING": 9730, ...},
#     "pem_subtotal": 46222,
#     "overhead_13pct": 6009,
#     "profit_6pct": 2773,
#     "subtotal": 55004,
#     "iva_21pct": 11551,
#     "total_with_iva": 66555
# }
```

### 1.4 Gemini Timeline Estimation

Call Gemini with BoQ to estimate realistic timeline.

**Files involved:**
- `backend/pipeline/gemini_client.py` - Gemini caller
- Create: `backend/pipeline/steps/estimate_timeline.py`

**Tasks:**
- [ ] Create `estimate_timeline.py` module
- [ ] Build prompt with BoQ summary and property context
- [ ] Define response schema for timeline phases
- [ ] Call Gemini Flash for speed
- [ ] Return phases with week ranges and milestones

```python
# backend/pipeline/steps/estimate_timeline.py

TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "total_weeks": {
            "type": "object",
            "properties": {
                "min": {"type": "integer"},
                "max": {"type": "integer"}
            }
        },
        "phases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "week_start": {"type": "integer"},
                    "week_end": {"type": "integer"},
                    "tasks": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "week": {"type": "integer"},
                    "description": {"type": "string"}
                }
            }
        }
    }
}

async def estimate_timeline(boq: dict, property_info: dict) -> dict:
    """Use Gemini to estimate renovation timeline from BoQ."""
    ...
```

### 1.5 V1-V4 Image Pipeline

Wire up the existing visuals pipeline.

**Files involved:**
- `backend/pipeline/steps/visuals.py` - V1-V4 functions exist but not wired
- `backend/routes/renovation.py` - Call them

**Tasks:**
- [ ] Call `run_v2_select_before()` - Select best photo
- [ ] Call `run_v1_defurnish()` - Remove furniture (optional)
- [ ] Call `run_v3_prompts()` - Generate render prompts per bracket
- [ ] Call `run_v4_render()` - Generate after images
- [ ] Store URLs in `listing_bracket_analyses`

```python
# In renovation.py analyse_bracket()

from backend.pipeline.steps.visuals import (
    run_v2_select_before,
    run_v1_defurnish,
    run_v3_prompts,
    run_v4_render
)

# Select best before photo
before_selection = await run_v2_select_before(orchestrator, listing_id)
before_url = before_selection.get('photo_url')

# Generate prompts for this bracket
prompts = await run_v3_prompts(orchestrator, listing_id, bracket=request.bracket)

# Render after image
after_result = await run_v4_render(orchestrator, listing_id, bracket=request.bracket)
after_url = after_result.get('after_url')
```

### 1.6 Save Complete Analysis to DB

Store the full analysis result.

**Tasks:**
- [ ] Update `listing_bracket_analyses` table schema if needed
- [ ] Save: scope_of_work, boq, timeline, before_url, after_url, comparables
- [ ] Return complete analysis in API response

```sql
-- Ensure listing_bracket_analyses has all needed columns
ALTER TABLE listing_bracket_analyses ADD COLUMN IF NOT EXISTS
    scope_of_work JSONB,
    boq_line_items JSONB,
    timeline_phases JSONB,
    before_photo_url TEXT,
    after_photo_url TEXT;
```

---

## Phase 2: Frontend Modal

### 2.1 Create BracketAnalysisModal Component

**Files to create:**
- `frontend/src/components/renovation/BracketAnalysisModal.tsx`

**Tasks:**
- [ ] Create full-screen modal component
- [ ] Sticky header with back button and share icon
- [ ] Scrollable content area
- [ ] Pass bracket analysis data as props

```tsx
// components/renovation/BracketAnalysisModal.tsx

interface BracketAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: BracketAnalysis;
  listingId: number;
  address?: string;
}

export const BracketAnalysisModal: React.FC<BracketAnalysisModalProps> = ({
  isOpen,
  onClose,
  analysis,
  listingId,
  address
}) => {
  // ...
};
```

### 2.2 THE MATH Section

Simple, mobile-first display of key numbers.

**Tasks:**
- [ ] Create `TheMathSection.tsx` component
- [ ] Stacked layout: asking, +reno, =investment, target, =gain
- [ ] Timeline at bottom
- [ ] Color code gain (green if positive, red if negative)

```tsx
// components/renovation/TheMathSection.tsx

export const TheMathSection: React.FC<{
  askingPrice: number;
  renovationCost: number;
  targetValue: number;
  timelineWeeks: string;
}> = ({ askingPrice, renovationCost, targetValue, timelineWeeks }) => {
  const investment = askingPrice + renovationCost;
  const gain = targetValue - investment;
  
  return (
    <div className="bg-slate-50 rounded-xl p-5">
      <h3 className="text-lg font-semibold mb-4">💰 THE MATH</h3>
      {/* ... */}
    </div>
  );
};
```

### 2.3 Before/After Slider

Reuse existing `BeforeAfterSlider` from buyer-intelligence.

**Tasks:**
- [ ] Import `BeforeAfterSlider` from buyer-intelligence
- [ ] Pass before_url and after_url
- [ ] Ensure it works in modal context

### 2.4 Scope Section with Room Thumbnails

**Tasks:**
- [ ] Create `ScopeSection.tsx` component
- [ ] Group items by category (ELECTRICAL, PLUMBING, etc.)
- [ ] Show room thumbnail on left, items on right
- [ ] Display category totals
- [ ] Show PEM breakdown at bottom

```tsx
// components/renovation/ScopeSection.tsx

interface ScopeSectionProps {
  scopeOfWork: {
    categories: Array<{
      name: string;
      total: number;
      items: string[];
      roomPhoto?: string;
    }>;
    pem: number;
    overhead: number;
    profit: number;
    iva: number;
    total: number;
  };
}
```

### 2.5 Timeline Gantt

**Tasks:**
- [ ] Create `TimelineSection.tsx` component
- [ ] Simple horizontal bars for each phase
- [ ] Week labels
- [ ] Milestone checkmarks

### 2.6 Comparables Carousel

**Tasks:**
- [ ] Create `ComparablesCarousel.tsx` component
- [ ] Horizontal scrolling with snap
- [ ] Mini cards with photo, price, area
- [ ] Link to original Casafari listing

### 2.7 Wire Modal to ComparablesCard

**Tasks:**
- [ ] Add modal state to `ComparablesCard.tsx`
- [ ] Open modal when RenovationOptionCard is tapped
- [ ] Pass analysis data to modal

---

## Phase 3: Export & Share

### 3.1 Share Icon and Popup

**Tasks:**
- [ ] Add share icon to modal sticky header
- [ ] Create `SharePopup.tsx` component
- [ ] Two options: Share Link, Export PDF
- [ ] Cancel button

```tsx
// components/renovation/SharePopup.tsx

export const SharePopup: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onShareLink: () => void;
  onExportPDF: () => void;
}> = ({ isOpen, onClose, onShareLink, onExportPDF }) => {
  // ...
};
```

### 3.2 Native Share (Web Share API)

**Tasks:**
- [ ] Implement `handleShareLink()` using `navigator.share()`
- [ ] Build deeplink URL: `/listing/{id}?bracket={bracket}&view={view}`
- [ ] Fallback to clipboard copy on desktop
- [ ] Toast confirmation

```tsx
const handleShareLink = async () => {
  const deeplink = `${window.location.origin}/listing/${listingId}?bracket=${bracket}&view=${view}`;
  
  if (navigator.share) {
    await navigator.share({
      title: `${bracketLabel} Renovation - ${address}`,
      text: `Renovation analysis: €${renovationCost.toLocaleString()} investment, €${gain.toLocaleString()} potential gain`,
      url: deeplink,
    });
  } else {
    await navigator.clipboard.writeText(deeplink);
    toast.success('Link copied to clipboard');
  }
};
```

### 3.3 Deeplink Handling

**Tasks:**
- [ ] Update listing page to read `?bracket=` and `?view=` params
- [ ] Auto-open modal if bracket param present
- [ ] Fetch analysis data if not in state

### 3.4 PDF Export Endpoint

**Files involved:**
- `backend/routes/renovation.py` - Add `/handover` endpoint
- Create: `backend/export/pdf_generator.py`

**Tasks:**
- [ ] Create PDF generator using WeasyPrint or similar
- [ ] Build HTML template with full CTE references
- [ ] Include scope, BoQ, timeline, photos
- [ ] Add architect checklist
- [ ] Return PDF bytes

```python
# backend/routes/renovation.py

@router.get("/{listing_id}/handover")
async def export_handover(
    listing_id: int, 
    format: str = "pdf",
    bracket: str = "premium"
):
    """
    Export detailed architect handover document.
    
    Formats: pdf, json
    """
    ...
```

### 3.5 Frontend PDF Download

**Tasks:**
- [ ] Call `/api/renovation/{id}/handover?format=pdf&bracket={bracket}`
- [ ] Trigger browser download
- [ ] Show loading state during generation

---

## Phase 4: Testing & Polish

### 4.1 Backend Testing

**Tasks:**
- [ ] Test `/analyse` endpoint with listing ID 6 (Rubí)
- [ ] Verify scope items generated from detected conditions
- [ ] Verify KGEstimator returns reasonable prices
- [ ] Verify Gemini timeline makes sense
- [ ] Verify images generated (or placeholder if V4 not ready)

### 4.2 Frontend Testing

**Tasks:**
- [ ] Test modal opens correctly
- [ ] Test all sections render
- [ ] Test share link works on mobile
- [ ] Test PDF download works
- [ ] Test deeplink opens correct modal

### 4.3 Edge Cases

**Tasks:**
- [ ] Handle missing photos gracefully
- [ ] Handle KGEstimator errors
- [ ] Handle Gemini timeout
- [ ] Handle no detected conditions (show message)

### 4.4 Polish

**Tasks:**
- [ ] Loading states for each section
- [ ] Smooth modal animations
- [ ] Proper error messages
- [ ] Responsive design (tablet)

---

## File Checklist

### Backend Files to Create/Modify

| File | Action | Status |
|------|--------|--------|
| `backend/pipeline/scope_builder.py` | CREATE | [ ] |
| `backend/pricing/kg_estimator.py` | MOVE from experiments | [ ] |
| `backend/pipeline/steps/estimate_timeline.py` | CREATE | [ ] |
| `backend/pipeline/steps/visuals.py` | MODIFY (wire up) | [ ] |
| `backend/routes/renovation.py` | MODIFY (full pipeline) | [ ] |
| `backend/export/pdf_generator.py` | CREATE | [ ] |

### Frontend Files to Create/Modify

| File | Action | Status |
|------|--------|--------|
| `components/renovation/BracketAnalysisModal.tsx` | CREATE | [ ] |
| `components/renovation/TheMathSection.tsx` | CREATE | [ ] |
| `components/renovation/ScopeSection.tsx` | CREATE | [ ] |
| `components/renovation/TimelineSection.tsx` | CREATE | [ ] |
| `components/renovation/ComparablesCarousel.tsx` | CREATE | [ ] |
| `components/renovation/SharePopup.tsx` | CREATE | [ ] |
| `components/renovation/ComparablesCard.tsx` | MODIFY (add modal) | [ ] |
| `components/renovation/index.ts` | MODIFY (exports) | [ ] |
| `app/listing/[id]/page.tsx` | MODIFY (deeplink params) | [ ] |

### Database

| Table | Action | Status |
|-------|--------|--------|
| `listing_bracket_analyses` | VERIFY columns | [ ] |

---

## API Response Schema

When `/analyse` completes, it should return:

```json
{
  "success": true,
  "data": {
    "bracket": "premium",
    "view": "filtered",
    
    "the_math": {
      "asking_price": 530000,
      "renovation_cost": 55004,
      "total_investment": 585004,
      "target_value": 590000,
      "potential_gain": 4996
    },
    
    "scope_of_work": {
      "total_items": 47,
      "categories": [
        {
          "name": "ELECTRICAL",
          "icon": "⚡",
          "total": 12163,
          "room_photo": "https://...",
          "items": [
            "Full rewiring to REBT 2002",
            "New consumer unit with RCD",
            "Earthing system upgrade",
            "24 new outlets"
          ]
        }
      ],
      "pricing": {
        "pem": 46222,
        "overhead_13pct": 6009,
        "profit_6pct": 2773,
        "subtotal": 55004,
        "iva_21pct": 11551,
        "total_with_iva": 66555
      }
    },
    
    "timeline": {
      "total_weeks": { "min": 8, "max": 10 },
      "phases": [
        { "name": "Demo + Electrical", "week_start": 1, "week_end": 2, "tasks": [...] },
        { "name": "Plumbing + Windows", "week_start": 3, "week_end": 4, "tasks": [...] }
      ],
      "milestones": [
        { "week": 2, "description": "MEP rough-in complete" },
        { "week": 6, "description": "Wet rooms finished" },
        { "week": 10, "description": "Ready for inspection" }
      ]
    },
    
    "images": {
      "before_url": "https://...",
      "after_url": "https://..."
    },
    
    "comparables": [
      {
        "property_id": "123",
        "sale_price": 600000,
        "total_area": 145,
        "plot_area": 380,
        "photo_url": "https://...",
        "property_url": "https://casafari.com/..."
      }
    ]
  }
}
```

---

## Progress Tracking

### Overall Progress

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Backend | [ ] Not Started | |
| Phase 2: Frontend | [ ] Not Started | |
| Phase 3: Export | [ ] Not Started | |
| Phase 4: Testing | [ ] Not Started | |

### Last Updated
- Date: 2026-01-08
- By: Cursor Agent

---

## Dependencies

- **KGEstimator**: Needs `hybrid_renovation_graph.json` and `construction.db`
- **Gemini**: Needs `GOOGLE_APPLICATION_CREDENTIALS`
- **Image Gen**: Needs Gemini vision API access
- **PDF**: Needs WeasyPrint or similar library

---

## Notes

- Keep the in-app view simple (cost, value, time)
- PDF export has all the detailed CTE references
- Share link should open directly to the bracket modal
- Room photos in scope section provide visual context
- Timeline Gantt is a nice differentiator

