# Source reference

Generated from source with Python AST and the TypeScript compiler. Each module links to its source and every discovered named symbol. The generator executes no application code and records no literal default values.

## backend

- [backend/__init__.py](modules/backend/__init__.py.md): 0 symbols.
- [backend/config.py](modules/backend/config.py.md): 6 symbols.
- [backend/database.py](modules/backend/database.py.md): 147 symbols.
- [backend/generate_ana_illustrations.py](modules/backend/generate_ana_illustrations.py.md): 4 symbols.
- [backend/generate_landing_images.py](modules/backend/generate_landing_images.py.md): 2 symbols.
- [backend/generate_new_before.py](modules/backend/generate_new_before.py.md): 3 symbols.
- [backend/generate_room_photos.py](modules/backend/generate_room_photos.py.md): 3 symbols.
- [backend/generate_scope_images.py](modules/backend/generate_scope_images.py.md): 2 symbols.
- [backend/main.py](modules/backend/main.py.md): 3 symbols.
- [backend/regenerate_landing_images.py](modules/backend/regenerate_landing_images.py.md): 2 symbols.
- [backend/run_single_stage.py](modules/backend/run_single_stage.py.md): 1 symbols.
- [backend/schema.py](modules/backend/schema.py.md): 29 symbols.
- [backend/test_router.py](modules/backend/test_router.py.md): 1 symbols.

## backend/clients

- [backend/clients/__init__.py](modules/backend/clients/__init__.py.md): 0 symbols.
- [backend/clients/casafari_client.py](modules/backend/clients/casafari_client.py.md): 15 symbols.
- [backend/clients/foursquare_client.py](modules/backend/clients/foursquare_client.py.md): 15 symbols.
- [backend/clients/geoapify_isochrone.py](modules/backend/clients/geoapify_isochrone.py.md): 6 symbols.
- [backend/clients/google_places_client.py](modules/backend/clients/google_places_client.py.md): 12 symbols.
- [backend/clients/overture_client.py](modules/backend/clients/overture_client.py.md): 15 symbols.
- [backend/clients/streetview_client.py](modules/backend/clients/streetview_client.py.md): 10 symbols.
- [backend/clients/transitland_client.py](modules/backend/clients/transitland_client.py.md): 27 symbols.

## backend/pipeline

- [backend/pipeline/__init__.py](modules/backend/pipeline/__init__.py.md): 0 symbols.
- [backend/pipeline/cadastre_client.py](modules/backend/pipeline/cadastre_client.py.md): 24 symbols.
- [backend/pipeline/gemini_client.py](modules/backend/pipeline/gemini_client.py.md): 31 symbols.
- [backend/pipeline/gla_stages.py](modules/backend/pipeline/gla_stages.py.md): 1 symbols.
- [backend/pipeline/v032_orchestrator.py](modules/backend/pipeline/v032_orchestrator.py.md): 7 symbols.
- [backend/pipeline/v5_stages.py](modules/backend/pipeline/v5_stages.py.md): 2 symbols.

## backend/pipeline/prompts

- [backend/pipeline/prompts/condition_assessment_v2.py](modules/backend/pipeline/prompts/condition_assessment_v2.py.md): 2 symbols.
- [backend/pipeline/prompts/rule_verification.py](modules/backend/pipeline/prompts/rule_verification.py.md): 2 symbols.
- [backend/pipeline/prompts/scope_mapper_v2.py](modules/backend/pipeline/prompts/scope_mapper_v2.py.md): 2 symbols.
- [backend/pipeline/prompts/uniclass_assessment.py](modules/backend/pipeline/prompts/uniclass_assessment.py.md): 3 symbols.

## backend/pipeline/schemas

- [backend/pipeline/schemas/gap_analysis.py](modules/backend/pipeline/schemas/gap_analysis.py.md): 9 symbols.
- [backend/pipeline/schemas/property_intelligence.py](modules/backend/pipeline/schemas/property_intelligence.py.md): 19 symbols.
- [backend/pipeline/schemas/renovation.py](modules/backend/pipeline/schemas/renovation.py.md): 32 symbols.

## backend/pipeline/steps

- [backend/pipeline/steps/__init__.py](modules/backend/pipeline/steps/__init__.py.md): 0 symbols.
- [backend/pipeline/steps/cluster_photos.py](modules/backend/pipeline/steps/cluster_photos.py.md): 8 symbols.
- [backend/pipeline/steps/cluster_photos_v5.py](modules/backend/pipeline/steps/cluster_photos_v5.py.md): 3 symbols.
- [backend/pipeline/steps/map_to_scope.py](modules/backend/pipeline/steps/map_to_scope.py.md): 8 symbols.
- [backend/pipeline/steps/smart_m2.py](modules/backend/pipeline/steps/smart_m2.py.md): 17 symbols.
- [backend/pipeline/steps/visuals.py](modules/backend/pipeline/steps/visuals.py.md): 6 symbols.

## backend/pipeline/utils

- [backend/pipeline/utils/glb_utils.py](modules/backend/pipeline/utils/glb_utils.py.md): 8 symbols.

## backend/pricing

