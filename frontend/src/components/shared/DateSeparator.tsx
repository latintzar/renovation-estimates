"use client";

interface DateSeparatorProps {
  date: Date;
}

const formatDateLabel = (date: Date): string => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.floor((today.getTime() - target.getTime()) / 86400000);

  if (diff === 0) return "TODAY";
  if (diff === 1) return "YESTERDAY";
  if (diff < 7) return date.toLocaleDateString("en-US", { weekday: "long" }).toUpperCase();
  return date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }).toUpperCase();
};

export function DateSeparator({ date }: DateSeparatorProps) {
  return (
    <div className="my-4 flex items-center justify-center">
      <span className="rounded-[7px] bg-white/90 px-3 py-1.5 text-[12px] font-semibold uppercase tracking-[0.2px] text-stone-500 shadow-sm">
        {formatDateLabel(date)}
      </span>
    </div>
  );
}

