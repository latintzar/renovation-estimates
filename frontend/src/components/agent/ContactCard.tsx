"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Phone, Star, Clock, Mic, Play, Pause } from "lucide-react";
import { MOCK_CONTACTS } from "@/lib/agent/mock-data";
import type { TrustedContact } from "@/lib/agent/types";

interface ContactCardProps {
  contact?: TrustedContact;
  contactIndex?: number;
}

export function ContactCard({ contact, contactIndex = 0 }: ContactCardProps) {
  const c = contact ?? MOCK_CONTACTS[contactIndex];
  if (!c) return null;

  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-lg font-semibold">
              {c.name.split(" ").map((n) => n[0]).join("")}
            </span>
          </div>

          <div className="flex-1 min-w-0">
            {/* Name + Phone */}
            <div className="flex items-center gap-2 mb-0.5">
              <h4 className="font-medium text-stone-900 text-[15px]">{c.name}</h4>
              <div className="flex items-center gap-0.5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={cn(
                      "w-3 h-3",
                      i < c.rating ? "text-amber-400 fill-amber-400" : "text-stone-200"
                    )}
                  />
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3 text-sm text-stone-500 mb-3">
              <div className="flex items-center gap-1">
                <Phone className="w-3 h-3" />
                {c.phone}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {c.yearsKnown} years
              </div>
            </div>

            {/* Trade + Specialty */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
                🔧 {c.trade}
              </span>
              <span className="text-xs text-stone-400">{c.specialty}</span>
            </div>

            {/* Strengths */}
            <div className="mb-2">
              <p className="text-[11px] text-stone-400 uppercase tracking-wider mb-1">
                Strengths
              </p>
              <div className="flex flex-wrap gap-1.5">
                {c.strengths.map((s) => (
                  <span
                    key={s}
                    className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700"
                  >
                    ✓ {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Weaknesses */}
            {c.weaknesses.length > 0 && (
              <div className="mb-2">
                <p className="text-[11px] text-stone-400 uppercase tracking-wider mb-1">
                  Note
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {c.weaknesses.map((w) => (
                    <span
                      key={w}
                      className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700"
                    >
                      ⚠ {w}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Personality */}
            <p className="text-xs text-stone-500 italic mt-2">
              &ldquo;{c.personality}&rdquo;
            </p>

            {/* Voice Note Player */}
            {c.voiceNoteDuration && (
              <VoiceNotePlayer durationSec={c.voiceNoteDuration} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function VoiceNotePlayer({ durationSec }: { durationSec: number }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          setIsPlaying(false);
          return 0;
        }
        return p + 100 / (durationSec * 10);
      });
    }, 100);
    return () => clearInterval(interval);
  }, [isPlaying, durationSec]);

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="mt-3 flex items-center gap-3 px-3 py-2 bg-stone-50 rounded-xl">
      <button
        onClick={() => {
          setIsPlaying(!isPlaying);
          if (!isPlaying) setProgress(0);
        }}
        className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center flex-shrink-0 hover:bg-blue-600 transition-colors"
        aria-label={isPlaying ? "Pause" : "Play voice note"}
        tabIndex={0}
      >
        {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
      </button>

      {/* Waveform */}
      <div className="flex-1 flex items-center gap-[2px] h-6">
        {Array.from({ length: 40 }).map((_, i) => {
          const height = 20 + Math.sin(i * 0.8) * 40 + Math.random() * 30;
          const isActive = (i / 40) * 100 <= progress;
          return (
            <div
              key={i}
              className={cn(
                "w-[3px] rounded-full transition-colors",
                isActive ? "bg-blue-500" : "bg-stone-300"
              )}
              style={{ height: `${height}%` }}
            />
          );
        })}
      </div>

      <span className="text-[11px] text-stone-400 flex-shrink-0 tabular-nums">
        {isPlaying
          ? formatTime((progress / 100) * durationSec)
          : formatTime(durationSec)}
      </span>

      <Mic className="w-3.5 h-3.5 text-stone-300 flex-shrink-0" />
    </div>
  );
}
