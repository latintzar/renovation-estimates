# Product tour

Leo Estimate is a renovation estimator for Spanish properties. It connects a listing and its rooms to proposed work, measured quantities, unit prices and a printable bill of quantities, helping buyers, investors and contractors discuss the scope of a renovation.

[Open demo](https://preview.atelierneyra.com/apps/estimates/listings) · [Run the native workspace](../README.md#run-the-app)

## From listing to itemized estimate

1. Choose a property from the listing feed. The selected property opens its original report workspace with **Reforma** selected.
2. In **Reforma**, compare the before/after images, inspect the investment and room plan, and follow the proposed changes room by room.
3. Open **Anuncio** to revisit the property information and photographs. Switch to **Comparables** to inspect the three authored comparison properties used to illustrate the target standard.
4. Return to **Reforma** and open **Presupuesto desglosado**. Expand the work chapters and read the measurements, quantities, unit prices and line totals. The report uses the selected property’s address and area.
5. Print the detailed report. It carries the priced scope into the next contractor or purchase conversation, while its supplied price basis remains visible.

The native example has three fictional properties, each with four rooms and 24 calculated work items. The original calculation modules produce the cached BOQ rows; narrative, measurements, prices and comparables are authored inputs. The recovered photographs were originally generated project assets. [Native workspace](native-workspace.md) records that provenance and the read-only API contract.

## Product areas and source

| Area | Actions and results | Source |
| --- | --- | --- |
| Listing intake and feed | Browse properties; configured mode also retains URL submission and pipeline start. | [listings/page.tsx](../frontend/src/app/listings/page.tsx), [API client](../frontend/src/lib/api.ts). |
| Property and room report | Keep renovation, listing and comparable views inside one property workspace. | [listing/[id]/page.tsx](../frontend/src/app/listing/[id]/page.tsx), [BeforeAfterSlider.tsx](../frontend/src/components/renovation/BeforeAfterSlider.tsx). |
| Comparable standard | Inspect comparison properties and the source’s target-standard selection stages. | [ComparablesTab.tsx](../frontend/src/components/renovation/ComparablesTab.tsx), [v5_comparable_selector.py](../backend/pricing/v5_comparable_selector.py), [v5_comparable_standard.py](../backend/pricing/v5_comparable_standard.py). |
| Costing | Validate work-item coverage and units, evaluate measured signals, then assemble quantities and prices into BOQ rows. | [bcca_price_lookup.py](../backend/pricing/bcca_price_lookup.py), [quantity_formula_v4.py](../backend/pricing/quantity_formula_v4.py), [v4_quantification_pipeline.py](../backend/pricing/v4_quantification_pipeline.py). |
| Budget report | Inspect prices, decompositions, work chapters and totals; print the complete report. | [OfficialBudgetReport.tsx](../frontend/src/components/renovation/OfficialBudgetReport.tsx). |
| Durable analysis | Run staged work with predecessor checks, leases, retries and stored artifacts under your configuration. | [v5_stages.py](../backend/pipeline/v5_stages.py), [pipeline_worker.py](../backend/workers/pipeline_worker.py). |
| Cached first result | Reproduce the native reports from original calculation modules and explicitly authored inputs. | [build-native-sample.py](../tools/build-native-sample.py), [native workspace](native-workspace.md). |

## Design and calculation decisions

The property report keeps visual proposals and priced work together. Rooms, slots and work-item identities carry coverage through the V5 pipeline. Comparable standards define the target; deterministic costing owns the quantity arithmetic. This makes a total traceable to measured signals and supplied unit rates. Durable jobs keep the analysis independent of the browser request that started it.

The small standalone costing example is another reuse point: two synthetic items total €310 with 7.4 synthetic labour hours. It exercises the original price lookup, plan validator, formula evaluator and assembler, replacing the remote persistence sink with local SQLite. [Calculation guide](../tools/README-first-estimate.md) describes the receipt and exact scope.

The native cached workspace is read-only. Connect your own listing acquisition, model/photo services, price/reference datasets and worker/database before processing a new property. Source implementation, cached UI and accepted live processing each retain their own evidence in [release status](../RELEASE-STATUS.md).

## Continue from here

- [Setup](setup.md) for native commands, private credentials and database artifacts.
- [Workflows](workflows.md) for property import, priced-package construction and recovery.
- [Architecture](architecture.md) and [decisions](decisions.md) for module boundaries and UX choices.
- [Source reference](reference/README.md) for functions and modules.
- [Providers and data rights](providers.md), [image provenance](assets/generated-property-images.json) and [source provenance](provenance.md).

A useful continuation is to supply a licensed local price basis and configure property intake through one complete worker run, carrying source evidence through to the printed report.
