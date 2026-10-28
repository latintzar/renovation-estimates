Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Agent Portal — Leo Property Onboarding

> **Status:** Design & Mock Phase
> **Goal:** A desktop web app where agents upload all property information through a conversational Leo chat interface.
> **Tech:** Next.js 14 (App Router) within existing `lean-mvp/frontend`, Supabase, Gemini 3.1 Pro, RasterScan HF API

---

## 0. Current Design Probe Scenario (Feb 2026)

The active demo baseline is now a high-end Alicante coast villa onboarding simulation:

- **Primary scenario:** Moraira / Altea luxury villa
- **Price range:** EUR 1M-EUR 3M (current flagship mock: EUR 1.845M)
- **Data fidelity:** Full room clusters, floor plan linking, inventory and document extraction, trusted contacts
- **Image set:** `frontend/public/agent-mock/` generated with Gemini 2.5 Flash Image (`pro-image` alias)
- **Chat UX baseline:** Expo Leo chat style ported to shared web components

### Generated Image Pack

- 36 generated assets including:
  - kitchen (5)
  - living (4)
  - master bedroom (4)
  - bedroom 2 (3)
  - bedroom 3 (3)
  - master bathroom (4)
  - guest bathroom (3)
  - terrace/pool (4)
  - exterior (3)
  - hallway (2)
  - floor plan visual (1)

### Production Hooking Reference

Use `docs/PRODUCTION_HOOKS.md` as the canonical checklist for:

- what to copy from app.leo.casa flows,
- what to build as new agent-portal services,
- and per-tool endpoint/model mapping.

---

## 1. Why Chat-Based Onboarding

Traditional property onboarding uses forms — 50+ fields across multiple pages. Agents abandon them, leave fields blank, or give low-quality data. A chat interface solves this because:

- **Agents live in WhatsApp/chat.** This is their native environment.
- **Leo analyzes in real-time.** When Leo says "I see a Bosch oven in your kitchen photos — do you have the receipt?" — that's a collaborator, not a form.
- **Conversational flow is forgiving.** No field is "required" — Leo just nudges. Agent can say "I don't have that" and move on.
- **Persistent state.** Close the browser, come back tomorrow. Leo picks up where you left off.
- **Voice notes for rich data.** Describing a contractor in a voice note gives 10x richer data than a text field.

---

## 2. Data We Need to Collect

### 2.1 Basic Property Info
| Field | Source | Required |
|-------|--------|----------|
| Address (full, geocodable) | Listing / manual | Yes |
| Property type (apartment, house, villa, etc.) | Listing / manual | Yes |
| m² built, m² useful, m² plot | Listing / manual / floor plan | Yes |
| Bedrooms, bathrooms | Listing / manual | Yes |
| Floor level (if apartment) | Listing / manual | If applicable |
| Year built / construction era | Listing / manual | Yes |
| Condition assessment | Listing / Leo inference | Yes |
| Listed/sale price | Listing / manual | Yes |
| Features (elevator, terrace, pool, etc.) | Listing / manual | Recommended |
| Cadastral reference | Nota Simple / manual | Recommended |

### 2.2 Listing URL (Optional but Preferred)
- If still live → scrape basic info + photos automatically
- If taken down → agent provides everything manually
- Saves agent 15-20 minutes if available

### 2.3 Photos (CRITICAL)
- **4-5 photos per room** from different angles
- **Every space:** bedrooms, bathrooms, kitchen, living, hallway, storage, utility, terrace, exterior
- From listing (auto-clustered) OR uploaded room-by-room
- Agent verifies/corrects clustering

### 2.4 Floor Plan
- From listing photos OR uploaded by agent
- Processed through **RasterScan** for room segmentation
- Interactive linking: each segmented room ↔ photo cluster
- Extracts room dimensions (m²)

### 2.5 Key Property Documents
| Document | What It Tells Us |
|----------|-----------------|
| Energy Performance Certificate (Certificado Energético) | Energy rating, insulation quality |
| Nota Simple (Property Register Extract) | Legal ownership, charges, boundaries |
| IBI Receipts (Property Tax) | Tax burden, cadastral reference |
| Community of Owners minutes/statutes | Monthly fees, upcoming assessments (derramas) |
| Cédula de Habitabilidad | Habitation compliance |
| Building insurance | Coverage status |
| Last inspection reports | Known structural/system issues |
| Utility contracts | Contracted kW, gas type, water |

### 2.6 Room-Specific Documents & Equipment
- Purchase receipts for appliances/fixtures
- Renovation invoices/quotes (past work)
- Warranty documents
- Equipment manuals
- Inventory lists from construction

### 2.7 Photo-Based Inventory
After photo clustering, Leo analyzes each room's photos to build an equipment/fixture inventory:
- Appliances (brand, model if visible)
- Fixtures (taps, sinks, toilets)
- Finishes (flooring type, countertop material)
- Built-ins (cabinets, wardrobes)

This inventory is then cross-referenced with uploaded documents.

### 2.8 Trusted Contacts
| Field | Notes |
|-------|-------|
| Name | Full name |
| Phone | For Leo to coordinate |
| Trade/Specialty | Plumbing, electrical, general, etc. |
| Relationship duration | "7 years" |
| Strengths | What they're great at |
| Weaknesses | Where they struggle |
| Personality | What to expect working with them |
| Working style | Reliable? Fast? Meticulous? |
| Voice note (encouraged) | Rich, natural description |

