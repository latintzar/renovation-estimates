"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Briefcase, Users, Train, Sparkles } from "lucide-react";
import { useDictionary } from "@/contexts/DictionaryContext";

/**
 * Simple dumbbell icon for gym
 */
const DumbbellIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6.5 6.5a2.5 2.5 0 0 0-5 0v11a2.5 2.5 0 0 0 5 0v-11Z" />
    <path d="M17.5 6.5a2.5 2.5 0 0 1 5 0v11a2.5 2.5 0 0 1-5 0v-11Z" />
    <path d="M6.5 12h11" />
  </svg>
);

/**
 * Venn diagram style isochrone visualization
 * Overlapping blobs for different priorities, sweet spot is the overlap
 * With recognizable Barcelona map underneath (simplified but accurate)
 */
export const IsochroneMap = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full max-w-md mx-auto aspect-[4/3]", className)} style={{ perspective: '800px' }}>
      {/* Background - Barcelona map with slight angle */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden" style={{ transform: 'rotateX(8deg) rotateY(-3deg)', transformOrigin: 'center center' }}>
        {/* Base map color */}
        <div className="absolute inset-0 bg-stone-50" />
        
        {/* SVG City Map - Barcelona with coast on RIGHT (east) side */}
        <svg width="100%" height="100%" viewBox="0 0 400 300" className="absolute inset-0 opacity-35" preserveAspectRatio="xMidYMid slice">
          
          <defs>
            {/* Sea gradient - horizontal for east coast */}
            <linearGradient id="seaGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#a8d4e8" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#7cc0e0" stopOpacity="0.6" />
            </linearGradient>
            {/* Beach gradient */}
            <linearGradient id="beachGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#f0e4c8" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#e8d8b8" stopOpacity="0.4" />
            </linearGradient>
          </defs>
          
          {/* ===== MEDITERRANEAN SEA - RIGHT SIDE (EAST) - angled clockwise ===== */}
          {/* Coast runs diagonally: top-right to bottom-center-right */}
          
          {/* Sea area - right side, angled */}
          <path 
            d="M 350 0 Q 330 60 310 120 Q 290 180 280 240 Q 275 270 280 300 L 400 300 L 400 0 Z" 
            fill="url(#seaGradient)" 
          />
          
          {/* Beach strip - Barceloneta beaches */}
          <path 
            d="M 305 100 Q 295 140 285 180 Q 280 210 275 240 L 285 245 Q 290 215 295 185 Q 305 145 315 105 Z" 
            fill="url(#beachGradient)" 
          />
          
          {/* Coastline edge - angled clockwise */}
          <path 
            d="M 345 0 Q 325 60 305 120 Q 285 180 275 240 Q 270 270 275 300" 
            stroke="#5a9cb8" 
            strokeWidth="1.5" 
            fill="none" 
            opacity="0.6"
          />
          
          {/* Port Olímpic hint - small bay indentation */}
          <path 
            d="M 295 150 Q 305 155 300 165 Q 290 160 295 150" 
            fill="#8ab8d0" 
            opacity="0.4"
          />
          
          {/* ===== MONTJUÏC HILL - BOTTOM LEFT ===== */}
          <ellipse cx="60" cy="260" rx="45" ry="30" fill="#c8e0c8" opacity="0.6" />
          
          {/* ===== COLLSEROLA HILLS - TOP LEFT (inland hills) ===== */}
          <ellipse cx="40" cy="40" rx="50" ry="35" fill="#d0e8d0" opacity="0.4" />
          
          {/* ===== EIXAMPLE GRID (center of city) ===== */}
          <g stroke="#d8d0c4" strokeWidth="1" fill="none" opacity="0.7">
            {/* Horizontal streets - stop before coastline */}
            <path d="M 80 80 L 270 80" />
            <path d="M 80 110 L 265 110" />
            <path d="M 80 140 L 260 140" />
            <path d="M 80 170 L 255 170" />
            <path d="M 100 200 L 250 200" />
            
            {/* Vertical streets */}
            <path d="M 100 60 L 100 210" />
            <path d="M 140 60 L 140 220" />
            <path d="M 180 50 L 180 230" />
            <path d="M 220 55 L 220 225" />
            <path d="M 255 70 L 255 200" />
          </g>
          
          {/* ===== MAJOR AVENUES ===== */}
          <g stroke="#c8c0b4" strokeWidth="2.5" fill="none" strokeLinecap="round">
            {/* Avinguda Diagonal - cuts diagonally, stops before coast */}
            <path d="M 0 30 Q 120 100 200 140 Q 250 165 275 180" />
            
            {/* Gran Via - major horizontal, stops before coast */}
            <path d="M 0 150 L 260 150" />
            
            {/* Passeig de Gràcia - main vertical spine */}
            <path d="M 180 0 L 180 240" />
            
            {/* La Rambla - angled toward the old port (bottom-center) */}
            <path d="M 150 70 Q 140 140 120 200 Q 100 250 90 280" />
            
            {/* Meridiana - angled avenue, stops before coast */}
            <path d="M 250 0 L 270 140" />
          </g>
          
          {/* ===== GRÀCIA (top center - organic streets) ===== */}
          <g stroke="#e0d8cc" strokeWidth="0.7" fill="none" opacity="0.5">
            <path d="M 140 35 Q 160 45 185 35" />
            <path d="M 150 50 Q 170 55 190 48" />
            <path d="M 160 25 L 165 60" />
          </g>
          
          {/* ===== OLD TOWN (Gothic/Raval - bottom center) ===== */}
          <g stroke="#e0d8cc" strokeWidth="0.6" fill="none" opacity="0.5">
            <path d="M 110 220 L 150 215" />
            <path d="M 115 235 L 145 230" />
            <path d="M 130 210 L 125 245" />
          </g>
          
          {/* ===== POBLENOU (right side, stays on land) ===== */}
          <g stroke="#e0d8cc" strokeWidth="0.7" fill="none" opacity="0.5">
            <path d="M 240 100 L 270 100" />
            <path d="M 240 125 L 265 125" />
            <path d="M 255 90 L 255 140" />
          </g>
          
          {/* ===== PARKS - Green areas with straight edges, on land ===== */}
          <g fill="#8fbc8f" opacity="0.7">
            {/* Parc de la Ciutadella - near coast but on land */}
            <rect x="220" y="180" width="32" height="26" rx="2" />
            {/* Park Güell area - hillside park, rectangular */}
            <rect x="130" y="18" width="28" height="20" rx="2" />
            {/* Plaça Catalunya - square */}
            <rect x="172" y="132" width="14" height="14" rx="1" />
            {/* Jardins de Gràcia - small plaza */}
            <rect x="202" y="45" width="12" height="10" rx="1" />
            {/* Park near Diagonal */}
            <rect x="220" y="124" width="16" height="12" rx="1" />
          </g>
          
          {/* ===== FILL BOTTOM AREA - Streets in Sant Antoni / Poble Sec ===== */}
          <g stroke="#d8d0c4" strokeWidth="0.8" fill="none" opacity="0.6">
            {/* More horizontal streets toward bottom - stay on land */}
            <path d="M 100 230 L 240 230" />
            <path d="M 100 255 L 220 255" />
            <path d="M 100 280 L 180 280" />
            {/* Vertical connectors */}
            <path d="M 120 200 L 120 290" />
            <path d="M 160 200 L 160 295" />
            <path d="M 200 200 L 200 270" />
            <path d="M 230 195 L 230 245" />
          </g>
          
          {/* Port area hint at bottom - curves toward coast */}
          <path d="M 180 280 Q 200 275 230 265" stroke="#c8c0b4" strokeWidth="1" fill="none" opacity="0.4" />
          
        </svg>
        
        {/* Subtle vignette */}
        <div className="absolute inset-0 bg-gradient-radial from-transparent to-stone-200/20" />
      </div>

      {/* VENN DIAGRAM BLOBS - Three overlapping zones, shifted LEFT away from water */}
      
      {/* Blob 1: Work zone (blue) - top center-left */}
      <div 
        className="absolute w-[48%] h-[52%] top-[5%] left-[28%] rounded-[60%_40%_45%_55%/50%_60%_40%_50%] bg-gradient-to-br from-blue-400/35 via-indigo-300/25 to-sky-400/35 blur-[2px]"
        style={{ animation: 'float 7s ease-in-out infinite' }}
      />
      
      {/* Blob 2: Friends zone (amber) - left side */}
      <div 
        className="absolute w-[46%] h-[50%] top-[18%] left-[2%] rounded-[45%_55%_60%_40%/55%_45%_55%_45%] bg-gradient-to-br from-amber-400/35 via-orange-300/25 to-yellow-400/35 blur-[2px]"
        style={{ animation: 'float 6s ease-in-out infinite', animationDelay: '1s' }}
      />
      
      {/* Blob 3: Lifestyle zone (rose) - bottom center-left, away from water */}
      <div 
        className="absolute w-[46%] h-[42%] top-[38%] left-[12%] rounded-[50%_50%_40%_60%/45%_55%_45%_55%] bg-gradient-to-br from-rose-400/35 via-pink-300/25 to-fuchsia-400/35 blur-[2px]"
        style={{ animation: 'float 8s ease-in-out infinite', animationDelay: '2s' }}
      />

      {/* THE SWEET SPOT - Overlap area (emerald) - centered in the overlap */}
      <div 
        className="absolute w-[24%] h-[24%] top-[35%] left-[28%] rounded-[50%_50%_45%_55%/55%_45%_55%_45%] bg-gradient-to-br from-emerald-400/65 via-green-400/55 to-teal-400/65 shadow-lg shadow-emerald-400/25 z-10"
        style={{ animation: 'pulse 3s ease-in-out infinite' }}
      />
      
      {/* Sweet spot label */}
      <div className="absolute top-[38%] left-[32%] z-20 flex items-center gap-1 bg-white/90 backdrop-blur px-2 py-1 rounded-full shadow-md border border-emerald-200">
        <Sparkles className="w-3 h-3 text-emerald-500" />
        <span className="text-[9px] font-bold text-emerald-700">
          {isEs ? 'Zona ideal' : 'Sweet spot'}
        </span>
      </div>

      {/* Tiny blob splats - fewer, subtler, on land */}
      <div className="absolute w-3 h-3 top-[15%] left-[18%] rounded-full bg-amber-300/40 blur-[1px]" />
      <div className="absolute w-4 h-3 top-[25%] left-[55%] rounded-[60%_40%_50%_50%] bg-blue-300/35 blur-[1px]" />
      <div className="absolute w-3 h-3 top-[60%] left-[8%] rounded-full bg-pink-300/35 blur-[1px]" />

      {/* Location labels - positioned on each blob, all on land (left side) */}
      <LocationLabel 
        icon={<Briefcase className="w-3 h-3" />}
        label={isEs ? 'Trabajo' : 'Work'}
        time="15 min"
        className="absolute top-[10%] left-[40%]"
        color="blue"
      />
      <LocationLabel 
        icon={<Users className="w-3 h-3" />}
        label={isEs ? 'Amigos' : 'Friends'}
        time="12 min"
        className="absolute top-[25%] left-[5%]"
        color="amber"
      />
      <LocationLabel 
        icon={<DumbbellIcon className="w-3 h-3" />}
        label={isEs ? 'Gimnasio' : 'Gym'}
        time="10 min"
        className="absolute top-[62%] left-[5%]"
        color="rose"
      />
      <LocationLabel 
        icon={<Train className="w-3 h-3" />}
        label="Metro"
        time="5 min"
        className="absolute top-[58%] left-[40%]"
        color="emerald"
      />
    </div>
  );
};

