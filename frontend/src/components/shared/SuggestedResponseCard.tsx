"use client";

import { ArrowRight, Sparkles } from "lucide-react";

interface SuggestedResponseData {
  text: string;
  title?: string;
  subtitle?: string;
}

interface SuggestedResponseCardProps {
  data: SuggestedResponseData;
  onSend: (text: string) => void;
}

export function SuggestedResponseCard({ data, onSend }: SuggestedResponseCardProps) {
  return (
    <div className="my-2 rounded-2xl bg-[#1A1A1A] p-4">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-[#da654d]" />
        <span className="text-[13px] font-semibold text-white">{data.title ?? "Suggested Reply"}</span>
      </div>
      <p className="mb-3 text-[14px] leading-6 text-white/70">{data.subtitle ?? data.text}</p>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => onSend(data.text)}
          className="inline-flex items-center gap-1.5 rounded-xl bg-[#da654d] px-4 py-2 text-[14px] font-semibold text-white transition hover:bg-[#c85b45]"
        >
          Send
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

