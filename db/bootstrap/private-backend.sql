-- The native frontend talks to the FastAPI server. Its database is service-only.
-- Apply these grants within the same fresh-install transaction as the retained DDL.
DO $security$
DECLARE
  item record;
BEGIN
  FOR item IN SELECT tablename FROM pg_tables WHERE schemaname='public'
    AND NOT EXISTS (SELECT 1 FROM pg_depend d
      WHERE d.objid = format('public.%I',tablename)::regclass AND d.deptype='e')
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',item.tablename);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC,anon,authenticated',item.tablename);
    EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role',item.tablename);
  END LOOP;
END;
$security$;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC,anon,authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
-- Retained SECURITY DEFINER RPCs are callable only by the trusted backend.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
REVOKE ALL ON public.gemini_run_costs_v1 FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.gemini_run_costs_v1 TO service_role;
