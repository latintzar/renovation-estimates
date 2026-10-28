"use client";

import React from "react";
import Image from "next/image";
import { 
  Users,
  GraduationCap,
  Briefcase,
  MapPin,
  Globe,
  Check,
  Clock,
  Building,
  Heart,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { LANDING_IMAGES } from "./LandingImages";

// ============================================================================
// RELOCATION VIGNETTES - For corporate relocation teams
// ============================================================================

/**
 * Step 1: "Create structured housing briefs"
 * Form-style brief creation
 */
export const VignetteBriefForm = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[220px] bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-stone-900 px-3 py-2">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-white" />
          <span className="text-[11px] text-white font-medium">
            {isEs ? 'Nuevo Brief de Vivienda' : 'New Housing Brief'}
          </span>
        </div>
      </div>
      
      {/* Form fields */}
      <div className="p-3 space-y-2.5">
        {/* Assignee */}
        <div>
          <label className="text-[9px] text-stone-400 block mb-1">
            {isEs ? 'Empleado' : 'Assignee'}
          </label>
          <div className="flex items-center gap-2 bg-stone-50 rounded-lg px-2 py-1.5">
            <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 text-[9px] font-bold">JM</div>
            <span className="text-[10px] text-stone-700">John Martinez</span>
          </div>
        </div>
        
        {/* Office location */}
        <div>
          <label className="text-[9px] text-stone-400 block mb-1">
            {isEs ? 'Ubicación oficina' : 'Office location'}
          </label>
          <div className="flex items-center gap-1.5 bg-stone-50 rounded-lg px-2 py-1.5">
            <Building className="w-3 h-3 text-stone-400" />
            <span className="text-[10px] text-stone-700">@22 District, Barcelona</span>
          </div>
        </div>
        
        {/* Family */}
        <div>
          <label className="text-[9px] text-stone-400 block mb-1">
            {isEs ? 'Composición familiar' : 'Family composition'}
          </label>
          <div className="flex gap-1.5">
            <span className="px-2 py-1 bg-stone-100 rounded text-[9px] text-stone-600">
              {isEs ? 'Pareja' : 'Partner'}
            </span>
            <span className="px-2 py-1 bg-stone-100 rounded text-[9px] text-stone-600">
              {isEs ? '2 niños' : '2 kids'}
            </span>
          </div>
        </div>
        
        {/* Requirements */}
        <div>
          <label className="text-[9px] text-stone-400 block mb-1">
            {isEs ? 'Requisitos clave' : 'Key requirements'}
          </label>
          <div className="flex flex-wrap gap-1">
            <span className="px-1.5 py-0.5 bg-emerald-50 border border-emerald-200 rounded text-[8px] text-emerald-700">
              {isEs ? 'Colegio int.' : "Int'l school"}
            </span>
            <span className="px-1.5 py-0.5 bg-emerald-50 border border-emerald-200 rounded text-[8px] text-emerald-700">
              {isEs ? '3+ hab.' : '3+ bed'}
            </span>
            <span className="px-1.5 py-0.5 bg-amber-50 border border-amber-200 rounded text-[8px] text-amber-700">
              {isEs ? 'Máx 30min' : 'Max 30min'}
            </span>
          </div>
        </div>
        
        {/* Submit */}
        <button className="w-full bg-stone-900 text-white text-[10px] font-medium py-2 rounded-lg mt-1">
          {isEs ? 'Crear Brief →' : 'Create Brief →'}
        </button>
      </div>
    </div>
  );
};

/**
 * Step 2: "Leo scouts the city"
 * City analysis card with family-relevant data
 */
