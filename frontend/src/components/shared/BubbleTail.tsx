"use client";

interface BubbleTailProps {
  color: string;
  isOutgoing: boolean;
}

export function BubbleTail({ color, isOutgoing }: BubbleTailProps) {
  if (isOutgoing) {
    return (
      <span className="absolute -right-[7px] top-0" aria-hidden>
        <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
          <path d="M5.188 0H0v11.193l6.467-8.625C7.526 1.156 6.958 0 5.188 0z" fill={color} />
        </svg>
      </span>
    );
  }

  return (
    <span className="absolute -left-[7px] top-0" aria-hidden>
      <svg width="8" height="13" viewBox="0 0 8 13" fill="none">
        <path d="M2.812 0H8v11.193L1.533 2.568C.474 1.156 1.042 0 2.812 0z" fill={color} />
      </svg>
    </span>
  );
}

