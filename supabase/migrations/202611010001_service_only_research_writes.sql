-- Keep the original shared-read contracts; scope backend writes to their role.
BEGIN;
DO $hardening$
DECLARE
  target text;
  policy_name text;
BEGIN
  IF to_regclass('public.due_diligence_research') IS NOT NULL THEN
    DROP POLICY IF EXISTS "Allow all access to due_diligence_research" ON public.due_diligence_research;
    DROP POLICY IF EXISTS "Recipient service manages due diligence" ON public.due_diligence_research;
    CREATE POLICY "Recipient service manages due diligence" ON public.due_diligence_research
      FOR ALL TO service_role USING (true) WITH CHECK (true);
    REVOKE ALL ON TABLE public.due_diligence_research FROM anon, authenticated;
  END IF;
  FOREACH target IN ARRAY ARRAY['listing_market_stats','listing_comparables','listing_bracket_analyses'] LOOP
    IF to_regclass(format('public.%I', target)) IS NOT NULL THEN
      policy_name := 'Allow service role full access to ' || target;
      EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', policy_name, target);
      EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', policy_name, target);
      -- The distinct public SELECT policies in 009 are intentionally retained.
      EXECUTE format('REVOKE INSERT, UPDATE, DELETE ON TABLE public.%I FROM anon, authenticated', target);
    END IF;
  END LOOP;
  FOREACH target IN ARRAY ARRAY['property_intelligence_reports','comparative_gap_analyses','aggregated_gap_analyses'] LOOP
    IF to_regclass(format('public.%I', target)) IS NOT NULL THEN
      FOR policy_name IN SELECT policyname FROM pg_policies
        WHERE schemaname='public' AND tablename=target
          AND policyname IN ('Allow service insert','Allow service update') LOOP
        EXECUTE format('ALTER POLICY %I ON public.%I TO service_role', policy_name, target);
      END LOOP;
      IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=target AND policyname='Allow read access') THEN
        -- Original schema comments specify authenticated shared reads.
        EXECUTE format('ALTER POLICY %I ON public.%I TO authenticated', 'Allow read access', target);
      END IF;
      EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon', target);
      EXECUTE format('REVOKE INSERT, UPDATE, DELETE ON TABLE public.%I FROM authenticated', target);
    END IF;
  END LOOP;
END
$hardening$;
COMMIT;
