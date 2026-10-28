Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# External Dependency Audit - Lean MVP

> **Generated:** January 8, 2026  
> **Purpose:** Document ALL references to files/folders OUTSIDE `Lean MVP/` folder  
> **Goal:** Ensure Lean MVP is fully self-contained before deleting legacy code

---

## 🚨 CRITICAL EXTERNAL DEPENDENCIES

### 1. Knowledge Graph Data Files (MUST MIGRATE)

| File | Location in Lean MVP | External Reference |
|------|---------------------|-------------------|
| `backend/pricing/kg_estimator.py` | Line 36-38 | `experiments/renovation_costing/hybrid_renovation_graph.json` |
| `backend/pricing/kg_estimator.py` | Line 36-38 | `experiments/renovation_costing/construction.db` |

**Code:**
```python
# Paths - use experiments folder for data files
EXPERIMENTS_DIR = Path(__file__).parent.parent.parent.parent / "experiments" / "renovation_costing"
KG_PATH = EXPERIMENTS_DIR / "hybrid_renovation_graph.json"
DB_PATH = EXPERIMENTS_DIR / "construction.db"
```

**Action Required:**
1. Copy `experiments/renovation_costing/hybrid_renovation_graph.json` → `Lean MVP/backend/data/`
2. Copy `experiments/renovation_costing/construction.db` → `Lean MVP/backend/data/`
3. Update paths in `kg_estimator.py` to use local `data/` folder

---

## ⚠️ ENVIRONMENT FILE REFERENCES

### Files Loading from Root `.env.local`

These files attempt to load environment variables from `puedo_casa/.env.local`:

| File | Line | Pattern |
|------|------|---------|
| `backend/config.py` | 16 | `load_dotenv(Path(__file__).parent.parent.parent / ".env.local")` |
| `backend/pipeline/gemini_client.py` | 27 | `load_dotenv(backend_root.parent.parent / ".env.local")` |
| `backend/clients/casafari_client.py` | 28 | `load_dotenv(backend_root.parent.parent / ".env.local")` |
| `backend/clients/transitland_client.py` | 25 | `load_dotenv(backend_root.parent.parent / ".env.local")` |
| `backend/clients/foursquare_client.py` | 35 | `load_dotenv(backend_root.parent.parent / ".env.local")` |
| `backend/clients/overture_client.py` | 34 | `load_dotenv(backend_root.parent.parent / ".env.local")` |
| `backend/utils/google_search.py` | 27 | `load_dotenv(backend_root.parent.parent / ".env.local")` |

**Action Required:**
- Create `Lean MVP/.env.local` with all required environment variables
- These files also fall back to `Lean MVP/.env.local` so they will continue to work

