import React, { useEffect, useMemo, useRef, useState } from "react";
import { Check, Copy, Share2, X } from "lucide-react";
import { useAppStrings } from "@/hooks/AppStringsContext";

type ELI5RoomLike = {
  room_id?: string;
  room_name?: string;
  tagline?: string;
  estimated_m2?: number;
  cost?: number;
};

type ELI5SummaryLike = {
  rooms?: ELI5RoomLike[];
  concept?: {
    intro_before?: string;
    intro_after?: string;
    vision_statement?: string;
    design_style?: string;
    value_story?: string;
  };
  property_summary?: {
    address?: string;
  };
};

type ShareModalProps = {
  isOpen: boolean;
  onClose: () => void;
  listingId: number;
  address?: string;
  eli5?: ELI5SummaryLike | null;
  /** When true, the "Compartir enlace" button shares the contractor view URL. */
  isContractorView?: boolean;
};

type ShareModalPanelProps = Omit<ShareModalProps, "isOpen"> & {
  /** Render the panel UI without fixed backdrop (for marketing mockups). */
  readOnly?: boolean;
};

const formatRoomM2 = (m2: unknown): string | null => {
  const n = typeof m2 === "number" ? m2 : Number(m2);
  if (!Number.isFinite(n) || n <= 0) return null;
  return `${Math.round(n)} m2`;
};

const copyToClipboard = async (text: string): Promise<boolean> => {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers / non-secure contexts.
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.top = "0";
      ta.style.left = "0";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
};

export const ShareModal: React.FC<ShareModalProps> = ({
  isOpen,
  onClose,
  listingId,
  address,
  eli5,
  isContractorView,
}) => {
  const { s: strings } = useAppStrings();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  const [shareCopied, setShareCopied] = useState(false);
  const [briefCopied, setBriefCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose]);

  const PRODUCTION_ORIGIN = "https://app.leo.casa";

  const contractorUrl = useMemo(() => {
    if (!isOpen) return "";
    try {
      const url = new URL(`/listing/${listingId}`, PRODUCTION_ORIGIN);
      url.searchParams.set("view", "contractor");
      return url.toString();
    } catch {
      return "";
    }
  }, [isOpen, listingId]);

  const displayAddress = useMemo(() => {
    const a = String(address || "").trim();
    if (a) return a;
    const fromEli5 = String(eli5?.property_summary?.address || "").trim();
    return fromEli5 || (strings.addressNotAvailable ?? "Address not available");
  }, [address, eli5, strings.addressNotAvailable]);

  const roomsForBrief = useMemo(() => {
    const rooms = Array.isArray(eli5?.rooms) ? eli5?.rooms : [];
    const withCost = rooms.filter(r => typeof r?.cost === "number");
    if (withCost.length === rooms.length) {
      return [...rooms].sort((a, b) => Number(b.cost || 0) - Number(a.cost || 0));
    }
    return rooms;
  }, [eli5]);

  const briefText = useMemo(() => {
    const title = strings.contractorBriefTitle ?? "Renovation brief";
    const intro = strings.contractorBriefIntro ?? "Hi \u2014 I\u2019d like a quote for renovation works on this property.";
    const roomsLabel = strings.contractorBriefRooms ?? "Rooms";
    const viewLabel = strings.contractorBriefLinkLabel ?? "Full details";

    const roomLines = roomsForBrief
      .map((r) => {
        const name = String(r?.room_name || "").trim();
        const tagline = String(r?.tagline || "").trim();
        const m2 = formatRoomM2(r?.estimated_m2);
        if (!name && !tagline) return null;
        const sizePart = m2 ? ` (~${m2})` : "";
        const desc = tagline ? ` \u2013 ${tagline}` : "";
        return `  \u2022 ${name || "Room"}${sizePart}${desc}`;
      })
      .filter(Boolean)
      .join("\n");

    const lines = [
      `*${title}*`,
      ``,
      intro,
      ``,
      `\uD83C\uDFE0 *${strings.detail ?? "Property"}:* ${displayAddress}`,
      ``,
      `\uD83D\uDDD8 *${roomsLabel}:*`,
      roomLines || `  \u2022 ${strings.contractorBriefNotReady ?? "Room breakdown not available yet"}`,
      ``,
      `\uD83D\uDD17 *${viewLabel}:*`,
      contractorUrl || "",
    ];

    return lines.join("\n").trim();
  }, [
    contractorUrl,
    displayAddress,
    roomsForBrief,
    strings.contractorBriefIntro,
    strings.contractorBriefLinkLabel,
    strings.contractorBriefNotReady,
    strings.contractorBriefRooms,
    strings.contractorBriefTitle,
    strings.detail,
  ]);

  const shareUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    try {
      const url = new URL(window.location.pathname, PRODUCTION_ORIGIN);
      url.search = window.location.search;
      return url.toString();
    } catch {
      return `${PRODUCTION_ORIGIN}/listing/${listingId}`;
    }
  }, [listingId]);

  const handleShareLink = async () => {
    if (!shareUrl) return;

    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title: "An\u00e1lisis de reforma", url: shareUrl });
        return;
      } catch {
        // User cancelled or browser rejected; fall back to copy.
      }
    }

    const ok = await copyToClipboard(shareUrl);
    if (!ok) return;
    setShareCopied(true);
    window.setTimeout(() => setShareCopied(false), 2000);
  };

  const handleCopyBrief = async () => {
    const ok = await copyToClipboard(briefText);
    if (!ok) return;
    setBriefCopied(true);
    window.setTimeout(() => setBriefCopied(false), 2000);
  };

  if (!isOpen) return null;
  return (
    <div
      className="fixed inset-0 z-[60] flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-modal-title"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <ShareModalPanel
        listingId={listingId}
        address={address}
        eli5={eli5}
        isContractorView={isContractorView}
        onClose={onClose}
        readOnly={false}
      />
    </div>
  );
};

