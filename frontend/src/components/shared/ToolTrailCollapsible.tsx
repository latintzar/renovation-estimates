"use client";

import { ChevronDown, ChevronRight, Check, Loader2 } from "lucide-react";
import { useState, useEffect, useRef } from "react";

interface ToolTrailStep {
  active?: string;
  done: string;
  detail?: string;
  durationMs?: number;
  linkedChatId?: string;
  linkedMessageId?: string;
}

interface ToolTrailCollapsibleProps {
  steps: ToolTrailStep[];
  animate?: boolean;
  onLinkedPress?: (chatId: string, messageId: string) => void;
}

export function ToolTrailCollapsible({ steps, animate = false, onLinkedPress }: ToolTrailCollapsibleProps) {
  const [expanded, setExpanded] = useState(animate);
  const [completedCount, setCompletedCount] = useState(animate ? 0 : steps.length);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (!animate || steps.length === 0 || hasAnimated.current) return;
    hasAnimated.current = true;
    let cancelled = false;
    let idx = 0;

    const advanceStep = () => {
      if (cancelled || idx >= steps.length) return;
      const delay = Math.min(steps[idx].durationMs ?? 600, 800);
      setTimeout(() => {
        if (cancelled) return;
        idx++;
        setCompletedCount(idx);
        advanceStep();
      }, delay);
    };

    advanceStep();
    return () => { cancelled = true; };
  }, [animate, steps]);

  if (steps.length === 0) return null;

  const allDone = completedCount >= steps.length;

  return (
    <div className="mb-1.5 w-full rounded-xl border border-stone-200 bg-white/80 px-3 py-2">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between text-left"
        aria-label={expanded ? "Collapse tool trail" : "Expand tool trail"}
      >
        <span className="flex items-center gap-2 text-xs text-stone-700">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#FCEEE9] text-[11px] font-semibold text-[#da654d]">
            L
          </span>
          {allDone
            ? `Used ${steps.length} tool${steps.length === 1 ? "" : "s"}`
            : `Using ${steps.length} tool${steps.length === 1 ? "" : "s"}\u2026`}
        </span>
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-stone-400" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-stone-400" />
        )}
      </button>
      {expanded ? (
        <div className="mt-2 space-y-2">
          {steps.map((step, index) => {
            const isDone = index < completedCount;
            const isActive = index === completedCount && !allDone;
            if (!isDone && !isActive) return null;

            const isLinked = isDone && Boolean(step.linkedChatId && step.linkedMessageId);
            const label = isDone ? step.done : (step.active ?? step.done);
            const content = (
              <>
                {isDone ? (
                  <Check className="mt-0.5 h-3 w-3 flex-shrink-0 text-[#da654d]" />
                ) : (
                  <Loader2 className="mt-0.5 h-3 w-3 flex-shrink-0 animate-spin text-[#da654d]" />
                )}
                <span className="flex-1">
                  <span className={`block text-[12px] ${isDone ? "text-stone-700" : "text-stone-500"}`}>{label}</span>
                  {isDone && step.detail ? <span className="block text-[11px] text-stone-500">{step.detail}</span> : null}
                </span>
                {isLinked ? <ChevronRight className="h-3 w-3 flex-shrink-0 text-[#da654d]" /> : null}
              </>
            );

            if (isLinked) {
              return (
                <button
                  key={`${label}-${index}`}
                  type="button"
                  onClick={() => onLinkedPress?.(step.linkedChatId!, step.linkedMessageId!)}
                  className="flex w-full items-start gap-2 rounded-md p-1 text-left hover:bg-stone-50"
                >
                  {content}
                </button>
              );
            }
            return (
              <div key={`${label}-${index}`} className="flex items-start gap-2 p-1">
                {content}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