- [backend/pricing/__init__.py](modules/backend/pricing/__init__.py.md): 0 symbols.
- [backend/pricing/bcca_embedding_matcher.py](modules/backend/pricing/bcca_embedding_matcher.py.md): 8 symbols.
- [backend/pricing/bcca_price_lookup.py](modules/backend/pricing/bcca_price_lookup.py.md): 13 symbols.
- [backend/pricing/coverage_ledger.py](modules/backend/pricing/coverage_ledger.py.md): 2 symbols.
- [backend/pricing/delta_scope_generator.py](modules/backend/pricing/delta_scope_generator.py.md): 14 symbols.
- [backend/pricing/embedding_runtime.py](modules/backend/pricing/embedding_runtime.py.md): 3 symbols.
- [backend/pricing/enrich_kg_quantity_guidance.py](modules/backend/pricing/enrich_kg_quantity_guidance.py.md): 3 symbols.
- [backend/pricing/flatten_bcca.py](modules/backend/pricing/flatten_bcca.py.md): 4 symbols.
- [backend/pricing/flatten_kg.py](modules/backend/pricing/flatten_kg.py.md): 8 symbols.
- [backend/pricing/gla_opinion.py](modules/backend/pricing/gla_opinion.py.md): 3 symbols.
- [backend/pricing/image_cache.py](modules/backend/pricing/image_cache.py.md): 18 symbols.
- [backend/pricing/measurement_catalog_v4.py](modules/backend/pricing/measurement_catalog_v4.py.md): 6 symbols.
- [backend/pricing/multi_phase_estimator_v1.py](modules/backend/pricing/multi_phase_estimator_v1.py.md): 36 symbols.
- [backend/pricing/phase_prompts_v1.py](modules/backend/pricing/phase_prompts_v1.py.md): 2 symbols.
- [backend/pricing/pir_generator.py](modules/backend/pricing/pir_generator.py.md): 18 symbols.
- [backend/pricing/quantity_formula_v4.py](modules/backend/pricing/quantity_formula_v4.py.md): 11 symbols.
- [backend/pricing/quantity_resolver.py](modules/backend/pricing/quantity_resolver.py.md): 6 symbols.
- [backend/pricing/room_inference.py](modules/backend/pricing/room_inference.py.md): 5 symbols.
- [backend/pricing/strategy_selector.py](modules/backend/pricing/strategy_selector.py.md): 3 symbols.
- [backend/pricing/takeoff_menu.py](modules/backend/pricing/takeoff_menu.py.md): 4 symbols.
- [backend/pricing/v2_boq_generator.py](modules/backend/pricing/v2_boq_generator.py.md): 29 symbols.
- [backend/pricing/v2_scheduler.py](modules/backend/pricing/v2_scheduler.py.md): 6 symbols.
- [backend/pricing/v3_boq_generator.py](modules/backend/pricing/v3_boq_generator.py.md): 3 symbols.
- [backend/pricing/v3_delta_scopes.py](modules/backend/pricing/v3_delta_scopes.py.md): 15 symbols.
- [backend/pricing/v4_quantification_pipeline.py](modules/backend/pricing/v4_quantification_pipeline.py.md): 66 symbols.
- [backend/pricing/v5_architect_report.py](modules/backend/pricing/v5_architect_report.py.md): 8 symbols.
- [backend/pricing/v5_comparable_selector.py](modules/backend/pricing/v5_comparable_selector.py.md): 6 symbols.
- [backend/pricing/v5_comparable_standard.py](modules/backend/pricing/v5_comparable_standard.py.md): 3 symbols.
- [backend/pricing/v5_eli5.py](modules/backend/pricing/v5_eli5.py.md): 1 symbols.
- [backend/pricing/v5_negotiation.py](modules/backend/pricing/v5_negotiation.py.md): 1 symbols.
- [backend/pricing/v5_pir.py](modules/backend/pricing/v5_pir.py.md): 3 symbols.
- [backend/pricing/v5_room_images.py](modules/backend/pricing/v5_room_images.py.md): 13 symbols.
- [backend/pricing/v5_room_tags.py](modules/backend/pricing/v5_room_tags.py.md): 1 symbols.
- [backend/pricing/v5_room_types.py](modules/backend/pricing/v5_room_types.py.md): 3 symbols.
- [backend/pricing/v5_run_market_standard.py](modules/backend/pricing/v5_run_market_standard.py.md): 5 symbols.
- [backend/pricing/v5_slots.py](modules/backend/pricing/v5_slots.py.md): 4 symbols.
- [backend/pricing/v5_strategy_delta_decompose.py](modules/backend/pricing/v5_strategy_delta_decompose.py.md): 14 symbols.
- [backend/pricing/v5_to_v4_adapter.py](modules/backend/pricing/v5_to_v4_adapter.py.md): 1 symbols.
- [backend/pricing/v5_work_items.py](modules/backend/pricing/v5_work_items.py.md): 3 symbols.
- [backend/pricing/worklist_validator.py](modules/backend/pricing/worklist_validator.py.md): 6 symbols.

## backend/pricing/prompts/gla

- [backend/pricing/prompts/gla/__init__.py](modules/backend/pricing/prompts/gla/__init__.py.md): 0 symbols.
- [backend/pricing/prompts/gla/opinion_room.py](modules/backend/pricing/prompts/gla/opinion_room.py.md): 1 symbols.

## backend/pricing/prompts/v5

- [backend/pricing/prompts/v5/__init__.py](modules/backend/pricing/prompts/v5/__init__.py.md): 0 symbols.
- [backend/pricing/prompts/v5/age_context.py](modules/backend/pricing/prompts/v5/age_context.py.md): 6 symbols.
- [backend/pricing/prompts/v5/comparable_selector.py](modules/backend/pricing/prompts/v5/comparable_selector.py.md): 1 symbols.
- [backend/pricing/prompts/v5/decompose_work_items.py](modules/backend/pricing/prompts/v5/decompose_work_items.py.md): 5 symbols.
- [backend/pricing/prompts/v5/delta_cross_room_review.py](modules/backend/pricing/prompts/v5/delta_cross_room_review.py.md): 2 symbols.
- [backend/pricing/prompts/v5/delta_slots.py](modules/backend/pricing/prompts/v5/delta_slots.py.md): 1 symbols.
- [backend/pricing/prompts/v5/pir_comparable_home.py](modules/backend/pricing/prompts/v5/pir_comparable_home.py.md): 1 symbols.
- [backend/pricing/prompts/v5/pir_target_room.py](modules/backend/pricing/prompts/v5/pir_target_room.py.md): 1 symbols.
- [backend/pricing/prompts/v5/strategy_targets.py](modules/backend/pricing/prompts/v5/strategy_targets.py.md): 1 symbols.

## backend/pricing/schemas

- [backend/pricing/schemas/__init__.py](modules/backend/pricing/schemas/__init__.py.md): 0 symbols.
- [backend/pricing/schemas/estimation_error.py](modules/backend/pricing/schemas/estimation_error.py.md): 19 symbols.
- [backend/pricing/schemas/gemini_schemas_v1.py](modules/backend/pricing/schemas/gemini_schemas_v1.py.md): 8 symbols.
- [backend/pricing/schemas/gemini_schemas_v2.py](modules/backend/pricing/schemas/gemini_schemas_v2.py.md): 1 symbols.
- [backend/pricing/schemas/gemini_schemas_v3.py](modules/backend/pricing/schemas/gemini_schemas_v3.py.md): 1 symbols.
- [backend/pricing/schemas/gemini_schemas_v4.py](modules/backend/pricing/schemas/gemini_schemas_v4.py.md): 2 symbols.
- [backend/pricing/schemas/gemini_schemas_v5.py](modules/backend/pricing/schemas/gemini_schemas_v5.py.md): 1 symbols.
- [backend/pricing/schemas/phase_outputs.py](modules/backend/pricing/schemas/phase_outputs.py.md): 21 symbols.
- [backend/pricing/schemas/unified_estimate.py](modules/backend/pricing/schemas/unified_estimate.py.md): 16 symbols.

## backend/pricing/scripts

