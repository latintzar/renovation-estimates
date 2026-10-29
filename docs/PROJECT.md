# Room-by-room renovation estimates from a property listing

Leo Estimate is a renovation estimator for Spanish properties. It turns a listing into a room-by-room scope, a priced bill of quantities and before-and-after images, with a printable report for the next conversation.

A property listing shows what is there. A buyer also needs to understand the work, quantities and likely cost before deciding what to buy or asking for contractor quotes.

| Feature | What it does |
| --- | --- |
| Property report | Keep listing details, photographs, rooms and comparables together. |
| Before and after | Use the original image comparison to explore a proposed renovation. |
| Bill of quantities | Inspect room-level work, measurements, materials, labour and price evidence. |
| Printable estimate | Carry the itemized scope and totals into a report. |
| Analysis pipeline | Continue with the original FastAPI services, durable workers and deterministic costing modules. |

## Workflow

Property listing → Room condition and scope → Quantities and unit rates → Before-and-after comparison → Itemized report

## Design decisions

- The report keeps the visual proposal and its priced work in one context.
- Deterministic costing makes the estimate’s arithmetic traceable to quantities and rates.

## Status and next steps

The native preview includes three authored properties and complete cached reports. It uses the original interface, costing results and recovered project images. Fresh property analysis and image generation use your configured providers. Connect property intake, verify local price evidence and run the analysis pipeline with your own accounts.

Source: [docs/workflows.md](../docs/workflows.md), [docs/native-workspace.md](../docs/native-workspace.md), [docs/setup.md](../docs/setup.md).