// =============================================================================
// SHARE MODAL PANEL — Full-screen warm cream sheet
// =============================================================================
// Used both by the ShareModal overlay and standalone (marketing mockups).
// Design: calm, warm, on-brand (#FDFBF7 cream), with prominent action buttons.
// =============================================================================

export const ShareModalPanel: React.FC<ShareModalPanelProps> = ({
  onClose,
  listingId,
  address,
  eli5,
  readOnly = false,
  isContractorView = false,
}) => {
  const { s: strings } = useAppStrings();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  const [shareCopied, setShareCopied] = useState(false);
  const [briefCopied, setBriefCopied] = useState(false);

  const PRODUCTION_ORIGIN = "https://app.leo.casa";

  const contractorUrl = useMemo(() => {
    try {
      const url = new URL(`/listing/${listingId}`, PRODUCTION_ORIGIN);
      url.searchParams.set("view", "contractor");
      return url.toString();
    } catch {
      return "";
    }
  }, [listingId]);

  const displayAddress = useMemo(() => {
    const a = String(address || "").trim();
    if (a) return a;
    const fromEli5 = String(eli5?.property_summary?.address || "").trim();
    return fromEli5 || (strings.addressNotAvailable ?? "Address not available");
  }, [address, eli5, strings.addressNotAvailable]);

  const roomsForBrief = useMemo(() => {
    const rooms = Array.isArray(eli5?.rooms) ? eli5?.rooms : [];
    const withCost = rooms.filter((r) => typeof r?.cost === "number");
    if (withCost.length === rooms.length) {
      return [...rooms].sort((a, b) => Number(b.cost || 0) - Number(a.cost || 0));
    }
    return rooms;
  }, [eli5]);

  const briefText = useMemo(() => {
    const title = strings.contractorBriefTitle ?? "Renovation brief";
    const intro =
      strings.contractorBriefIntro ??
      "Hi \u2014 I\u2019d like a quote for renovation works on this property.";
    const roomsLabel = strings.contractorBriefRooms ?? "Rooms";
    const viewLabel = strings.contractorBriefLinkLabel ?? "Full details";

    const roomLines = roomsForBrief
      .map((r) => {
        const name = String(r?.room_name || "").trim();
        const tagline = String(r?.tagline || "").trim();
        const m2 = formatRoomM2(r?.estimated_m2);
        if (!name && !tagline) return null;
        const sizePart = m2 ? ` (~${m2})` : "";
        const desc = tagline ? ` \u2013 ${tagline}` : "";
        return `  \u2022 ${name || "Room"}${sizePart}${desc}`;
      })
      .filter(Boolean)
      .join("\n");

    const lines = [
      `*${title}*`,
      ``,
      intro,
      ``,
      `\uD83C\uDFE0 *${strings.detail ?? "Property"}:* ${displayAddress}`,
      ``,
      `\uD83D\uDDD8 *${roomsLabel}:*`,
      roomLines ||
        `  \u2022 ${strings.contractorBriefNotReady ?? "Room breakdown not available yet"}`,
      ``,
      `\uD83D\uDD17 *${viewLabel}:*`,
      contractorUrl || "",
    ];

    return lines.join("\n").trim();
  }, [
    contractorUrl,
    displayAddress,
    roomsForBrief,
    strings.contractorBriefIntro,
    strings.contractorBriefLinkLabel,
    strings.contractorBriefNotReady,
    strings.contractorBriefRooms,
    strings.contractorBriefTitle,
    strings.detail,
  ]);

  const shareUrl = useMemo(() => {
    try {
      const url = new URL(`/listing/${listingId}`, PRODUCTION_ORIGIN);
      if (isContractorView) url.searchParams.set("view", "contractor");
      return url.toString();
    } catch {
      return `${PRODUCTION_ORIGIN}/listing/${listingId}`;
    }
  }, [listingId, isContractorView]);

  const handleShareLink = async () => {
    if (readOnly) return;
    if (!shareUrl) return;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title: "An\u00e1lisis de reforma", url: shareUrl });
        return;
      } catch {
        // fall back to copy
      }
    }
    const ok = await copyToClipboard(shareUrl);
    if (!ok) return;
    setShareCopied(true);
    window.setTimeout(() => setShareCopied(false), 2000);
  };

  const handleCopyBrief = async () => {
    if (readOnly) return;
    const ok = await copyToClipboard(briefText);
    if (!ok) return;
    setBriefCopied(true);
    window.setTimeout(() => setBriefCopied(false), 2000);
  };

  return (
    <div
      className="relative w-full h-full flex flex-col bg-[#FDFBF7] overflow-y-auto animate-slide-up sm:max-w-lg sm:mx-auto sm:my-8 sm:rounded-2xl sm:h-auto sm:max-h-[90vh] sm:shadow-2xl"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#FDFBF7]/95 backdrop-blur-sm border-b border-stone-100">
        <div className="flex items-center justify-between px-5 py-4">
          <h2
            id="share-modal-title"
            className="font-serif text-lg font-medium text-stone-800"
          >
            {strings.shareWithContractor ?? strings.share ?? "Share"}
          </h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="rounded-full p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 focus:outline-none focus:ring-2 focus:ring-stone-300 transition-colors"
            aria-label={strings.cancel ?? "Close"}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 px-5 py-6 space-y-5">
        {/* ── Share Link — normal listing URL, centered compact pill ── */}
        <div className="flex justify-center">
          <button
            onClick={handleShareLink}
            type="button"
            className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all duration-200 ${
              shareCopied
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-white text-stone-700 border border-stone-200 hover:border-stone-300 hover:shadow-sm active:scale-[0.97]"
            }`}
            aria-label={strings.shareLink ?? strings.share ?? "Share link"}
          >
            {shareCopied ? (
              <Check className="h-4 w-4 text-emerald-600" />
            ) : (
              <Share2 className="h-4 w-4 text-stone-400" />
            )}
            {shareCopied
              ? (strings.briefCopied ?? "Copied!")
              : (strings.shareLink ?? "Compartir enlace")}
          </button>
        </div>

        {/* ── Divider ── */}
        <div className="h-px bg-stone-200/80" />

        {/* ── Contractor Resumen Card — gradient border + dark copy header ── */}
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-3">
            Resumen para contratista
          </p>
          <div className="relative p-[2px] rounded-2xl bg-gradient-to-r from-violet-500 via-fuchsia-500 via-rose-500 via-amber-500 to-emerald-500 animate-gradient-x">
            <div className="rounded-2xl bg-white overflow-hidden">
              {/* Dark copy header */}
              <button
                onClick={handleCopyBrief}
                type="button"
                className={`w-full px-5 py-3.5 flex items-center justify-between transition-all duration-200 ${
                  briefCopied
                    ? "bg-emerald-50"
                    : "bg-stone-800 hover:bg-stone-700 active:scale-[0.995]"
                }`}
                aria-label="Copiar resumen"
              >
                <span className={`text-sm font-medium ${briefCopied ? "text-emerald-700" : "text-white"}`}>
                  {briefCopied ? (strings.briefCopied ?? "¡Copiado!") : "Copiar resumen"}
                </span>
                {briefCopied ? (
                  <Check className="h-5 w-5 text-emerald-600 shrink-0" />
                ) : (
                  <Copy className="h-5 w-5 text-stone-400 shrink-0" />
                )}
              </button>

              {/* Resumen content */}
              <div className="p-5">
                <p className="text-base font-semibold text-stone-800">
                  Resumen para contratista
                </p>
                <p className="mt-1.5 text-sm text-stone-500 leading-relaxed">
                  {strings.contractorBriefIntro ??
                    "Hola - quiero un presupuesto para la reforma de esta propiedad."}
                </p>

            <div className="mt-4 pt-4 border-t border-stone-100">
              <p className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-1">
                {strings.detail ?? "Property"}
              </p>
              <p className="text-sm text-stone-700">{displayAddress}</p>
            </div>

            <div className="mt-4 pt-4 border-t border-stone-100">
              <p className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-2">
                {strings.contractorBriefRooms ?? "Rooms"}
              </p>
              <div className="space-y-2">
                {roomsForBrief.length > 0 ? (
                  roomsForBrief.map((r, idx) => {
                    const name =
                      String(r?.room_name || "").trim() ||
                      (strings.detail ?? "Room");
                    const tagline = String(r?.tagline || "").trim();
                    const m2 = formatRoomM2(r?.estimated_m2);
                    return (
                      <div
                        key={`${String(r?.room_id || "")}-${idx}`}
                        className="flex items-start gap-2 text-sm"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-stone-300 mt-1.5 shrink-0" />
                        <span>
                          <span className="font-medium text-stone-700">
                            {name}
                          </span>
                          {m2 ? (
                            <span className="text-stone-400 ml-1">({m2})</span>
                          ) : null}
                          {tagline ? (
                            <span className="text-stone-500 block text-xs mt-0.5">
                              {tagline}
                            </span>
                          ) : null}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-stone-400 italic">
                    {strings.contractorBriefNotReady ??
                      "Room breakdown not available yet"}
                  </p>
                )}
              </div>
            </div>

              {contractorUrl && (
                <div className="mt-4 pt-4 border-t border-stone-100">
                  <p className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-1">
                    {strings.contractorBriefLinkLabel ?? "Contractor view"}
                  </p>
                  <a
                    href={contractorUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-[#da654d] underline underline-offset-4 hover:text-[#c8553d] break-all"
                    aria-label={strings.contractorView ?? "Contractor view link"}
                    tabIndex={0}
                  >
                    {contractorUrl}
                  </a>
                </div>
              )}
            </div>
          </div>
          </div>
        </div>

        {/* Raw text toggle */}
        <details className="pb-4">
          <summary className="cursor-pointer select-none text-xs text-stone-400 hover:text-stone-500 transition-colors">
            {strings.contractorBriefShowRaw ?? "Show raw text"}
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-stone-500 bg-stone-50 border border-stone-200 rounded-lg p-3">
            {briefText}
          </pre>
        </details>
      </div>
    </div>
  );
};
