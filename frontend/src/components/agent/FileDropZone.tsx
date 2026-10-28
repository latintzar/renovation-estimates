"use client";

import { useState, useCallback, type ReactNode, type DragEvent } from "react";
import { cn } from "@/lib/utils";
import { Upload, FileText, Image as ImageIcon, Folder } from "lucide-react";

interface FileDropZoneProps {
  children: ReactNode;
  onFilesDropped?: (files: File[]) => void;
  className?: string;
}

export function FileDropZone({
  children,
  onFilesDropped,
  className,
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragCount, setDragCount] = useState(0);
  const [fileInfo, setFileInfo] = useState<{
    count: number;
    hasImages: boolean;
    hasDocs: boolean;
    hasFolders: boolean;
  } | null>(null);

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCount((c) => c + 1);
    setIsDragging(true);

    const items = e.dataTransfer?.items;
    if (items) {
      let count = 0;
      let hasImages = false;
      let hasDocs = false;
      let hasFolders = false;

      for (let i = 0; i < items.length; i++) {
        count++;
        const item = items[i];
        if (item.type.startsWith("image/")) hasImages = true;
        else if (
          item.type.includes("pdf") ||
          item.type.includes("document")
        )
          hasDocs = true;
        if (item.webkitGetAsEntry?.()?.isDirectory) hasFolders = true;
      }
      setFileInfo({ count, hasImages, hasDocs, hasFolders });
    }
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCount((c) => {
      const next = c - 1;
      if (next <= 0) {
        setIsDragging(false);
        setFileInfo(null);
        return 0;
      }
      return next;
    });
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      setDragCount(0);
      setFileInfo(null);

      const files = Array.from(e.dataTransfer?.files ?? []);
      if (files.length > 0) {
        onFilesDropped?.(files);
      }
    },
    [onFilesDropped]
  );

  const getTypeLabel = () => {
    if (!fileInfo) return "files";
    const parts: string[] = [];
    if (fileInfo.hasImages) parts.push("images");
    if (fileInfo.hasDocs) parts.push("documents");
    if (fileInfo.hasFolders) parts.push("folders");
    return parts.length > 0 ? parts.join(", ") : "files";
  };

  return (
    <div
      className={cn("relative", className)}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}

      {/* Drop Zone Overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center animate-fade-in">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-stone-900/60 backdrop-blur-sm" />

          {/* Drop Area */}
          <div
            className={cn(
              "relative w-[85%] max-w-md aspect-[4/3] rounded-3xl",
              "border-[3px] border-dashed border-white/50",
              "bg-white/10 backdrop-blur-md",
              "flex flex-col items-center justify-center gap-4",
              "transition-all"
            )}
          >
            <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center">
              <Upload className="w-8 h-8 text-white" />
            </div>

            <div className="text-center">
              <p className="text-white text-lg font-medium">Drop files here</p>
              {fileInfo && (
                <p className="text-white/70 text-sm mt-1">
                  {fileInfo.count} {getTypeLabel()} ready to upload
                </p>
              )}
            </div>

            {/* Supported types */}
            <div className="flex items-center gap-3 mt-2">
              <div className="flex items-center gap-1.5 text-white/50 text-xs">
                <ImageIcon className="w-3.5 h-3.5" />
                <span>Images</span>
              </div>
              <div className="flex items-center gap-1.5 text-white/50 text-xs">
                <FileText className="w-3.5 h-3.5" />
                <span>Documents</span>
              </div>
              <div className="flex items-center gap-1.5 text-white/50 text-xs">
                <Folder className="w-3.5 h-3.5" />
                <span>Folders</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
