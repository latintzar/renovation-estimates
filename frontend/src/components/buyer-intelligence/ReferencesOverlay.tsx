/**
 * ReferencesOverlay Component
 * ===========================
 * 
 * Modal showing sources/references from Google Search.
 * Displays categorized sources with credibility badges.
 */

"use client";

import React from 'react';
import { X, ExternalLink, Shield, ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';

interface Source {
  url: string;
  title?: string;
  domain?: string;
  category?: string;
  credibility?: string;
  credibility_method?: string;
}

interface ReferencesOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  sources: Source[];
  title?: string;
}

// Credibility badge configuration
const CREDIBILITY_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  bgColor: string;
  textColor: string;
}> = {
  high: {
    icon: ShieldCheck,
    label: "High",
    bgColor: "bg-green-50",
    textColor: "text-green-600",
  },
  "medium-high": {
    icon: ShieldCheck,
    label: "Medium-High",
    bgColor: "bg-emerald-50",
    textColor: "text-emerald-600",
  },
  medium: {
    icon: Shield,
    label: "Medium",
    bgColor: "bg-amber-50",
    textColor: "text-amber-600",
  },
  "medium-low": {
    icon: ShieldAlert,
    label: "Medium-Low",
    bgColor: "bg-orange-50",
    textColor: "text-orange-600",
  },
  low: {
    icon: ShieldAlert,
    label: "Low",
    bgColor: "bg-red-50",
    textColor: "text-red-600",
  },
  unknown: {
    icon: ShieldQuestion,
    label: "Unknown",
    bgColor: "bg-stone-50",
    textColor: "text-stone-500",
  },
};

// Category display names
const CATEGORY_LABELS: Record<string, string> = {
  costs: "Costs & Pricing",
  timings: "Duration & Timings",
  permits: "Permits & Approvals",
  laws_regulations: "Laws & Regulations",
  incentives: "Incentives & Subsidies",
  flooring: "Flooring",
  plumbing: "Plumbing",
  electrical: "Electrical",
  structure: "Structural",
  finishes: "Finishes",
};

export function ReferencesOverlay({ 
  isOpen, 
  onClose, 
  sources,
  title = "Research Sources",
}: ReferencesOverlayProps) {
  if (!isOpen) return null;

  // Group sources by category
  const groupedSources: Record<string, Source[]> = {};
  
  for (const source of sources) {
    const category = source.category || 'other';
    if (!groupedSources[category]) {
      groupedSources[category] = [];
    }
    groupedSources[category].push(source);
  }

  const categories = Object.keys(groupedSources).sort();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-stone-900">{title}</h2>
            <p className="text-sm text-stone-500 mt-0.5">
              {sources.length} sources from Google Search
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-stone-100 transition-colors"
          >
            <X className="w-5 h-5 text-stone-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          {sources.length === 0 ? (
            <div className="text-center py-12 text-stone-400">
              No sources available
            </div>
          ) : (
            <div className="space-y-6">
              {categories.map((category) => {
                const categoryLabel = CATEGORY_LABELS[category] || category;
                const categorySources = groupedSources[category];
                
                return (
                  <div key={category}>
                    <h3 className="text-sm font-semibold text-stone-600 uppercase tracking-wider mb-3">
                      {categoryLabel}
                    </h3>
                    <div className="space-y-2">
                      {categorySources.map((source, index) => {
                        const cred = source.credibility || 'unknown';
                        const credConfig = CREDIBILITY_CONFIG[cred] || CREDIBILITY_CONFIG.unknown;
                        const Icon = credConfig.icon;
                        const domain = source.domain || (() => {
                          try { return new URL(source.url).hostname; } catch { return ''; }
                        })();
                        const faviconUrl = domain 
                          ? `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
                          : null;
                        
                        // Get first letter of domain for fallback
                        const domainInitial = domain ? domain.replace('www.', '').charAt(0).toUpperCase() : '?';
                        
                        return (
                          <a
                            key={index}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex items-start gap-3 p-3 rounded-xl hover:bg-stone-50 transition-colors border border-stone-100"
                          >
                            {/* Favicon with fallback to domain initial */}
                            <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center shrink-0 overflow-hidden relative">
                              {faviconUrl ? (
                                <>
                                  {/* Fallback initial (always rendered behind) */}
                                  <span className="absolute text-sm font-semibold text-stone-400">
                                    {domainInitial}
                                  </span>
                                  {/* Favicon (overlays initial when loaded) */}
                                  <img 
                                    src={faviconUrl} 
                                    alt="" 
                                    className="w-5 h-5 relative z-10"
                                    onError={(e) => {
                                      // Hide broken image to reveal fallback initial
                                      (e.target as HTMLImageElement).style.display = 'none';
                                    }}
                                  />
                                </>
                              ) : (
                                <span className="text-sm font-semibold text-stone-400">
                                  {domainInitial}
                                </span>
                              )}
                            </div>
                            
                            {/* Source info */}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-stone-900 group-hover:text-[#da654d] transition-colors line-clamp-1">
                                {source.title || domain || source.url}
                              </div>
                              <div className="text-sm text-stone-500 truncate">
                                {domain}
                              </div>
                            </div>
                            
                            {/* Credibility badge */}
                            <div 
                              className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${credConfig.bgColor} shrink-0`}
                            >
                              <Icon className={`w-3 h-3 ${credConfig.textColor}`} />
                              <span className={`text-xs font-medium ${credConfig.textColor}`}>
                                {credConfig.label}
                              </span>
                            </div>
                          </a>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-stone-200 bg-stone-50">
          <div className="flex items-center gap-4 text-sm text-stone-500">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-green-500" />
              <span>High: Official sources</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-amber-500" />
              <span>Medium: Established sites</span>
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-red-500" />
              <span>Low: Forums, blogs</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReferencesOverlay;

