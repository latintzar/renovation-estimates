"""Private CLI contract: no connections or credentials in command arguments/output."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bootstrap_database", ROOT / "tools/bootstrap-database.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
EXAMPLE = "postgresql://fixture:authored-test-password@db.example.test:5432/postgres"


class PrivateDatabaseSetup(unittest.TestCase):
    def test_selected_connection_clears_ambient_libpq(self):
        env = bootstrap.private_psql_env({"DATABASE_URL": EXAMPLE, "PGHOST": "ambient.invalid", "PGSERVICE": "ambient", "PATH": "/usr/bin"})
        self.assertEqual(env["PGDATABASE"], EXAMPLE)
        self.assertNotIn("PGHOST", env)
        self.assertNotIn("PGSERVICE", env)
        self.assertEqual(env["PGSSLMODE"], "require")

    def test_default_does_not_connect(self):
        with patch.dict(os.environ, {"DATABASE_URL": EXAMPLE}, clear=True), patch.object(bootstrap.shutil, "which", return_value="/usr/bin/psql"), patch.object(bootstrap.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(bootstrap.main([]), 0)
            self.assertEqual(run.call_count, 1)
            self.assertNotIn("psql", run.call_args.args[0])

    def test_apply_keeps_url_out_of_argv(self):
        with patch.dict(os.environ, {"DATABASE_URL": EXAMPLE}, clear=True), patch.object(bootstrap.shutil, "which", return_value="/usr/bin/psql"), patch.object(bootstrap.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertEqual(bootstrap.main(["--apply"]), 0)
            args, kwargs = run.call_args
            self.assertNotIn(EXAMPLE, args[0])
            self.assertEqual(kwargs["env"]["PGDATABASE"], EXAMPLE)
            self.assertTrue(kwargs["capture_output"])

    def test_malformed_connections_fail_before_process(self):
        for value in ["", "https://example.test/db", "postgresql://user@host/db\nPGHOST=other", "postgresql://[invalid"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                bootstrap.private_psql_env({"DATABASE_URL": value})


if __name__ == "__main__":
    unittest.main()
