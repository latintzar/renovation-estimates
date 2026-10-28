Scripts Overview
================

This folder holds operational scripts for the Lean MVP backend.

Grand goal
----------
These scripts exist to keep the pipeline reliable and observable, so long-running
jobs never go unnoticed and failures are caught early.

Pipeline health
---------------
Use the health check to catch stuck or stalled runs before they become multi-hour issues.

Run:
  ./venv/bin/python scripts/pipeline_health.py

What it checks:
- Zombie jobs: in_progress with expired locks
- Long-running jobs: in_progress for longer than the threshold
- Stale runs: runs with pending jobs older than the threshold
- Throughput: completed jobs in the last hour

Exit codes:
- 0: Healthy
- 1: Warning (needs attention)
- 2: Critical (pipeline likely stuck)

Houzz headless probe
--------------------
Use this to validate whether Houzz quote submission can be automated reliably
for a given listing/location.

Script:
  ./venv/bin/python scripts/try_houzz_quote_submission.py --listing-id 13

It writes:
- `backend/reports/houzz_probe/run_<timestamp>/report.json`
- `backend/reports/houzz_probe/run_<timestamp>/screenshots/*.png`

Notes:
- It is fail-loud and logs every major step.
- If credentials are available (`HOUZZ_EMAIL`, `HOUZZ_PASSWORD`), it attempts login.
- If playwright is missing, install:
  - `pip install playwright`
  - `python -m playwright install chromium`
