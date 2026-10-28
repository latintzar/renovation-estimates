# Providers and data

Each capability uses the recipient's account and its own permission boundary. The personal Atelier preview allowance is a separate typed integration; this source preserves the original adapters.

| Capability | Private configuration | Source |
|---|---|---|
| Durable store and queue | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY | backend/database.py, backend/workers |
| Room analysis, scope and reports | GEMINI_API_KEY; optional GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL | backend/pipeline/gemini_client.py, backend/pricing/v5_* |
| Comparable acquisition | CASAFARI_API_TOKEN | backend/clients/casafari_client.py |
| Listing/photo acquisition | SCRAPFLY_API_KEY, SCRAPINGDOG_API_KEY | backend/scraper, backend/pricing/image_cache.py |
| Embedding and older Vertex adapters | GOOGLE_CLOUD_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS | backend/pricing/embedding_runtime.py, backend/scraper/parsers |
| Place/transport context | GOOGLE_MAPS_API_KEY, FOURSQUARE_API_KEY, TRANSITLAND_API_KEY | backend/clients, backend/routes/curation_v2.py |
| Browser map | NEXT_PUBLIC_MAPBOX_TOKEN | frontend/src/components |

Use `tools/runtime-env.py` for hidden input, private-file permissions, masked doctor and selected-file execution. Backend source reads explicit process environment. Original credential literals, personal aliases, ancestor dotenv discovery and business account defaults are removed from this derivative. Gemini configuration occurs at the actual call boundary; key values and fragments stay out of its setup logs.

## Models

The original `MODELS` mapping is retained as historical source behaviour. Full identifiers remain accepted; GEMINI_FLASH_MODEL and GEMINI_PRO_MODEL override the corresponding aliases for an owned installation. Select models supported by the recipient's account and verify structured-output/image behaviour for the actual stage. Google's [model catalogue](https://ai.google.dev/gemini-api/docs/models), checked28 October 2026, lists the current model families and lifecycle. The original SDK and model-stage integration have fixture/source evidence; live account acceptance remains a separate check.

The historical token-pricing tables are dated engineering records. Provider billing and actual usage receipts govern charges. The source does not claim those old tables are today's prices.

## Data rights

Code permission and data permission are separate. Original BCCA/construction databases, indexes, embeddings, reference derivatives, commercial comparable responses, property images and customer rows are excluded from the export. Recipients supply their own licensed inputs. The included `SYNTH-*` prices, room measurements and local receipts are independently authored demonstration data, labelled synthetic at the row and receipt boundary.

Historical building manuals, copied standards, Uniclass distributions and other third-party documents remain outside this source release until their own terms are reconciled. Original prompts, schemas, calculation code and architecture guides remain available. [Setup](setup.md) identifies required regeneration artifacts and the queue-schema gap.

Optional worker notifications and retained communications helpers use the communications group with the recipient’s Twilio/Meta/Resend credentials, sender IDs, webhook verification value and public callback origin. The Estimate entry leaves those routers unmounted; commissioning this separate capability includes its own webhook/auth/recipient acceptance. Vertex selection maps the owned project ID to the standard GOOGLE_CLOUD_PROJECT environment name.

The scraper’s existing google.genai import is declared as google-genai 1.62.0, whose published metadata accepts the original Pydantic 2.10.4 constraint. The original Google generative/Vertex branches remain separate. Dependency declaration and full live runtime acceptance are recorded separately in release status.

The report accepts optional recipient-owned labor_rates and machinery_rates with {name, rate} records, plus a price_basis label. The included fixture supplies only its actual synthetic composite unit prices. Unprovided decomposition/rate tables are omitted from its report.