export const VignetteCityAnalysis = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("w-[200px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Map/City preview with real image */}
      <div className="h-20 relative">
        <Image
          src={LANDING_IMAGES.citySkyline}
          alt="Barcelona skyline"
          fill
          className="object-cover"
          sizes="200px"
        />
        {/* Overlay with zones */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 200 80">
          {/* Sweet spot zone overlay */}
          <ellipse cx="100" cy="45" rx="40" ry="25" fill="#d1fae5" opacity="0.4" stroke="#10b981" strokeWidth="1.5" />
        </svg>
        
        <div className="absolute top-2 left-2 bg-white/90 backdrop-blur px-2 py-1 rounded-lg shadow-sm">
          <span className="text-[9px] font-medium text-stone-700">Barcelona • Sarrià-Sant Gervasi</span>
        </div>
      </div>
      
      {/* Analysis */}
      <div className="p-3 space-y-2">
        <div className="text-[10px] font-semibold text-stone-700">
          {isEs ? 'Zona ideal para familia Martinez:' : 'Sweet spot for Martinez family:'}
        </div>
        
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-[9px] text-stone-600">
              {isEs ? '3 colegios int. a 10 min' : "3 int'l schools within 10 min"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Briefcase className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-[9px] text-stone-600">
              {isEs ? '22 min a @22 en metro' : '22 min to @22 by metro'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-[9px] text-stone-600">
              {isEs ? 'Alta densidad expat (32%)' : 'High expat density (32%)'}
            </span>
          </div>
        </div>
        
        <div className="bg-emerald-50 rounded-lg p-2 mt-2">
          <div className="text-[9px] text-emerald-700">
            {isEs 
              ? <><strong>12 propiedades</strong> encajan en esta zona</>
              : <><strong>12 properties</strong> match in this zone</>}
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Step 3: "Track all assignees"
 * Dashboard view with multiple profiles
 */
export const VignetteDashboard = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  const assignees = [
    { initials: "JM", name: "J. Martinez", status: isEs ? "visitando" : "viewing", city: "Barcelona" },
    { initials: "SK", name: "S. Kim", status: isEs ? "buscando" : "searching", city: "Madrid" },
    { initials: "AR", name: "A. Rodriguez", status: isEs ? "firmado" : "signed", city: "Barcelona" },
  ];
  
  const statusColors: Record<string, string> = {
    searching: "bg-amber-100 text-amber-700",
    buscando: "bg-amber-100 text-amber-700",
    viewing: "bg-emerald-100 text-emerald-700",
    visitando: "bg-emerald-100 text-emerald-700",
    signed: "bg-stone-100 text-stone-600",
    firmado: "bg-stone-100 text-stone-600",
  };
  
  return (
    <div className={cn("w-[240px] bg-white rounded-xl shadow-lg border border-stone-200 overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-stone-900 px-3 py-2 flex items-center justify-between">
        <span className="text-[11px] text-white font-medium">
          {isEs ? 'Reubicaciones activas' : 'Active Relocations'}
        </span>
        <span className="text-[10px] text-stone-400">Q4 2024</span>
      </div>
      
      {/* Assignee list */}
      <div className="divide-y divide-stone-100">
        {assignees.map((assignee, i) => (
          <div key={i} className="px-3 py-2.5 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center text-stone-600 text-[10px] font-bold">
              {assignee.initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-medium text-stone-800 truncate">{assignee.name}</div>
              <div className="text-[9px] text-stone-500">{assignee.city}</div>
            </div>
            <span className={cn("px-2 py-0.5 rounded text-[8px] font-medium capitalize", statusColors[assignee.status])}>
              {assignee.status}
            </span>
          </div>
        ))}
      </div>
      
      {/* Summary */}
      <div className="px-3 py-2 bg-stone-50 border-t border-stone-100">
        <div className="flex items-center justify-between text-[9px]">
          <span className="text-stone-500">
            {isEs ? 'Total activos: ' : 'Total active: '}<strong className="text-stone-700">8</strong>
          </span>
          <span className="text-emerald-600 font-medium">
            {isEs ? '3 firmados este mes' : '3 signed this month'}
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// RELOCATION-SPECIFIC MOCKUPS
// ============================================================================

/**
 * Family Requirements Overlap Visual
 * Shows how different family needs intersect
 */
export const FamilyOverlapVisual = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("relative w-full max-w-[280px] aspect-square", className)}>
      <svg viewBox="0 0 200 200" className="w-full h-full">
        {/* Background map hint */}
        <rect width="200" height="200" fill="#f5f5f4" rx="16" />
        <path d="M0,100 L200,100 M100,0 L100,200" stroke="#e7e5e4" strokeWidth="1" />
        
        {/* Partner's commute zone */}
        <ellipse cx="75" cy="90" rx="55" ry="45" fill="#dbeafe" fillOpacity="0.5" stroke="#3b82f6" strokeWidth="1.5" />
        
        {/* Kids' school zone */}
        <ellipse cx="125" cy="85" rx="50" ry="50" fill="#d1fae5" fillOpacity="0.5" stroke="#10b981" strokeWidth="1.5" />
        
        {/* Assignee's commute zone */}
        <ellipse cx="100" cy="120" rx="45" ry="40" fill="#fef3c7" fillOpacity="0.5" stroke="#f59e0b" strokeWidth="1.5" />
        
        {/* Sweet spot */}
        <ellipse cx="100" cy="95" rx="20" ry="18" fill="#10b981" fillOpacity="0.7" />
      </svg>
      
      {/* Labels */}
      <div className="absolute top-[20%] left-[10%] bg-blue-500 text-white text-[9px] px-2 py-1 rounded-lg shadow">
        {isEs ? 'Trabajo pareja' : "Partner's work"}
      </div>
      <div className="absolute top-[15%] right-[10%] bg-emerald-500 text-white text-[9px] px-2 py-1 rounded-lg shadow">
        {isEs ? 'Colegios int.' : "Int'l schools"}
      </div>
      <div className="absolute bottom-[20%] left-1/2 -translate-x-1/2 bg-amber-500 text-white text-[9px] px-2 py-1 rounded-lg shadow">
        {isEs ? 'Tu oficina' : 'Your office'}
      </div>
      <div className="absolute top-[42%] left-1/2 -translate-x-1/2 bg-white text-emerald-700 text-[10px] px-2 py-1 rounded-lg shadow-lg font-semibold border border-emerald-200">
        {isEs ? 'Zona ideal ✓' : 'Sweet spot ✓'}
      </div>
    </div>
  );
};

/**
 * Assignee Profile Card (detailed)
 */
export const AssigneeProfileCard = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-white rounded-2xl shadow-lg border border-stone-200 overflow-hidden max-w-xs", className)}>
      {/* Header */}
      <div className="bg-stone-900 text-white p-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center text-lg font-bold">JM</div>
          <div>
            <h3 className="font-bold">John Martinez</h3>
            <p className="text-stone-300 text-xs">
              {isEs ? 'Ingeniero Senior • De Austin, TX' : 'Senior Engineer • From Austin, TX'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Details */}
      <div className="p-4 space-y-3">
        <div className="flex items-start gap-3">
          <Building className="w-4 h-4 text-stone-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] text-stone-500">{isEs ? 'Oficina' : 'Office'}</p>
            <p className="text-xs text-stone-800 font-medium">@22 District, Barcelona</p>
          </div>
        </div>
        
        <div className="flex items-start gap-3">
          <Users className="w-4 h-4 text-stone-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] text-stone-500">{isEs ? 'Familia' : 'Family'}</p>
            <p className="text-xs text-stone-800 font-medium">
              {isEs ? 'Pareja + 2 hijos (5, 8)' : 'Partner + 2 children (5, 8)'}
            </p>
          </div>
        </div>
        
        <div className="flex items-start gap-3">
          <Clock className="w-4 h-4 text-stone-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] text-stone-500">{isEs ? 'Fecha mudanza' : 'Move date'}</p>
            <p className="text-xs text-stone-800 font-medium">
              {isEs ? 'Enero 2025' : 'January 2025'}
            </p>
          </div>
        </div>
        
        {/* Tags */}
        <div className="pt-2 border-t border-stone-100">
          <p className="text-[10px] text-stone-500 mb-2">{isEs ? 'Requisitos' : 'Requirements'}</p>
          <div className="flex flex-wrap gap-1.5">
            <span className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded text-[10px]">
              {isEs ? 'Colegio int.' : "Int'l school"}
            </span>
            <span className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded text-[10px]">
              {isEs ? '3+ hab.' : '3+ bed'}
            </span>
            <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-[10px]">
              {isEs ? '≤30min commute' : '≤30min commute'}
            </span>
          </div>
        </div>
        
        {/* Sensitivities */}
        <div className="pt-2 border-t border-stone-100">
          <p className="text-[10px] text-stone-500 mb-2">{isEs ? 'Sensibilidades' : 'Sensitivities'}</p>
          <div className="flex flex-wrap gap-1.5">
            <span className="px-2 py-1 bg-red-50 text-red-700 rounded text-[10px] flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              {isEs ? 'Sin escaleras (pareja)' : 'No stairs (partner)'}
            </span>
            <span className="px-2 py-1 bg-stone-100 text-stone-600 rounded text-[10px]">
              {isEs ? 'Noches tranquilas' : 'Quiet evenings'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default {
  VignetteBriefForm,
  VignetteCityAnalysis,
  VignetteDashboard,
  FamilyOverlapVisual,
  AssigneeProfileCard
};

