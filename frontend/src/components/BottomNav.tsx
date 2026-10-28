"use client";

/**
 * BottomNav Component
 * ===================
 * 
 * Compact fixed bottom navigation with raised center button.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface BottomNavProps {
  /** Callback when the + button is clicked */
  onAdd?: () => void;
}

// Leo "L" icon component
function LeoIcon({ className }: { className?: string }) {
  return (
    <span className={cn("font-serif font-bold", className)}>L</span>
  );
}

export function BottomNav({ onAdd }: BottomNavProps) {
  const pathname = usePathname();

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname.startsWith(href);
  };

  const handleAddClick = (e: React.MouseEvent) => {
    if (onAdd) {
      e.preventDefault();
      onAdd();
    }
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-sm border-t border-stone-200 z-40">
      <div className="relative flex items-center justify-around max-w-lg mx-auto py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
        {/* Left - Leo/Home */}
        <Link
          href="/"
          className={cn(
            "flex flex-col items-center justify-center gap-0.5 px-6 transition-colors",
            isActive("/", true) 
              ? "text-stone-900" 
              : "text-stone-400 hover:text-stone-600"
          )}
        >
          <LeoIcon className="text-lg" />
          <span className="text-[10px] font-medium">Leo</span>
        </Link>

        {/* Center - Raised Add Button */}
        {onAdd ? (
          <button
            onClick={handleAddClick}
            className="absolute left-1/2 -translate-x-1/2 -top-5 w-14 h-14 bg-gradient-to-br from-[#da654d] to-[#e07c5f] rounded-full flex items-center justify-center shadow-lg shadow-[#da654d]/30 hover:shadow-xl hover:shadow-[#da654d]/40 hover:scale-105 active:scale-95 transition-all"
          >
            <Plus className="w-7 h-7 text-white" strokeWidth={2.5} />
          </button>
        ) : (
          <Link
            href="/"
            className="absolute left-1/2 -translate-x-1/2 -top-5 w-14 h-14 bg-gradient-to-br from-[#da654d] to-[#e07c5f] rounded-full flex items-center justify-center shadow-lg shadow-[#da654d]/30 hover:shadow-xl hover:shadow-[#da654d]/40 hover:scale-105 active:scale-95 transition-all"
          >
            <Plus className="w-7 h-7 text-white" strokeWidth={2.5} />
          </Link>
        )}

        {/* Right - Profile/You */}
        <Link
          href="/profile"
          className={cn(
            "flex flex-col items-center justify-center gap-0.5 px-6 transition-colors",
            isActive("/profile") 
              ? "text-stone-900" 
              : "text-stone-400 hover:text-stone-600"
          )}
        >
          <User className="w-5 h-5" />
          <span className="text-[10px] font-medium">Tú</span>
        </Link>
      </div>
    </nav>
  );
}
