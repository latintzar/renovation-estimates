# backend/pricing/v2_boq_generator.py

[Source](../../../../../backend/pricing/v2_boq_generator.py)

V2 BOQ Generator - Delta Scope to Bill of Quantities =====================================================

| Symbol | Kind | Source line |
|---|---|---|
| `_gather_or_cancel` | AsyncFunctionDef | [L33](../../../../../backend/pricing/v2_boq_generator.py#L33) |
| `_chunk_list` | FunctionDef | [L45](../../../../../backend/pricing/v2_boq_generator.py#L45) |
| `BOQWriteQueue` | ClassDef | [L51](../../../../../backend/pricing/v2_boq_generator.py#L51) |
| `BOQWriteQueue.__init__` | FunctionDef | [L54](../../../../../backend/pricing/v2_boq_generator.py#L54) |
| `BOQWriteQueue.start` | FunctionDef | [L72](../../../../../backend/pricing/v2_boq_generator.py#L72) |
| `BOQWriteQueue._raise_if_error` | FunctionDef | [L76](../../../../../backend/pricing/v2_boq_generator.py#L76) |
| `BOQWriteQueue.enqueue` | AsyncFunctionDef | [L80](../../../../../backend/pricing/v2_boq_generator.py#L80) |
| `BOQWriteQueue.close` | AsyncFunctionDef | [L84](../../../../../backend/pricing/v2_boq_generator.py#L84) |
| `BOQWriteQueue._save_chunk` | AsyncFunctionDef | [L91](../../../../../backend/pricing/v2_boq_generator.py#L91) |
| `BOQWriteQueue._run` | AsyncFunctionDef | [L123](../../../../../backend/pricing/v2_boq_generator.py#L123) |
| `_load_bcca_index` | FunctionDef | [L166](../../../../../backend/pricing/v2_boq_generator.py#L166) |
| `_load_ffe_index` | FunctionDef | [L186](../../../../../backend/pricing/v2_boq_generator.py#L186) |
| `_load_knowledge_base` | FunctionDef | [L194](../../../../../backend/pricing/v2_boq_generator.py#L194) |
| `_load_knowledge_graph` | FunctionDef | [L208](../../../../../backend/pricing/v2_boq_generator.py#L208) |
| `_load_all_knowledge_bases` | FunctionDef | [L216](../../../../../backend/pricing/v2_boq_generator.py#L216) |
| `aggregate_boq_from_db` | AsyncFunctionDef | [L603](../../../../../backend/pricing/v2_boq_generator.py#L603) |
| `_format_delta_scopes_for_prompt` | FunctionDef | [L658](../../../../../backend/pricing/v2_boq_generator.py#L658) |
| `_format_target_pir_summary` | FunctionDef | [L724](../../../../../backend/pricing/v2_boq_generator.py#L724) |
| `BOQContextCache` | ClassDef | [L850](../../../../../backend/pricing/v2_boq_generator.py#L850) |
| `BOQContextCache.__init__` | FunctionDef | [L855](../../../../../backend/pricing/v2_boq_generator.py#L855) |
| `BOQContextCache.get_instance` | FunctionDef | [L863](../../../../../backend/pricing/v2_boq_generator.py#L863) |
| `BOQContextCache.load` | FunctionDef | [L868](../../../../../backend/pricing/v2_boq_generator.py#L868) |
| `_format_dimension_scope` | FunctionDef | [L954](../../../../../backend/pricing/v2_boq_generator.py#L954) |
| `_build_bcca_lookup` | FunctionDef | [L1138](../../../../../backend/pricing/v2_boq_generator.py#L1138) |
| `_generate_boq_for_scope_item` | AsyncFunctionDef | [L1168](../../../../../backend/pricing/v2_boq_generator.py#L1168) |
| `_generate_boq_for_room` | AsyncFunctionDef | [L1292](../../../../../backend/pricing/v2_boq_generator.py#L1292) |
| `_generate_boq_for_dimension` | AsyncFunctionDef | [L1432](../../../../../backend/pricing/v2_boq_generator.py#L1432) |
| `_generate_boq_for_dimension.process_scope_item` | AsyncFunctionDef | [L1478](../../../../../backend/pricing/v2_boq_generator.py#L1478) |
| `generate_v2_boq` | AsyncFunctionDef | [L1581](../../../../../backend/pricing/v2_boq_generator.py#L1581) |
