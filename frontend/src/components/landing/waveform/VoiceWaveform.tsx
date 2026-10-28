"use client";

import { useEffect, useState } from "react";

export const VoiceWaveform = () => {
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    // Start animation loop
    const interval = setInterval(() => {
      setIsAnimating(true);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-center gap-1 h-12">
      {[...Array(20)].map((_, i) => (
        <div
          key={i}
          className="w-1 bg-stone-900 rounded-full transition-all duration-300 ease-in-out"
          style={{
            height: isAnimating 
              ? `${Math.max(10, Math.random() * 40)}px` 
              : "4px",
            opacity: Math.max(0.3, Math.random())
          }}
        />
      ))}
    </div>
  );
};

