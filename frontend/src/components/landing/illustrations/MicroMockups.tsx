"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { 
  Check, 
  X, 
  Heart, 
  Star, 
  MapPin, 
  Sun, 
  Volume2, 
  Clock, 
  Sparkles,
  Send,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Home,
  User,
  MessageCircle,
  Calendar,
  FileText,
  Building
} from "lucide-react";

// ============================================================================
// MICRO PROPERTY CARDS (~100-150px)
// ============================================================================

/**
 * Tiny property card with match indicator
 */
export const MicroPropertyCard = ({ 
  title = "2-bed Gràcia",
  price = "€1,200/mo",
  match = 94,
  tags = ["Bright", "Quiet"],
  className
}: { 
  title?: string;
  price?: string;
  match?: number;
  tags?: string[];
  className?: string;
}) => {
  return (
    <div className={cn(
      "w-[140px] bg-white rounded-lg shadow-md border border-stone-200 overflow-hidden",
      className
    )}>
      {/* Mini image placeholder */}
      <div className="h-16 bg-gradient-to-br from-stone-200 to-stone-300 relative">
        <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 bg-emerald-500 text-white text-[8px] font-bold rounded">
          {match}%
        </div>
      </div>
      <div className="p-2">
        <div className="text-[10px] font-semibold text-stone-900 truncate">{title}</div>
        <div className="text-[9px] text-stone-500">{price}</div>
        <div className="flex gap-1 mt-1">
          {tags.slice(0, 2).map((tag, i) => (
            <span key={i} className="text-[7px] px-1 py-0.5 bg-stone-100 rounded text-stone-600">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * Micro checklist card
 */
export const MicroChecklist = ({ 
  items = ["Check noise", "Ask fees", "Look corners"],
  className
}: { 
  items?: string[];
  className?: string;
}) => {
  return (
    <div className={cn(
      "w-[130px] bg-white rounded-lg shadow-md border border-stone-200 p-2",
      className
    )}>
      <div className="text-[9px] font-bold text-stone-900 mb-1.5 flex items-center gap-1">
        <FileText className="w-3 h-3 text-blue-500" />
        Checklist
      </div>
      <div className="space-y-1">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-1.5 text-[8px] text-stone-600">
            <div className={cn(
              "w-2.5 h-2.5 rounded border flex items-center justify-center",
              i === 0 ? "bg-green-100 border-green-300" : "border-stone-300"
            )}>
              {i === 0 && <Check className="w-2 h-2 text-green-600" />}
            </div>
            <span className="truncate">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Micro fit badge - super small
 */
export const MicroFitBadge = ({ 
  score = 92,
  label = "Strong fit",
  className 
}: { 
  score?: number;
  label?: string;
  className?: string;
}) => {
  const color = score >= 90 ? "emerald" : score >= 70 ? "amber" : "red";
  const colorClasses = {
    emerald: "bg-emerald-100 text-emerald-700 border-emerald-200",
    amber: "bg-amber-100 text-amber-700 border-amber-200",
    red: "bg-red-100 text-red-700 border-red-200"
  };
  
  return (
    <div className={cn(
      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[8px] font-medium",
      colorClasses[color],
      className
    )}>
      <Sparkles className="w-2 h-2" />
      <span>{score}%</span>
    </div>
  );
};

// ============================================================================
// MICRO FEEDBACK/REACTION ELEMENTS
// ============================================================================

/**
 * Quick reaction buttons
 */
export const MicroReactions = ({ className }: { className?: string }) => {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      <button className="w-7 h-7 rounded-full bg-green-100 flex items-center justify-center hover:bg-green-200 transition-colors">
        <ThumbsUp className="w-3 h-3 text-green-600" />
      </button>
      <button className="w-7 h-7 rounded-full bg-stone-100 flex items-center justify-center hover:bg-stone-200 transition-colors">
        <span className="text-[10px]">🤔</span>
      </button>
      <button className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center hover:bg-red-200 transition-colors">
        <ThumbsDown className="w-3 h-3 text-red-600" />
      </button>
    </div>
  );
};

/**
 * Viewing note tag
 */
export const MicroViewingNote = ({ 
  note = "Too dark",
  type = "negative"
}: { 
  note?: string;
  type?: "positive" | "negative" | "neutral";
}) => {
  const typeClasses = {
    positive: "bg-green-100 text-green-700 border-green-200",
    negative: "bg-red-100 text-red-700 border-red-200",
    neutral: "bg-stone-100 text-stone-600 border-stone-200"
  };
  
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-medium",
      typeClasses[type]
    )}>
      {type === "positive" && <Check className="w-2 h-2" />}
      {type === "negative" && <X className="w-2 h-2" />}
      {note}
    </span>
  );
};

// ============================================================================
// MICRO CHAT/MESSAGE ELEMENTS
// ============================================================================

/**
 * Leo chat bubble - tiny
 */
export const MicroLeoBubble = ({ 
  message = "I found 3 places in Gràcia",
  className
}: { 
  message?: string;
  className?: string;
}) => {
  return (
    <div className={cn("flex items-start gap-1.5", className)}>
      <div className="w-5 h-5 rounded-full bg-stone-900 flex items-center justify-center shrink-0">
        <span className="text-[8px] text-white font-bold">L</span>
      </div>
      <div className="bg-stone-100 rounded-lg rounded-tl-none px-2 py-1 text-[9px] text-stone-700 max-w-[120px]">
        {message}
      </div>
    </div>
  );
};

/**
 * User message bubble - tiny
 */
export const MicroUserBubble = ({ 
  message = "Near the beach please",
  className
}: { 
  message?: string;
  className?: string;
}) => {
  return (
    <div className={cn("flex justify-end", className)}>
      <div className="bg-stone-900 text-white rounded-lg rounded-tr-none px-2 py-1 text-[9px] max-w-[120px]">
        {message}
      </div>
    </div>
  );
};

// ============================================================================
// MICRO STATUS/PROGRESS ELEMENTS
// ============================================================================

/**
 * Assignee status pill (for Relocation)
 */
export const MicroAssigneeStatus = ({ 
  name = "Ana",
  city = "Madrid",
  status = "Searching"
}: { 
  name?: string;
  city?: string;
  status?: "Searching" | "Shortlist" | "Settled";
}) => {
  const statusColors = {
    Searching: "bg-blue-100 text-blue-700",
    Shortlist: "bg-amber-100 text-amber-700",
    Settled: "bg-green-100 text-green-700"
  };
  
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-1.5 bg-white rounded-lg border border-stone-200 shadow-sm">
      <div className="flex items-center gap-1.5">
        <div className="w-5 h-5 rounded-full bg-stone-200 flex items-center justify-center">
          <User className="w-3 h-3 text-stone-500" />
        </div>
        <div>
          <div className="text-[9px] font-medium text-stone-900">{name}</div>
          <div className="text-[7px] text-stone-500">{city}</div>
        </div>
      </div>
      <span className={cn("text-[7px] font-medium px-1.5 py-0.5 rounded-full", statusColors[status])}>
        {status}
      </span>
    </div>
  );
};

/**
 * Client fit indicator (for Buyer Agents)
 */
export const MicroClientFit = ({ 
  clientName = "Marta P.",
  fit = 87,
  className
}: { 
  clientName?: string;
  fit?: number;
  className?: string;
}) => {
  return (
    <div className={cn(
      "flex items-center gap-2 px-2 py-1.5 bg-white rounded-lg border border-stone-200 shadow-sm",
      className
    )}>
      <div className="text-[9px]">
        <span className="text-stone-500">For</span>{" "}
        <span className="font-medium text-stone-900">{clientName}</span>
      </div>
      <MicroFitBadge score={fit} />
    </div>
  );
};

// ============================================================================
// MICRO ALERT/WARNING ELEMENTS
// ============================================================================

/**
 * Red flag indicator
 */
export const MicroRedFlag = ({ 
  text = "Aluminosis risk",
  className
}: { 
  text?: string;
  className?: string;
}) => {
  return (
    <div className={cn(
      "inline-flex items-center gap-1 px-2 py-1 bg-red-50 border border-red-200 rounded-lg",
      className
    )}>
      <AlertTriangle className="w-3 h-3 text-red-500" />
      <span className="text-[9px] font-medium text-red-700">{text}</span>
    </div>
  );
};

/**
 * Green check indicator
 */
export const MicroGreenCheck = ({ 
  text = "ITE passed",
  className
}: { 
  text?: string;
  className?: string;
}) => {
  return (
    <div className={cn(
      "inline-flex items-center gap-1 px-2 py-1 bg-green-50 border border-green-200 rounded-lg",
      className
    )}>
      <Check className="w-3 h-3 text-green-500" />
      <span className="text-[9px] font-medium text-green-700">{text}</span>
    </div>
  );
};

// ============================================================================
// COMPOUND MICRO MOCKUPS
// ============================================================================

/**
 * "Send to Leo" extension button
 */
export const MicroSendToLeo = ({ className }: { className?: string }) => {
  return (
    <div className={cn(
      "inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-stone-900 text-white rounded-lg shadow-md",
      className
    )}>
      <Send className="w-3 h-3" />
      <span className="text-[10px] font-medium">Send to Leo</span>
    </div>
  );
};

/**
 * Mini notification card
 */
export const MicroNotification = ({ 
  title = "New match",
  subtitle = "2-bed in Gràcia",
  className
}: { 
  title?: string;
  subtitle?: string;
  className?: string;
}) => {
  return (
    <div className={cn(
      "flex items-center gap-2 px-2.5 py-2 bg-white rounded-lg border border-stone-200 shadow-lg w-[150px]",
      className
    )}>
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-stone-200 to-stone-300 shrink-0" />
      <div className="min-w-0">
        <div className="text-[9px] font-semibold text-stone-900">{title}</div>
        <div className="text-[8px] text-stone-500 truncate">{subtitle}</div>
      </div>
    </div>
  );
};

/**
 * Mini price comparison
 */
export const MicroPriceCompare = ({ className }: { className?: string }) => {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="text-center">
        <div className="text-[8px] text-stone-400">Asking</div>
        <div className="text-[11px] font-bold text-stone-900">€450k</div>
      </div>
      <div className="text-[10px] text-stone-400">vs</div>
      <div className="text-center">
        <div className="text-[8px] text-stone-400">Leo's est.</div>
        <div className="text-[11px] font-bold text-emerald-600">€420k</div>
      </div>
    </div>
  );
};

/**
 * Mini timeline indicator
 */
export const MicroTimeline = ({ 
  current = 2,
  total = 4,
  className 
}: { 
  current?: number;
  total?: number;
  className?: string;
}) => {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {Array.from({ length: total }).map((_, i) => (
        <div 
          key={i}
          className={cn(
            "w-2 h-2 rounded-full transition-colors",
            i < current ? "bg-emerald-500" : "bg-stone-200"
          )}
        />
      ))}
      <span className="text-[8px] text-stone-500 ml-1">{current}/{total}</span>
    </div>
  );
};

