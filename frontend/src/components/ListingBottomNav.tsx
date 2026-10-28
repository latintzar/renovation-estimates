"use client";

/**
 * ListingBottomNav Component
 * ==========================
 *
 * Mobile-style tab bar for the listing page:
 * - Anuncio (left): Property listing details
 * - Reforma (center, hero): Renovation analysis — elevated circle
 * - Comparables (right): Sold comparables + map
 *
 * Design language: warm stone palette, terra-cotta accent on hero.
 */

import { Home, Search, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export type ListingTab = "listing" | "renovation" | "comparables";

interface ListingBottomNavProps {
  activeTab: ListingTab;
  onTabChange: (tab: ListingTab) => void;
  labels?: { renovation?: string; comparables?: string; listing?: string };
  /** Render inside a relative container (absolute), not viewport-fixed. */
  embedded?: boolean;
}

const ACCENT = "#da654d";

export function ListingBottomNav({ activeTab, onTabChange, labels, embedded = false }: ListingBottomNavProps) {
  const renoLabel = labels?.renovation || "Reforma";
  const renoActive = activeTab === "renovation";

  const sideTab = (
    id: ListingTab,
    defaultLabel: string,
    Icon: typeof Sparkles,
  ) => {
    const isActive = activeTab === id;
    const label = labels?.[id] || defaultLabel;
    return (
      <button
        key={id}
        onClick={() => onTabChange(id)}
        className={cn(
          "flex-1 flex flex-col items-center justify-center gap-0.5 pt-2.5 pb-1 transition-colors",
          isActive
            ? "text-stone-800"
            : "text-stone-400 hover:text-stone-500",
        )}
        aria-label={label}
        aria-current={isActive ? "page" : undefined}
        tabIndex={0}
      >
        <Icon
          className="w-5 h-5"
          strokeWidth={isActive ? 2.2 : 1.8}
        />
        <span className={cn("text-[10px]", isActive ? "font-semibold" : "font-normal")}>
          {label}
        </span>
        {/* Active dot indicator */}
        {isActive ? (
          <span className="w-1 h-1 rounded-full bg-stone-800 mt-0.5" />
        ) : (
          <span className="w-1 h-1 mt-0.5" />
        )}
      </button>
    );
  };

  return (
    <nav
      className={cn(
        embedded ? "absolute bottom-0 left-0 right-0 z-40" : "fixed bottom-0 left-0 right-0 z-40"
      )}
      aria-label="Main navigation"
    >
      <div className="bg-white border-t border-stone-200/60">
        <div className="relative flex items-end max-w-lg mx-auto pb-[max(0.25rem,env(safe-area-inset-bottom))]">
          {/* Left — Listing */}
          {sideTab("listing", "Anuncio", Home)}

          {/* Center — Reforma: elevated circle */}
          <div className="flex-1 flex flex-col items-center -mt-5 pb-1">
            <button
              onClick={() => onTabChange("renovation")}
              className={cn(
                "flex items-center justify-center w-[52px] h-[52px] rounded-full transition-all",
                "focus:outline-none focus:ring-2 focus:ring-offset-1",
                renoActive ? "scale-[1.02]" : "hover:scale-[1.02]",
              )}
              style={{
                backgroundColor: renoActive ? ACCENT : "#fff",
                border: renoActive ? "none" : `1.5px solid ${ACCENT}30`,
                boxShadow: renoActive
                  ? `0 4px 16px ${ACCENT}40`
                  : "0 2px 10px rgba(0,0,0,0.06)",
              }}
              aria-label={renoLabel}
              aria-current={renoActive ? "page" : undefined}
              tabIndex={0}
            >
              <Sparkles
                className="w-[22px] h-[22px]"
                strokeWidth={renoActive ? 2.2 : 1.8}
                style={{ color: renoActive ? "#fff" : ACCENT }}
              />
            </button>
            <span
              className={cn("mt-0.5 text-[10px]", renoActive ? "font-semibold" : "font-normal")}
              style={{ color: renoActive ? ACCENT : "#a8a29e" }}
            >
              {renoLabel}
            </span>
          </div>

          {/* Right — Comparables */}
          {sideTab("comparables", "Comparables", Search)}
        </div>
      </div>
    </nav>
  );
}
