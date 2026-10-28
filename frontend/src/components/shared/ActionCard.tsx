"use client";

import { ArrowRight } from "lucide-react";

interface ActionCardProps {
  title: string;
  subtitle: string;
  buttonLabel: string;
  onClick?: () => void;
}

export function ActionCard({ title, subtitle, buttonLabel, onClick }: ActionCardProps) {
  return (
    <div className="my-2 rounded-2xl border border-stone-200 bg-white p-4">
      <p className="text-[14px] font-semibold text-stone-900">{title}</p>
      <p className="mt-1 text-[13px] leading-5 text-stone-600">{subtitle}</p>
      <button
        type="button"
        onClick={onClick}
        className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-[#da654d] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[#c85b45]"
      >
        {buttonLabel}
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

