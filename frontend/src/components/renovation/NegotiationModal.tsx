"use client";

import {appFetch as fetch} from '@/lib/app-path';

/**
 * NegotiationModal Component
 * ==========================
 *
 * Full-screen modal showing AI-generated negotiation advice.
 * Layout (top → bottom):
 *   1. Goal price hero — big target number + savings
 *   2. Main issue — with room photo evidence
 *   3. Supporting issues — compact cards with photos
 *   4. "How to frame it" — dark box with 2-3 encouraging bullets
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Loader2,
  MessageCircle,
  Shield,
  Target,
  X,
} from "lucide-react";
import { motion, AnimatePresence, useMotionValue, useTransform } from "framer-motion";
import { useAppStrings } from "@/hooks/AppStringsContext";

/* ── PhotoLightbox — Instagram-style full-screen viewer with pinch-zoom ── */

const PhotoLightbox: React.FC<{ url: string; onClose: () => void }> = ({ url, onClose }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scaleVal = useMotionValue(1);
  const xVal = useMotionValue(0);
  const yVal = useMotionValue(0);
  const bgOpacity = useTransform(yVal, [-250, 0, 250], [0.3, 1, 0.3]);

  // Gesture state refs (avoid re-renders during touch)
  const gesture = useRef({
    startTouches: null as null | { x1: number; y1: number; x2: number; y2: number },
    startScale: 1,
    startX: 0,
    startY: 0,
    lastTap: 0,
    isPinching: false,
    isPanning: false,
  });

  const dist = (x1: number, y1: number, x2: number, y2: number) =>
    Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

  const springTo = (mv: { set: (v: number) => void }, target: number, velocity = 0) => {
    const spring = { stiffness: 300, damping: 30, mass: 0.8 };
    let v = velocity;
    let current = (mv as any).get?.() ?? target;
    let raf: number;
    const step = () => {
      const dx = target - current;
      const springForce = dx * spring.stiffness;
      const dampForce = -v * spring.damping;
      const accel = (springForce + dampForce) / spring.mass;
      v += accel * (1 / 60);
      current += v * (1 / 60);
      mv.set(current);
      if (Math.abs(dx) > 0.01 || Math.abs(v) > 0.01) {
        raf = requestAnimationFrame(step);
      } else {
        mv.set(target);
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const g = gesture.current;
    if (e.touches.length === 2) {
      const [a, b] = [e.touches[0], e.touches[1]];
      g.startTouches = { x1: a.clientX, y1: a.clientY, x2: b.clientX, y2: b.clientY };
      g.startScale = scaleVal.get();
      g.isPinching = true;
    } else if (e.touches.length === 1) {
      g.startX = e.touches[0].clientX;
      g.startY = e.touches[0].clientY;
      g.isPanning = true;
      g.isPinching = false;
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const g = gesture.current;
    if (g.isPinching && e.touches.length === 2 && g.startTouches) {
      const [a, b] = [e.touches[0], e.touches[1]];
      const startDist = dist(g.startTouches.x1, g.startTouches.y1, g.startTouches.x2, g.startTouches.y2);
      const curDist = dist(a.clientX, a.clientY, b.clientX, b.clientY);
      const newScale = Math.max(0.5, Math.min(5, g.startScale * (curDist / startDist)));
      scaleVal.set(newScale);
    } else if (g.isPanning && e.touches.length === 1) {
      const dx = e.touches[0].clientX - g.startX;
      const dy = e.touches[0].clientY - g.startY;
      const s = scaleVal.get();
      if (s > 1.05) {
        xVal.set(dx);
        yVal.set(dy);
      } else {
        yVal.set(dy);
      }
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const g = gesture.current;
    if (g.isPinching && e.touches.length < 2) {
      g.isPinching = false;
      if (scaleVal.get() < 1) {
        springTo(scaleVal, 1);
        springTo(xVal, 0);
        springTo(yVal, 0);
      }
    }
    if (g.isPanning && e.touches.length === 0) {
      g.isPanning = false;
      const s = scaleVal.get();
      const y = yVal.get();
      if (s <= 1.05 && Math.abs(y) > 100) {
        onClose();
        return;
      }
      if (s <= 1.05) {
        springTo(xVal, 0);
        springTo(yVal, 0);
      }
    }
  };

  const handleTap = (e: React.MouseEvent) => {
    const now = Date.now();
    const g = gesture.current;
    if (now - g.lastTap < 300) {
      // Double-tap: toggle zoom
      const current = scaleVal.get();
      if (current > 1.2) {
        springTo(scaleVal, 1);
        springTo(xVal, 0);
        springTo(yVal, 0);
      } else {
        springTo(scaleVal, 2.5);
      }
      g.lastTap = 0;
    } else {
      g.lastTap = now;
    }
  };

  return (
    <motion.div
      ref={containerRef}
      className="fixed inset-0 z-[100] flex items-center justify-center touch-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onClick={handleTap}
    >
      <motion.div className="absolute inset-0 bg-black" style={{ opacity: bgOpacity }} />
      <button
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        aria-label="Close"
        tabIndex={0}
        className="absolute top-4 right-4 z-[101] w-10 h-10 rounded-full bg-black/50 backdrop-blur-sm text-white flex items-center justify-center"
      >
        <X className="h-5 w-5" />
      </button>
      <motion.img
        src={url}
        alt=""
        className="relative z-[1] max-w-full max-h-full object-contain select-none pointer-events-none"
        style={{ scale: scaleVal, x: xVal, y: yVal }}
        draggable={false}
      />
    </motion.div>
  );
};

/* ── Types ── */

interface NegotiationIssue {
  title: string;
  explanation: string;
  estimated_cost?: number;
  room_ids?: string[];
}

interface NegotiationData {
  asking_price: number;
  renovation_cost: number;
  total_investment: number;
  comparable_sold_price: number;
  target_price: number;
  savings: number;
  savings_pct: number;
  confidence?: "low" | "medium" | "high";
  reality_check?: string;
  main_issue: NegotiationIssue;
  supporting_issues: NegotiationIssue[];
  framing_tips: string[];
  // Legacy v1 fields (backwards compat)
  discount_estimate?: { low_eur: number; high_eur: number; low_pct: number; high_pct: number; reasoning: string };
  opening_line?: string;
  strategy_summary?: string;
}

interface NegotiationModalProps {
  isOpen: boolean;
  onClose: () => void;
  listingId: number;
}

type RoomPhotosMap = Record<string, string[]>;

/* ── Helpers ── */

const eur = (v: number): string => {
  if (!v || !Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
};

/** Pick the first photo from any of the issue's room_ids */
const pickPhoto = (roomIds: string[] | undefined, roomPhotos: Record<string, string[]>): string | null => {
  if (!roomIds) return null;
  for (const rid of roomIds) {
    const urls = roomPhotos[rid];
    if (urls && urls.length > 0) return urls[0];
  }
  return null;
};

/** Collect up to N unique photos from an issue's room_ids */
const collectPhotos = (roomIds: string[] | undefined, roomPhotos: Record<string, string[]>, max = 3): string[] => {
  if (!roomIds) return [];
  const out: string[] = [];
  for (const rid of roomIds) {
    for (const url of roomPhotos[rid] || []) {
      if (!out.includes(url)) out.push(url);
      if (out.length >= max) return out;
    }
  }
  return out;
};

export const NegotiationPanel: React.FC<{
  data: NegotiationData;
  roomPhotos?: RoomPhotosMap;
}> = ({ data, roomPhotos }) => {
  const { s, translateText, isSourceLanguage } = useAppStrings();
  const [tr, setTr] = useState<Record<string, string>>({});

  const photosMap = roomPhotos || {};
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  // Translate dynamic content (same behavior as the modal).
  useEffect(() => {
    if (isSourceLanguage || !data) {
      setTr({});
      return;
    }
    const texts: string[] = [];
    if (data.main_issue?.title) texts.push(data.main_issue.title);
    if (data.main_issue?.explanation) texts.push(data.main_issue.explanation);
    for (const issue of data.supporting_issues || []) {
      if (issue.title) texts.push(issue.title);
      if (issue.explanation) texts.push(issue.explanation);
    }
    for (const tip of data.framing_tips || []) {
      if (tip) texts.push(tip);
    }
    if (data.opening_line) texts.push(data.opening_line);
    if (texts.length === 0) return;

    const doIt = async () => {
      const map: Record<string, string> = {};
      for (const t of texts) {
        map[t] = await translateText(t);
      }
      setTr(map);
    };
    doIt();
  }, [data, isSourceLanguage, translateText]);

  const t = (text: string) => tr[text] || text;

  const targetPrice = data?.target_price || (data?.asking_price && data?.discount_estimate
    ? data.asking_price - data.discount_estimate.high_eur
    : 0);
  const savings = data?.savings || (data?.asking_price ? data.asking_price - targetPrice : 0);
  const savingsPct = data?.savings_pct || (data?.asking_price ? Math.round(savings / data.asking_price * 100) : 0);
  const tips = data?.framing_tips?.length ? data.framing_tips : (
    data?.opening_line ? [data.opening_line] : []
  );

  return (
    <div className="space-y-6">
      <div className="text-center pt-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400 mb-1">{s.targetPrice}</p>
        <p className="font-serif text-4xl font-bold text-stone-900">{eur(targetPrice)}</p>
        {savings > 0 ? (
          <p className="mt-1.5 text-emerald-600 font-medium text-sm">
            {s.savingsOf} {eur(savings)} ({savingsPct}% {s.percentLess})
          </p>
        ) : null}
        <div className="mt-3 flex items-center justify-center gap-4 text-xs text-stone-400">
          <span>{s.asked}: {eur(data.asking_price)}</span>
          <span className="w-px h-3 bg-stone-300" />
          <span>{s.renovation}: {eur(data.renovation_cost)}</span>
        </div>
      </div>

      <div className="h-px bg-stone-200/60" />

      <div>
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">{s.mainPoint}</p>
        </div>

        {(() => {
          const photos = collectPhotos(data.main_issue.room_ids, photosMap, 3);
          if (!photos.length) return null;
          return (
            <div className="flex gap-1.5 mb-3 overflow-x-auto">
              {photos.map((url, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setLightboxUrl(url)}
                  className="shrink-0 rounded-lg overflow-hidden border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400"
                  aria-label="View photo full screen"
                  tabIndex={0}
                >
                  <img src={url} alt="" className="h-24 w-auto object-cover" />
                </button>
              ))}
            </div>
          );
        })()}

        <div className="rounded-xl border-2 border-amber-200 bg-amber-50/50 p-4">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-serif text-base font-semibold text-stone-900">{t(data.main_issue.title)}</h3>
            {data.main_issue.estimated_cost ? (
              <span className="shrink-0 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                {eur(data.main_issue.estimated_cost)}
              </span>
            ) : null}
          </div>
          <p className="text-stone-600 text-sm leading-relaxed">{t(data.main_issue.explanation)}</p>
        </div>
      </div>

      {data.supporting_issues.length > 0 ? (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-stone-400" />
            <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">{s.otherArguments}</p>
          </div>
          <div className="space-y-2.5">
            {data.supporting_issues.map((issue, idx) => {
              const photo = pickPhoto(issue.room_ids, photosMap);
              return (
                <div key={idx} className="flex gap-3 rounded-xl border border-stone-200 bg-white p-3">
                  {photo ? (
                    <button
                      type="button"
                      onClick={() => setLightboxUrl(photo)}
                      className="shrink-0 rounded-lg overflow-hidden border border-stone-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
                      aria-label="View photo full screen"
                      tabIndex={0}
                    >
                      <img src={photo} alt="" className="w-16 h-16 object-cover" />
                    </button>
                  ) : null}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium text-stone-900 text-sm">{t(issue.title)}</h4>
                      {issue.estimated_cost ? (
                        <span className="shrink-0 text-[11px] font-semibold text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded-full">
                          {eur(issue.estimated_cost)}
                        </span>
                      ) : null}
                    </div>
                    <p className="text-stone-500 text-xs leading-relaxed mt-0.5">{t(issue.explanation)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {tips.length > 0 ? (
        <div className="bg-stone-900 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2.5">
            <MessageCircle className="w-4 h-4 text-stone-400" />
            <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">{s.howToFrame}</p>
          </div>
          <ul className="space-y-2">
            {tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-white/90 text-sm leading-relaxed">
                <span className="shrink-0 mt-1 w-1.5 h-1.5 rounded-full bg-[#da654d]" />
                <span>{t(tip)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="text-[11px] text-stone-400 text-center leading-relaxed">
        {s.disclaimer}
      </p>

      <AnimatePresence>
        {lightboxUrl ? (
          <PhotoLightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />
        ) : null}
      </AnimatePresence>
    </div>
  );
};

/* ── Component ── */

export const NegotiationModal: React.FC<NegotiationModalProps> = ({ isOpen, onClose, listingId }) => {
  const { s, translateText, isSourceLanguage } = useAppStrings();
  const [data, setData] = useState<NegotiationData | null>(null);
  const [roomPhotos, setRoomPhotos] = useState<RoomPhotosMap>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || data) return;
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const resp = await fetch(`/api/listings/${listingId}/negotiation`, { cache: "no-store" });
        const json = await resp.json();
        if (json?.success && json?.hasData && json?.negotiation) {
          setData(json.negotiation);
          setRoomPhotos(json.roomPhotos || {});
        } else {
          setError(s.negotiationNotReady);
        }
      } catch {
        setError(s.loadError);
      } finally {
        setIsLoading(false);
      }
    };
    void fetchData();
  }, [isOpen, listingId, data]);

  // Lock body scroll
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [isOpen]);

  // ESC
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  }, [onClose]);
  useEffect(() => {
    if (!isOpen) return;
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[80] bg-[#FDFBF7] overflow-y-auto">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-200/60">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#da654d]" />
            <span className="font-serif text-lg font-medium text-stone-900">{s.negotiation}</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 -mr-2 text-stone-400 hover:text-stone-700 rounded-full transition-colors"
            aria-label={s.close}
            tabIndex={0}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 pb-16 pt-5">
        {/* Loading */}
        {isLoading ? (
          <div className="text-center py-16">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-stone-400" />
            <p className="mt-3 text-sm text-stone-500">{s.loading}</p>
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <Shield className="mx-auto h-8 w-8 text-stone-300" />
            <p className="mt-3 text-sm text-stone-500">{error}</p>
          </div>
        ) : data ? (
          <NegotiationPanel data={data} roomPhotos={roomPhotos} />
        ) : null}
      </div>
    </div>
  );
};

export default NegotiationModal;