- [backend/pricing/scripts/build_bcca_dimension_artifacts_v1.py](modules/backend/pricing/scripts/build_bcca_dimension_artifacts_v1.py.md): 7 symbols.
- [backend/pricing/scripts/build_bcca_embedding_index.py](modules/backend/pricing/scripts/build_bcca_embedding_index.py.md): 4 symbols.
- [backend/pricing/scripts/build_bcca_embedding_index_full.py](modules/backend/pricing/scripts/build_bcca_embedding_index_full.py.md): 4 symbols.

## backend/routes

- [backend/routes/__init__.py](modules/backend/routes/__init__.py.md): 0 symbols.
- [backend/routes/admin_routes.py](modules/backend/routes/admin_routes.py.md): 22 symbols.
- [backend/routes/building_context.py](modules/backend/routes/building_context.py.md): 4 symbols.
- [backend/routes/cs_chat.py](modules/backend/routes/cs_chat.py.md): 10 symbols.
- [backend/routes/curation_v2.py](modules/backend/routes/curation_v2.py.md): 20 symbols.
- [backend/routes/listings.py](modules/backend/routes/listings.py.md): 7 symbols.
- [backend/routes/meta_whatsapp.py](modules/backend/routes/meta_whatsapp.py.md): 15 symbols.
- [backend/routes/scrape.py](modules/backend/routes/scrape.py.md): 6 symbols.
- [backend/routes/story.py](modules/backend/routes/story.py.md): 7 symbols.
- [backend/routes/transcribe.py](modules/backend/routes/transcribe.py.md): 3 symbols.
- [backend/routes/translate.py](modules/backend/routes/translate.py.md): 11 symbols.
- [backend/routes/v2_routes.py](modules/backend/routes/v2_routes.py.md): 12 symbols.
- [backend/routes/v3_routes.py](modules/backend/routes/v3_routes.py.md): 9 symbols.
- [backend/routes/webhooks.py](modules/backend/routes/webhooks.py.md): 11 symbols.

## backend/scraper

- [backend/scraper/__init__.py](modules/backend/scraper/__init__.py.md): 0 symbols.
- [backend/scraper/address_resolver.py](modules/backend/scraper/address_resolver.py.md): 12 symbols.
- [backend/scraper/bot_detection.py](modules/backend/scraper/bot_detection.py.md): 7 symbols.
- [backend/scraper/description_formatter.py](modules/backend/scraper/description_formatter.py.md): 1 symbols.
- [backend/scraper/fetcher.py](modules/backend/scraper/fetcher.py.md): 8 symbols.
- [backend/scraper/geoapify_geocoder.py](modules/backend/scraper/geoapify_geocoder.py.md): 9 symbols.
- [backend/scraper/geocoder.py](modules/backend/scraper/geocoder.py.md): 7 symbols.
- [backend/scraper/location_intelligence.py](modules/backend/scraper/location_intelligence.py.md): 5 symbols.
- [backend/scraper/normalizer.py](modules/backend/scraper/normalizer.py.md): 6 symbols.
- [backend/scraper/router.py](modules/backend/scraper/router.py.md): 4 symbols.
- [backend/scraper/rules.py](modules/backend/scraper/rules.py.md): 5 symbols.

## backend/scraper/parsers

- [backend/scraper/parsers/__init__.py](modules/backend/scraper/parsers/__init__.py.md): 0 symbols.
- [backend/scraper/parsers/gemini_universal.py](modules/backend/scraper/parsers/gemini_universal.py.md): 5 symbols.
- [backend/scraper/parsers/idealista.py](modules/backend/scraper/parsers/idealista.py.md): 3 symbols.
- [backend/scraper/parsers/universal.py](modules/backend/scraper/parsers/universal.py.md): 2 symbols.
- [backend/scraper/parsers/url_validator.py](modules/backend/scraper/parsers/url_validator.py.md): 3 symbols.

## backend/scripts

