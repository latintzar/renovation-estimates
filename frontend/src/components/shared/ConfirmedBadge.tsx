"use client";

import { ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";
import { useState } from "react";

interface ConfirmedBadgeProps {
  detail?: string;
}

export function ConfirmedBadge({ detail }: ConfirmedBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setExpanded((value) => !value)}
      className="my-1 inline-flex w-full flex-col items-start rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-left"
      aria-label={expanded ? "Collapse confirmation detail" : "Expand confirmation detail"}
    >
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" />
        You confirmed this
        {detail ? (
          expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />
        ) : null}
      </span>
      {expanded && detail ? <span className="mt-1 text-[11px] text-emerald-800">{detail}</span> : null}
    </button>
  );
}

