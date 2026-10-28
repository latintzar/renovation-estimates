"use client";

import { ChevronDown, ChevronUp, Link2 } from "lucide-react";
import { useState } from "react";

interface Citation {
  id: string;
  title: string;
  url: string;
}

interface CitationsBlockProps {
  citations: Citation[];
}

export function CitationsBlock({ citations }: CitationsBlockProps) {
  const [expanded, setExpanded] = useState(false);
  if (citations.length === 0) return null;

  return (
    <div className="my-1 w-full rounded-xl border border-stone-200 bg-white/80 px-3 py-2">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between text-left text-xs text-stone-700"
      >
        <span>Citations ({citations.length})</span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-stone-400" /> : <ChevronDown className="h-3.5 w-3.5 text-stone-400" />}
      </button>
      {expanded ? (
        <div className="mt-2 space-y-1.5">
          {citations.map((citation, index) => (
            <a
              key={citation.id}
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-start gap-2 rounded-md p-1.5 text-[12px] text-stone-700 hover:bg-stone-50"
            >
              <span className="text-stone-500">{index + 1}.</span>
              <span className="flex-1">{citation.title}</span>
              <Link2 className="mt-0.5 h-3 w-3 text-stone-400" />
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}

