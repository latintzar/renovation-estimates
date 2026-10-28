Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Property Hood Tour - Architecture Document

**Version:** 2.0 (Tile-Based Implementation)  
**Last Updated:** December 30, 2025  
**Status:** Production Ready

---

## Overview

The Property Hood Tour is an immersive neighborhood exploration feature that curates nearby places for a property and generates cinematic Street View tours with AI-powered narration.

### Key Innovation

**Tile-Based Street View + Cached Playback = Unlimited Free Replays**

Instead of using Google's dynamic Street View (which charges per view), we:
1. Fetch tiles once during curation ($0.64/listing)
2. Cache to Supabase Storage
3. Play back via Marzipano viewer (FREE, unlimited)

---

## Architecture Decision: Tile-Based vs Static API

| Approach | Cost per Location | Replay Cost | AI Analysis | Decision |
|----------|------------------|-------------|-------------|----------|
| Static API (640x640) | $0.007 | $0.007/view | Single angle | ❌ Rejected |
| **Tiles (Zoom 3)** | **$0.64** | **FREE** | **Full 360°** | ✅ **Selected** |
| Dynamic Embed | Free | Free | None | ❌ No AI possible |

### Why Tiles Win

1. **Full 360° Coverage** - Gemini can analyze entire panorama
2. **One-Time Cost** - Pay once, play forever
3. **Custom Viewer** - Marzipano = cinematic control
4. **No API Dependency** - Cached tiles = offline capable

---

## System Components

### 1. Place Curation (`curation_v2.py`)

Fetches nearby places from multiple providers:

| Slot | Category | Provider | Cost |
|------|----------|----------|------|
| 1 | Property | N/A | N/A |
| 2 | Supermarket | Foursquare | $15/1000 |
| 3 | Metro | Transitland | FREE |
| 4 | Bus | Transitland | FREE |
| 5 | Restaurant | Foursquare | $15/1000 |
| 6 | Gym | Foursquare | $15/1000 |
| 7 | School | Foursquare | $15/1000 |
| 8 | Medical Center | Foursquare | $15/1000 |
| 9 | Park | Foursquare | $15/1000 |
| 10 | Cultural | Foursquare | $15/1000 |

**Coordinate Verification:** Google Places "Find Place" API corrects Foursquare coordinates for accurate Street View positioning.

### 2. Street View Client (`streetview_client.py`)

**Tile Configuration:**
```
Zoom Level: 3
Grid: 8x4 = 32 tiles
Tile Size: 512x512 pixels
Total Resolution: 4096 x 2048 (equirectangular)
```

**Process:**
1. Get metadata (pano_id, exact location)
2. Create session token
3. Fetch all 32 tiles in parallel
4. Upload to Supabase Storage
5. Store URLs in database

**Storage Path:** `streetview/{listing_id}/{slot}/{x}_{y}.jpg`

### 3. Tour Generator (`tour_generator.py`)

**Model:** Gemini 2.0 Flash (gemini-2.0-flash)

**Input:** Stitched panorama PNG (4096x2048)

**Output:** Tour sequence with actions:
```json
{
  "actions": [
    {"heading": 45, "pitch": 5, "fov": 80, "duration": 2.0, "caption": "Wide residential street"},
    {"heading": 120, "pitch": 0, "fov": 70, "duration": 2.5, "caption": "Small park on the corner"},
    {"heading": 180, "pitch": -5, "fov": 75, "duration": 2.0, "caption": "Local shops across the road"}
  ]
}
```

**Prompt Philosophy:**
- Calm, neutral, observational tone
- "Friend showing you around" style
- NOT sell-y or hyped
- Describe what you SEE
- 5-12 word captions
- 6-10 seconds total per location

### 4. Custom Viewer (`gamepad-streetview.html`)

**Technology:** Marzipano.js (equirectangular panorama viewer)

**Features:**
- Plays cached tiles from Supabase Storage
- Keyframe animation system
- Caption overlay display
- Gesture controls (hold=pause, tap edges=navigate)