- [backend/scripts/_md_report.py](modules/backend/scripts/_md_report.py.md): 1 symbols.
- [backend/scripts/audit_v4_matching_deterministic.py](modules/backend/scripts/audit_v4_matching_deterministic.py.md): 11 symbols.
- [backend/scripts/audit_v4_narrative_to_worklist.py](modules/backend/scripts/audit_v4_narrative_to_worklist.py.md): 6 symbols.
- [backend/scripts/build_bcca_whole_dwelling_denylist_v1.py](modules/backend/scripts/build_bcca_whole_dwelling_denylist_v1.py.md): 4 symbols.
- [backend/scripts/build_ffe_database.py](modules/backend/scripts/build_ffe_database.py.md): 6 symbols.
- [backend/scripts/capture_flipper_listing_screenshots.py](modules/backend/scripts/capture_flipper_listing_screenshots.py.md): 14 symbols.
- [backend/scripts/clear_listing_from_stage.py](modules/backend/scripts/clear_listing_from_stage.py.md): 4 symbols.
- [backend/scripts/clear_v4_artifacts.py](modules/backend/scripts/clear_v4_artifacts.py.md): 3 symbols.
- [backend/scripts/cost_optimization_test.py](modules/backend/scripts/cost_optimization_test.py.md): 9 symbols.
- [backend/scripts/crawl_atelier.py](modules/backend/scripts/crawl_atelier.py.md): 6 symbols.
- [backend/scripts/embed_glb_pir_viewer.py](modules/backend/scripts/embed_glb_pir_viewer.py.md): 5 symbols.
- [backend/scripts/enqueue_listing_12_run.py](modules/backend/scripts/enqueue_listing_12_run.py.md): 1 symbols.
- [backend/scripts/enqueue_v2_pipeline_run.py](modules/backend/scripts/enqueue_v2_pipeline_run.py.md): 2 symbols.
- [backend/scripts/export_bcca_index.py](modules/backend/scripts/export_bcca_index.py.md): 1 symbols.
- [backend/scripts/export_ffe_index.py](modules/backend/scripts/export_ffe_index.py.md): 1 symbols.
- [backend/scripts/export_v4_artifacts_md.py](modules/backend/scripts/export_v4_artifacts_md.py.md): 2 symbols.
- [backend/scripts/export_v4_postrich_analysis_md.py](modules/backend/scripts/export_v4_postrich_analysis_md.py.md): 6 symbols.
- [backend/scripts/extract_energy_knowledge.py](modules/backend/scripts/extract_energy_knowledge.py.md): 4 symbols.
- [backend/scripts/extract_interior_design_knowledge.py](modules/backend/scripts/extract_interior_design_knowledge.py.md): 7 symbols.
- [backend/scripts/extract_process_knowledge.py](modules/backend/scripts/extract_process_knowledge.py.md): 4 symbols.
- [backend/scripts/gate0_export_smart_m2_listing_12.py](modules/backend/scripts/gate0_export_smart_m2_listing_12.py.md): 9 symbols.
- [backend/scripts/gate0_export_smart_m2_panorama_single_room.py](modules/backend/scripts/gate0_export_smart_m2_panorama_single_room.py.md): 9 symbols.
- [backend/scripts/gate0_export_smart_m2_single_room.py](modules/backend/scripts/gate0_export_smart_m2_single_room.py.md): 8 symbols.
- [backend/scripts/gate0_export_smart_m2_three_rooms.py](modules/backend/scripts/gate0_export_smart_m2_three_rooms.py.md): 8 symbols.
- [backend/scripts/gemini_image_gen_smoke.py](modules/backend/scripts/gemini_image_gen_smoke.py.md): 2 symbols.
- [backend/scripts/gen_vinterior_render.py](modules/backend/scripts/gen_vinterior_render.py.md): 2 symbols.
- [backend/scripts/generate_bcca_full_index.py](modules/backend/scripts/generate_bcca_full_index.py.md): 4 symbols.
- [backend/scripts/glb_pir_builder.py](modules/backend/scripts/glb_pir_builder.py.md): 8 symbols.
- [backend/scripts/model_shootout.py](modules/backend/scripts/model_shootout.py.md): 3 symbols.
- [backend/scripts/paraphrase_bcca_descriptions.py](modules/backend/scripts/paraphrase_bcca_descriptions.py.md): 9 symbols.
- [backend/scripts/parse_ffe_research.py](modules/backend/scripts/parse_ffe_research.py.md): 7 symbols.
- [backend/scripts/pipeline_health.py](modules/backend/scripts/pipeline_health.py.md): 7 symbols.
- [backend/scripts/probe_glb_indoorgml_lite.py](modules/backend/scripts/probe_glb_indoorgml_lite.py.md): 7 symbols.
- [backend/scripts/qc_delta_bcca_worklist.py](modules/backend/scripts/qc_delta_bcca_worklist.py.md): 21 symbols.
- [backend/scripts/rasterscan_floorplan.py](modules/backend/scripts/rasterscan_floorplan.py.md): 1 symbols.
- [backend/scripts/renovation_report_smoke.py](modules/backend/scripts/renovation_report_smoke.py.md): 2 symbols.
- [backend/scripts/rerun_from_stage.py](modules/backend/scripts/rerun_from_stage.py.md): 3 symbols.
- [backend/scripts/rerun_v4_bcca_match_rich_and_compare.py](modules/backend/scripts/rerun_v4_bcca_match_rich_and_compare.py.md): 4 symbols.
- [backend/scripts/research_ffe_expansion.py](modules/backend/scripts/research_ffe_expansion.py.md): 2 symbols.
- [backend/scripts/run_v2_pipeline.py](modules/backend/scripts/run_v2_pipeline.py.md): 2 symbols.
- [backend/scripts/run_v4_all_strategies.py](modules/backend/scripts/run_v4_all_strategies.py.md): 9 symbols.
- [backend/scripts/run_v4_pricing_from_rich_matches.py](modules/backend/scripts/run_v4_pricing_from_rich_matches.py.md): 9 symbols.
- [backend/scripts/smoke_delta_bcca_worklist.py](modules/backend/scripts/smoke_delta_bcca_worklist.py.md): 7 symbols.
- [backend/scripts/smoke_v4_quantification.py](modules/backend/scripts/smoke_v4_quantification.py.md): 1 symbols.
- [backend/scripts/smoke_v4_tail_forage_only_from_v5_work_items.py](modules/backend/scripts/smoke_v4_tail_forage_only_from_v5_work_items.py.md): 7 symbols.
- [backend/scripts/smoke_v4_tail_match_only_from_v5_work_items.py](modules/backend/scripts/smoke_v4_tail_match_only_from_v5_work_items.py.md): 2 symbols.
- [backend/scripts/smoke_v4_tail_quant_plan_only_from_v5_work_items.py](modules/backend/scripts/smoke_v4_tail_quant_plan_only_from_v5_work_items.py.md): 3 symbols.
- [backend/scripts/smoke_v5_clustering.py](modules/backend/scripts/smoke_v5_clustering.py.md): 1 symbols.
- [backend/scripts/smoke_v5_comparable_pir_v5.py](modules/backend/scripts/smoke_v5_comparable_pir_v5.py.md): 1 symbols.
- [backend/scripts/smoke_v5_comparable_selector.py](modules/backend/scripts/smoke_v5_comparable_selector.py.md): 1 symbols.
- [backend/scripts/smoke_v5_comparables_snapshot.py](modules/backend/scripts/smoke_v5_comparables_snapshot.py.md): 1 symbols.
- [backend/scripts/smoke_v5_decompose_work_items.py](modules/backend/scripts/smoke_v5_decompose_work_items.py.md): 1 symbols.
- [backend/scripts/smoke_v5_delta_slots.py](modules/backend/scripts/smoke_v5_delta_slots.py.md): 1 symbols.
- [backend/scripts/smoke_v5_eli5.py](modules/backend/scripts/smoke_v5_eli5.py.md): 1 symbols.
- [backend/scripts/smoke_v5_listing_snapshot.py](modules/backend/scripts/smoke_v5_listing_snapshot.py.md): 1 symbols.
- [backend/scripts/smoke_v5_pir_target_slots.py](modules/backend/scripts/smoke_v5_pir_target_slots.py.md): 2 symbols.
- [backend/scripts/smoke_v5_room_images.py](modules/backend/scripts/smoke_v5_room_images.py.md): 1 symbols.
- [backend/scripts/smoke_v5_room_tags.py](modules/backend/scripts/smoke_v5_room_tags.py.md): 1 symbols.
- [backend/scripts/smoke_v5_strategy_targets.py](modules/backend/scripts/smoke_v5_strategy_targets.py.md): 1 symbols.
- [backend/scripts/smoke_v5_to_v4_tail.py](modules/backend/scripts/smoke_v5_to_v4_tail.py.md): 1 symbols.
- [backend/scripts/smoke_v5_work_items_to_v4_tail.py](modules/backend/scripts/smoke_v5_work_items_to_v4_tail.py.md): 1 symbols.
- [backend/scripts/test_houzz.py](modules/backend/scripts/test_houzz.py.md): 1 symbols.
- [backend/scripts/try_houzz_quote_submission.py](modules/backend/scripts/try_houzz_quote_submission.py.md): 19 symbols.
- [backend/scripts/validate_pipeline_listing.py](modules/backend/scripts/validate_pipeline_listing.py.md): 18 symbols.

## backend/services

