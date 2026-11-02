-- The native frontend talks to the FastAPI server. Its database is service-only.
-- Apply these grants within the same fresh-install transaction as the retained DDL.
DO $security$
DECLARE
  item record;
BEGIN
  FOR item IN SELECT tablename FROM pg_tables WHERE schemaname='public'
    AND NOT EXISTS (SELECT 1 FROM pg_depend d
      WHERE d.classid='pg_class'::regclass AND d.objid = format('public.%I',tablename)::regclass AND d.deptype='e')
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',item.tablename);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC,anon,authenticated',item.tablename);
    EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role',item.tablename);
  END LOOP;
END;
$security$;
-- Retained SECURITY DEFINER RPCs are callable only by the trusted backend.
DO $objects$
DECLARE item record;
BEGIN
  FOR item IN SELECT p.oid::regprocedure AS signature FROM pg_proc p
    JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
    AND NOT EXISTS(SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e') LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,anon,authenticated',item.signature);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role',item.signature);
  END LOOP;
  FOR item IN SELECT c.oid::regclass AS name FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='S'
    AND NOT EXISTS(SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype='e') LOOP
    EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM PUBLIC,anon,authenticated',item.name);
    EXECUTE format('GRANT ALL ON SEQUENCE %s TO service_role',item.name);
  END LOOP;
END;
$objects$;
REVOKE ALL ON public.gemini_run_costs_v1 FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.gemini_run_costs_v1 TO service_role;
