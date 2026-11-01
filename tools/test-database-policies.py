"""Execute retained-policy regression against a task-owned isolated Postgres."""
from pathlib import Path
import subprocess,time,json,uuid
ROOT=Path(__file__).resolve().parents[1];name='atelier-rls-audit-'+uuid.uuid4().hex[:8]
subprocess.run(['docker','run','--detach','--rm','--name',name,'--network','none','--memory','256m','--cpus','1','--pids-limit','128','-e','POSTGRES_HOST_AUTH_METHOD=trust','--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=192m','--tmpfs','/var/run/postgresql:rw,noexec,nosuid,size=16m','postgres:16-alpine'],check=True,stdout=subprocess.DEVNULL)
def sql(text,ok=True):
 p=subprocess.run(['docker','exec','-i',name,'psql','-X','-U','postgres','-v','ON_ERROR_STOP=1','-qAt'],input=text,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if ok and p.returncode:raise AssertionError(p.stderr)
 if not ok and not p.returncode:raise AssertionError('Expected database denial')
 return p.stdout.strip(),p.stderr
try:
 for _ in range(100):
  if 'PostgreSQL init process complete' in subprocess.check_output(['docker','logs',name],text=True,stderr=subprocess.STDOUT) and subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(.1)
 else:raise AssertionError('Isolated Postgres failed startup')
 sql('''CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
 CREATE SCHEMA auth; GRANT USAGE ON SCHEMA auth TO anon,authenticated,service_role;
 CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE SQL STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
''')
 sql('''CREATE TABLE public.due_diligence_research(id int);ALTER TABLE public.due_diligence_research ENABLE ROW LEVEL SECURITY;GRANT ALL ON public.due_diligence_research TO anon,authenticated,service_role;CREATE POLICY "Allow all access to due_diligence_research" ON public.due_diligence_research FOR ALL USING(true)WITH CHECK(true);''')
 for table in ['listing_market_stats','listing_comparables','listing_bracket_analyses']:
  sql(f'''CREATE TABLE public.{table}(id int);ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;GRANT ALL ON public.{table} TO anon,authenticated,service_role;CREATE POLICY "Allow public read for {table}" ON public.{table} FOR SELECT USING(true);CREATE POLICY "Allow service role full access to {table}" ON public.{table} FOR ALL USING(true);INSERT INTO public.{table} VALUES(1);''')
 for table in ['property_intelligence_reports','comparative_gap_analyses','aggregated_gap_analyses']:
  sql(f'''CREATE TABLE public.{table}(id int);ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;GRANT ALL ON public.{table} TO anon,authenticated,service_role;CREATE POLICY "Allow read access" ON public.{table} FOR SELECT USING(true);CREATE POLICY "Allow service insert" ON public.{table} FOR INSERT WITH CHECK(true);CREATE POLICY "Allow service update" ON public.{table} FOR UPDATE USING(true);INSERT INTO public.{table} VALUES(1);''')
 sql('SET ROLE anon;INSERT INTO public.due_diligence_research VALUES(0);')
 migration=(ROOT/'supabase/migrations/202611010001_service_only_research_writes.sql').read_text();sql(migration);sql(migration)
 sql('SET ROLE anon;SELECT * FROM public.due_diligence_research;',ok=False);sql('SET ROLE authenticated;SELECT * FROM public.due_diligence_research;',ok=False);sql('SET ROLE service_role;INSERT INTO public.due_diligence_research VALUES(1);')
 for table in ['listing_market_stats','listing_comparables','listing_bracket_analyses']:
  count,_=sql(f'SET ROLE anon;SELECT count(*) FROM public.{table};');assert count=='1';sql(f'SET ROLE anon;INSERT INTO public.{table} VALUES(2);',ok=False);sql(f'SET ROLE service_role;INSERT INTO public.{table} VALUES(2);')
 for table in ['property_intelligence_reports','comparative_gap_analyses','aggregated_gap_analyses']:
  sql(f'SET ROLE anon;SELECT * FROM public.{table};',ok=False);count,_=sql(f'SET ROLE authenticated;SELECT count(*) FROM public.{table};');assert count=='1';sql(f'SET ROLE authenticated;INSERT INTO public.{table} VALUES(2);',ok=False);sql(f'SET ROLE service_role;INSERT INTO public.{table} VALUES(2);')
 result={'project':'renovation-estimates','engine':'PostgreSQL16-alpine','network':'none','synthetic_roles_only':True,'historical_policy_leak_reproduced':True,'anonymous_access_denied':True,'service_writes':True,'intended_shared_reads':True,'idempotent_forward_migrations':True,'existing_hosted_db_touched':False};print(json.dumps(result))
finally:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