**Required Environment Variables:**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SCRAPFLY_API_KEY`
- `GOOGLE_AI_API_KEY`
- `GOOGLE_CLOUD_PROJECT_ID` (default: `fifth-incentive-471523-b1`)
- `GOOGLE_CLOUD_LOCATION` (default: `us-central1`)
- `CASAFARI_API_TOKEN`
- `TRANSITLAND_API_KEY`
- `FOURSQUARE_API_KEY`
- `MAPBOX_TOKEN`
- `SCRAPINGDOG_API_KEY`

---

## 📝 DOCUMENTATION REFERENCES (Comments Only)

These are **documentation comments only** - not functional dependencies:

| File | Reference | Type |
|------|-----------|------|
| `backend/pipeline/steps/visuals.py` | `src/app/api/listings/[id]/photos/remove-furniture/route.ts` | Ported from comment |
| `backend/pipeline/steps/architect.py` | `src/app/api/listings/[id]/rooms/group-catalog/route.ts` | Ported from comment |
| `backend/pipeline/steps/scope.py` | `src/app/api/listings/[id]/renovation-scope/route.ts` | Ported from comment |
| `backend/utils/domain_credibility.py` | `src/lib/cred/scoreDomain.ts` | Ported from comment |
| `backend/clients/overture_client.py` | `Leo/backend/tools/tools_athena.py` | Same approach comment |
| `backend/services/tour_generator_legacy.py` | `Leo/random stuff/gamepad-streetview.html` | Original source comment |
| `lib/types.ts` | `Leo/backend/schema.py` | Ported patterns comment |
| `lib/gemini-client.ts` | `Leo/backend/gemini_client.py` | Ported from comment |
| `Design/Scraper Extraction Guide.md` | `src/lib/extraction/adapters/server.ts` | Documentation |
| `Design/Architecture Decision.md` | `Leo` references | Documentation |
| `Design/Implementation Checklist.md` | `Leo` references | Documentation |
| `Design/EXISTING_CODE_MAP.md` | `src/app/api/listings/[id]/...` | Documentation |

**Action:** None required - these are just historical comments documenting code origins.

---

## 🔗 HARDCODED VALUES

### Google Cloud Project ID
| File | Line | Value |
|------|------|-------|
| `backend/scraper/parsers/gemini_universal.py` | 45 | `fifth-incentive-471523-b1` (default) |
| `backend/scraper/parsers/url_validator.py` | 24 | `fifth-incentive-471523-b1` (default) |
| `backend/scraper/location_intelligence.py` | 45 | `fifth-incentive-471523-b1` (default) |

**Note:** These use `os.environ.get()` with fallback - not a blocking issue.

### Mapbox Token
| File | Line | Value |
|------|------|-------|
| `frontend/src/components/MapModal.tsx` | 20 | Hardcoded public token with fallback |

**Code:**
```typescript
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";
```

**Note:** Has fallback - continues to work. Add to `.env.local` for cleaner config.

---

## 📁 WORKSPACE FILE (DELETE)

| File | Reference |
|------|-----------|
| `backend/pipeline/steps/puedo_casa.code-workspace` | `"path": "../../../.."` |

**Action:** Delete this file - it's a VS Code workspace file pointing to root.

---

## ✅ INTERNAL REFERENCES (NO ACTION NEEDED)

These use relative paths but stay WITHIN Lean MVP:

### Python sys.path inserts (internal navigation)
| File | Line | Target |
|------|------|--------|
| `backend/pipeline/db_helpers.py` | 18 | `Path(__file__).parent.parent` (→ backend) |
| `backend/pipeline/steps/analyze_comparables.py` | 38 | `Path(__file__).parent.parent.parent` (→ backend) |
| `backend/pipeline/steps/scope_search.py` | 363 | `Path(__file__).parent.parent.parent` (→ backend) |
| `backend/pipeline/steps/context_research.py` | 25 | `Path(__file__).parent.parent.parent` (→ backend) |

### Local JSON file loads (all within Lean MVP)
| File | Target File |
|------|-------------|
| `backend/pipeline/prompts/uniclass_assessment.py` | `standards/uniclass_ss_residential.json` |
| `backend/pipeline/prompts/uniclass_assessment.py` | `standards/uniclass_pr_residential.json` |
| `backend/pipeline/scope_builder.py` | `pipeline/rules_engine_v2.json` |
| `backend/pipeline/steps/verify_rules.py` | `pipeline/rules_engine_v2.json` |
| `backend/pipeline/steps/analyze_room.py` | `pipeline/rules_engine_v2.json` |
| `backend/pipeline/steps/_archive/renovation_report_v1.py` | `pipeline/rules_engine.json` |
| `backend/utils/domain_credibility.py` | `utils/learned_whitelist.json` |
| `backend/scraper/bot_detection.py` | `scraper/.learned_domains.json` |

### Test files writing to /tmp (safe)
| File | Target |
|------|--------|
| `backend/test_renovation_report.py` | `/tmp/renovation_report_test.json` |
| `backend/clients/geoapify_isochrone.py` | `/tmp/isochrone_test.geojson` |

---

## 🧪 TEST FILES WITH HARDCODED PATHS

| File | Line | Path |
|------|------|------|
| `backend/test_renovation_route.py` | 6-7 | `/root/puedo_casa/Lean MVP/backend/.env` |
| `backend/test_renovation_report.py` | 18 | `/root/puedo_casa/Lean MVP/backend` |

**Action:** These are test files - can be updated or deleted.

---

## 📊 SUMMARY

### MUST FIX BEFORE DELETION

| Priority | Item | Action |
|----------|------|--------|
| 🔴 Critical | `experiments/renovation_costing/*.json` + `*.db` | Migrate to `Lean MVP/backend/data/` |
| 🟡 Important | Root `.env.local` | Copy to `Lean MVP/.env.local` |
| 🟢 Minor | `puedo_casa.code-workspace` | Delete workspace file |

### NO ACTION NEEDED

| Category | Count | Notes |
|----------|-------|-------|
| Documentation comments | 12 | Historical references only |
| Internal Python paths | 4 | Navigate within Lean MVP |
| Internal JSON loads | 8 | All files within Lean MVP |
| Test /tmp writes | 2 | Safe temporary files |
| Env var fallbacks | 4 | Have defaults, work without root .env |

---

## ✅ MIGRATION CHECKLIST

```bash
# 1. Create data directory
mkdir -p "Lean MVP/backend/data"

# 2. Copy KG files
cp experiments/renovation_costing/hybrid_renovation_graph.json "Lean MVP/backend/data/"
cp experiments/renovation_costing/construction.db "Lean MVP/backend/data/"

# 3. Update kg_estimator.py path (manual edit)
# Change: EXPERIMENTS_DIR = Path(__file__).parent.parent.parent.parent / "experiments" / "renovation_costing"
# To:     DATA_DIR = Path(__file__).parent.parent / "data"

# 4. Copy environment file
cp .env.local "Lean MVP/.env.local"

# 5. Delete workspace file
rm "Lean MVP/backend/pipeline/steps/puedo_casa.code-workspace"

# 6. Verify no remaining external refs
grep -r "experiments\|/root/puedo_casa[^/L]" "Lean MVP/" --include="*.py" --include="*.ts"
```

---

## 🎯 AFTER MIGRATION: FINAL VERIFICATION

Run this to confirm no external dependencies remain:

```bash
# Check for any remaining external references
grep -rn "parent.parent.parent.parent" "Lean MVP/"
grep -rn "experiments/" "Lean MVP/" --include="*.py"
grep -rn "Leo/" "Lean MVP/" --include="*.py" --include="*.ts"
grep -rn "src/app" "Lean MVP/" --include="*.py" --include="*.ts"
```

Expected result: Only documentation/comment matches, no functional code.

---

*Document generated by comprehensive codebase audit on January 8, 2026*


## Public Mapbox configuration

The map components read NEXT_PUBLIC_MAPBOX_TOKEN from the recipient environment. An unconfigured map shows the required variable and makes zero Mapbox requests. Supply a public browser token scoped to the recipient’s allowed URLs.
