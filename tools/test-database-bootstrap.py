#!/usr/bin/env python3
"""Verify a fresh schema and queue in disposable, network-isolated PostgreSQL16."""
from pathlib import Path
import ast
import asyncio
import json
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional
import uuid

ROOT = Path(__file__).resolve().parents[1]
NAME = "estimates-bootstrap-" + uuid.uuid4().hex[:12]


def command():
    return ["docker", "exec", "-i", NAME, "psql", "-X", "-U", "postgres", "-v", "ON_ERROR_STOP=1", "-qAt"]


def sql(text, allowed=True):
    result = subprocess.run(command(), input=text, text=True, capture_output=True)
    if allowed and result.returncode:
        raise AssertionError(result.stderr)
    if not allowed and not result.returncode:
        raise AssertionError("Expected database refusal")
    return result.stdout.strip()


def verify_released_payloads():
    """Execute released client functions with a fenced SQL-backed request recorder.

    This checks their real JSON field contracts against PostgreSQL, independently
    of a deployed PostgREST installation or provider configuration.
    """
    selected = {
        "create_pipeline_run", "enqueue_pipeline_job", "add_pipeline_job_event",
        "save_pir", "save_unified_estimate", "save_boq_line_items_batch",
        "create_cost_tracking_run", "add_gemini_call_log_row",
    }

    class Response:
        status_code = 201
        text = "local SQL contract result"
        def __init__(self, rows): self.rows = rows
        def json(self): return self.rows

    class Client:
        async def delete(self, url, *, params, **kwargs):
            table = url.split("/rest/v1/", 1)[1]
            assert table == "property_intelligence_reports"
            conditions = []
            for key,value in params.items():
                assert key in {"listing_id", "pir_type"} and value.startswith("eq.")
                conditions.append('"' + key + '"=\'' + value[3:].replace("'", "''") + "'")
            sql("SET ROLE service_role;DELETE FROM public." + table + " WHERE " + " AND ".join(conditions) + ";")
            response = Response([]); response.status_code = 204
            return response

        async def post(self, url, *, json, **kwargs):
            table = url.split("/rest/v1/", 1)[1].split("?", 1)[0]
            document = __import__("json").dumps(json).replace("'", "''")
            if table == "rpc/boq_line_items_upsert":
                value = sql("SET ROLE service_role;SELECT public.boq_line_items_upsert('" + __import__("json").dumps(json["rows"]).replace("'", "''") + "'::jsonb);")
                response = Response(int(value)); response.status_code = 200
                return response
            assert table.replace("_", "").isalnum()
            columns = set(sql("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='" + table + "';").splitlines())
            assert set(json) <= columns, (table, set(json) - columns)
            names = ",".join('"' + key + '"' for key in json)
            returned = sql("SET ROLE service_role;INSERT INTO public." + table + "(" + names + ") SELECT " + names + " FROM json_populate_record(NULL::public." + table + ",'" + document + "'::json) RETURNING to_jsonb(" + table + ".*);")
            return Response([__import__("json").loads(returned)])

    client = Client()
    async def get_client(): return client
    namespace = dict(Optional=Optional, Dict=Dict, Any=Any, List=List,
        get_client=get_client, _get_base_url=lambda: "https://example.test/rest/v1",
        _get_headers=lambda: {}, logger=logging.getLogger("fresh-database-contract"))
    tree = ast.parse((ROOT / "backend/database.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name in selected]
    assert len(functions) == len(selected)
    exec(compile(ast.Module(body=functions, type_ignores=[]), "released-database-functions", "exec"), namespace)

    async def exercise():
        assert await namespace["create_pipeline_run"]("released-payload-run",101,{"pipeline":"fixture"})
        job = await namespace["enqueue_pipeline_job"]("released-payload-run",101,"capture","capture",{},"released-payload-key")
        assert job
        assert await namespace["add_pipeline_job_event"](job,"test","Authored event",{"source":"test"})
        assert await namespace["save_pir"](101,{"type":"target","rooms":[{"id":"kitchen"}],"building_profile":{"year_built":1990,"year_source":"listing"}})
        assert await namespace["save_pir"](101,{"type":"bracket_fair_market","rooms":[]})
        assert sql("SELECT count(*) FROM public.property_intelligence_reports WHERE listing_id=101;") == "2"
        assert await namespace["save_unified_estimate"](101,"v2_boq",{"total_cost":20,"v05_schema_continuity":True,"line_items_count":1})
        assert await namespace["save_boq_line_items_batch"](101,"v5_payload","finishes","Kitchen",[{"bcca_code":"payload-fixture","description":"Authored floor","quantity":1,"unit":"m2","unit_price":10,"line_total":10,"room_id":"kitchen","provenance":{"source":"released-client-test"}}]) == 1
        assert await namespace["create_cost_tracking_run"](101,"released-payload-run")
        result = await namespace["add_gemini_call_log_row"](listing_id=101,run_id="released-payload-run",stage="fixture",model="offline-fixture",prompt_tokens=0,output_tokens=0,thinking_tokens=0,total_tokens=0,cost_regular=0,cost_cached=0)
        assert result
    asyncio.run(exercise())


def main():
    subprocess.run(["python3", str(ROOT / "tools/build-database-bootstrap.py"), "--check"], check=True)
    subprocess.run([
        "docker", "run", "--detach", "--rm", "--name", NAME,
        "--network", "none", "--memory", "384m", "--cpus", "1", "--pids-limit", "128",
        "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
        "--tmpfs", "/var/lib/postgresql/data:rw,noexec,nosuid,size=256m",
        "--tmpfs", "/var/run/postgresql:rw,noexec,nosuid,size=16m", "postgres:16-alpine",
    ], check=True, stdout=subprocess.DEVNULL)
    try:
        for _ in range(150):
            logs = subprocess.check_output(["docker", "logs", NAME], text=True, stderr=subprocess.STDOUT)
            ready = subprocess.run(["docker", "exec", NAME, "pg_isready", "-U", "postgres"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if "PostgreSQL init process complete" in logs and ready.returncode == 0:
                break
            time.sleep(.1)
        else:
            raise AssertionError("Disposable database did not become ready")
        # Supabase owns these objects. This fixture supplies only their SQL contracts.
        sql("""CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;
          CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY);
          CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
            $$SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
          CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS
            $$SELECT coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb$$;
          GRANT USAGE ON SCHEMA auth TO anon,authenticated,service_role;
        """)
        bootstrap = (ROOT / "db/bootstrap.sql").read_text()
        sql(bootstrap)
        sql(bootstrap, allowed=False)  # An existing project is preserved, not reinitialized.
        sql("""SET ROLE service_role;
          INSERT INTO public.listings(id,source_url,title) VALUES(101,'https://example.test/home/101','Authored home');
          INSERT INTO public.pipeline_runs(run_id,listing_id,status,config)
            VALUES('fixture-run',101,'queued','{"pipeline":"fixture"}');
          INSERT INTO public.pipeline_jobs(run_id,listing_id,stage,job_type,payload,idempotency_key)
            SELECT 'fixture-run',101,'stage-'||n,'job-'||n,'{}','fixture-'||n FROM generate_series(1,3) n;
        """)
        assert sql("SELECT jobs_total||':'||jobs_queued FROM public.pipeline_runs WHERE run_id='fixture-run';") == "3:3"
        sql("SET ROLE service_role;INSERT INTO public.pipeline_jobs(run_id,listing_id,stage,job_type,idempotency_key) VALUES('fixture-run',101,'s','j','fixture-1') ON CONFLICT(idempotency_key) DO NOTHING;")
        assert sql("SELECT count(*) FROM public.pipeline_jobs;") == "3"

        # Keep one claim transaction open while a second worker claims the queue.
        first = subprocess.Popen(command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        first.stdin.write("BEGIN;SET ROLE service_role;SELECT id FROM public.claim_pipeline_jobs('worker-A',1,60);SELECT pg_sleep(1);COMMIT;\n")
        first.stdin.close()
        claimed_a = first.stdout.readline().strip()
        claimed_b = sql("SET ROLE service_role;SELECT id FROM public.claim_pipeline_jobs('worker-B',2,60);").splitlines()
        assert claimed_a and len(claimed_b) == 2 and claimed_a not in claimed_b
        assert first.wait(timeout=5) == 0, first.stderr.read()
        assert sql("SELECT jobs_in_progress FROM public.pipeline_runs WHERE run_id='fixture-run';") == "3"
        assert sql("SELECT count(*) FROM public.claim_pipeline_jobs('worker-C',10,60);") == "0"
        sql("SELECT * FROM public.claim_pipeline_jobs('',10,60);", allowed=False)
        sql("SELECT * FROM public.claim_pipeline_jobs('worker',101,60);", allowed=False)
        sql("SELECT * FROM public.claim_pipeline_jobs('worker',10,0);", allowed=False)
        # Heartbeat renewal, explicit requeue and cancellation use the retained REST PATCH fields.
        sql("""SET ROLE service_role; UPDATE public.pipeline_jobs SET locked_until=now()+interval '60 seconds',last_heartbeat_at=now(),updated_at=now() WHERE locked_by='worker-A' AND status='in_progress';
          UPDATE public.pipeline_jobs SET status='queued',locked_by=NULL,locked_until=NULL,finished_at=NULL,available_at=now()+interval '1 hour' WHERE locked_by='worker-B';
        """)
        assert sql("SELECT count(*) FROM public.claim_pipeline_jobs('worker-C',10,60);") == "0"
        sql("UPDATE public.pipeline_jobs SET status='cancelled',locked_by=NULL,locked_until=NULL WHERE id=" + "'" + claimed_b[0] + "';")
        assert sql("SELECT count(*) FROM public.claim_pipeline_jobs('worker-C',10,60);") == "0"
        # A dead worker is failed by the original reaper rather than silently rerun.
        sql("UPDATE public.pipeline_jobs SET locked_until=now()-interval '1 hour',last_heartbeat_at=now()-interval '1 hour' WHERE locked_by='worker-A';")
        assert sql("SELECT public.reap_stuck_pipeline_jobs(0,0,10);") == "1"
        assert sql("SELECT status FROM public.pipeline_jobs WHERE locked_by='worker-A';") == ""
        assert sql("SELECT jobs_failed FROM public.pipeline_runs WHERE run_id='fixture-run';") == "1"
        sql("UPDATE public.pipeline_jobs SET status='succeeded',finished_at=now(),updated_at=now() WHERE run_id='fixture-run';")
        assert sql("SELECT status FROM public.pipeline_runs WHERE run_id='fixture-run';") == "complete"
        assert sql("SELECT count FROM public.pipeline_job_counts('fixture-run') WHERE status='succeeded';") == "3"
        # Real merge RPC: repeated measured lines accumulate quantities and retain provenance.
        row = json.dumps([dict(listing_id=101,strategy_name="v5_market_standard",dimension="finishes",room_name="Kitchen",bcca_code="fixture-code",description="Authored floor",quantity=2,unit="m2",unit_price=10,line_total=20,labor_hours=1,room_id="kitchen",provenance={"source":"authored-test"})])
        statement = "SET ROLE service_role;SELECT public.boq_line_items_upsert('" + row.replace("'", "''") + "'::jsonb);"
        assert sql(statement) == "1"
        assert sql(statement) == "1"
        assert sql("SELECT quantity||':'||line_total||':'||(provenance->>'source') FROM public.boq_line_items;") == "4:40:authored-test"
        sql("SET ROLE anon;SELECT * FROM public.pipeline_jobs;", allowed=False)
        sql("SET ROLE authenticated;SELECT * FROM public.listings;", allowed=False)
        sql("SET ROLE anon;SELECT * FROM public.claim_pipeline_jobs('anonymous',1,60);", allowed=False)
        sql("SET ROLE authenticated;SELECT public.refresh_pipeline_run_status('fixture-run');", allowed=False)
        verify_released_payloads()
        print(json.dumps({"engine":"PostgreSQL16","network":"none","fresh_bootstrap":True,"existing_project_refused":True,"concurrent_claims_disjoint":True,"idempotent_enqueue":True,"future_availability":True,"lease_reaper":True,"terminal_jobs_not_claimed":True,"run_status_and_counts":True,"boq_merge_and_provenance":True,"service_only_access":True,"released_client_payloads":True,"hosted_databases_touched":False}))
    finally:
        subprocess.run(["docker", "rm", "-f", NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
