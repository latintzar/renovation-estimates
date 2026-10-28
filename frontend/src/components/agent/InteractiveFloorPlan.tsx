"use client";

import { useState, useCallback } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Check, MapPin } from "lucide-react";
import { MOCK_FLOOR_PLAN_ROOMS, MOCK_CLUSTERS } from "@/lib/agent/mock-data";
import type { FloorPlanRoom, PhotoCluster } from "@/lib/agent/types";

interface InteractiveFloorPlanProps {
  rooms?: FloorPlanRoom[];
  clusters?: PhotoCluster[];
  onRoomLinked?: (roomId: string, clusterId: string) => void;
  onAllLinked?: () => void;
}

export function InteractiveFloorPlan({
  rooms = MOCK_FLOOR_PLAN_ROOMS,
  clusters = MOCK_CLUSTERS,
  onRoomLinked,
  onAllLinked,
}: InteractiveFloorPlanProps) {
  const [links, setLinks] = useState<Record<string, string>>({});
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null);

  const linkedClusterIds = new Set(Object.values(links));
  const availableClusters = clusters.filter(
    (c) => !linkedClusterIds.has(c.id)
  );
  const allLinked = Object.keys(links).length === rooms.length;

  const handleRoomClick = useCallback((roomId: string) => {
    if (links[roomId]) return;
    setSelectedRoom((prev) => (prev === roomId ? null : roomId));
  }, [links]);

  const handleClusterSelect = useCallback(
    (clusterId: string) => {
      if (!selectedRoom) return;

      const newLinks = { ...links, [selectedRoom]: clusterId };
      setLinks(newLinks);
      setSelectedRoom(null);
      onRoomLinked?.(selectedRoom, clusterId);

      if (Object.keys(newLinks).length === rooms.length) {
        setTimeout(() => onAllLinked?.(), 600);
      }
    },
    [selectedRoom, links, rooms.length, onRoomLinked, onAllLinked]
  );

  const getClusterForRoom = (roomId: string) =>
    clusters.find((c) => c.id === links[roomId]);

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-100">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-stone-500" />
          <span className="text-sm font-medium text-stone-700">
            Floor Plan — Room Linking
          </span>
        </div>
        <span className="text-xs text-stone-400">
          {Object.keys(links).length}/{rooms.length} rooms linked
        </span>
      </div>

      <div className="flex flex-col lg:flex-row">
        {/* Floor Plan Image with Overlays */}
        <div className="flex-1 p-4 relative">
          <div className="relative aspect-[4/3] bg-stone-50 rounded-xl overflow-hidden border border-stone-100">
            <Image
              src="/mock/floorplan-segmented.png"
              alt="Floor plan"
              fill
              className="object-contain"
              sizes="(max-width: 1024px) 100vw, 50vw"
            />

            {/* Clickable Room Overlays */}
            {rooms.map((room) => {
              const isLinked = !!links[room.id];
              const isSelected = selectedRoom === room.id;
              const isHovered = hoveredRoom === room.id;
              const linkedCluster = getClusterForRoom(room.id);

              return (
                <button
                  key={room.id}
                  className={cn(
                    "absolute rounded-lg transition-all border-2",
                    isLinked
                      ? "border-emerald-500/60 bg-emerald-500/10"
                      : isSelected
                        ? "border-[#da654d] bg-[#da654d]/10 ring-2 ring-[#da654d]/30"
                        : isHovered
                          ? "border-stone-400/60 bg-stone-400/10"
                          : "border-transparent hover:border-stone-300/50 hover:bg-stone-300/10",
                    !isLinked && "cursor-pointer animate-pulse-slow"
                  )}
                  style={{
                    left: `${room.bounds.x}%`,
                    top: `${room.bounds.y}%`,
                    width: `${room.bounds.width}%`,
                    height: `${room.bounds.height}%`,
                  }}
                  onClick={() => handleRoomClick(room.id)}
                  onMouseEnter={() => setHoveredRoom(room.id)}
                  onMouseLeave={() => setHoveredRoom(null)}
                  aria-label={`${room.label} - ${room.sqm} m²${isLinked ? ` (linked to ${linkedCluster?.roomName})` : ""}`}
                  tabIndex={0}
                >
                  {isLinked && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="bg-emerald-500 text-white text-[10px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        {linkedCluster?.roomName}
                      </div>
                    </div>
                  )}
                  {isSelected && !isLinked && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="bg-[#da654d] text-white text-[10px] font-medium px-2 py-0.5 rounded-full">
                        Select photos →
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Room legend */}
          <div className="flex flex-wrap gap-2 mt-3">
            {rooms.map((room) => {
              const isLinked = !!links[room.id];
              return (
                <div
                  key={room.id}
                  className={cn(
                    "text-[11px] px-2 py-1 rounded-lg flex items-center gap-1.5",
                    isLinked
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-stone-100 text-stone-500"
                  )}
                >
                  {isLinked && <Check className="w-3 h-3" />}
                  {room.label} · {room.sqm} m²
                </div>
              );
            })}
          </div>
        </div>

        {/* Cluster Selection Panel */}
        {selectedRoom && (
          <div className="w-full lg:w-72 border-t lg:border-t-0 lg:border-l border-stone-100 p-4 bg-stone-50/50">
            <p className="text-sm font-medium text-stone-700 mb-1">
              Which room is this?
            </p>
            <p className="text-xs text-stone-400 mb-3">
              {rooms.find((r) => r.id === selectedRoom)?.label} ·{" "}
              {rooms.find((r) => r.id === selectedRoom)?.sqm} m²
            </p>

            <div className="space-y-2">
              {availableClusters.map((cluster) => (
                <button
                  key={cluster.id}
                  onClick={() => handleClusterSelect(cluster.id)}
                  className={cn(
                    "w-full flex items-center gap-3 p-2.5 rounded-xl border border-stone-200",
                    "bg-white hover:border-stone-300 hover:shadow-sm transition-all text-left"
                  )}
                  tabIndex={0}
                  aria-label={`Link to ${cluster.roomName}`}
                >
                  {/* Thumbnail strip */}
                  <div className="flex -space-x-1.5 flex-shrink-0">
                    {cluster.photos.slice(0, 3).map((photo, i) => (
                      <div
                        key={i}
                        className="w-8 h-8 rounded-md overflow-hidden border-2 border-white relative"
                      >
                        <Image
                          src={photo}
                          alt=""
                          fill
                          className="object-cover"
                          sizes="32px"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-stone-800 truncate">
                      {cluster.roomName}
                    </p>
                    <p className="text-[11px] text-stone-400">
                      {cluster.photos.length} photos
                    </p>
                  </div>
                </button>
              ))}

              {availableClusters.length === 0 && (
                <p className="text-sm text-stone-400 text-center py-4">
                  All clusters linked!
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Completion Banner */}
      {allLinked && (
        <div className="px-4 py-3 bg-emerald-50 border-t border-emerald-100 flex items-center gap-2 animate-fade-in">
          <Check className="w-4 h-4 text-emerald-600" />
          <span className="text-sm font-medium text-emerald-700">
            All rooms linked successfully!
          </span>
        </div>
      )}
    </div>
  );
}
