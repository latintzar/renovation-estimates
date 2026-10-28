# First synthetic estimate

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/first-estimate.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The original pricing modules import NumPy (and Pydantic for the original schema imports) through their matcher. Use an existing Python environment with the declared dependencies; this command installs nothing. It imports the real package and complete `v4_quantification_pipeline` module. The matcher is never instantiated, and no original price book, embedding index or provider module is used.

The command creates a new owned mode-0700 temporary directory. Its two mode-0600 SQLite files contain an authored synthetic price book and the rows produced by the original assembler. The JSON receipt records source hashes, runtime/import closure, inputs’ coverage, output rows and scope. `--output /absolute/new/receipt.json` selects a new receipt file outside the source checkout; the owned SQLite state remains in the printed receipt’s state directory.

The fixture has one room: 12m² of synthetic floor finish at €20/m² and 14m of synthetic skirting at €5/m. The result is two rows totaling **€310**, with 7.4 synthetic labor hours. These are authored demonstration inputs, rather than a construction price quotation or a redistributed BCCA catalogue.

Execution uses original `_plans_validate_or_raise`, `BCCAPriceLookup.get_price`, `measurement_catalog_v4.validate_catalog`, `quantity_formula_v4.evaluate_formula` and `assemble_v4_boq`. Only `db.save_boq_line_items_batch` is supplied by a local SQLite sink. The receipt preserves original `signals_used`, formula AST, work item, room and dimensional provenance. Formula validation and quantity caps remain the original code.

Ten tests verify exact rows/totals, original plan coverage/provenance, absent lookup, missing signal, unit mismatch, an unmatched work item, unsupported formula, negative/nonfinite quantity, area cap and the Python network fence. The fence blocks socket/DNS attempts before transport during the proof. This is an offline calculation proof; the listing importer, full V5 queue, Supabase RPCs, model stages and original browser path have separate setup and verification.
