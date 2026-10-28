"use client";

import { BubbleTail } from "@/components/shared/BubbleTail";
import { sharedColors } from "@/lib/shared/colors";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/agent/types";

interface ChatBubbleProps {
  message: ChatMessage;
  showTail?: boolean;
}

const formatTime = (date: Date): string =>
  date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

function RichTextBlock({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={`${part}-${i}`} className="font-semibold">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("*") && part.endsWith("*")) {
          return (
            <em key={`${part}-${i}`} className="italic">
              {part.slice(1, -1)}
            </em>
          );
        }
        return <span key={`${part}-${i}`}>{part}</span>;
      })}
    </>
  );
}

export function ChatBubble({ message, showTail = true }: ChatBubbleProps) {
  const isOut = message.role === "agent";
  const bubbleColor = isOut ? sharedColors.light.bubbleOutgoing : sharedColors.light.bubbleIncoming;

  return (
    <div className={cn("w-full", isOut ? "pr-4 pl-2" : "pl-4 pr-2")}>
      <div className={cn("max-w-[82%]", isOut ? "ml-auto" : "mr-auto")}>
        <div
          className={cn(
            "relative min-w-20 rounded-[18px] px-3.5 py-2.5 text-[15px] leading-5",
            isOut ? "rounded-tr-[4px]" : "rounded-tl-[4px]",
          )}
          style={{ backgroundColor: bubbleColor }}
        >
          {showTail ? <BubbleTail color={bubbleColor} isOutgoing={isOut} /> : null}
          {message.content ? (
            <div className="whitespace-pre-wrap text-[15px] leading-5 text-stone-900">
              <RichTextBlock text={message.content} />
            </div>
          ) : null}
          <div className="mt-1.5 flex justify-end">
            <span className="text-[11px] leading-4 text-stone-500">{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

