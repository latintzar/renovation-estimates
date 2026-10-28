"use client";

export function ChatWallpaper() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[#FDFBF7]" />
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 360 800" preserveAspectRatio="none">
        <g>
          {Array.from({ length: 12 }).map((_, x) =>
            Array.from({ length: 20 }).map((__, y) => {
              const cx = x * 30 + (y % 2) * 8 + 12;
              const cy = y * 40 + 12;
              return (
                <circle
                  key={`c-${x}-${y}`}
                  cx={cx}
                  cy={cy}
                  r={7}
                  fill="rgba(218,101,77,0.04)"
                  stroke="rgba(0,0,0,0.03)"
                />
              );
            }),
          )}
          {Array.from({ length: 10 }).map((_, index) => {
            const startX = index * 36 + 6;
            const startY = (index % 2) * 20 + 30;
            return (
              <path
                key={`p-${index}`}
                d={`M${startX} ${startY} q 8 -8 16 0 q 8 8 16 0`}
                stroke="rgba(0,0,0,0.03)"
                strokeWidth={1}
                fill="none"
              />
            );
          })}
        </g>
      </svg>
      <div className="absolute inset-0 bg-[#F5F1EB]/90" />
    </div>
  );
}

