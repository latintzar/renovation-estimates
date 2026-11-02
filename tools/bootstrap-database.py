#!/usr/bin/env python3
"""Install the current schema in your fresh Supabase project using private libpq input."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def private_psql_env(inherited):
    value = inherited.get("DATABASE_URL", "")
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in {"postgres", "postgresql"} and parsed.hostname and parsed.username and parsed.path.strip("/")
    except ValueError:
        valid = False
    if not valid or any(char in value for char in "\n\r\0"):
        raise ValueError("Configure DATABASE_URL through your private database-admin file")
    env = {key: val for key, val in inherited.items() if not key.startswith("PG") and key != "DATABASE_URL"}
    # libpq accepts a URI through PGDATABASE; it stays outside argv and output.
    env.update(PGDATABASE=value, PGPASSFILE=os.devnull, PGSERVICEFILE=os.devnull,
               PGSYSCONFDIR=os.devnull, PGCONNECT_TIMEOUT="10", PGSSLMODE="require")
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply fresh-install SQL; the SQL refuses an existing application schema")
    args = parser.parse_args(argv)
    try:
        env = private_psql_env(dict(os.environ))
        binary = shutil.which("psql")
        if binary is None:
            raise ValueError("Install the PostgreSQL client tools")
        subprocess.run(["python3", str(ROOT / "tools/build-database-bootstrap.py"), "--check"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if not args.apply:
            print("Database input and psql are ready. Add --apply to initialize your fresh project.")
            return 0
        result = subprocess.run([binary, "-X", "-v", "ON_ERROR_STOP=1", "--file", str(ROOT / "db/bootstrap.sql")], env=env, text=True, capture_output=True)
        if result.returncode:
            print("Database initialization failed. Check your connection, fresh project and SQL input privately.")
            return 1
        print("Fresh Estimate database initialized.")
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError):
        print("Configure your private DATABASE_URL, install psql and verify the generated SQL before initializing.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
