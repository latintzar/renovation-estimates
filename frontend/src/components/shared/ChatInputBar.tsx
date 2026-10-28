"use client";

import { useCallback, useRef, useState, type KeyboardEvent } from "react";
import { sharedColors } from "@/lib/shared/colors";
import { cn } from "@/lib/utils";
import { Camera, FileText, ImageIcon, MapPin, Mic, Paperclip, Plus, Send } from "lucide-react";

interface ChatInputBarProps {
  onSend: (text: string) => void;
  onAttachFiles?: (files: File[]) => void;
  onCameraPress?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

const ATTACH_ITEMS = [
  { id: "document", label: "Document", icon: FileText, color: sharedColors.light.attachDocument, accept: ".pdf,.doc,.docx,.xls,.xlsx" },
  { id: "camera", label: "Camera", icon: Camera, color: sharedColors.light.attachCamera, accept: "image/*" },
  { id: "gallery", label: "Gallery", icon: ImageIcon, color: sharedColors.light.attachGallery, accept: "image/*" },
  { id: "location", label: "Location", icon: MapPin, color: sharedColors.light.attachLocation, accept: "" },
] as const;

export function ChatInputBar({
  onSend,
  onAttachFiles,
  onCameraPress,
  disabled = false,
  placeholder = "Message",
}: ChatInputBarProps) {
  const [text, setText] = useState("");
  const [showAttachmentPicker, setShowAttachmentPicker] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentAccept, setCurrentAccept] = useState<string>("");
  const hasText = text.trim().length > 0;

  const handleSend = useCallback(() => {
    if (disabled || !hasText) return;
    onSend(text.trim());
    setText("");
    inputRef.current?.focus();
  }, [disabled, hasText, onSend, text]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleAttachClick = useCallback(
    (accept: string) => {
      if (disabled) return;
      if (accept) {
        setCurrentAccept(accept);
        fileInputRef.current?.click();
        setShowAttachmentPicker(false);
        return;
      }
      setShowAttachmentPicker(false);
    },
    [disabled],
  );

  const handleFilesChanged = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      if (files.length > 0) onAttachFiles?.(files);
      event.target.value = "";
    },
    [onAttachFiles],
  );

  return (
    <div className="relative border-t border-stone-200 bg-[#FDFBF7] px-2 py-1.5">
      {showAttachmentPicker ? (
        <div className="mb-2 rounded-2xl border border-stone-200 bg-white p-3 shadow-md">
          <div className="grid grid-cols-4 gap-3">
            {ATTACH_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    if (item.id === "camera") onCameraPress?.();
                    handleAttachClick(item.accept);
                  }}
                  className="flex flex-col items-center gap-1.5 rounded-xl p-2 transition hover:bg-stone-50"
                  aria-label={item.label}
                >
                  <span className="flex h-12 w-12 items-center justify-center rounded-full" style={{ backgroundColor: item.color }}>
                    <Icon className="h-5 w-5 text-white" />
                  </span>
                  <span className="text-[12px] text-stone-700">{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="flex items-end gap-1.5">
        <div className="flex min-h-[52px] flex-1 items-end rounded-[26px] border border-black/5 bg-white px-1.5 pb-1 pt-1 shadow-sm">
          <textarea
            ref={inputRef}
            rows={1}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            className="max-h-[130px] flex-1 resize-none bg-transparent px-3 py-1.5 text-[15px] leading-6 text-stone-900 placeholder:text-stone-400 focus:outline-none disabled:cursor-not-allowed"
            aria-label="Message input"
          />
          <button
            type="button"
            onClick={() => setShowAttachmentPicker((value) => !value)}
            disabled={disabled}
            className="mb-1.5 mr-0.5 flex h-9 w-9 items-center justify-center rounded-full text-stone-500 transition hover:bg-stone-100 disabled:opacity-50"
            aria-label="Open attachments"
          >
            {showAttachmentPicker ? <Plus className="h-5 w-5 rotate-45" /> : <Paperclip className="h-5 w-5" />}
          </button>
        </div>

        <button
          type="button"
          onClick={hasText ? handleSend : undefined}
          className={cn(
            "flex h-12 w-12 items-center justify-center rounded-full text-white shadow-sm transition",
            hasText ? "bg-[#da654d] hover:bg-[#c85b45]" : "bg-[#da654d]",
          )}
          aria-label={hasText ? "Send message" : "Record voice note"}
        >
          {hasText ? <Send className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={currentAccept}
        onChange={handleFilesChanged}
        className="hidden"
      />
    </div>
  );
}

