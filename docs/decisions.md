# Decisions

Retrospective 28 October 2026, based on leo-archive commit 4dca5f9b. The original source and specifications provide the evidence; extraction choices below describe this release.

## Rooms and slots preserve coverage

A property-wide paragraph can hide an omitted room or trade. The V5 design carries room tags, slots, work-item IDs and coverage forward through the analysis. `backend/pipeline/v5_stages.py`, `backend/pricing/v5_slots.py` and `v5_work_items.py` define those joins. The interface keeps property details and renovation evidence in the same listing workspace.

## Comparable standards define the target

The model proposes the difference between a target property and selected comparable standards. The source separates comparable selection, room/property intelligence, strategy deltas and work decomposition in `v5_comparable_selector.py`, `v5_comparable_standard.py` and `v5_strategy_delta_decompose.py`. Those are explicit stages with retained evidence, rather than one unexplained total.

## The calculator owns quantity arithmetic

`quantity_formula_v4.py` validates a restricted expression tree and units. `measurement_catalog_v4.py` names the signals. The upstream plan validator enforces coverage before `assemble_v4_boq` multiplies supplied rates and quantities and writes provenance. The synthetic first result exercises these exact original modules. It replaces only the remote persistence sink with owned local SQLite.

## Jobs outlive HTTP requests

The importer creates a listing and enqueues work. `v2_scheduler.py` and `workers/pipeline_worker.py` use durable jobs, predecessor gates, claim leases, heartbeat, retry and acknowledgement. This keeps an expensive run independent of the initiating browser request. The archive's missing original claim/bootstrap DDL is recorded as installation work; source implementation and fresh database acceptance remain distinct evidence.

## Recipient files own provider access

The archive mixed root environment discovery, personal aliases and embedded legacy defaults. The release uses explicit private-file input and selected-file child execution. Configuration values stay on the recipient's server. Optional capabilities retain their original providers; the source does not silently substitute the Atelier preview transport.

## The Estimate workspace is the entry point

The final archive also carried later Leo Copilot marketing, pitch, portal experiments and compiled Expo exports. This derivative opens the original Estimate listing/detail/admin workspace on every installation hostname. Separate later surfaces retain their archive authority and lineage. Their unreviewed compiled assets and property media are excluded from this source beta.

## Supported tooling preserves the original interface

The original frontend locked Next 14.2.20. Its audit showed critical/high advisories. This derivative moves the framework/tooling to Next 16.4.3, retains React 18 and the existing components, adapts dynamic route params and uses the Webpack build path. Its dependency lock audits clean. Playfair Display and Source Sans3 are self-hosted from exact upstream font blobs under OFL, preserving the type choices while making the build independent of font-network access. Build/type/browser results are recorded separately in RELEASE-STATUS.md.

## A populated first result uses the native report

The release adds a small /first-estimate entry. tools/export-first-result.py regenerates its JSON directly from the proved original costing tail; the page opens the existing OfficialBudgetReport component. Its inputs and people are labelled synthetic. The archived report’s additional fixed percentage calculations remain visible as interface-example behaviour, separate from a real project’s tax treatment. The original listing importer remains the main app entry.

## Price evidence belongs to the selected inputs

Visual verification exposed a fixed reference-rate table and a claim of refreshed BCCA prices in the archived report. The derivative removes those defaults. Optional analysis.labor_rates and machinery_rates supply recipient-owned rates, and analysis.price_basis identifies their basis. Unprovided rate/decomposition sections stay out of the fixture. The report heading and footer describe the actual budget layout, without asserting official approval or regulatory compatibility. The synthetic entry provides its own explicit project/basis labels.
