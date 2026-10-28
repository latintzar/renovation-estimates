"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { sharedColors } from "@/lib/shared/colors";

interface ThoughtData {
  durationSec: number;
  summary: string;
}

interface ThoughtIndicatorProps {
  thought?: ThoughtData;
}

export function ThoughtIndicator({ thought }: ThoughtIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  if (!thought) return null;

  return (
    <div className="mb-1.5 w-full rounded-xl border border-stone-200 bg-white/80 px-3 py-2">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between text-left"
        aria-label={expanded ? "Collapse thought" : "Expand thought"}
      >
        <span className="flex items-center gap-2 text-xs text-stone-700">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#FCEEE9] text-[11px] font-semibold text-[#da654d]">
            L
          </span>
          Thought for <span className="text-stone-500">{thought.durationSec}s</span>
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-stone-400" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-stone-400" />
        )}
      </button>
      {expanded ? (
        <p className="mt-2 text-[12px] leading-5 text-stone-500" style={{ color: sharedColors.light.textMuted }}>
          {thought.summary}
        </p>
      ) : null}
    </div>
  );
}

