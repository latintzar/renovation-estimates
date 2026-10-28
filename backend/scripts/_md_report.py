from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def write_md_report(
    *,
    report_path: str,
    title: str,
    meta: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
    sample: Optional[Any] = None,
) -> str:
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"## {title}\n\n")
        f.write(f"- created_at_utc: **{now}**\n")
        for k, v in (meta or {}).items():
            f.write(f"- {k}: **{v}**\n")
        f.write("\n")

        if sample is not None:
            f.write("### Sample\n\n")
            f.write("```json\n")
            f.write(json.dumps(sample, ensure_ascii=False, indent=2)[:20000])
            f.write("\n```\n\n")

        if payload is not None:
            f.write("### Full payload (truncated)\n\n")
            f.write("```json\n")
            f.write(json.dumps(payload, ensure_ascii=False, indent=2)[:20000])
            f.write("\n```\n")
    return report_path