/**
 * Small location label with icon
 */
const LocationLabel = ({ 
  icon, 
  label, 
  time, 
  className,
  color = "stone"
}: { 
  icon: React.ReactNode;
  label: string;
  time: string;
  className?: string;
  color?: "stone" | "blue" | "green" | "amber" | "emerald" | "rose";
}) => {
  const colorClasses = {
    stone: "bg-white border-stone-200 text-stone-700",
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    green: "bg-green-50 border-green-200 text-green-700",
    amber: "bg-amber-50 border-amber-200 text-amber-700",
    emerald: "bg-emerald-50 border-emerald-200 text-emerald-700",
    rose: "bg-rose-50 border-rose-200 text-rose-700",
  };
  
  return (
    <div className={cn(
      "flex items-center gap-1.5 px-2 py-1 rounded-full border shadow-sm text-[10px] font-medium bg-white/80 backdrop-blur-sm",
      colorClasses[color],
      className
    )}>
      {icon}
      <span>{label}</span>
      <span className="opacity-60">• {time}</span>
    </div>
  );
};

/**
 * Compact isochrone - tiny Venn diagram version for inline use (~100px)
 */
export const MiniIsochrone = ({ className }: { className?: string }) => {
  return (
    <div className={cn("relative w-24 h-20", className)}>
      {/* Three overlapping blobs */}
      <div className="absolute w-[50%] h-[55%] top-0 right-[10%] rounded-[60%_40%_45%_55%] bg-gradient-to-br from-blue-300/50 to-indigo-300/50" />
      <div className="absolute w-[45%] h-[50%] top-[15%] left-0 rounded-[45%_55%_60%_40%] bg-gradient-to-br from-amber-300/50 to-orange-300/50" />
      <div className="absolute w-[48%] h-[45%] bottom-0 left-[25%] rounded-[50%_50%_40%_60%] bg-gradient-to-br from-rose-300/50 to-pink-300/50" />
      {/* Sweet spot */}
      <div className="absolute w-[25%] h-[25%] top-[38%] left-[38%] rounded-full bg-gradient-to-br from-emerald-400/70 to-green-400/70 shadow-sm" />
    </div>
  );
};

