"use client";

/**
 * UrlInput Component
 * ==================
 * 
 * Clean paste-first URL input. Primary action is a big paste button.
 * Input field as fallback for manual entry.
 */

import { useState, useCallback, useRef } from "react";
import { Clipboard, X, Link2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface UrlInputProps {
  onSubmit: (url: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  showActionButtons?: boolean;
}

export function UrlInput({
  onSubmit,
  isLoading = false,
  placeholder = "Paste a URL here...",
  className,
}: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [showInput, setShowInput] = useState(false);
  const [clipboardError, setClipboardError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Normalize and validate URL
  const normalizeUrl = (text: string): string | null => {
    try {
      const testUrl = text.trim().startsWith("http") ? text.trim() : `https://${text.trim()}`;
      new URL(testUrl);
      return testUrl;
    } catch {
      return null;
    }
  };

  // Handle paste button click - read clipboard and submit
  const handlePasteAndGo = useCallback(async () => {
    if (isLoading) return;
    
    try {
      const text = await navigator.clipboard.readText();
      const validUrl = normalizeUrl(text);
      
      if (validUrl) {
        setUrl(text);
        onSubmit(validUrl);
        setClipboardError(false);
      } else {
        // Not a valid URL - show input for manual entry
        setShowInput(true);
        setClipboardError(true);
        inputRef.current?.focus();
      }
    } catch {
      // Clipboard access denied - show input for manual entry
      setShowInput(true);
      setClipboardError(true);
      inputRef.current?.focus();
    }
  }, [isLoading, onSubmit]);

  // Handle manual input submission
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const validUrl = normalizeUrl(url);
      if (validUrl && !isLoading) {
        onSubmit(validUrl);
      }
    },
    [url, isLoading, onSubmit]
  );

  // Handle paste in input - auto-submit
  const handleInputPaste = useCallback(
    (e: React.ClipboardEvent) => {
      const pastedText = e.clipboardData.getData("text");
      const validUrl = normalizeUrl(pastedText);
      if (validUrl && !isLoading) {
        setTimeout(() => onSubmit(validUrl), 100);
      }
    },
    [isLoading, onSubmit]
  );

  // Clear input
  const handleClear = useCallback(() => {
    setUrl("");
    inputRef.current?.focus();
  }, []);

  return (
    <div className={cn("w-full", className)}>
      {/* Main Paste Button - Energetic, inviting */}
      <button
        type="button"
        onClick={handlePasteAndGo}
        disabled={isLoading}
        className={cn(
          "group w-full flex items-center justify-center gap-3 py-5 px-6 rounded-2xl",
          "font-semibold text-lg transition-all duration-200",
          "shadow-lg",
          isLoading
            ? "bg-stone-200 text-stone-500 cursor-wait shadow-none"
            : "bg-gradient-to-r from-[#da654d] to-[#e07c5f] text-white hover:from-[#c8553d] hover:to-[#d06b4d] hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 active:shadow-lg"
        )}
      >
        {isLoading ? (
          <>
            <div className="flex gap-1.5">
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span>Analysing...</span>
          </>
        ) : (
          <>
            <Clipboard className="w-5 h-5 transition-transform group-hover:scale-110" />
            <span>Paste Listing Link</span>
          </>
        )}
      </button>

      {/* Fallback Input - shows on clipboard error or user preference */}
      {(showInput || clipboardError) && !isLoading && (
        <form onSubmit={handleSubmit} className="mt-3">
          <div className="relative flex items-center rounded-xl border border-stone-200 bg-white hover:border-stone-300 focus-within:border-stone-400 transition-colors">
            <div className="pl-3 text-stone-400">
              <Link2 className="w-4 h-4" />
            </div>
            <input
              ref={inputRef}
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onPaste={handleInputPaste}
              placeholder={placeholder}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              className="flex-1 py-3 px-2 text-[15px] text-stone-900 placeholder:text-stone-400 bg-transparent focus:outline-none"
            />
            {url && (
              <button
                type="button"
                onClick={handleClear}
                className="p-2 mr-1 text-stone-400 hover:text-stone-600 rounded-md hover:bg-stone-100"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          {clipboardError && (
            <p className="mt-2 text-xs text-stone-500">
              Couldn&apos;t access clipboard. Paste or type the URL above.
            </p>
          )}
        </form>
      )}

      {/* Toggle to show manual input */}
      {!showInput && !clipboardError && !isLoading && (
        <button
          type="button"
          onClick={() => {
            setShowInput(true);
            setTimeout(() => inputRef.current?.focus(), 100);
          }}
          className="mt-4 text-sm text-stone-400 hover:text-stone-600 transition-colors w-full text-center"
        >
          or manually enter the link
        </button>
      )}
    </div>
  );
}
