Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Google Places API Decision

**Date:** 2024-12-31  
**Status:** ✅ Approved & Implemented

---

## Summary

We are replacing **Foursquare + Google Geocoding** with a **Google-only Nearby Search Pro** approach for place curation.

---

## Why Google-Only?

### Problems with Foursquare
1. **API returns no coordinates** - Despite documentation claiming lat/lng are "Pro tier" fields, the API consistently omits them
2. **Requires fallback geocoding** - Each place needs a Google Geocoding call to get coordinates
3. **No opening hours** - Cannot identify "late night" venues
4. **No ratings** - Missing quality signals for curated places
5. **Inconsistent data** - Address quality varies significantly

### Google Advantages
1. **Direct coordinates** - `location.latitude/longitude` always included
2. **Opening hours** - Full `regularOpeningHours` with periods and weekday descriptions
3. **Ratings** - `rating` (1-5 stars) and `userRatingCount`
4. **Single API** - No fallback chains, simpler code
5. **Reliable** - Consistent data quality worldwide

---

## Pricing Analysis

### Google Places API (New) - Nearby Search Pro

| Tier | Monthly Events | Price/1000 | Per Request |
|------|----------------|------------|-------------|
| **Free** | First 5,000 | $0.00 | $0.00 |
| Tier 1 | 5,001 - 100,000 | $32.00 | $0.032 |
| Tier 2 | 100,001 - 500,000 | $25.60 | $0.026 |
| Tier 3 | 500,001 - 1,000,000 | $19.20 | $0.019 |

### Cost Per Listing

We make **8 Nearby Search calls per listing** (one per category):
- Restaurant/Cafe (50m)
- Bar/Late Night (100m)
- Grocery/Supermarket (1250m)
- Medical/Hospital (2500m)
- Schools (1500m)
- Parks/Recreation (1000m)
- Transit (750m)
- Cultural/Entertainment (1000m)

```
8 calls × $0.032 = $0.256/listing (after free tier)
```

### Monthly Projections

| Listings/Month | API Calls | Free Tier | Paid Calls | Cost |
|----------------|-----------|-----------|------------|------|
| 100 | 800 | ✅ Covered | 0 | **$0** |
| 500 | 4,000 | ✅ Covered | 0 | **$0** |
| 625 | 5,000 | ✅ Covered | 0 | **$0** |
| 1,000 | 8,000 | 5,000 | 3,000 | **$96** |
| 5,000 | 40,000 | 5,000 | 35,000 | **$1,120** |

### Comparison: Old vs New Approach

| Approach | Calls/Listing | Cost/Listing | Data |
|----------|---------------|--------------|------|
| Foursquare + Geocode | 8 + 32 | ~$0.16 | ❌ No hours, ❌ No ratings |
| **Google Pro** | 8 | ~$0.26 | ✅ Hours, ✅ Ratings |

**Verdict:** Slightly higher cost per listing, but significantly better data quality.

---

## Data Fields Returned

### From Nearby Search Pro (What We Use)

```json
{
  "places": [
    {
      "displayName": { "text": "Hard Rock Café", "languageCode": "en" },
      "location": { "latitude": 41.3858, "longitude": 2.1707 },
      "primaryType": "american_restaurant",
      "formattedAddress": "Plaça de Catalunya, 21, Barcelona",
      "rating": 4.1,
      "userRatingCount": 8160,
      "regularOpeningHours": {
        "openNow": true,
        "weekdayDescriptions": [
          "Monday: 9:00 AM – 1:30 AM",
          "Tuesday: 9:00 AM – 1:30 AM"
        ],
        "periods": [
          {
            "open": { "day": 0, "hour": 9, "minute": 0 },
            "close": { "day": 1, "hour": 1, "minute": 30 }
          }
        ]
      }
    }
  ]
}
```

### Field Mask Used

```
places.displayName,places.location,places.primaryType,places.formattedAddress,places.rating,places.userRatingCount,places.regularOpeningHours
```

---

## Implementation

### Backend Changes
1. **New client:** `google_places_nearby_client.py` - Pure Google implementation
2. **Updated endpoint:** `POST /api/listings/{id}/curated-places` - Uses Google Nearby Search
3. **Enhanced schema:** `CuratedPlace` includes `rating`, `review_count`, `opening_hours`, `is_open_late`

### Frontend Changes
1. **PlaceCard component:** Beautiful card with rating stars, hours badge, late-night indicator
2. **NeighborhoodMap:** Click markers to show place cards
3. **Legend:** Updated to show rating/hours availability

---

## Late Night Detection

A place is "open late" if it closes after 11 PM or crosses midnight:

```python
def is_open_late(opening_hours: dict) -> bool:
    """Determine if a place is open late (after 11 PM)."""
    if not opening_hours or 'periods' not in opening_hours:
        return False
    
    for period in opening_hours.get('periods', []):
        close = period.get('close', {})
        open_day = period.get('open', {}).get('day')
        close_day = close.get('day')
        close_hour = close.get('hour', 0)
        
        # Crosses midnight (different day)
        if close_day != open_day:
            return True
        # Closes after 11 PM
        if close_hour >= 23:
            return True
    
    return False
```

---

## API Key

Using existing Google API key: ``

Required APIs enabled:
- ✅ Places API (New)
- ✅ Geocoding API (legacy, can be removed)

---

## Migration Notes

1. **No breaking changes** - Frontend continues to receive same data structure
2. **Enhanced data** - Additional fields (rating, hours) are additive
3. **Foursquare removal** - Can be deleted after verification
4. **Cost monitoring** - Set up billing alerts at $50, $100, $200

---

## References

- [Google Places API Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Nearby Search Documentation](https://developers.google.com/maps/documentation/places/web-service/nearby-search)
- [Field Masks](https://developers.google.com/maps/documentation/places/web-service/place-data-fields)