// Note: Float animation is defined in globals.css as @keyframes float

/**
 * Madrid Isochrone Map - For Buyers
 * Polished, cohesive map with Retiro visible in corner
 * Same aesthetic as Barcelona map
 */
import { Home, Coffee, ShoppingBag } from "lucide-react";

export const MadridIsochroneMap = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full max-w-md mx-auto aspect-[4/3]", className)} style={{ perspective: '800px' }}>
      {/* Background - Madrid map with slight angle */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden" style={{ transform: 'rotateX(8deg) rotateY(-3deg)', transformOrigin: 'center center' }}>
        {/* Base map color - same as Barcelona */}
        <div className="absolute inset-0 bg-stone-50" />
        
        {/* SVG City Map - Madrid (Retiro in bottom-right corner like Barcelona's sea) */}
        <svg width="100%" height="100%" viewBox="0 0 400 300" className="absolute inset-0 opacity-35" preserveAspectRatio="xMidYMid slice">
          
          {/* ===== RETIRO PARK - Corner shape like Barcelona's sea ===== */}
          <path 
            d="M 280 120 L 400 120 L 400 300 L 280 300 Q 265 240 270 180 Q 275 140 280 120" 
            fill="#c8e0c8"
          />
          {/* Estanque (lake) */}
          <ellipse cx="340" cy="200" rx="28" ry="20" fill="#a8d4e8" opacity="0.6" />
          {/* Park paths */}
          <path d="M 300 140 Q 315 180 310 230 Q 305 270 315 295" stroke="#a8d0a8" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M 350 130 L 355 200 Q 360 260 375 295" stroke="#a8d0a8" strokeWidth="2" fill="none" opacity="0.4" />
          
          {/* ===== CASA DE CAMPO hint - left ===== */}
          <ellipse cx="25" cy="220" rx="35" ry="45" fill="#d0e8d0" opacity="0.4" />
          
          {/* ===== COLLSEROLA hint - top left ===== */}
          <ellipse cx="35" cy="35" rx="45" ry="35" fill="#d0e8d0" opacity="0.3" />
          
          {/* ===== STREET GRID - Full coverage, stops at Retiro ===== */}
          <g stroke="#d8d0c4" strokeWidth="1" fill="none" opacity="0.7">
            {/* Horizontal streets */}
            <path d="M 60 40 L 400 40" />
            <path d="M 60 70 L 400 70" />
            <path d="M 60 100 L 280 100" />
            <path d="M 60 130 L 275 130" />
            <path d="M 60 160 L 270 160" />
            <path d="M 70 190 L 268 190" />
            <path d="M 80 220 L 265 220" />
            <path d="M 90 250 L 270 250" />
            <path d="M 100 280 L 275 280" />
            {/* Vertical streets */}
            <path d="M 80 20 L 80 290" />
            <path d="M 120 15 L 120 295" />
            <path d="M 160 20 L 160 290" />
            <path d="M 200 10 L 200 285" />
            <path d="M 240 25 L 240 260" />
            <path d="M 280 30 L 280 120" />
            <path d="M 320 25 L 320 115" />
            <path d="M 360 20 L 360 110" />
          </g>
          
          {/* ===== MAJOR AVENUES ===== */}
          <g stroke="#c8c0b4" strokeWidth="2.5" fill="none" strokeLinecap="round">
            {/* Gran Vía - curves across */}
            <path d="M 0 100 Q 100 85 180 95 Q 240 105 275 100" />
            
            {/* Calle de Alcalá - to Retiro entrance */}
            <path d="M 0 150 L 180 155 Q 230 165 270 175" />
            
            {/* Paseo de la Castellana - main N-S spine */}
            <path d="M 200 0 L 200 280" />
            
            {/* Paseo del Prado - toward Retiro */}
            <path d="M 255 0 L 260 120" />
          </g>
          
          {/* ===== RADIAL AVENUES from Puerta del Sol ===== */}
          <g stroke="#d8d0c4" strokeWidth="1.5" fill="none" opacity="0.6">
            <path d="M 175 155 L 70 40" />
            <path d="M 175 155 L 45 210" />
            <path d="M 175 155 L 90 280" />
          </g>
          
          {/* ===== OLD TOWN (Centro) - Organic streets ===== */}
          <g stroke="#e0d8cc" strokeWidth="0.7" fill="none" opacity="0.5">
            <path d="M 120 170 Q 140 185 130 205" />
            <path d="M 145 165 L 165 200" />
            <path d="M 110 195 L 160 215" />
          </g>
          
          {/* ===== KEY PLAZAS ===== */}
          <g fill="#e8e0d4" opacity="0.8">
            {/* Puerta del Sol */}
            <ellipse cx="175" cy="155" rx="10" ry="8" />
            {/* Plaza de Cibeles */}
            <circle cx="260" cy="160" r="8" />
            {/* Plaza Mayor */}
            <rect x="135" y="180" width="12" height="10" rx="2" />
            {/* Plaza de España */}
            <rect x="88" y="108" width="10" height="10" rx="1" />
          </g>
          
          {/* ===== SMALL PARKS ===== */}
          <g fill="#8fbc8f" opacity="0.5">
            {/* Jardines de Sabatini */}
            <rect x="65" y="78" width="14" height="12" rx="2" />
          </g>
          
        </svg>
        
        {/* Subtle vignette - same as Barcelona */}
        <div className="absolute inset-0 bg-gradient-radial from-transparent to-stone-200/20" />
      </div>

      {/* VENN DIAGRAM BLOBS */}
      
      {/* Blob 1: Work zone (blue) - top center */}
      <div 
        className="absolute w-[48%] h-[52%] top-[5%] left-[28%] rounded-[60%_40%_45%_55%/50%_60%_40%_50%] bg-gradient-to-br from-blue-400/35 via-indigo-300/25 to-sky-400/35 blur-[2px]"
        style={{ animation: 'float 7s ease-in-out infinite' }}
      />
      
      {/* Blob 2: Lifestyle zone (rose) - left side */}
      <div 
        className="absolute w-[46%] h-[50%] top-[18%] left-[2%] rounded-[45%_55%_60%_40%/55%_45%_55%_45%] bg-gradient-to-br from-rose-400/35 via-pink-300/25 to-fuchsia-400/35 blur-[2px]"
        style={{ animation: 'float 6s ease-in-out infinite', animationDelay: '1s' }}
      />
      
      {/* Blob 3: Family zone (amber) - bottom center */}
      <div 
        className="absolute w-[46%] h-[42%] top-[38%] left-[22%] rounded-[50%_50%_40%_60%/45%_55%_45%_55%] bg-gradient-to-br from-amber-400/35 via-orange-300/25 to-yellow-400/35 blur-[2px]"
        style={{ animation: 'float 8s ease-in-out infinite', animationDelay: '2s' }}
      />

      {/* THE SWEET SPOT */}
      <div 
        className="absolute w-[24%] h-[24%] top-[32%] left-[25%] rounded-[50%_50%_45%_55%/55%_45%_55%_45%] bg-gradient-to-br from-emerald-400/65 via-green-400/55 to-teal-400/65 shadow-lg shadow-emerald-400/25 z-10"
        style={{ animation: 'pulse 3s ease-in-out infinite' }}
      />
      
      {/* Sweet spot label */}
      <div className="absolute top-[35%] left-[28%] z-20 flex items-center gap-1 bg-white/90 backdrop-blur px-2 py-1 rounded-full shadow-md border border-emerald-200">
        <Sparkles className="w-3 h-3 text-emerald-500" />
        <span className="text-[9px] font-bold text-emerald-700">
          {isEs ? 'Zona ideal' : 'Sweet spot'}
        </span>
      </div>

      {/* Location labels */}
      <LocationLabel 
        icon={<Briefcase className="w-3 h-3" />}
        label={isEs ? 'Oficina' : 'Office'}
        time="20 min"
        className="absolute top-[10%] left-[38%]"
        color="blue"
      />
      <LocationLabel 
        icon={<Coffee className="w-3 h-3" />}
        label={isEs ? 'Ocio' : 'Leisure'}
        time="10 min"
        className="absolute top-[25%] left-[5%]"
        color="rose"
      />
      <LocationLabel 
        icon={<ShoppingBag className="w-3 h-3" />}
        label={isEs ? 'Familia' : 'Family'}
        time="15 min"
        className="absolute top-[58%] left-[18%]"
        color="amber"
      />
      <LocationLabel 
        icon={<Train className="w-3 h-3" />}
        label="Metro"
        time="5 min"
        className="absolute top-[55%] left-[45%]"
        color="emerald"
      />
    </div>
  );
};

