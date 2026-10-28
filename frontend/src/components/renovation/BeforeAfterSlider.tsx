/**
 * BeforeAfterSlider Component
 * ===========================
 *
 * Draggable comparison slider for before/after images.
 * No external dependencies - pure CSS transitions.
 */
+
'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStrings } from '@/hooks/AppStringsContext';

interface BeforeAfterSliderProps {
  beforeImage: string;
  afterImage: string;
  beforeLabel?: string;
  afterLabel?: string;
  className?: string;
  /**
   * Marketing / demo mode: auto-move the slider handle.
   * Defaults to false so listing UX is unchanged.
   */
  autoAnimate?: boolean;
  /** Interval for auto animation steps (ms). */
  autoAnimateIntervalMs?: number;
  /** Slider range for auto animation (percent). */
  autoAnimateRange?: { min: number; max: number };
  /** Suppress the built-in "← Desliza →" hint (parent provides its own). */
  hideSlideHint?: boolean;
}

export default function BeforeAfterSlider({
  beforeImage,
  afterImage,
  beforeLabel,
  afterLabel,
  className = '',
  autoAnimate = false,
  autoAnimateIntervalMs = 1800,
  autoAnimateRange = { min: 28, max: 72 },
  hideSlideHint = false,
}: BeforeAfterSliderProps) {
  const { s } = useAppStrings();
  const resolvedBeforeLabel = beforeLabel || s.before;
  const resolvedAfterLabel = afterLabel || s.after;
  const containerRef = useRef<HTMLDivElement>(null);
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [imagesLoaded, setImagesLoaded] = useState({ before: false, after: false });
  const [showHint, setShowHint] = useState(true);

  const handleMove = (clientX: number) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(percentage);
    setShowHint(false);
  };

  const handleMouseDown = () => setIsDragging(true);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    handleMove(e.clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    if (!e.touches[0]) return;
    handleMove(e.touches[0].clientX);
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false);
    window.addEventListener('mouseup', handleGlobalMouseUp);
    window.addEventListener('touchend', handleGlobalMouseUp);
    return () => {
      window.removeEventListener('mouseup', handleGlobalMouseUp);
      window.removeEventListener('touchend', handleGlobalMouseUp);
    };
  }, []);

  const allLoaded = imagesLoaded.before && imagesLoaded.after;
  const shouldAutoAnimate = autoAnimate && allLoaded && !isDragging;

  useEffect(() => {
    if (!shouldAutoAnimate) return;

    let dir: 1 | -1 = 1;
    const clamp = (n: number) => Math.max(0, Math.min(100, n));
    const min = clamp(autoAnimateRange.min);
    const max = clamp(autoAnimateRange.max);
    const step = Math.max(6, Math.round((max - min) / 3));

    const interval = window.setInterval(() => {
      setSliderPosition((prev) => {
        const next = prev + dir * step;
        if (next >= max) {
          dir = -1;
          return max;
        }
        if (next <= min) {
          dir = 1;
          return min;
        }
        return next;
      });
      setShowHint(false);
    }, autoAnimateIntervalMs);

    return () => window.clearInterval(interval);
  }, [shouldAutoAnimate, autoAnimateIntervalMs, autoAnimateRange.max, autoAnimateRange.min]);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden select-none bg-stone-100 ${className}`}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      style={{ touchAction: 'pan-y' }}
    >
      {!allLoaded && (
        <div className="absolute inset-0 bg-stone-100 flex items-center justify-center z-20">
          <div className="animate-pulse text-stone-400">{s.loadingImages}</div>
        </div>
      )}

      <img
        src={afterImage}
        alt={resolvedAfterLabel}
        className="w-full h-full object-cover"
        onLoad={() => setImagesLoaded(prev => ({ ...prev, after: true }))}
      />

      <div
        className="absolute inset-0 overflow-hidden"
        style={{
          clipPath: `inset(0 ${100 - sliderPosition}% 0 0)`,
          transition: shouldAutoAnimate ? 'clip-path 800ms ease-in-out' : undefined,
        }}
      >
        <img
          src={beforeImage}
          alt={resolvedBeforeLabel}
          className="w-full h-full object-cover"
          onLoad={() => setImagesLoaded(prev => ({ ...prev, before: true }))}
        />
      </div>

      <div
        className="absolute top-0 bottom-0 w-6 cursor-ew-resize z-10 -ml-3"
        style={{
          left: `${sliderPosition}%`,
          transition: shouldAutoAnimate ? 'left 800ms ease-in-out' : undefined,
        }}
        onMouseDown={handleMouseDown}
        onTouchStart={handleMouseDown}
      >
        <div className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-white shadow-lg" />

        <div
          className={`
            absolute left-1/2 -translate-x-1/2 -translate-y-1/2
            w-10 h-10 rounded-full bg-white shadow-lg
            flex items-center justify-center
            border-2 border-stone-200
            transition-transform duration-150
            ${isDragging ? 'scale-110' : 'hover:scale-110'}
          `}
          style={{ top: '75%' }}
        >
          <svg className="w-5 h-5 text-stone-500 rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
          </svg>
        </div>
      </div>

      <div className="absolute top-3 left-3 z-10">
        <span className="bg-black/70 text-white text-xs font-medium px-2.5 py-1 rounded-full">{resolvedBeforeLabel}</span>
      </div>
      <div className="absolute top-3 right-3 z-10">
        <span className="bg-white/90 text-stone-900 text-xs font-medium px-2.5 py-1 rounded-full shadow">
          {resolvedAfterLabel}
        </span>
      </div>

      {allLoaded && showHint && !hideSlideHint && (
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10 animate-pulse">
          <span className="bg-black/70 text-white text-xs px-2.5 py-1 rounded-full">{s.slideHint}</span>
        </div>
      )}
    </div>
  );
}

