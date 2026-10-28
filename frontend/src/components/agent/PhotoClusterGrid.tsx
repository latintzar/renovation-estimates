"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Check, AlertTriangle, Plus, Camera } from "lucide-react";
import { MOCK_CLUSTERS } from "@/lib/agent/mock-data";
import type { PhotoCluster } from "@/lib/agent/types";

interface PhotoClusterGridProps {
  clusters?: PhotoCluster[];
  onClusterClick?: (clusterId: string) => void;
}

const STATUS_ICON: Record<PhotoCluster["status"], React.ReactNode> = {
  good: <Check className="w-3.5 h-3.5 text-emerald-500" />,
  needs_more: <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />,
  insufficient: <AlertTriangle className="w-3.5 h-3.5 text-red-500" />,
};

const STATUS_DOT: Record<PhotoCluster["status"], string> = {
  good: "bg-emerald-500",
  needs_more: "bg-amber-500",
  insufficient: "bg-red-500",
};

const STATUS_LABEL: Record<PhotoCluster["status"], string> = {
  good: "",
  needs_more: "Need 1-2 more",
  insufficient: "Need 2-3 more",
};

export function PhotoClusterGrid({
  clusters = MOCK_CLUSTERS,
  onClusterClick,
}: PhotoClusterGridProps) {
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null);

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-100">
        <div className="flex items-center gap-2">
          <Camera className="w-4 h-4 text-stone-500" />
          <span className="text-sm font-medium text-stone-700">Photo Clusters</span>
        </div>
        <span className="text-xs text-stone-400">
          {clusters.filter((c) => c.status === "good").length}/{clusters.length} rooms complete
        </span>
      </div>

      {/* Clusters */}
      <div className="p-3 space-y-2">
        {clusters.map((cluster) => {
          const isExpanded = expandedCluster === cluster.id;
          return (
            <div
              key={cluster.id}
              className={cn(
                "rounded-xl border transition-all cursor-pointer",
                isExpanded
                  ? "border-stone-300 bg-stone-50"
                  : "border-stone-100 hover:border-stone-200 bg-white"
              )}
              onClick={() => {
                setExpandedCluster(isExpanded ? null : cluster.id);
                onClusterClick?.(cluster.id);
              }}
              role="button"
              tabIndex={0}
              aria-label={`${cluster.roomName} - ${cluster.photos.length} photos`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  setExpandedCluster(isExpanded ? null : cluster.id);
                }
              }}
            >
              {/* Room Header */}
              <div className="flex items-center gap-3 px-3 py-2.5">
                <div className={cn("w-2 h-2 rounded-full flex-shrink-0", STATUS_DOT[cluster.status])} />
                <span className="text-sm font-medium text-stone-800 flex-1">
                  {cluster.roomName}
                </span>
                <span className="text-xs text-stone-400">
                  {cluster.photos.length} photos
                </span>
                {STATUS_ICON[cluster.status]}
                {cluster.status !== "good" && (
                  <span className="text-[11px] text-stone-400">
                    {STATUS_LABEL[cluster.status]}
                  </span>
                )}
              </div>

              {/* Photo Thumbnails (always show a strip, expanded shows larger) */}
              <div
                className={cn(
                  "flex gap-1.5 px-3 pb-2.5 overflow-x-auto scrollbar-hide",
                  isExpanded && "flex-wrap"
                )}
              >
                {cluster.photos.map((photo, i) => (
                  <div
                    key={i}
                    className={cn(
                      "relative rounded-lg overflow-hidden flex-shrink-0 bg-stone-100",
                      isExpanded ? "w-[calc(25%-6px)] aspect-[4/3]" : "w-12 h-12"
                    )}
                  >
                    <Image
                      src={photo}
                      alt={`${cluster.roomName} photo ${i + 1}`}
                      fill
                      className="object-cover"
                      sizes={isExpanded ? "25vw" : "48px"}
                    />
                  </div>
                ))}
                {cluster.status !== "good" && (
                  <div
                    className={cn(
                      "flex items-center justify-center rounded-lg border-2 border-dashed border-stone-200 flex-shrink-0",
                      isExpanded ? "w-[calc(25%-6px)] aspect-[4/3]" : "w-12 h-12"
                    )}
                  >
                    <Plus className="w-4 h-4 text-stone-300" />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Excluded Content */}
      <div className="px-4 py-2.5 bg-stone-50 border-t border-stone-100">
        <span className="text-xs text-stone-400">
          ⚪ Excluded: 1 floor plan, 1 building exterior
        </span>
      </div>
    </div>
  );
}
