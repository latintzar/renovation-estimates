"use client";

import { cn } from "@/lib/utils";
import { Check, AlertTriangle, HelpCircle, FileText } from "lucide-react";
import { MOCK_DOCUMENTS } from "@/lib/agent/mock-data";
import type { ClassifiedDocument } from "@/lib/agent/types";

interface DocumentCardsProps {
  documents?: ClassifiedDocument[];
}

const STATUS_CONFIG = {
  classified: {
    icon: <Check className="w-3.5 h-3.5" />,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    label: "Classified",
  },
  needs_review: {
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
    label: "Needs Review",
  },
  unrecognized: {
    icon: <HelpCircle className="w-3.5 h-3.5" />,
    color: "text-stone-500",
    bg: "bg-stone-50",
    border: "border-stone-200",
    label: "Unrecognized",
  },
} as const;

export function DocumentCards({ documents = MOCK_DOCUMENTS }: DocumentCardsProps) {
  return (
    <div className="w-full rounded-2xl bg-white border border-stone-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-100">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-stone-500" />
          <span className="text-sm font-medium text-stone-700">Documents Classified</span>
        </div>
        <span className="text-xs text-stone-400">
          {documents.filter((d) => d.status === "classified").length}/{documents.length} classified
        </span>
      </div>

      <div className="p-3 space-y-2">
        {documents.map((doc) => {
          const config = STATUS_CONFIG[doc.status];
          return (
            <div
              key={doc.id}
              className={cn(
                "rounded-xl border p-3 transition-all",
                config.border,
                config.bg
              )}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl flex-shrink-0 mt-0.5">{doc.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-stone-800">
                      {doc.documentType}
                    </span>
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium",
                        config.bg,
                        config.color
                      )}
                    >
                      {config.icon}
                      {config.label}
                    </span>
                  </div>
                  <p className="text-[11px] text-stone-400 mb-2 truncate">
                    {doc.fileName}
                  </p>

                  {/* Extracted fields */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(doc.extractedFields).map(([key, value]) => (
                      <div key={key} className="flex items-baseline gap-1.5">
                        <span className="text-[11px] text-stone-400 flex-shrink-0">
                          {key}:
                        </span>
                        <span
                          className={cn(
                            "text-[11px] font-medium truncate",
                            value.includes("EXPIRED")
                              ? "text-red-600"
                              : "text-stone-700"
                          )}
                        >
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>

                  {doc.linkedRoom && (
                    <div className="mt-2 text-[11px] text-stone-400">
                      Linked to: <span className="text-stone-600 font-medium">{doc.linkedRoom}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
