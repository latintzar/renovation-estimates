/**
 * ComplexitySlider Component
 * ==========================
 * 
 * Visual slider for maintenance complexity (0-100).
 * Used for Section 2: How challenging is this property to maintain?
 * 
 * Zones:
 * - 0-20: Very easy (green)
 * - 21-40: Easy (light green)
 * - 41-60: Moderate (yellow)
 * - 61-80: Challenging (orange)
 * - 81-100: Very challenging (red)
 */

"use client";

import React from 'react';

interface ComplexitySliderProps {
  score: number;
  label?: string;
}

export function ComplexitySlider({ score, label }: ComplexitySliderProps) {
  // Calculate position percentage (0-100)
  const position = Math.max(0, Math.min(100, score));
  
  // Get color based on complexity
  const getColor = (score: number): string => {
    if (score <= 20) return '#22c55e'; // green-500
    if (score <= 40) return '#84cc16'; // lime-500
    if (score <= 60) return '#eab308'; // yellow-500
    if (score <= 80) return '#f97316'; // orange-500
    return '#ef4444'; // red-500
  };
  
  // Get label if not provided
  const getLabel = (score: number): string => {
    if (label) return label;
    if (score <= 20) return 'Very easy';
    if (score <= 40) return 'Easy';
    if (score <= 60) return 'Moderate';
    if (score <= 80) return 'Challenging';
    return 'Very challenging';
  };
  
  const color = getColor(score);
  const displayLabel = getLabel(score);

  return (
    <div className="w-full">
      {/* Score and Label */}
      <div className="flex items-center justify-between mb-3">
        <span 
          className="text-2xl font-bold"
          style={{ color }}
        >
          {score}
        </span>
        <span 
          className="text-sm font-medium px-3 py-1 rounded-full"
          style={{ 
            backgroundColor: `${color}20`,
            color,
          }}
        >
          {displayLabel}
        </span>
      </div>

      {/* Slider Track */}
      <div className="relative">
        {/* Background gradient */}
        <div className="h-3 rounded-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 opacity-30" />
        
        {/* Progress fill */}
        <div 
          className="absolute top-0 left-0 h-3 rounded-full transition-all duration-500"
          style={{ 
            width: `${position}%`,
            backgroundColor: color,
          }}
        />
        
        {/* Position indicator */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 border-white shadow-md transition-all duration-500"
          style={{ 
            left: `calc(${position}% - 10px)`,
            backgroundColor: color,
          }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between mt-2 text-xs text-stone-400">
        <span>Easy to maintain</span>
        <span>Challenging</span>
      </div>
    </div>
  );
}

export default ComplexitySlider;