/**
 * Multi-Family Isochrone Map - For Relocation
 * Shows multiple family isochrones on a single map with photo headshots
 * Less overlapping, smaller sweet spots, more amorphous shapes
 */
export const MultiClientDashboard = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full max-w-md mx-auto aspect-[4/3]", className)} style={{ perspective: '800px' }}>
      {/* Background - Barcelona map with slight angle (same as renters) */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden" style={{ transform: 'rotateX(8deg) rotateY(-3deg)', transformOrigin: 'center center' }}>
        <div className="absolute inset-0 bg-stone-50" />
        
        {/* SVG City Map - Barcelona base */}
        <svg width="100%" height="100%" viewBox="0 0 400 300" className="absolute inset-0 opacity-25" preserveAspectRatio="xMidYMid slice">
          {/* Sea on right */}
          <path d="M 345 0 Q 325 60 305 120 Q 285 180 275 240 Q 270 270 275 300 L 400 300 L 400 0 Z" fill="#a8d4e8" fillOpacity="0.4" />
          
          {/* Grid streets */}
          <g stroke="#d8d0c4" strokeWidth="1" fill="none" opacity="0.5">
            <path d="M 80 80 L 270 80" />
            <path d="M 80 140 L 260 140" />
            <path d="M 80 200 L 250 200" />
            <path d="M 100 60 L 100 240" />
            <path d="M 180 50 L 180 250" />
            <path d="M 250 70 L 250 200" />
          </g>
          
          {/* Main avenues */}
          <g stroke="#c8c0b4" strokeWidth="2" fill="none" strokeLinecap="round">
            <path d="M 0 30 Q 120 100 200 140 Q 250 165 275 180" />
            <path d="M 0 150 L 260 150" />
            <path d="M 180 0 L 180 240" />
          </g>
        </svg>
      </div>

      {/* FAMILY ISOCHRONES - Three SEPARATE zones with minimal overlap */}
      
      {/* Family 1: Martinez (blue) - top left - amorphous blob */}
      <div 
        className="absolute w-[32%] h-[38%] top-[5%] left-[8%] rounded-[65%_35%_45%_55%/55%_60%_40%_45%] bg-gradient-to-br from-blue-400/35 via-blue-300/25 to-sky-400/35 blur-[2px]"
        style={{ animation: 'float 7s ease-in-out infinite' }}
      />
      
      {/* Family 2: Kim (rose) - top right - amorphous blob */}
      <div 
        className="absolute w-[30%] h-[35%] top-[8%] right-[15%] rounded-[40%_60%_55%_45%/50%_45%_55%_50%] bg-gradient-to-br from-rose-400/35 via-pink-300/25 to-fuchsia-400/35 blur-[2px]"
        style={{ animation: 'float 6s ease-in-out infinite', animationDelay: '1s' }}
      />
      
      {/* Family 3: Rodriguez (amber) - bottom center - amorphous blob */}
      <div 
        className="absolute w-[35%] h-[32%] bottom-[12%] left-[28%] rounded-[50%_50%_40%_60%/45%_55%_45%_55%] bg-gradient-to-br from-amber-400/35 via-orange-300/25 to-yellow-400/35 blur-[2px]"
        style={{ animation: 'float 8s ease-in-out infinite', animationDelay: '2s' }}
      />

      {/* Tiny sweet spots - where each family finds a home */}
      <div className="absolute w-2.5 h-2.5 top-[22%] left-[18%] rounded-[60%_40%_50%_50%] bg-emerald-500 shadow-md ring-1 ring-white animate-pulse" />
      <div className="absolute w-2 h-2.5 top-[20%] right-[22%] rounded-[45%_55%_50%_50%] bg-emerald-500 shadow-md ring-1 ring-white animate-pulse" style={{ animationDelay: '0.5s' }} />
      <div className="absolute w-2.5 h-2 bottom-[22%] left-[42%] rounded-[50%_50%_45%_55%] bg-emerald-500 shadow-md ring-1 ring-white animate-pulse" style={{ animationDelay: '1s' }} />

      {/* Family labels with HEADSHOT photos */}
      
      {/* Martinez family - with headshot */}
      <div className="absolute top-[3%] left-[5%] flex items-center gap-2 bg-white/95 backdrop-blur px-2.5 py-1.5 rounded-full shadow-lg border border-blue-200">
        <img 
          src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face" 
          alt="Martinez"
          className="w-8 h-8 rounded-full object-cover ring-2 ring-blue-400"
        />
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-stone-800">Martinez</span>
          <span className="text-[9px] text-blue-600 font-medium">Austin → BCN</span>
        </div>
      </div>
      
      {/* Kim family - with headshot */}
      <div className="absolute top-[5%] right-[15%] flex items-center gap-2 bg-white/95 backdrop-blur px-2.5 py-1.5 rounded-full shadow-lg border border-rose-200">
        <img 
          src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop&crop=face" 
          alt="Kim"
          className="w-8 h-8 rounded-full object-cover ring-2 ring-rose-400"
        />
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-stone-800">Kim</span>
          <span className="text-[9px] text-rose-600 font-medium">Seoul → BCN</span>
        </div>
      </div>
      
      {/* Rodriguez family - with headshot */}
      <div className="absolute bottom-[8%] left-[25%] flex items-center gap-2 bg-white/95 backdrop-blur px-2.5 py-1.5 rounded-full shadow-lg border border-amber-200">
        <img 
          src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop&crop=face" 
          alt="Rodriguez"
          className="w-8 h-8 rounded-full object-cover ring-2 ring-amber-400"
        />
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-stone-800">Rodriguez</span>
          <span className="text-[9px] text-amber-600 font-medium">London → BCN</span>
        </div>
      </div>

      {/* Badge - total families */}
      <div className="absolute -top-2 -right-2 bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
        {isEs ? '12 familias' : '12 families'}
      </div>
    </div>
  );
}