**Cinematic Effects:**
- **Sway:** Gentle continuous camera movement (handheld feel)
- **Shake:** Micro-jitter for realism
- **Arc:** Pitch curve during large heading changes
- **Establishing Shots:** 4 creative patterns
  - Side-turn: Start offset, pan to POI
  - Zoom-in: Start wide, zoom to normal
  - Look-down: Start pitched up, level out
  - Sweep: Horizontal pan to reveal

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURATION PHASE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Property Coords ──► Foursquare ──► POI Candidates              │
│        │                   │                                     │
│        │                   ▼                                     │
│        │            Google Places ──► Verified Coords            │
│        │                   │                                     │
│        ▼                   ▼                                     │
│  Transitland ──► Transit Stops                                   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              CURATED PLACES (Slots 2-10)                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CACHING PHASE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each location (Property + POIs):                            │
│                                                                  │
│  1. GET Street View Metadata ──► pano_id, exact_location        │
│  2. CREATE Session Token                                         │
│  3. FETCH 32 Tiles (8x4 grid, Zoom 3)                           │
│  4. UPLOAD to Supabase Storage                                   │
│  5. SAVE tile_urls to database                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TOUR GENERATION PHASE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each location with tiles:                                   │
│                                                                  │
│  1. STITCH tiles into panorama (4096x2048 PNG)                  │
│  2. SEND to Gemini with context prompt                           │
│  3. PARSE response into TourSequence                             │
│  4. SAVE tour_program to database                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PLAYBACK PHASE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Marzipano Viewer:                                               │
│                                                                  │
│  1. LOAD tile URLs from database                                 │
│  2. CREATE equirectangular scene                                 │
│  3. CONVERT actions to keyframes                                 │
│  4. ADD establishing shot                                        │
│  5. ANIMATE with cinematic effects                               │
│  6. DISPLAY captions                                             │
│                                                                  │
│  Cost: FREE (tiles already cached)                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pricing Analysis

### Per-Listing Costs

| Component | API | Calls | Cost |
|-----------|-----|-------|------|
| Property metadata | Street View Metadata | 1 | FREE |
| Property tiles | Street View Tiles | 32 | $0.64 |
| POI search | Foursquare | ~7 | $0.11 |
| Coord verification | Google Places | ~7 | $0.12 |
| POI metadata | Street View Metadata | ~7 | FREE |
| POI tiles | Street View Tiles | ~224 | $4.48 |
| Tour generation | Gemini 2.0 Flash | ~8 | ~$0.08 |
| **TOTAL** | | | **~$5.43** |

### Monthly Projections

| Scale | Listings/Month | Tile Cost | API Cost | Total |
|-------|----------------|-----------|----------|-------|
| MVP | 100 | $512 | $31 | $543 |
| Growth | 500 | $2,560 | $155 | $2,715 |
| Scale | 2,000 | $10,240 | $620 | $10,860 |

### Key Insight: Replay is FREE

After initial curation:
- **First view:** ~$5.43
- **Every replay:** $0.00
- **1000 replays:** Still $0.00

---

## API Configuration

### Required Environment Variables