- [backend/services/__init__.py](modules/backend/services/__init__.py.md): 0 symbols.
- [backend/services/curation_service.py](modules/backend/services/curation_service.py.md): 27 symbols.
- [backend/services/tour_executor.py](modules/backend/services/tour_executor.py.md): 24 symbols.
- [backend/services/tour_generator.py](modules/backend/services/tour_generator.py.md): 10 symbols.
- [backend/services/tour_generator_legacy.py](modules/backend/services/tour_generator_legacy.py.md): 35 symbols.
- [backend/services/translation_service.py](modules/backend/services/translation_service.py.md): 8 symbols.

## backend/tests

- [backend/tests/test_smoke.py](modules/backend/tests/test_smoke.py.md): 1 symbols.

## backend/tools

- [backend/tools/__init__.py](modules/backend/tools/__init__.py.md): 0 symbols.
- [backend/tools/leo_call_transcriber.py](modules/backend/tools/leo_call_transcriber.py.md): 15 symbols.
- [backend/tools/leo_conference_call.py](modules/backend/tools/leo_conference_call.py.md): 10 symbols.
- [backend/tools/leo_email_proxy.py](modules/backend/tools/leo_email_proxy.py.md): 8 symbols.
- [backend/tools/leo_webhook_handler.py](modules/backend/tools/leo_webhook_handler.py.md): 10 symbols.

## backend/utils

- [backend/utils/__init__.py](modules/backend/utils/__init__.py.md): 0 symbols.
- [backend/utils/google_search.py](modules/backend/utils/google_search.py.md): 11 symbols.

## backend/whatsapp

- [backend/whatsapp/__init__.py](modules/backend/whatsapp/__init__.py.md): 0 symbols.
- [backend/whatsapp/agent.py](modules/backend/whatsapp/agent.py.md): 31 symbols.
- [backend/whatsapp/formatter.py](modules/backend/whatsapp/formatter.py.md): 3 symbols.
- [backend/whatsapp/media.py](modules/backend/whatsapp/media.py.md): 7 symbols.
- [backend/whatsapp/message_queue.py](modules/backend/whatsapp/message_queue.py.md): 25 symbols.
- [backend/whatsapp/tools.py](modules/backend/whatsapp/tools.py.md): 35 symbols.
- [backend/whatsapp/twilio_client.py](modules/backend/whatsapp/twilio_client.py.md): 8 symbols.

## backend/workers

- [backend/workers/__init__.py](modules/backend/workers/__init__.py.md): 0 symbols.
- [backend/workers/handlers.py](modules/backend/workers/handlers.py.md): 73 symbols.
- [backend/workers/pipeline_worker.py](modules/backend/workers/pipeline_worker.py.md): 18 symbols.

## frontend/src

- [frontend/src/proxy.ts](modules/frontend/src/proxy.ts.md): 2 symbols.

## frontend/src/app

- [frontend/src/app/layout.tsx](modules/frontend/src/app/layout.tsx.md): 4 symbols.
- [frontend/src/app/providers.tsx](modules/frontend/src/app/providers.tsx.md): 1 symbols.
- [frontend/src/app/sitemap.ts](modules/frontend/src/app/sitemap.ts.md): 3 symbols.

## frontend/src/app/admin

- [frontend/src/app/admin/gla-detail.tsx](modules/frontend/src/app/admin/gla-detail.tsx.md): 46 symbols.
- [frontend/src/app/admin/page.tsx](modules/frontend/src/app/admin/page.tsx.md): 155 symbols.

## frontend/src/app/api/admin/listings

- [frontend/src/app/api/admin/listings/route.ts](modules/frontend/src/app/api/admin/listings/route.ts.md): 7 symbols.

## frontend/src/app/api/admin/listings/[id]

