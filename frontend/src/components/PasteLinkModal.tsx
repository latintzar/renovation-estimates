"use client";

/**
 * PasteLinkModal
 * ==============
 * 
 * Full-screen modal for pasting property links.
 * Auto-checks clipboard on open - skips input if URL found.
 */

import { useState, useEffect, useRef } from "react";
import { X, Clipboard, Sparkles, ExternalLink, AlertCircle, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { validateUrl } from "@/lib/api";
import { useAppStrings } from "@/hooks/AppStringsContext";

type ModalState = "checking" | "input" | "validating" | "analysing";

/**
 * Extract the first URL from a string that may contain surrounding text.
 * Handles cases like:
 *   "https://idealista.com/inmueble/123" → "https://idealista.com/inmueble/123"
 *   "Check this: https://idealista.com/inmueble/123 great deal" → "https://idealista.com/inmueble/123"
 *   "idealista.com/inmueble/123" → "idealista.com/inmueble/123"
 *   "not a url at all" → null
 */
const extractUrl = (text: string): string | null => {
  if (!text || !text.trim()) return null;
  const trimmed = text.trim();

  // 1. If the whole thing is already a valid URL, use it directly
  const withProtocol = trimmed.startsWith("http") ? trimmed : `https://${trimmed}`;
  try {
    const u = new URL(withProtocol);
    if (u.hostname.includes('.')) return trimmed;
  } catch { /* not a plain URL */ }

  // 2. Try to find an https?:// URL embedded in the text
  const httpMatch = trimmed.match(/https?:\/\/[^\s<>"')\]]+/i);
  if (httpMatch) return httpMatch[0];

  // 3. Try to find a www. or domain-looking URL without protocol
  const domainMatch = trimmed.match(/(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s<>"')\]]*/i);
  if (domainMatch) {
    const candidate = domainMatch[0];
    try {
      const u = new URL(`https://${candidate}`);
      if (u.hostname.includes('.')) return candidate;
    } catch { /* not valid */ }
  }

  return null;
};

interface PasteLinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
}

export function PasteLinkModal({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
  error: externalError,
}: PasteLinkModalProps) {
  const [url, setUrl] = useState("");
  const [pastedUrl, setPastedUrl] = useState<string | null>(null);
  const [state, setState] = useState<ModalState>("checking");
  const [error, setError] = useState<{ instruction: string; reason: string } | string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasCheckedClipboard = useRef(false);

  // Centralized translation
  const { s: strings } = useAppStrings();

  // Sync external loading state
  useEffect(() => {
    if (isLoading) {
      setState("analysing");
    }
  }, [isLoading]);

  // Sync external error
  useEffect(() => {
    if (externalError) {
      setError(externalError);
      setState("input");
    }
  }, [externalError]);

  // Process URL: extract URL from text, validate, then submit
  const processUrl = async (inputUrl: string) => {
    // Extract URL from potentially messy clipboard text
    const extracted = extractUrl(inputUrl);
    if (!extracted) {
      setError(strings.notALink);
      setState("input");
      return;
    }

    const cleanUrl = extracted.startsWith("http") ? extracted : `https://${extracted}`;

    setPastedUrl(cleanUrl);
    setError(null);
    setState("validating");

    try {
      const result = await validateUrl(cleanUrl);
      
      if (result.success && !result.data.is_valid) {
        const reason = result.data.rejection_reason;
        setError({
          instruction: strings.trySpecific,
          reason: reason 
            ? `Eso parece ${reason.toLowerCase()}.`
            : strings.notPropertyListing,
        });
        setState("input");
        return;
      }

      setState("analysing");
      await onSubmit(cleanUrl);
      
    } catch (e) {
      setError(strings.somethingWrong);
      setState("input");
      console.error("Process error:", e);
    }
  };

  // Check clipboard immediately when modal opens
  useEffect(() => {
    if (!isOpen) {
      // Reset when closed
      hasCheckedClipboard.current = false;
      setUrl("");
      setPastedUrl(null);
      setState("checking");
      setError(null);
      return;
    }

    // Only check once per open
    if (hasCheckedClipboard.current) return;
    hasCheckedClipboard.current = true;

    const checkClipboard = async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          const found = extractUrl(text);
          if (found) {
            // Valid URL found in clipboard — go straight to validating!
            await processUrl(found);
            return;
          }
        }
      } catch {
        // Clipboard access denied — fall through to input
      }
      // No URL found - show input
      setState("input");
      setTimeout(() => inputRef.current?.focus(), 100);
    };

    checkClipboard();
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle paste from clipboard button
  const handlePasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        const found = extractUrl(text);
        if (found) {
          setUrl(found);
          await processUrl(found);
        } else {
          // Show what they pasted so they can fix it
          setUrl(text.trim());
          setError(strings.notALink);
          setState("input");
        }
      }
    } catch {
      setError(strings.clipboardFailed);
    }
  };

  // Handle paste into input — auto-extract URL from messy text
  const handleInputPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData("text");
    if (!pasted) return;
    
    const found = extractUrl(pasted);
    if (found && found !== pasted.trim()) {
      // The paste had extra text around the URL — replace with just the URL
      e.preventDefault();
      setUrl(found);
    }
    // If found === pasted.trim(), let the default paste behavior work
    // If not found, let it paste as-is and show error on submit
  };

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    await processUrl(url);
  };

  // Keyboard shortcuts
  useEffect(() => {
    if (!isOpen || state === "checking" || state === "validating" || state === "analysing") return;
    
    const handleKeyDown = async (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      
      if ((e.metaKey || e.ctrlKey) && e.key === "v") {
        if (document.activeElement === inputRef.current) return;
        e.preventDefault();
        await handlePasteFromClipboard();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, state, onClose]); // eslint-disable-line react-hooks/exhaustive-deps

  const isBusy = state === "checking" || state === "validating" || state === "analysing";

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#FDFBF7]"
        >
          {/* Close Button */}
          {!isBusy && (
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 text-stone-400 hover:text-stone-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          )}

          {/* Content */}
          <div className="w-full max-w-md px-6">
            <AnimatePresence mode="wait">
              {/* Checking clipboard - minimal UI */}
              {state === "checking" && (
                <motion.div
                  key="checking"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-center py-20"
                >
                  <div className="w-8 h-8 mx-auto border-2 border-stone-200 border-t-stone-400 rounded-full animate-spin" />
                </motion.div>
              )}

              {/* Validating */}
              {state === "validating" && (
                <motion.div
                  key="validating"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="text-center"
                >
                  <div className="relative w-20 h-20 mx-auto mb-6">
                    <div className="absolute inset-0 rounded-full border-2 border-stone-200" />
                    <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-stone-500 animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Search className="w-7 h-7 text-stone-500" />
                    </div>
                  </div>
                  
                  <h2 className="font-serif text-xl font-medium text-stone-900 mb-2">
                    {strings.checkingLink}
                  </h2>
                  <p className="text-stone-500 text-sm">
                    {strings.verifyingProperty}
                  </p>
                  
                  {pastedUrl && (
                    <div className="mt-4 px-4 py-2 bg-stone-100 rounded-lg inline-flex items-center gap-2 text-xs text-stone-500 max-w-full">
                      <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{pastedUrl}</span>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Analysing */}
              {state === "analysing" && (
                <motion.div
                  key="analysing"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="text-center"
                >
                  <div className="relative w-20 h-20 mx-auto mb-6">
                    <div className="absolute inset-0 rounded-full border-2 border-stone-200" />
                    <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#da654d] animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Sparkles className="w-8 h-8 text-[#da654d]" />
                    </div>
                  </div>
                  
                  <h2 className="font-serif text-xl font-medium text-stone-900 mb-2">
                    {strings.analysingProperty}
                  </h2>
                  <p className="text-stone-500 text-sm">
                    {strings.extractingDetails}
                  </p>
                  
                  {pastedUrl && (
                    <div className="mt-4 px-4 py-2 bg-stone-100 rounded-lg inline-flex items-center gap-2 text-xs text-stone-500 max-w-full">
                      <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{pastedUrl}</span>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Input */}
              {state === "input" && (
                <motion.div
                  key="input"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {/* Header */}
                  <div className="text-center mb-8">
                    <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-[#da654d] to-[#e07c5f] flex items-center justify-center shadow-lg shadow-[#da654d]/20">
                      <Sparkles className="w-7 h-7 text-white" />
                    </div>
                    <h1 className="font-serif text-2xl font-medium text-stone-900 mb-2">
                      {strings.addProperty}
                    </h1>
                    <p className="text-stone-500 text-sm">
                      {strings.pasteLink}
                    </p>
                  </div>

                  {/* Error */}
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mb-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-sm"
                    >
                      {typeof error === 'string' ? (
                        <div className="flex items-start gap-3">
                          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-500" />
                          <span>{error}</span>
                        </div>
                      ) : (
                        <div className="flex items-start gap-3">
                          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-500" />
                          <div>
                            <p className="font-semibold">{error.instruction}</p>
                            <p className="text-amber-700 mt-0.5">{error.reason}</p>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* Paste Button */}
                  <button
                    onClick={handlePasteFromClipboard}
                    className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-stone-900 hover:bg-stone-800 text-white rounded-2xl font-medium transition-colors mb-4"
                  >
                    <Clipboard className="w-5 h-5" />
                    <span>{strings.pastePropertyLink}</span>
                  </button>

                  {/* Divider */}
                  <div className="flex items-center gap-3 my-4">
                    <div className="flex-1 h-px bg-stone-200" />
                    <span className="text-xs text-stone-400">{strings.orTypeUrl}</span>
                    <div className="flex-1 h-px bg-stone-200" />
                  </div>

                  {/* Manual Input */}
                  <form onSubmit={handleSubmit}>
                    <input
                      ref={inputRef}
                      type="text"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      onPaste={handleInputPaste}
                      placeholder="https://..."
                      className="w-full px-4 py-3 bg-white border border-stone-200 rounded-xl text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[#da654d]/20 focus:border-[#da654d] transition-all"
                      autoComplete="off"
                      spellCheck={false}
                    />
                    
                    {url && (
                      <motion.button
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        type="submit"
                        className="w-full mt-3 px-6 py-3 bg-[#da654d] hover:bg-[#c8553d] text-white rounded-xl font-medium transition-colors"
                      >
                        {strings.analyse}
                      </motion.button>
                    )}
                  </form>

                  {/* Keyboard hint */}
                  <p className="mt-6 text-center text-xs text-stone-400">
                    <kbd className="px-1.5 py-0.5 bg-stone-100 rounded text-[10px] font-mono">⌘V</kbd>
                    {" "}{strings.pasteAnywhereShort}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
