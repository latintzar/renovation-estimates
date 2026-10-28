"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

type BeforeAfterProps = {
  before: string;
  after: string;
  altBefore?: string;
  altAfter?: string;
  className?: string;
  caption?: string;
  // Optional: For multiple room views
  rooms?: Array<{
    before: string;
    after: string;
    roomName: string;
  }>;
};

export function BeforeAfter({
  before,
  after,
  altBefore = "Before",
  altAfter = "After",
  className,
  caption,
  rooms,
}: BeforeAfterProps) {
  const [pos, setPos] = React.useState(50); // percent
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [loadError, setLoadError] = React.useState({ before: false, after: false });
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  // If rooms array provided, use that; otherwise use single before/after
  const allRooms = rooms || [{ before, after, roomName: "Room" }];
  const currentRoom = allRooms[currentIndex];
  const hasMultiple = allRooms.length > 1;

  // Navigation handlers
  const goToPrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : allRooms.length - 1));
    setLoadError({ before: false, after: false });
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < allRooms.length - 1 ? prev + 1 : 0));
    setLoadError({ before: false, after: false });
  };

  // Mouse & Touch drag functionality
  const [isDragging, setIsDragging] = React.useState(false);

  // Position calculation helper
  const setPosFromClientX = React.useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = Math.min(Math.max(0, clientX - rect.left), rect.width);
    const next = Math.round((x / rect.width) * 100);
    setPos(next);
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
    setPosFromClientX(e.clientX);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    e.stopPropagation();
    setIsDragging(true);
    if (e.touches.length > 0) {
      setPosFromClientX(e.touches[0].clientX);
    }
  };

  const handleMouseMove = React.useCallback((e: MouseEvent) => {
    setPosFromClientX(e.clientX);
  }, [setPosFromClientX]);

  const handleTouchMove = React.useCallback((e: TouchEvent) => {
    if (e.touches.length > 0) {
      e.preventDefault(); // Prevent scrolling while dragging
      setPosFromClientX(e.touches[0].clientX);
    }
  }, [setPosFromClientX]);

  const handleEnd = React.useCallback(() => {
    setIsDragging(false);
  }, []);

  React.useEffect(() => {
    if (isDragging) {
      // Mouse events
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleEnd);
      // Touch events
      document.addEventListener('touchmove', handleTouchMove, { passive: false });
      document.addEventListener('touchend', handleEnd);
      document.addEventListener('touchcancel', handleEnd);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleEnd);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleEnd);
        document.removeEventListener('touchcancel', handleEnd);
      };
    }
  }, [isDragging, handleMouseMove, handleTouchMove, handleEnd]);

  return (
    <div className={cn("w-full h-full relative", className)}>
      <div
        ref={containerRef}
        className="relative h-full overflow-hidden bg-stone-200 rounded-xl"
        role="group"
        aria-label="Before/After comparison"
      >
        {/* Before layer */}
        {currentRoom.before && !loadError.before ? (
          <img
            key={`before-${currentRoom.before}-${currentIndex}`}
            src={currentRoom.before}
            alt={altBefore}
            className="absolute inset-0 h-full w-full object-cover select-none"
            draggable={false}
            loading="eager"
            onError={() => setLoadError((prev) => ({ ...prev, before: true }))}
          />
        ) : (
          <div className="absolute inset-0 h-full w-full bg-stone-200 flex items-center justify-center text-stone-500 text-sm">
            {loadError.before ? "Failed to load before image" : "No before image"}
          </div>
        )}

        {/* After layer clipped by pos (reveal on the RIGHT side) */}
        {currentRoom.after && !loadError.after && (
          <div
            key={`after-container-${currentRoom.after}-${currentIndex}`}
            className="absolute inset-0"
            style={{ clipPath: `inset(0 0 0 ${pos}%)` }}
            aria-hidden="true"
          >
            <img
              key={`after-${currentRoom.after}-${currentIndex}`}
              src={currentRoom.after}
              alt={altAfter}
              className="absolute inset-0 h-full w-full object-cover select-none"
              draggable={false}
              loading="eager"
              onError={() => setLoadError((prev) => ({ ...prev, after: true }))}
            />
          </div>
        )}

        {/* Labels */}
        <div className="absolute top-3 left-3 px-2 py-1 bg-black/60 backdrop-blur-sm rounded text-xs text-white font-medium">
          ANTES
        </div>
        <div className="absolute top-3 right-3 px-2 py-1 bg-black/60 backdrop-blur-sm rounded text-xs text-white font-medium">
          DESPUÉS
        </div>

        {/* Handle + track - Interactive (Mouse + Touch) */}
        <div 
          className="absolute inset-0 touch-none" 
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
        >
          {/* Vertical track line */}
          <div className="absolute inset-y-0" style={{ left: `calc(${pos}% - 1px)` }}>
            <div className="h-full w-0.5 bg-white/90 shadow-[0_0_0_1px_rgba(0,0,0,0.25)]" />
          </div>

          {/* Interactive handle - positioned at 75% from top (closer to bottom) */}
          <div
            className="absolute"
            style={{ 
              left: `calc(${pos}% - 20px)`,
              top: '75%',
              transform: 'translateY(-50%)'
            }}
          >
            <div
              className="pointer-events-auto h-10 w-10 rounded-full border-2 border-white bg-black/70 backdrop-blur-md shadow-xl flex items-center justify-center relative cursor-ew-resize"
              role="slider"
              aria-label="Before/After slider"
              tabIndex={0}
            >
              {/* Chevron icons */}
              <div className="absolute inset-0 flex items-center justify-center gap-1 text-white select-none">
                <svg aria-hidden viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-none stroke-current stroke-[2.5]">
                  <path d="M14.5 6.5 9 12l5.5 5.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <svg aria-hidden viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-none stroke-current stroke-[2.5]">
                  <path d="M9.5 17.5 15 12 9.5 6.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation arrows on sides - only show if multiple rooms */}
        {hasMultiple && (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); goToPrev(); }}
              className="absolute left-2 top-1/2 -translate-y-1/2 z-10 h-10 w-10 rounded-full bg-black/50 hover:bg-black/70 backdrop-blur-sm flex items-center justify-center transition-colors"
              aria-label="Previous room"
            >
              <ChevronLeft className="w-6 h-6 text-white" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); goToNext(); }}
              className="absolute right-2 top-1/2 -translate-y-1/2 z-10 h-10 w-10 rounded-full bg-black/50 hover:bg-black/70 backdrop-blur-sm flex items-center justify-center transition-colors"
              aria-label="Next room"
            >
              <ChevronRight className="w-6 h-6 text-white" />
            </button>
          </>
        )}

        {/* Room name indicator - show if multiple rooms */}
        {hasMultiple && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-black/60 backdrop-blur-sm rounded-full text-xs text-white font-medium">
            {currentRoom.roomName || `Room ${currentIndex + 1}`} ({currentIndex + 1}/{allRooms.length})
          </div>
        )}
      </div>

      {/* Caption */}
      {caption && (
        <p className="text-xs text-stone-500 text-center mt-2">{caption}</p>
      )}
    </div>
  );
}