- [frontend/src/app/api/admin/listings/[id]/route.ts](modules/frontend/src/app/api/admin/listings/[id]/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/listings/[id]/clear-from-stage

- [frontend/src/app/api/admin/listings/[id]/clear-from-stage/route.ts](modules/frontend/src/app/api/admin/listings/[id]/clear-from-stage/route.ts.md): 7 symbols.

## frontend/src/app/api/admin/listings/[id]/comparables

- [frontend/src/app/api/admin/listings/[id]/comparables/route.ts](modules/frontend/src/app/api/admin/listings/[id]/comparables/route.ts.md): 13 symbols.

## frontend/src/app/api/admin/listings/[id]/delete

- [frontend/src/app/api/admin/listings/[id]/delete/route.ts](modules/frontend/src/app/api/admin/listings/[id]/delete/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/listings/[id]/gla-detail

- [frontend/src/app/api/admin/listings/[id]/gla-detail/route.ts](modules/frontend/src/app/api/admin/listings/[id]/gla-detail/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/listings/[id]/resume

- [frontend/src/app/api/admin/listings/[id]/resume/route.ts](modules/frontend/src/app/api/admin/listings/[id]/resume/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/listings/[id]/stop

- [frontend/src/app/api/admin/listings/[id]/stop/route.ts](modules/frontend/src/app/api/admin/listings/[id]/stop/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/pipeline-version

- [frontend/src/app/api/admin/pipeline-version/route.ts](modules/frontend/src/app/api/admin/pipeline-version/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/resume-all

- [frontend/src/app/api/admin/resume-all/route.ts](modules/frontend/src/app/api/admin/resume-all/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/runs

- [frontend/src/app/api/admin/runs/route.ts](modules/frontend/src/app/api/admin/runs/route.ts.md): 11 symbols.

## frontend/src/app/api/admin/runs/[runId]

- [frontend/src/app/api/admin/runs/[runId]/route.ts](modules/frontend/src/app/api/admin/runs/[runId]/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/runs/[runId]/costs

- [frontend/src/app/api/admin/runs/[runId]/costs/route.ts](modules/frontend/src/app/api/admin/runs/[runId]/costs/route.ts.md): 6 symbols.

## frontend/src/app/api/admin/runs/[runId]/logs

- [frontend/src/app/api/admin/runs/[runId]/logs/route.ts](modules/frontend/src/app/api/admin/runs/[runId]/logs/route.ts.md): 13 symbols.

## frontend/src/app/api/admin/stop-all

- [frontend/src/app/api/admin/stop-all/route.ts](modules/frontend/src/app/api/admin/stop-all/route.ts.md): 6 symbols.

## frontend/src/app/api/listings

- [frontend/src/app/api/listings/route.ts](modules/frontend/src/app/api/listings/route.ts.md): 14 symbols.

## frontend/src/app/api/listings/[id]

- [frontend/src/app/api/listings/[id]/route.ts](modules/frontend/src/app/api/listings/[id]/route.ts.md): 20 symbols.

## frontend/src/app/api/listings/[id]/comparables

- [frontend/src/app/api/listings/[id]/comparables/route.ts](modules/frontend/src/app/api/listings/[id]/comparables/route.ts.md): 24 symbols.

## frontend/src/app/api/listings/[id]/negotiation

- [frontend/src/app/api/listings/[id]/negotiation/route.ts](modules/frontend/src/app/api/listings/[id]/negotiation/route.ts.md): 16 symbols.

## frontend/src/app/api/listings/[id]/photo-clusters

- [frontend/src/app/api/listings/[id]/photo-clusters/route.ts](modules/frontend/src/app/api/listings/[id]/photo-clusters/route.ts.md): 8 symbols.

## frontend/src/app/api/listings/[id]/photos

- [frontend/src/app/api/listings/[id]/photos/route.ts](modules/frontend/src/app/api/listings/[id]/photos/route.ts.md): 8 symbols.

## frontend/src/app/api/listings/[id]/room-analyses

- [frontend/src/app/api/listings/[id]/room-analyses/route.ts](modules/frontend/src/app/api/listings/[id]/room-analyses/route.ts.md): 8 symbols.

## frontend/src/app/api/listings/[id]/run-pipeline

- [frontend/src/app/api/listings/[id]/run-pipeline/route.ts](modules/frontend/src/app/api/listings/[id]/run-pipeline/route.ts.md): 7 symbols.

## frontend/src/app/api/listings/[id]/translations

- [frontend/src/app/api/listings/[id]/translations/route.ts](modules/frontend/src/app/api/listings/[id]/translations/route.ts.md): 15 symbols.

## frontend/src/app/api/renovation/[id]/comparables/brackets

- [frontend/src/app/api/renovation/[id]/comparables/brackets/route.ts](modules/frontend/src/app/api/renovation/[id]/comparables/brackets/route.ts.md): 11 symbols.

## frontend/src/app/api/renovation/[id]/v048/packages

- [frontend/src/app/api/renovation/[id]/v048/packages/route.ts](modules/frontend/src/app/api/renovation/[id]/v048/packages/route.ts.md): 16 symbols.

## frontend/src/app/api/renovation/[id]/v048/status

- [frontend/src/app/api/renovation/[id]/v048/status/route.ts](modules/frontend/src/app/api/renovation/[id]/v048/status/route.ts.md): 8 symbols.

## frontend/src/app/api/scrape

- [frontend/src/app/api/scrape/route.ts](modules/frontend/src/app/api/scrape/route.ts.md): 9 symbols.

## frontend/src/app/api/scrape/validate

- [frontend/src/app/api/scrape/validate/route.ts](modules/frontend/src/app/api/scrape/validate/route.ts.md): 6 symbols.

## frontend/src/app/api/translate/batch

- [frontend/src/app/api/translate/batch/route.ts](modules/frontend/src/app/api/translate/batch/route.ts.md): 6 symbols.

## frontend/src/app/api/translate/languages

- [frontend/src/app/api/translate/languages/route.ts](modules/frontend/src/app/api/translate/languages/route.ts.md): 5 symbols.

## frontend/src/app/api/translate/listing

- [frontend/src/app/api/translate/listing/route.ts](modules/frontend/src/app/api/translate/listing/route.ts.md): 6 symbols.

## frontend/src/app/api/translate/text

- [frontend/src/app/api/translate/text/route.ts](modules/frontend/src/app/api/translate/text/route.ts.md): 6 symbols.

## frontend/src/app/confirm

- [frontend/src/app/confirm/page.tsx](modules/frontend/src/app/confirm/page.tsx.md): 13 symbols.

## frontend/src/app/first-estimate

- [frontend/src/app/first-estimate/page.tsx](modules/frontend/src/app/first-estimate/page.tsx.md): 3 symbols.

## frontend/src/app/listing/[id]

- [frontend/src/app/listing/[id]/layout.tsx](modules/frontend/src/app/listing/[id]/layout.tsx.md): 18 symbols.
- [frontend/src/app/listing/[id]/opengraph-image.tsx](modules/frontend/src/app/listing/[id]/opengraph-image.tsx.md): 38 symbols.
- [frontend/src/app/listing/[id]/page.tsx](modules/frontend/src/app/listing/[id]/page.tsx.md): 14 symbols.

## frontend/src/app/listings

- [frontend/src/app/listings/page.tsx](modules/frontend/src/app/listings/page.tsx.md): 22 symbols.

## frontend/src/app/run-status

- [frontend/src/app/run-status/page.tsx](modules/frontend/src/app/run-status/page.tsx.md): 1 symbols.

## frontend/src/components

- [frontend/src/components/BeforeAfter.tsx](modules/frontend/src/components/BeforeAfter.tsx.md): 18 symbols.
- [frontend/src/components/BottomNav.tsx](modules/frontend/src/components/BottomNav.tsx.md): 6 symbols.
- [frontend/src/components/LanguageToggle.tsx](modules/frontend/src/components/LanguageToggle.tsx.md): 8 symbols.
- [frontend/src/components/ListingBottomNav.tsx](modules/frontend/src/components/ListingBottomNav.tsx.md): 9 symbols.
- [frontend/src/components/ListingReview.tsx](modules/frontend/src/components/ListingReview.tsx.md): 18 symbols.
- [frontend/src/components/ListingReviewMode.tsx](modules/frontend/src/components/ListingReviewMode.tsx.md): 53 symbols.
- [frontend/src/components/MapModal.tsx](modules/frontend/src/components/MapModal.tsx.md): 15 symbols.
- [frontend/src/components/PasteLinkModal.tsx](modules/frontend/src/components/PasteLinkModal.tsx.md): 31 symbols.
- [frontend/src/components/PlaceCard.tsx](modules/frontend/src/components/PlaceCard.tsx.md): 15 symbols.
- [frontend/src/components/PropertyCard.tsx](modules/frontend/src/components/PropertyCard.tsx.md): 7 symbols.
- [frontend/src/components/UrlInput.tsx](modules/frontend/src/components/UrlInput.tsx.md): 14 symbols.
- [frontend/src/components/index.ts](modules/frontend/src/components/index.ts.md): 0 symbols.

## frontend/src/components/agent

- [frontend/src/components/agent/CompletionSummary.tsx](modules/frontend/src/components/agent/CompletionSummary.tsx.md): 4 symbols.
- [frontend/src/components/agent/ContactCard.tsx](modules/frontend/src/components/agent/ContactCard.tsx.md): 10 symbols.
- [frontend/src/components/agent/DocumentCards.tsx](modules/frontend/src/components/agent/DocumentCards.tsx.md): 4 symbols.
- [frontend/src/components/agent/FileDropZone.tsx](modules/frontend/src/components/agent/FileDropZone.tsx.md): 17 symbols.
- [frontend/src/components/agent/InteractiveFloorPlan.tsx](modules/frontend/src/components/agent/InteractiveFloorPlan.tsx.md): 14 symbols.
- [frontend/src/components/agent/InventoryList.tsx](modules/frontend/src/components/agent/InventoryList.tsx.md): 7 symbols.
- [frontend/src/components/agent/PhotoClusterGrid.tsx](modules/frontend/src/components/agent/PhotoClusterGrid.tsx.md): 6 symbols.
- [frontend/src/components/agent/PropertySummaryCard.tsx](modules/frontend/src/components/agent/PropertySummaryCard.tsx.md): 5 symbols.

## frontend/src/components/buyer-intelligence

- [frontend/src/components/buyer-intelligence/ComplexitySlider.tsx](modules/frontend/src/components/buyer-intelligence/ComplexitySlider.tsx.md): 7 symbols.
- [frontend/src/components/buyer-intelligence/ReferencesOverlay.tsx](modules/frontend/src/components/buyer-intelligence/ReferencesOverlay.tsx.md): 17 symbols.

## frontend/src/components/landing

- [frontend/src/components/landing/AgentContent.tsx](modules/frontend/src/components/landing/AgentContent.tsx.md): 1 symbols.
- [frontend/src/components/landing/BuyerAgentsContent.tsx](modules/frontend/src/components/landing/BuyerAgentsContent.tsx.md): 2 symbols.
- [frontend/src/components/landing/BuyersContent.tsx](modules/frontend/src/components/landing/BuyersContent.tsx.md): 3 symbols.
- [frontend/src/components/landing/HomebuyerContent.tsx](modules/frontend/src/components/landing/HomebuyerContent.tsx.md): 1 symbols.
- [frontend/src/components/landing/RelocationContent.tsx](modules/frontend/src/components/landing/RelocationContent.tsx.md): 2 symbols.
- [frontend/src/components/landing/RentersContent.tsx](modules/frontend/src/components/landing/RentersContent.tsx.md): 3 symbols.
- [frontend/src/components/landing/content-data.ts](modules/frontend/src/components/landing/content-data.ts.md): 6 symbols.
- [frontend/src/components/landing/phone-mockups.tsx](modules/frontend/src/components/landing/phone-mockups.tsx.md): 17 symbols.

## frontend/src/components/landing/illustrations

- [frontend/src/components/landing/illustrations/AgentVignettes.tsx](modules/frontend/src/components/landing/illustrations/AgentVignettes.tsx.md): 18 symbols.
- [frontend/src/components/landing/illustrations/BuyersVignettes.tsx](modules/frontend/src/components/landing/illustrations/BuyersVignettes.tsx.md): 13 symbols.
- [frontend/src/components/landing/illustrations/ChecklistVisuals.tsx](modules/frontend/src/components/landing/illustrations/ChecklistVisuals.tsx.md): 12 symbols.
- [frontend/src/components/landing/illustrations/ClientPortalMockup.tsx](modules/frontend/src/components/landing/illustrations/ClientPortalMockup.tsx.md): 7 symbols.
- [frontend/src/components/landing/illustrations/CompactVignettes.tsx](modules/frontend/src/components/landing/illustrations/CompactVignettes.tsx.md): 13 symbols.
- [frontend/src/components/landing/illustrations/HeroVisuals.tsx](modules/frontend/src/components/landing/illustrations/HeroVisuals.tsx.md): 9 symbols.
- [frontend/src/components/landing/illustrations/Isochrones.tsx](modules/frontend/src/components/landing/illustrations/Isochrones.tsx.md): 10 symbols.
- [frontend/src/components/landing/illustrations/LandingImages.tsx](modules/frontend/src/components/landing/illustrations/LandingImages.tsx.md): 18 symbols.
- [frontend/src/components/landing/illustrations/LifeStagesVisual.tsx](modules/frontend/src/components/landing/illustrations/LifeStagesVisual.tsx.md): 10 symbols.
- [frontend/src/components/landing/illustrations/MarketingMockups.tsx](modules/frontend/src/components/landing/illustrations/MarketingMockups.tsx.md): 24 symbols.
- [frontend/src/components/landing/illustrations/MicroMockups.tsx](modules/frontend/src/components/landing/illustrations/MicroMockups.tsx.md): 19 symbols.
- [frontend/src/components/landing/illustrations/RelocationVignettes.tsx](modules/frontend/src/components/landing/illustrations/RelocationVignettes.tsx.md): 12 symbols.
- [frontend/src/components/landing/illustrations/RenovationTiersMockup.tsx](modules/frontend/src/components/landing/illustrations/RenovationTiersMockup.tsx.md): 24 symbols.
- [frontend/src/components/landing/illustrations/index.ts](modules/frontend/src/components/landing/illustrations/index.ts.md): 0 symbols.

## frontend/src/components/landing/sections

- [frontend/src/components/landing/sections/HowItWorks.tsx](modules/frontend/src/components/landing/sections/HowItWorks.tsx.md): 4 symbols.
- [frontend/src/components/landing/sections/RentersHowItWorks.tsx](modules/frontend/src/components/landing/sections/RentersHowItWorks.tsx.md): 4 symbols.
- [frontend/src/components/landing/sections/SectionBenefits.tsx](modules/frontend/src/components/landing/sections/SectionBenefits.tsx.md): 3 symbols.
- [frontend/src/components/landing/sections/SectionCTA.tsx](modules/frontend/src/components/landing/sections/SectionCTA.tsx.md): 2 symbols.
- [frontend/src/components/landing/sections/SectionCallout.tsx](modules/frontend/src/components/landing/sections/SectionCallout.tsx.md): 2 symbols.
- [frontend/src/components/landing/sections/SectionChecklist.tsx](modules/frontend/src/components/landing/sections/SectionChecklist.tsx.md): 7 symbols.
- [frontend/src/components/landing/sections/SectionFeatureCard.tsx](modules/frontend/src/components/landing/sections/SectionFeatureCard.tsx.md): 2 symbols.
- [frontend/src/components/landing/sections/SectionHero.tsx](modules/frontend/src/components/landing/sections/SectionHero.tsx.md): 5 symbols.
- [frontend/src/components/landing/sections/SectionHowItWorks.tsx](modules/frontend/src/components/landing/sections/SectionHowItWorks.tsx.md): 4 symbols.
- [frontend/src/components/landing/sections/SectionTestimonials.tsx](modules/frontend/src/components/landing/sections/SectionTestimonials.tsx.md): 2 symbols.
- [frontend/src/components/landing/sections/index.ts](modules/frontend/src/components/landing/sections/index.ts.md): 0 symbols.

## frontend/src/components/landing/waveform

- [frontend/src/components/landing/waveform/VoiceWaveform.tsx](modules/frontend/src/components/landing/waveform/VoiceWaveform.tsx.md): 2 symbols.

## frontend/src/components/renovation

- [frontend/src/components/renovation/BeforeAfterSlider.tsx](modules/frontend/src/components/renovation/BeforeAfterSlider.tsx.md): 22 symbols.
- [frontend/src/components/renovation/BracketAnalysisModal.tsx](modules/frontend/src/components/renovation/BracketAnalysisModal.tsx.md): 60 symbols.
- [frontend/src/components/renovation/ComparableCard.tsx](modules/frontend/src/components/renovation/ComparableCard.tsx.md): 43 symbols.
- [frontend/src/components/renovation/ComparableDetailModal.tsx](modules/frontend/src/components/renovation/ComparableDetailModal.tsx.md): 20 symbols.
- [frontend/src/components/renovation/ComparablesCard.tsx](modules/frontend/src/components/renovation/ComparablesCard.tsx.md): 114 symbols.
- [frontend/src/components/renovation/ComparablesMap.tsx](modules/frontend/src/components/renovation/ComparablesMap.tsx.md): 72 symbols.
- [frontend/src/components/renovation/ComparablesTab.tsx](modules/frontend/src/components/renovation/ComparablesTab.tsx.md): 18 symbols.
- [frontend/src/components/renovation/NegotiationModal.tsx](modules/frontend/src/components/renovation/NegotiationModal.tsx.md): 69 symbols.
- [frontend/src/components/renovation/OfficialBudgetReport.tsx](modules/frontend/src/components/renovation/OfficialBudgetReport.tsx.md): 49 symbols.
- [frontend/src/components/renovation/ShareModal.tsx](modules/frontend/src/components/renovation/ShareModal.tsx.md): 72 symbols.
- [frontend/src/components/renovation/index.ts](modules/frontend/src/components/renovation/index.ts.md): 0 symbols.

## frontend/src/components/shared

- [frontend/src/components/shared/ActionCard.tsx](modules/frontend/src/components/shared/ActionCard.tsx.md): 2 symbols.
- [frontend/src/components/shared/BubbleTail.tsx](modules/frontend/src/components/shared/BubbleTail.tsx.md): 2 symbols.
- [frontend/src/components/shared/ChatBubble.tsx](modules/frontend/src/components/shared/ChatBubble.tsx.md): 7 symbols.
- [frontend/src/components/shared/ChatInputBar.tsx](modules/frontend/src/components/shared/ChatInputBar.tsx.md): 12 symbols.
- [frontend/src/components/shared/ChatWallpaper.tsx](modules/frontend/src/components/shared/ChatWallpaper.tsx.md): 5 symbols.
- [frontend/src/components/shared/CitationsBlock.tsx](modules/frontend/src/components/shared/CitationsBlock.tsx.md): 3 symbols.
- [frontend/src/components/shared/ConfirmedBadge.tsx](modules/frontend/src/components/shared/ConfirmedBadge.tsx.md): 2 symbols.
- [frontend/src/components/shared/DateSeparator.tsx](modules/frontend/src/components/shared/DateSeparator.tsx.md): 7 symbols.
- [frontend/src/components/shared/FilesGizmo.tsx](modules/frontend/src/components/shared/FilesGizmo.tsx.md): 3 symbols.
- [frontend/src/components/shared/SuggestedResponseCard.tsx](modules/frontend/src/components/shared/SuggestedResponseCard.tsx.md): 3 symbols.
- [frontend/src/components/shared/ThoughtIndicator.tsx](modules/frontend/src/components/shared/ThoughtIndicator.tsx.md): 3 symbols.
- [frontend/src/components/shared/ToolTrailCollapsible.tsx](modules/frontend/src/components/shared/ToolTrailCollapsible.tsx.md): 14 symbols.

## frontend/src/components/ui

- [frontend/src/components/ui/badge.tsx](modules/frontend/src/components/ui/badge.tsx.md): 3 symbols.
- [frontend/src/components/ui/button.tsx](modules/frontend/src/components/ui/button.tsx.md): 4 symbols.
- [frontend/src/components/ui/card.tsx](modules/frontend/src/components/ui/card.tsx.md): 6 symbols.

## frontend/src/contexts

- [frontend/src/contexts/DictionaryContext.tsx](modules/frontend/src/contexts/DictionaryContext.tsx.md): 5 symbols.

## frontend/src/hooks

- [frontend/src/hooks/AppStringsContext.tsx](modules/frontend/src/hooks/AppStringsContext.tsx.md): 18 symbols.
- [frontend/src/hooks/useTranslation.ts](modules/frontend/src/hooks/useTranslation.ts.md): 46 symbols.

## frontend/src/lib

- [frontend/src/lib/api.ts](modules/frontend/src/lib/api.ts.md): 34 symbols.
- [frontend/src/lib/i18n.ts](modules/frontend/src/lib/i18n.ts.md): 10 symbols.
- [frontend/src/lib/types.ts](modules/frontend/src/lib/types.ts.md): 30 symbols.
- [frontend/src/lib/utils.ts](modules/frontend/src/lib/utils.ts.md): 10 symbols.

## frontend/src/lib/agent

- [frontend/src/lib/agent/chat-engine.ts](modules/frontend/src/lib/agent/chat-engine.ts.md): 10 symbols.
- [frontend/src/lib/agent/mock-data.ts](modules/frontend/src/lib/agent/mock-data.ts.md): 9 symbols.
- [frontend/src/lib/agent/types.ts](modules/frontend/src/lib/agent/types.ts.md): 24 symbols.

## frontend/src/lib/i18n

- [frontend/src/lib/i18n/index.tsx](modules/frontend/src/lib/i18n/index.tsx.md): 14 symbols.

## frontend/src/lib/shared

- [frontend/src/lib/shared/colors.ts](modules/frontend/src/lib/shared/colors.ts.md): 4 symbols.

## frontend/src/types

- [frontend/src/types/renovation-v2.ts](modules/frontend/src/types/renovation-v2.ts.md): 25 symbols.
- [frontend/src/types/renovation.ts](modules/frontend/src/types/renovation.ts.md): 7 symbols.

## tools

- [tools/export-first-result.py](modules/tools/export-first-result.py.md): 1 symbols.
- [tools/first-estimate.py](modules/tools/first-estimate.py.md): 12 symbols.
- [tools/link-gate.py](modules/tools/link-gate.py.md): 3 symbols.
- [tools/runtime-env.py](modules/tools/runtime-env.py.md): 6 symbols.
- [tools/source-reference.py](modules/tools/source-reference.py.md): 4 symbols.
