"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Package, ChevronDown, ChevronRight, Check, AlertTriangle } from "lucide-react";
import { MOCK_INVENTORY } from "@/lib/agent/mock-data";
import type { InventoryItem } from "@/lib/agent/types";

const CONDITION_BADGE: Record<InventoryItem["condition"], { label: string; color: string }> = {
  new: { label: "New", color: "bg-emerald-50 text-emerald-700" },
  good: { label: "Good", color: "bg-blue-50 text-blue-700" },
  fair: { label: "Fair", color: "bg-amber-50 text-amber-700" },
  poor: { label: "Poor", color: "bg-red-50 text-red-700" },
};

const CATEGORY_ICON: Record<InventoryItem["category"], string> = {
  appliance: "🔌",
  fixture: "🚿",
  finish: "🎨",
  structural: "🧱",
};

export function InventoryList() {
  const [expandedRoom, setExpandedRoom] = useState<string | null>("Kitchen");

  const rooms = Array.from(new Set(MOCK_INVENTORY.map((i) => i.room)));

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-100">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-stone-500" />
          <span className="text-sm font-medium text-stone-700">Room Inventory</span>
        </div>
        <span className="text-xs text-stone-400">
          {MOCK_INVENTORY.length} items across {rooms.length} rooms
        </span>
      </div>

      <div className="divide-y divide-stone-100">
        {rooms.map((room) => {
          const items = MOCK_INVENTORY.filter((i) => i.room === room);
          const isExpanded = expandedRoom === room;

          return (
            <div key={room}>
              <button
                onClick={() => setExpandedRoom(isExpanded ? null : room)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stone-50 transition-colors text-left"
                tabIndex={0}
                aria-label={`${room} - ${items.length} items`}
              >
                {isExpanded ? (
                  <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-stone-400" />
                )}
                <span className="text-sm font-medium text-stone-800 flex-1">
                  {room}
                </span>
                <span className="text-xs text-stone-400">{items.length} items</span>
              </button>

              {isExpanded && (
                <div className="px-4 pb-3 space-y-1">
                  {items.map((item) => {
                    const condBadge = CONDITION_BADGE[item.condition];
                    return (
                      <div
                        key={item.id}
                        className="flex items-center gap-2.5 py-1.5 pl-6 text-xs animate-fade-in"
                      >
                        <span>{CATEGORY_ICON[item.category]}</span>
                        <span className="text-stone-700 flex-1">
                          {item.name}
                          {item.brand && (
                            <span className="text-stone-400 ml-1">
                              ({item.brand}{item.model ? ` ${item.model}` : ""})
                            </span>
                          )}
                        </span>
                        <span className={cn("px-1.5 py-0.5 rounded-full text-[10px] font-medium", condBadge.color)}>
                          {condBadge.label}
                        </span>
                        {item.hasReceipt && (
                          <span className="text-emerald-500" title="Has receipt">
                            <Check className="w-3 h-3" />
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
