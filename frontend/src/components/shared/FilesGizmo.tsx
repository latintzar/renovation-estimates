"use client";

import { FileText } from "lucide-react";

interface FileItem {
  name: string;
  size?: string;
  pages?: number;
  issuedDate?: string;
}

interface FilesGizmoProps {
  files: FileItem[];
}

export function FilesGizmo({ files }: FilesGizmoProps) {
  if (files.length === 0) return null;

  return (
    <div className="my-1 w-full rounded-xl border border-stone-200 bg-white p-3">
      <div className="space-y-2">
        {files.map((file, index) => (
          <div key={`${file.name}-${index}`} className="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2">
            <div className="flex items-start gap-2">
              <FileText className="mt-0.5 h-4 w-4 text-[#da654d]" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-stone-800">{file.name}</p>
                <p className="mt-0.5 text-[11px] text-stone-500">
                  {[file.size, file.pages ? `${file.pages} pages` : undefined, file.issuedDate]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