```bash
# .env.local

# Google Maps (Street View Tiles + Places)
GOOGLE_MAPS_API_KEY=AIzaSy...

# Foursquare (POI search)
FOURSQUARE_API_KEY=fsq3...

# Transitland (Transit stops) - has default
TRANSITLAND_API_KEY=

# Gemini (Tour generation)
GOOGLE_API_KEY=AIzaSy...

# Supabase (Storage)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Google Cloud APIs Required

1. **Street View Static API** - Metadata endpoint
2. **Street View Tiles API** - Tile fetching
3. **Places API** - Coordinate verification
4. **Generative Language API** - Gemini

### Quota Settings (User-Defined)

| API | Daily Quota | Notes |
|-----|-------------|-------|
| Street View Static | Unlimited | Metadata only |
| Street View Tiles | 15,000 | ~468 listings/day |
| Places API | 500 | ~71 listings/day (bottleneck) |

---

## Database Schema

### `listings` table

```sql
street_view_tile_urls JSONB
-- Structure:
{
  "pano_id": "CAoSLEF...",
  "lat": 41.4872827,
  "lng": 2.0141898,
  "heading": 0,
  "tile_count": 32,
  "zoom": 3,
  "tiles_x": 8,
  "tiles_y": 4,
  "tile_urls": {
    "0_0": "https://xxx.supabase.co/storage/v1/object/public/streetview/6/1/0_0.jpg",
    "0_1": "...",
    ...
  },
  "tour_program": {
    "pano_id": "CAoSLEF...",
    "location_type": "property",
    "total_duration": 8.5,
    "actions": [...]
  }
}
```

### `curated_places` table

```sql
CREATE TABLE curated_places (
  id BIGSERIAL PRIMARY KEY,
  listing_id BIGINT REFERENCES listings(id),
  slot INT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  lat NUMERIC,
  lng NUMERIC,
  distance_m NUMERIC,
  walking_min NUMERIC,
  rating NUMERIC,
  source TEXT DEFAULT 'foursquare',
  fsq_id TEXT,
  address TEXT,
  
  -- Google Places verification
  original_lat NUMERIC,
  original_lng NUMERIC,
  google_place_id TEXT,
  distance_correction_m NUMERIC,
  
  -- Street View data
  tile_urls JSONB,
  sv_heading NUMERIC,
  tour_program JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(listing_id, slot)
);
```

### `streetview` Storage Bucket

- **Bucket name:** `streetview`
- **Public access:** Yes (for playback)
- **Path structure:** `{listing_id}/{slot}/{x}_{y}.jpg`

---

## API Endpoints

### Curation

```
POST /api/listings/{listing_id}/curate-places
```

Curates nearby places and caches tiles. Returns:
```json
{
  "success": true,
  "listing_id": 6,
  "places": [...],
  "empty_slots": {...},
  "tiles_cached": 8,
  "tiles_failed": 2
}
```

### Get Curated Places

```
GET /api/listings/{listing_id}/curated-places
```

Returns array of curated places with tile_urls and tour_program.

### Generate Tours

```
POST /api/listings/{listing_id}/generate-tours
```

Generates Gemini-powered tours for all places with tiles. Returns:
```json
{
  "success": true,
  "generated": 6,
  "failed": 2,
  "tours": [...]
}
```

---

## Frontend Integration

### Loading a Property Tour

```javascript
// 1. Load listing with curated places
const listing = await fetch(`/api/listings/${id}`).then(r => r.json());
const places = await fetch(`/api/listings/${id}/curated-places`).then(r => r.json());

// 2. Build places array (property + POIs)
const allPlaces = [
  { slot: 1, ...listing, place_type: 'property' },
  ...places
];

// 3. Initialize Marzipano viewer
const viewer = new Marzipano.Viewer(element);

// 4. For each place with tiles, create CachedPanoramaViewer
const panoramaViewer = new CachedPanoramaViewer(viewer, place);
panoramaViewer.start();
```

### CachedPanoramaViewer Features

- Loads tiles from Supabase Storage URLs
- Converts tour_program.actions to keyframes
- Adds establishing shots automatically
- Applies cinematic effects (sway, shake, arc)
- Displays captions with fade transitions
- Gesture controls for navigation

---

## Future Enhancements

### Phase 2: Story Mode

- Automated tour through all locations
- Transition animations between places
- Progress indicator showing journey
- Auto-advance with timing

### Phase 3: Embed Widget

- Standalone embeddable viewer
- iframe integration for agencies
- Customizable branding
- Analytics tracking

### Phase 4: Offline Support

- Service worker for tile caching
- IndexedDB for tour programs
- Progressive loading
- Background sync

---

## Files Reference

| File | Purpose |
|------|---------|
| `routes/curation_v2.py` | Place curation + tile caching + tour generation endpoints |
| `clients/streetview_client.py` | Street View tile fetching and Supabase caching |
| `clients/foursquare_client.py` | POI search |
| `clients/transitland_client.py` | Transit stop search |
| `clients/google_places_client.py` | Coordinate verification |
| `services/tour_generator.py` | Gemini tour generation |
| `gamepad-streetview.html` | Marzipano viewer with cinematic effects |

---

## Success Metrics

- ✅ Full 360° Street View analysis with Gemini
- ✅ One-time tile cost, unlimited free replays
- ✅ Cinematic camera effects (sway, shake, arc)
- ✅ Friend-style AI narration
- ✅ No Google Maps JS API dependency
- ✅ Cross-platform playback (any browser)

---

**Architecture designed for scale, optimized for cost, built for delight.**