### 2.9 Context & History
- **Previous renovations:** What was done, when, by whom
- **Known issues:** Humidity, noise, cracks, electrical quirks
- **Access logistics:** Key handoff, alarm codes, parking, portero
- **Seller context:** Why selling, price flexibility, timeline
- **Neighborhood notes:** Agent's local expertise
- **Building construction type:** Pre-1980, concrete, brick, load-bearing walls

---

## 3. Chat Flow — Simulated Transcript

Below is the **ideal conversation** showing every phase, interaction, and tool trail.

### Phase 1: Welcome & Listing Check

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Hey! I'm Leo, your property intelligence assistant.     │
│                                                         │
│ I'm going to help you set up a new property so we can   │
│ give you a complete renovation analysis with accurate    │
│ pricing. Think of this as a conversation — just share    │
│ what you have, and I'll guide you through what we need.  │
│                                                         │
│ First question — do you have a listing URL for this      │
│ property? If it's still live online, I can grab most     │
│ of the basic info and photos automatically, saving you   │
│ a lot of time.                                          │
│                                                         │
│ [Paste listing URL]  [No listing, I'll add manually]    │
└─────────────────────────────────────────────────────────┘
```

**Agent sends:** `https://www.idealista.com/inmueble/12345678/`

```
TOOL TRAIL:
├─ 🔗 Validating URL... ✓ idealista.com detected
├─ 🌐 Scraping listing data from Idealista...
├─ 📊 Parsing property details (25 fields)...
├─ 📸 Found 24 photos + 1 floor plan
└─ ✓ Listing scraped successfully
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Got it! Here's what I found:                            │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📍 Calle Mayor 15, 3º Izq, Madrid                  │ │
│ │ 🏠 Apartment · 3 bed · 1 bath · 75 m²              │ │
│ │ 📐 Built: 75 m² | Useful: 68 m²                    │ │
│ │ 🏗️ Year: 1965 | Floor: 3rd (no elevator)           │ │
│ │ 💰 Listed at €185,000                               │ │
│ │                                                     │ │
│ │ Features: Exterior, balcony, gas heating            │ │
│ │ Condition: Needs renovation                         │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ I also grabbed 24 photos and detected a floor plan.     │
│ Does everything look right? Anything to correct?        │
│                                                         │
│ [✓ Looks good]  [I need to correct something]           │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "The useful area is actually 70 m² and it has 2 bathrooms, not 1"

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Updated! 70 m² useful area and 2 bathrooms. Thanks for  │
│ catching that — this is exactly why your input matters.  │
│                                                         │
│ A few more details the listing didn't have:             │
│                                                         │
│ • Do you know the year it was built? The listing said   │
│   1965 but that might be approximate.                   │
│ • Do you have the cadastral reference?                  │
│ • Has anything been renovated recently?                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "Year is correct. Cadastral ref is 1234567QR. The kitchen was fully renovated about 3 years ago."

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Kitchen renovated 3 years ago — great, that's important │
│ context for the analysis. I'll flag it so we don't      │
│ recommend redoing work that's already done.             │
│                                                         │
│ Now let's organize those 24 photos by room...           │
└─────────────────────────────────────────────────────────┘
```

### Phase 2: Photo Clustering & Verification

```
TOOL TRAIL:
├─ 📸 Loading 24 listing photos...
├─ 🧠 Analyzing photos with Gemini 3.1 Pro...
│  ├─ Detecting visual continuity (floors, walls, ceilings)
│  ├─ Identifying room transitions
│  └─ Classifying AI-generated vs real photos
├─ 🏷️ Clustering by room (found 7 rooms + 2 excluded)
└─ ✓ Photo clustering complete (18.3s)
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Here's how I've grouped the photos. Take a look and     │
│ let me know if anything's wrong — you can drag photos   │
│ between rooms to fix any mistakes.                      │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │  PHOTO CLUSTERS                          [Edit Mode]│ │
│ │                                                     │ │
│ │  🟢 Kitchen ·········· 4 photos ✓                   │ │
│ │  ┌───┐ ┌───┐ ┌───┐ ┌───┐                          │ │
│ │  │   │ │   │ │   │ │   │                           │ │
│ │  └───┘ └───┘ └───┘ └───┘                          │ │
│ │                                                     │ │
│ │  🟢 Living Room ······ 5 photos ✓                   │ │
│ │  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐                   │ │
│ │  │   │ │   │ │   │ │   │ │   │                    │ │
│ │  └───┘ └───┘ └───┘ └───┘ └───┘                   │ │
│ │                                                     │ │
│ │  🟡 Bedroom 1 ········ 3 photos (need 1-2 more)    │ │
│ │  ┌───┐ ┌───┐ ┌───┐                                │ │
│ │  │   │ │   │ │   │                                 │ │
│ │  └───┘ └───┘ └───┘                                │ │
│ │                                                     │ │
│ │  🟡 Bedroom 2 ········ 3 photos (need 1-2 more)    │ │
│ │  🟢 Bathroom 1 ······· 3 photos                     │ │
│ │  🔴 Bathroom 2 ······· 2 photos (need 2-3 more)    │ │
│ │  🔴 Hallway ·········· 2 photos (need 2-3 more)    │ │
│ │                                                     │ │
│ │  ⚪ Excluded: 1 floor plan, 1 building exterior     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Rooms with enough photos are marked 🟢. The ones in     │
│ 🟡 or 🔴 could use more angles — 4-5 photos per room   │
│ from different angles really helps our analysis.        │
│                                                         │
│ Do you have extra photos of the spaces marked in        │
│ yellow/red? Even phone photos work great.               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent drags and drops 8 photos into the chat.**

The drop zone overlay appears:

```
┌─────────────────────────────────────────────────────────┐
│ ╔═══════════════════════════════════════════════════════╗│
│ ║                                                       ║│
│ ║              📎 Drop files here                       ║│
│ ║                                                       ║│
│ ║          8 photos ready to upload                     ║│
│ ║                                                       ║│
│ ║     Images · Documents · Folders · Cloud links        ║│
│ ║                                                       ║│
│ ╚═══════════════════════════════════════════════════════╝│
└─────────────────────────────────────────────────────────┘
```

```
TOOL TRAIL:
├─ 📥 Receiving 8 photos (12.4 MB total)...
├─ 🧠 Analyzing new photos with Gemini 3.1 Pro...
│  ├─ Comparing to existing room clusters
│  ├─ Matching visual continuity
│  └─ 7 matched, 1 needs clarification
└─ ✓ Photos integrated
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Nice! I matched most of them:                           │
│                                                         │
│ +2 photos → Bathroom 2 (now 4 total ✓)                 │
│ +2 photos → Hallway (now 4 total ✓)                    │
│ +2 photos → Bedroom 1 (now 5 total ✓)                  │
│ +1 photo  → Bedroom 2 (now 4 total ✓)                  │
│                                                         │
│ This one I'm not sure about — which room is this?       │
│                                                         │
│ ┌───────────────────┐                                   │
│ │                   │                                   │
│ │  [unmatched photo] │                                  │
│ │                   │                                   │
│ └───────────────────┘                                   │
│                                                         │
│ [Kitchen] [Living Room] [Bedroom 1] [Bedroom 2]        │
│ [Bathroom 1] [Bathroom 2] [Hallway] [New room...]      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "That's the storage room in the hallway"

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Storage room — added! All rooms now have good coverage: │
│                                                         │
│ ✅ Kitchen ·········· 4 photos                          │
│ ✅ Living Room ······ 5 photos                          │
│ ✅ Bedroom 1 ········ 5 photos                          │
│ ✅ Bedroom 2 ········ 4 photos                          │
│ ✅ Bathroom 1 ······· 3 photos                          │
│ ✅ Bathroom 2 ······· 4 photos                          │
│ ✅ Hallway ·········· 4 photos                          │
│ ✅ Storage ·········· 1 photo                           │
│                                                         │
│ Now let's work with your floor plan!                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase 3: Floor Plan Analysis & Room Linking

```
TOOL TRAIL:
├─ 📐 Sending floor plan to RasterScan API...
├─ 🗺️ Detecting room boundaries (6 rooms found)
├─ 📏 Calculating room areas
├─ 🚪 Detecting doors (5 found)
├─ 🧱 Detecting walls (12 segments)
└─ ✓ Floor plan analysis complete (4.2s)
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ I've analyzed the floor plan and detected these rooms:  │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                INTERACTIVE FLOOR PLAN                │ │
│ │                                                     │ │
│ │  ┌──────────┐ ┌───────────────────────┐            │ │
│ │  │          │ │                       │            │ │
│ │  │  Room E  │ │                       │            │ │
│ │  │  7.0 m²  │ │      Room B          │            │ │
│ │  └──────────┘ │      23.5 m²         │            │ │
│ │  ┌──────┐     │                       │            │ │
│ │  │Room F│     └───────────────────────┘            │ │
│ │  │3.5m² │                                          │ │
│ │  └──────┘                                          │ │
│ │  ┌──────────┐ ┌───────────────────────┐            │ │
│ │  │          │ │                       │            │ │
│ │  │  Room D  │ │                       │            │ │
│ │  │  8.4 m²  │ │      Room A          │            │ │
│ │  │          │ │      23.8 m²         │            │ │
│ │  └──────────┘ │                       │            │ │
│ │  ┌──────────┐ │                       │            │ │
│ │  │  Room C  │ └───────────────────────┘            │ │
│ │  │ 12.5 m²  │                                      │ │
│ │  └──────────┘                                      │ │
│ │                                                     │ │
│ │  ⬜ Click a room to link it to your photos          │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Now I need your help linking rooms to photos.           │
│ Click on any room in the floor plan to get started!     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent clicks on Room A (23.8 m²):**

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ You selected Room A (23.8 m²) — the largest room.      │
│ Which photo group does this room correspond to?         │
│                                                         │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│ │Kitchen │ │Living  │ │Bedroom │ │Bedroom │           │
│ │  (4)   │ │Room(5) │ │ 1 (5)  │ │ 2 (4)  │           │
│ │ [imgs] │ │ [imgs] │ │ [imgs] │ │ [imgs] │           │
│ └────────┘ └────────┘ └────────┘ └────────┘           │
│                                                         │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│ │Bath 1  │ │Bath 2  │ │Hallway │ │Storage │           │
│ │  (3)   │ │  (4)   │ │  (4)   │ │  (1)   │           │
│ │ [imgs] │ │ [imgs] │ │ [imgs] │ │ [imgs] │           │
│ └────────┘ └────────┘ └────────┘ └────────┘           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent selects "Living Room":**

```
TOOL TRAIL:
├─ 🔗 Linking Room A → Living Room cluster
├─ 🧠 Gemini confirms: room matches living room photos ✓
└─ ✓ Living Room → 23.8 m²
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ ✅ Living Room → Room A (23.8 m²)                       │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │            FLOOR PLAN (1 of 7 linked)               │ │
│ │                                                     │ │
│ │  ┌──────────┐ ┌───────────────────────┐            │ │
│ │  │          │ │ ✅ KITCHEN            │            │ │
│ │  │  Room E  │ │      23.5 m²         │            │ │
│ │  │  7.0 m²  │ │                       │            │ │
│ │  └──────────┘ └───────────────────────┘            │ │
│ │  ...                                               │ │
│ │  ┌──────────┐ ┌───────────────────────┐            │ │
│ │  │  Room D  │ │ ✅ LIVING ROOM        │            │ │
│ │  │  8.4 m²  │ │      23.8 m²         │            │ │
│ │  └──────────┘ └───────────────────────┘            │ │
│ │                                                     │ │
│ │  Click the next room to continue...                 │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Great! Click the next room to continue linking.         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**[Agent continues clicking each room and selecting clusters until all 7 are linked]**

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ All rooms linked! Here's the complete map:              │
│                                                         │
│ ✅ Living Room ···· 23.8 m² · 5 photos                  │
│ ✅ Kitchen ········ 23.5 m² · 4 photos                  │
│ ✅ Bedroom 1 ······ 12.5 m² · 5 photos                  │
│ ✅ Bedroom 2 ······  8.4 m² · 4 photos                  │
│ ✅ Bathroom 1 ·····  7.0 m² · 3 photos                  │
│ ✅ Hallway ········  3.5 m² · 4 photos                  │
│ ───────────────────────────                             │
│ Total from plan:    78.7 m²                             │
│ Listed built area:  75.0 m²                             │
│ Difference: 3.7 m² (within normal tolerance)            │
│                                                         │
│ Note: Bathroom 2 and Storage aren't clearly defined     │
│ in the floor plan. I'll estimate their sizes from the   │
│ photos and the remaining area.                          │
│                                                         │
│ Now let's analyze what's actually in each room...       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase 4: Photo Inventory Analysis

```
TOOL TRAIL:
├─ 🔍 Analyzing Kitchen photos (4 images)...
│  ├─ Detected: Bosch oven, Siemens dishwasher, induction cooktop
│  ├─ Finishes: White quartz countertop, glossy cabinets
│  └─ Flooring: Ceramic tile (light grey)
├─ 🔍 Analyzing Living Room photos (5 images)...
│  ├─ Detected: Parquet flooring (original), plaster walls
│  ├─ Condition: Wear on flooring, dated finishes
│  └─ Windows: Wooden frames (likely original 1965)
├─ 🔍 Analyzing Bedroom 1 photos (5 images)...
├─ 🔍 Analyzing Bedroom 2 photos (4 images)...
├─ 🔍 Analyzing Bathroom 1 photos (3 images)...
├─ 🔍 Analyzing Bathroom 2 photos (4 images)...
├─ 🔍 Analyzing Hallway photos (4 images)...
├─ 📋 Building property-wide equipment inventory
└─ ✓ 23 items inventoried across 8 rooms (42.1s)
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ I've done a detailed scan of every room's photos.       │
│ Here's what I found:                                    │
│                                                         │
│ 🍳 KITCHEN (renovated ~3 years ago)                     │
│ ├─ Bosch built-in oven                                  │
│ ├─ Siemens dishwasher                                   │
│ ├─ Induction cooktop (brand unclear)                    │
│ ├─ Integrated extractor hood                            │
│ ├─ White quartz countertop                              │
│ ├─ Glossy white cabinets (upper + lower)                │
│ └─ Ceramic floor tiles (light grey, good condition)     │
│                                                         │
│ 🛋️ LIVING ROOM (original condition)                     │
│ ├─ Original parquet flooring (worn)                     │
│ ├─ Wooden window frames (likely 1965)                   │
│ ├─ Plaster walls (minor cracking)                       │
│ └─ Cast iron radiator                                   │
│                                                         │
│ [View all 8 rooms ▼]                                    │
│                                                         │
│ Quick questions about the kitchen:                      │
│ • What brand is the cooktop?                            │
│ • And the extractor hood?                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "Cooktop is Balay, extractor is Teka"

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Updated! Now, some things I noticed that you should     │
│ know I'm flagging for the analysis:                     │
│                                                         │
│ ⚠️ Living room windows appear to be original 1965       │
│    wooden frames — likely no thermal break              │
│ ⚠️ Bathroom 1 has what looks like dated piping visible  │
│    in one photo — might indicate pre-1990 plumbing      │
│ ⚠️ Bedroom flooring appears original — likely needs     │
│    refinishing or replacement                           │
│                                                         │
│ Is there anything else about the condition I should     │
│ know? Any humidity issues, noise, electrical quirks?    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "Yes actually the bathroom 1 has had a humidity issue on the ceiling. And the electricity trips sometimes when you use the oven and the washing machine at the same time"

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Really helpful, thank you. I've noted:                  │
│ • Bathroom 1: Ceiling humidity → likely needs           │
│   waterproofing investigation                           │
│ • Electrical: Trips under load → may need panel         │
│   upgrade or circuit rebalancing (common in 1965        │
│   buildings with modern appliances)                     │
│                                                         │
│ Now let's get your documents...                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase 5: Document Collection

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ For the analysis, these documents are really valuable.  │
│ Upload whatever you have — I'll figure out what's what: │
│                                                         │
│ 📄 Energy Certificate (Certificado Energético)          │
│ 📄 Nota Simple (Property Register Extract)              │
│ 📄 IBI Receipts (Property Tax)                          │
│ 📄 Community minutes or statutes                        │
│ 📄 Cédula de Habitabilidad                              │
│ 📄 Building insurance                                   │
│ 📄 Any inspection reports                               │
│ 📄 Utility contracts (electricity, gas, water)          │
│                                                         │
│ Just drop them all in — even a whole folder works!      │
│                                                         │
│ [📎 Attach files]  [I don't have these]                 │
└─────────────────────────────────────────────────────────┘
```

**Agent drops a folder with 8 PDF files.**

```
DROP ZONE OVERLAY:
╔═══════════════════════════════════════════════════╗
║                                                   ║
║           📁 Drop files here                      ║
║                                                   ║
║        1 folder · 8 files · 4.2 MB                ║
║                                                   ║
║   Images · Documents · Folders · Cloud links      ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
```

```
TOOL TRAIL:
├─ 📥 Receiving 8 files (4.2 MB)...
├─ 📄 Analyzing document 1/8 with Gemini 3.1 Pro...
│  └─ Energy Certificate detected (Rating E, 2023)
├─ 📄 Analyzing document 2/8...
│  └─ Nota Simple detected (clean title, 2019 transfer)
├─ 📄 Analyzing document 3/8...
│  └─ IBI Receipt (€842/year)
├─ 📄 Analyzing document 4/8...
│  └─ Community Minutes 2024 (monthly fee: €85)
├─ 📄 Analyzing document 5/8...
│  └─ Building Insurance (EXPIRED — 2023)
├─ 📄 Analyzing document 6/8...
│  └─ Renovation quote — kitchen (2022)
├─ 📄 Analyzing document 7/8...
│  └─ Renovation quote — kitchen (2022)
├─ 📄 Analyzing document 8/8...
│  └─ ⚠️ Partially illegible scan — attempting OCR...
└─ ✓ 8 documents classified (31.2s)
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Here's what I found in your documents:                  │
│                                                         │
│ ✅ Energy Certificate — Rating E, issued 2023           │
│    → Poor energy efficiency, insulation upgrades likely │
│                                                         │
│ ✅ Nota Simple — Clean title, no charges                │
│    → Last transfer: 2019, no liens or encumbrances     │
│                                                         │
│ ✅ IBI Receipt — €842/year                              │
│    → Cadastral ref matches yours ✓                     │
│                                                         │
│ ✅ Community Minutes (2024) — €85/month                 │
│    → ⚠️ Upcoming façade renovation mentioned            │
│    → Possible derrama (special assessment) coming       │
│                                                         │
│ ⚠️ Building Insurance — EXPIRED (last renewed 2023)    │
│    → The buyer will need to address this               │
│                                                         │
│ 📋 2 Kitchen Renovation Quotes (2022)                   │
│    → Linked to kitchen renovation 3 years ago           │
│    → €12,400 and €14,200 from two contractors          │
│                                                         │
│ ❓ 1 document — partially illegible scan                │
│    → Looks like it might be a habitability certificate  │
│    → Could you check if you have a clearer copy?       │
│                                                         │
│ The community minutes mention a façade renovation       │
│ project — do you know more about that? Is there an     │
│ estimated derrama amount?                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "Yes there's a derrama of about €3,000 per apartment approved for next year. And that illegible doc is indeed the cédula, I'll try to find a better copy"

### Phase 6: Room-Specific Documents

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ €3,000 derrama noted — important for the buyer to know. │
│                                                         │
│ Now, room by room — do you have any purchase receipts,  │
│ warranties, or documentation for the things I spotted   │
│ in the photos?                                          │
│                                                         │
│ Starting with the KITCHEN (since it was renovated):     │
│ • Bosch oven — receipt or warranty?                     │
│ • Siemens dishwasher — receipt or warranty?             │
│ • Balay cooktop — receipt or warranty?                  │
│ • Teka extractor — receipt or warranty?                 │
│ • Countertop/cabinets — installation invoice?           │
│                                                         │
│ Even if you don't have everything, whatever you have    │
│ helps. Or just say "I don't have those" and we move on. │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "I have the Bosch oven receipt and the overall kitchen renovation invoice. Let me upload them"

**[Agent uploads 2 files]**

```
TOOL TRAIL:
├─ 📥 Receiving 2 files...
├─ 📄 Analyzing: Bosch oven purchase receipt
│  └─ Model: HBG675BS1, purchased 2022, €789, MediaMarkt
├─ 📄 Analyzing: Kitchen renovation invoice
│  └─ Total: €13,800, Reformas López S.L., March 2022
│  └─ Breakdown: demolition, plumbing, electrical, tiling,
│     cabinetry, countertop, appliance installation
└─ ✓ Documents linked to Kitchen
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Perfect! I got:                                         │
│ • Bosch HBG675BS1 oven — purchased 2022 at MediaMarkt  │
│   for €789. Warranty likely still active!               │
│ • Kitchen renovation invoice — €13,800 by Reformas     │
│   López S.L., March 2022. Includes demolition,         │
│   plumbing, electrical, tiling, cabinetry.              │
│                                                         │
│ This matches the ~3 year renovation you mentioned ✓     │
│                                                         │
│ Any other rooms with documentation? What about the      │
│ bathrooms — any receipts for fixtures or equipment?     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent:** "No, nothing else for the other rooms"

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ No problem at all. The photos tell me a lot already.    │
│ Let's move on to the last section...                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase 7: Trusted Contacts

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Almost done! This last part is really valuable.         │
│                                                         │
│ Do you have trusted tradespeople or contractors you     │
│ work with? Plumbers, electricians, general builders —   │
│ anyone you'd recommend to a client?                     │
│                                                         │
│ For each person, I'd love to know:                      │
│ • Name and phone number                                 │
│ • What they're great at                                 │
│ • How long you've worked together                       │
│ • What they're like to work with                        │
│                                                         │
│ 💡 Pro tip: Send me a voice note for each person!       │
│ It's much easier than typing and I get a much richer    │
│ picture of who they are.                                │
│                                                         │
│ [🎙️ Record voice note]  [Type instead]                  │
│ [I don't have contacts to share]                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Agent records a 45-second voice note:**
*"So my plumber is Miguel, Miguel Fernández. I've known him for about 7 years now. He's absolutely fantastic with bathrooms, complete renovations. He's a bit slow sometimes to get started but once he's on the job the quality is excellent. He charges fair prices, very honest. He can be a bit gruff at first but he warms up. His number is 612 345 678."*

```
TOOL TRAIL:
├─ 🎙️ Transcribing voice note (45s)...
├─ 🧠 Extracting contact information...
│  ├─ Name: Miguel Fernández
│  ├─ Phone: +34 612 345 678
│  ├─ Trade: Plumbing, bathroom renovations
│  ├─ Duration: 7 years
│  ├─ Strengths: Quality work, fair prices, honest
│  ├─ Weaknesses: Slow to start
│  └─ Personality: Gruff initially, warms up
└─ ✓ Contact profile created
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ Got Miguel! Here's what I captured:                     │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 👤 Miguel Fernández                                 │ │
│ │ 📞 +34 612 345 678                                  │ │
│ │ 🔧 Plumbing · Bathroom renovations                  │ │
│ │ ⏱️ 7 years working together                         │ │
│ │                                                     │ │
│ │ ✅ Strengths: Excellent quality, fair prices, honest │ │
│ │ ⚠️ Note: Can be slow to start initially             │ │
│ │ 💬 Personality: A bit gruff at first, warms up      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Sound right? Anyone else to add?                        │
│                                                         │
│ [🎙️ Add another contact]  [That's everyone]             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**[Agent adds 2 more contacts via voice notes, then says "That's everyone"]**

### Phase 8: Final Review

```
┌─────────────────────────────────────────────────────────┐
│ 🟢 LEO                                                  │
│                                                         │
│ 🎉 We're done! Here's your complete property dossier:   │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ PROPERTY SUMMARY                                    │ │
│ │                                                     │ │
│ │ 📍 Calle Mayor 15, 3º Izq, Madrid                  │ │
│ │ 🏠 Apartment · 3 bed · 2 bath · 75 m² built        │ │
│ │ 🏗️ Year: 1965 · Floor: 3rd · No elevator           │ │
│ │ 💰 €185,000                                         │ │
│ │                                                     │ │
│ │ ✅ 30 photos organized across 8 rooms               │ │
│ │ ✅ Floor plan analyzed — all rooms linked            │ │
│ │ ✅ 8 documents processed and categorized            │ │
│ │ ✅ 23-item equipment inventory                      │ │
│ │ ✅ 3 trusted contacts profiled                      │ │
│ │ ✅ Kitchen renovation history (2022)                │ │
│ │ ✅ Known issues logged (humidity, electrical)       │ │
│ │                                                     │ │
│ │ ⚠️ COULD STILL USE:                                │ │
│ │ • Better scan of Cédula de Habitabilidad           │ │
│ │ • Utility contract details (electricity kW)        │ │
│ │ • Building insurance renewal status                │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ This property is ready for analysis! You can always     │
│ come back to this chat and add more documents or info   │
│ — I'll pick up right where we left off.                 │
│                                                         │
│ [▶ Start Analysis]  [Add more info]  [Back to Dashboard]│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Tool Trail — Complete Tool Registry

Every capability Leo needs, showing what exists vs. what's new:

### Existing Tools (from V5 pipeline)
| Tool | Function | Status |
|------|----------|--------|
| `scrape_listing(url)` | Scrape property listing from URL | ✅ Exists (`backend/scraper/`) |
| `cluster_photos(photos)` | Cluster photos by room using Gemini | ✅ Exists (`cluster_photos_v5.py`) — upgrade to 3.1 Pro |
| `fetch_image_as_base64(url)` | Fetch and encode images | ✅ Exists (`gemini_client.py`) |
| `call_gemini_json(prompt, images)` | Call Gemini with structured output | ✅ Exists (`gemini_client.py`) |

### New Tools Required
| Tool | Function | Implementation |
|------|----------|----------------|
| `analyze_floorplan(image)` | Send floor plan to RasterScan HF API, get room segments | Call public `RasterScan/Automated-Floor-Plan-Digitalization` Gradio API (low volume — public space is fine; fallback: `peteran/Automated-Floor-Plan-Digitalization` or local Docker) |
| `classify_document(file)` | Analyze PDF/image, determine document type and extract key data | Gemini 3.1 Pro with document-specific prompt |
| `build_room_inventory(photos, room_name)` | Analyze room photos, list all equipment/fixtures/finishes | Gemini 3.1 Pro with inventory extraction prompt |
| `transcribe_voice(audio)` | Transcribe voice note to text | Gemini 3.1 Pro (native audio) or Whisper API |
| `extract_contact_info(transcript)` | Parse contact details from transcription | Gemini 3.1 Pro structured extraction |
| `verify_room_click(floorplan, coords, room_photos)` | Confirm which room was clicked on floor plan | Gemini 3.1 Pro with annotated floor plan |
| `match_documents_to_inventory(docs, inventory)` | Cross-reference uploaded docs with photo inventory | Gemini 3.1 Pro reasoning |
| `resume_session(session_id)` | Load chat state and resume onboarding | Supabase query |

---

## 5. Interactive UI Components

### 5.1 File Drop Zone
```
Trigger: dragenter on chat container
Behavior:
- Full-screen overlay with dashed border
- Shows file count, type detection, total size
- Accepts: images, PDFs, docs, videos, audio, folders
- Up to 100 files at once
- Cloud link detection (Google Drive, OneDrive, Dropbox URLs)
- Progress bar per file during upload
- Thumbnail preview for images in chat after upload
```

### 5.2 Photo Cluster Grid
```
Layout: Grouped by room, thumbnails in a row
Features:
- Drag photos between rooms to reclassify
- Click photo to view full-size
- Status indicators: 🟢 (enough), 🟡 (need more), 🔴 (too few)
- "Add photos" button per room
- "New room" button to create a cluster
```

### 5.3 Interactive Floor Plan
```
Layout: Floor plan image with segmented room overlays
Features:
- Rooms highlighted with semi-transparent colored overlays
- Click a room → shows cluster selection panel
- Linked rooms show ✅ with room name label
- Unlinked rooms pulse gently to indicate they need attention
- Room area displayed inside each room
- Zoom/pan controls
```

### 5.4 Contact Profile Card
```
Layout: Card with avatar, name, trade, key details
Features:
- Auto-populated from voice note transcription
- Editable fields
- Playback button for original voice note
- Star rating (agent's assessment)
```

### 5.5 Document Classification Card
```
Layout: Document preview thumbnail + classification
Features:
- Auto-detected document type badge
- Key extracted fields shown
- Status: ✅ classified, ⚠️ needs attention, ❓ unrecognized
- "This is wrong" button to reclassify
```

### 5.6 Voice Note Recorder
```
Behavior: Hold-to-record (like WhatsApp)
Features:
- Waveform visualization during recording
- Slide to cancel
- Duration display
- Playback before sending
```

---

## 6. Data Model — Supabase Schema

### New Table: `agent_onboarding_sessions`
```sql
CREATE TABLE agent_onboarding_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID REFERENCES auth.users(id),
  listing_id BIGINT REFERENCES listings(id),
  
  -- Chat state
  current_phase TEXT NOT NULL DEFAULT 'welcome',
  -- Phases: welcome, listing_check, basic_info, photos, 
  --         floor_plan, inventory_scan, documents, 
  --         room_documents, contacts, review, complete
  chat_messages JSONB NOT NULL DEFAULT '[]',
  
  -- Collected data
  property_data JSONB DEFAULT '{}',     -- basic info, corrections
  photo_clusters JSONB DEFAULT '[]',    -- clustered photos
  floor_plan_data JSONB DEFAULT NULL,   -- RasterScan output
  room_links JSONB DEFAULT '{}',        -- floor_plan_room_id → cluster_id
  room_inventory JSONB DEFAULT '{}',    -- room_id → [items]
  documents JSONB DEFAULT '[]',         -- classified documents
  room_documents JSONB DEFAULT '{}',    -- room_id → [documents]
  trusted_contacts JSONB DEFAULT '[]',  -- contact profiles
  known_issues JSONB DEFAULT '[]',      -- agent-reported issues
  agent_notes JSONB DEFAULT '{}',       -- free-form notes
  
  -- Metadata
  completion_pct SMALLINT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);
```

### New Table: `onboarding_files`
```sql
CREATE TABLE onboarding_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES agent_onboarding_sessions(id),
  
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL,        -- 'image', 'pdf', 'audio', 'document'
  file_size BIGINT,
  mime_type TEXT,
  storage_path TEXT NOT NULL,     -- Supabase Storage path
  
  -- Classification
  document_class TEXT,            -- 'energy_cert', 'nota_simple', etc.
  room_id TEXT,                   -- linked room if applicable
  extracted_data JSONB,           -- AI-extracted key fields
  
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 7. Implementation Plan

### Phase A: Mock Demo (1-2 days)

Build a fully interactive mock that looks and feels real but uses scripted data.

#### A.1 Dashboard Page (`/agent`)
- Agent's property list (2-3 mock properties)
- "Add New Property" button
- Property cards with status (Draft, In Progress, Ready)
- Clean, on-brand design (terracotta + cream + Playfair Display)

#### A.2 Onboarding Chat (`/agent/onboard/[id]`)
- Full chat UI (reuse patterns from Expo app's Leo chat)
- Scripted conversation with realistic timing
- Real interactive components:
  - File drop zone (real drag-and-drop, mock processing)
  - Photo cluster grid (real images, drag-to-reclassify)
  - Interactive floor plan (real click detection, mock RasterScan output)
  - Voice note player (mock recording/playback)
  - Document classification cards
  - Contact profile cards
- Tool trail animations
- Suggested response buttons
- Chat state persistence (localStorage for mock)

#### A.3 Mock Data
- Use the floor plan images from the conversation
- Stock property photos (or generate with Gemini)
- Sample documents (energy cert, nota simple templates)

### Phase B: Production Backend (3-5 days)

Wire up real AI and APIs:

#### B.1 Listing Scraper Integration
- Connect existing `scrape_listing()` to chat flow
- Parse response into property_data format
- Handle scraping errors gracefully in chat

#### B.2 Photo Clustering (Gemini 3.1 Pro)
- Upgrade existing `cluster_photos_v5.py` to use Gemini 3.1 Pro
- Add interactive correction endpoint (move photo between clusters)
- Store corrections in session

#### B.3 RasterScan Floor Plan API
```python
from gradio_client import Client

async def analyze_floorplan(image_path: str) -> dict:
    # Public space — sufficient for our volume; fallback to peteran/ fork or local Docker if needed
    client = Client("RasterScan/Automated-Floor-Plan-Digitalization")
    result = client.predict(image_path, api_name="/predict")
    return {
        "image": result[0],     # Processed/annotated floor plan
        "rooms": result[1],     # Room boundaries and areas
        "doors": result[1],     # Door positions
        "walls": result[1],     # Wall segments
    }
```

#### B.4 Document Classification
- New Gemini 3.1 Pro prompt for document classification
- Extract key fields per document type
- Store in onboarding_files table

#### B.5 Room Inventory Builder
- New Gemini 3.1 Pro prompt for photo inventory
- Run per-room after clustering
- Cross-reference with uploaded documents

#### B.6 Voice Transcription
- Use Gemini 3.1 Pro's native audio understanding
- OR Whisper API for cost efficiency
- Extract structured contact data from transcription

#### B.7 Session Persistence
- Supabase tables as defined above
- Save after each message
- Resume on page load

### Phase C: Polish & Launch (2-3 days)

- Auth integration (Supabase Auth)
- Real file upload to Supabase Storage
- Pipeline trigger from completed onboarding
- Email notifications
- Mobile-responsive tweaks
- Error handling and edge cases

---

## 8. What's Needed to Make Each Feature ACTUALLY Work

| Feature | Mock Behavior | Production Requirement |
|---------|--------------|----------------------|
| Listing scraping | Shows pre-loaded data | Connect `backend/scraper/` with error handling |
| Photo clustering | Pre-grouped mock photos | Call `cluster_photos_v5.py` with Gemini 3.1 Pro |
| Photo reclassification | Drag-and-drop updates local state | PATCH endpoint to update cluster assignment |
| Floor plan segmentation | Pre-segmented overlay | Call public RasterScan HF API (`RasterScan/Automated-Floor-Plan-Digitalization`) |
| Room-click linking | Click detection → mock match | Annotate click coords on floor plan → Gemini confirms room |
| Document classification | Pre-classified mock docs | Gemini 3.1 Pro document analysis prompt |
| Room inventory | Pre-built inventory list | Gemini 3.1 Pro multi-image analysis per room |
| Voice transcription | Mock transcript shown | Gemini 3.1 Pro audio or Whisper API |
| Contact extraction | Pre-parsed contact card | Gemini structured extraction from transcript |
| Doc-inventory matching | Pre-matched | Gemini reasoning over inventory + document content |
| Chat persistence | localStorage | Supabase `agent_onboarding_sessions` table |
| File upload | Mock upload animation | Supabase Storage + `onboarding_files` table |
| Cloud links (GDrive, etc.) | URL detection shown | Google Drive API / OneDrive API to fetch files |
| Auth | Mock agent profile | Supabase Auth with agent role |
| Pipeline trigger | "Analysis started" message | Create pipeline_run + pipeline_jobs in Supabase |

---

## 9. File Structure

```
lean-mvp/frontend/src/app/agent/
├── page.tsx                    # Agent dashboard (property list)
├── layout.tsx                  # Agent portal layout (nav, branding)
├── onboard/
│   └── [id]/
│       └── page.tsx            # Onboarding chat interface
└── property/
    └── [id]/
        └── page.tsx            # Property detail/status view

lean-mvp/frontend/src/components/agent/
├── AgentDashboard.tsx          # Property list + add button
├── PropertyCard.tsx            # Property status card
├── OnboardingChat.tsx          # Main chat container
├── ChatMessage.tsx             # Message bubble (Leo + Agent)
├── ChatInput.tsx               # Text input + attachment + voice
├── FileDropZone.tsx            # Drag-and-drop overlay
├── PhotoClusterGrid.tsx        # Interactive photo grouping
├── InteractiveFloorPlan.tsx    # Clickable floor plan
├── DocumentCard.tsx            # Classified document display
├── ContactCard.tsx             # Trusted contact profile
├── VoiceNotePlayer.tsx         # Audio playback/recording
├── ToolTrail.tsx               # Tool trail animation
├── SuggestedActions.tsx        # Action buttons
└── CompletionSummary.tsx       # Final property summary

lean-mvp/frontend/src/lib/
├── mock-data/
│   ├── onboarding-script.ts    # Scripted conversation flow
│   ├── mock-property.ts        # Sample property data
│   ├── mock-clusters.ts        # Pre-grouped photos
│   ├── mock-floorplan.ts       # Pre-segmented floor plan
│   ├── mock-documents.ts       # Sample classified documents
│   └── mock-contacts.ts        # Sample contact profiles
└── onboarding/
    ├── chat-engine.ts          # Chat state machine
    ├── phase-handlers.ts       # Logic per conversation phase
    └── types.ts                # Onboarding-specific types
```

---

## 10. Branding & Design

### Colors (from existing Leo branding)
- **Primary:** `#da654d` (terracotta)
- **Primary Light:** `#e07c5f`
- **Background:** `#FDFBF7` (warm cream)
- **Surface:** `#FAF7F2`
- **Text:** `#1c1917` (stone-900)
- **Text Secondary:** `#78716c` (stone-500)
- **Success:** `#22c55e`
- **Warning:** `#f59e0b`
- **Leo Green:** `#10b981` (for Leo's messages)

### Typography
- **Headlines:** Playfair Display (serif)
- **Body:** Source Sans 3 (sans-serif)
- **Chat messages:** Source Sans 3, 15px
- **Tool trail:** Source Sans 3, 13px, stone-500

### Chat UI Spec
- **Leo messages:** Left-aligned, light green-tinted bubble
- **Agent messages:** Right-aligned, terracotta-tinted bubble
- **Tool trail:** Indented, smaller text, animated steps
- **Interactive components:** Full-width cards within chat flow
- **Suggested actions:** Pill buttons below Leo's messages
- **File drop zone:** Full-chat overlay, dashed border, brand green
