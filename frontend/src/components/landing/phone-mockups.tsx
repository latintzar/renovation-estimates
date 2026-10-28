"use client";

import React from "react";
import Image from "next/image";
import { Check, ChevronDown, MessageCircle, AlertTriangle, ArrowRight, Info, MapPin, Sparkles, User, Calendar, ClipboardList, Layers, ExternalLink, BarChart3, X, Clock, Bell, MoreVertical, Mail } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { LANDING_IMAGES } from "./illustrations/LandingImages";

// --- Phone Frame (Stripe Connect hero style — no notch, no buttons, clean shadow) ---
export const PhoneFrame = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div
      className={className}
      style={{
        position: 'relative',
        margin: '0 auto',
        width: 300,
        height: 600,
        borderRadius: 36,
        border: '8px solid #0a2540',
        background: '#0a2540',
        boxShadow: [
          '0 50px 100px -20px rgba(50, 50, 93, 0.25)',
          '0 30px 60px -30px rgba(0, 0, 0, 0.30)',
          '0 0 0 0.5px rgba(0, 0, 0, 0.10)',
        ].join(', '),
        flexShrink: 0,
      }}
    >
      <div
        className="scrollbar-hide overflow-y-auto"
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 28,
          overflow: 'hidden',
          background: '#fff',
          position: 'relative',
        }}
      >
        {children}
      </div>
    </div>
  );
};

// --- Desktop Frame (Sharpened) ---
export const DesktopFrame = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={`relative mx-auto bg-white rounded-xl shadow-[0_20px_50px_-12px_rgba(0,0,0,0.15)] border border-stone-300 overflow-hidden ring-1 ring-black/5 ${className}`}>
      {/* Browser Bar */}
      <div className="bg-stone-100/90 backdrop-blur-md border-b border-stone-300 h-10 flex items-center px-4 gap-3 select-none">
        <div className="flex gap-1.5 opacity-80">
          <div className="w-3 h-3 rounded-full bg-[#FF5F57] border border-[#E0443E] shadow-sm"></div>
          <div className="w-3 h-3 rounded-full bg-[#FEBC2E] border border-[#D89E24] shadow-sm"></div>
          <div className="w-3 h-3 rounded-full bg-[#28C840] border border-[#1AAB29] shadow-sm"></div>
        </div>
        <div className="flex-1 ml-4 flex justify-center">
           <div className="bg-white h-7 w-full max-w-md rounded-[6px] border border-stone-200/80 shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex items-center justify-center gap-2 px-3 text-[11px] text-stone-500 font-medium tracking-tight">
             <span className="w-2 h-2 rounded-full bg-green-500"></span>
             leo.casa/agent/dashboard
           </div>
        </div>
      </div>
      {/* Content */}
      <div className="h-full overflow-y-auto scrollbar-hide bg-stone-50/50 min-h-[450px]">
        {children}
      </div>
    </div>
  );
};


// --- Mock Components ---

// 1. Mock Viewing Checklist
export const MockViewingChecklist = () => {
  return (
    <div className="flex flex-col h-full bg-white font-sans">
      <div className="pt-12 pb-3 px-4 border-b border-stone-100 bg-white/90 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-lg font-bold text-stone-900 leading-tight">Viewing Checklist</h2>
          <Badge variant="secondary" className="bg-stone-100 text-stone-600 border-none">6 points</Badge>
        </div>
        <div className="flex gap-2">
           <Button size="sm" variant="outline" className="h-7 text-xs border-stone-200">Copy</Button>
           <Button size="sm" className="h-7 text-xs bg-[#25d366] hover:bg-[#20bd5a] text-white border-none gap-1">
             <MessageCircle className="w-3 h-3" /> WhatsApp
           </Button>
        </div>
      </div>
      
      <div className="p-3 space-y-3 bg-stone-50 flex-1">
        <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-3">
          <div className="flex items-start gap-2 mb-2">
             <div className="bg-amber-100 text-amber-700 p-1 rounded-md">
               <AlertTriangle className="w-4 h-4" />
             </div>
             <div>
               <h3 className="font-semibold text-sm text-stone-900">Aluminosis Risk</h3>
               <p className="text-xs text-stone-500">Built 1965 (High Risk Era)</p>
             </div>
          </div>
          <div className="bg-stone-50 rounded p-2 text-xs text-stone-700 mb-2">
            <strong>Ask Agent:</strong> "Has an ITE been passed recently? Are there any cement test results?"
          </div>
          <div className="flex gap-1 h-16">
             <div className="w-1/2 bg-stone-200 rounded-md overflow-hidden relative">
                <div className="absolute inset-0 bg-stone-300 animate-pulse"></div>
             </div>
             <div className="w-1/2 bg-stone-200 rounded-md overflow-hidden relative">
                 <div className="absolute inset-0 bg-stone-300 animate-pulse delay-75"></div>
             </div>
          </div>
        </div>
         <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-3">
          <div className="flex items-start gap-2 mb-2">
             <div className="bg-blue-100 text-blue-700 p-1 rounded-md">
               <Info className="w-4 h-4" />
             </div>
             <div>
               <h3 className="font-semibold text-sm text-stone-900">Legal vs. Usage</h3>
               <p className="text-xs text-stone-500">Listing says 85m², Cadastre 72m²</p>
             </div>
          </div>
          <div className="bg-stone-50 rounded p-2 text-xs text-stone-700">
            <strong>Check:</strong> Verify if the balcony was enclosed (often illegal).
          </div>
        </div>
      </div>
    </div>
  );
};

// 2. Mock Property Analysis
export const MockPropertyAnalysis = () => {
  // This is a marketing mock; avoid i18n hooks to keep build/lint deterministic.
  const isEs = false;
  
  return (
    <div className="flex flex-col h-full bg-stone-50 font-sans">
      <div className="h-48 relative">
         <Image
           src={LANDING_IMAGES.interiorApartment}
           alt="Carrer de Bailèn, 124"
           fill
           className="object-cover"
           sizes="300px"
         />
         <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
         <div className="absolute bottom-4 left-4 text-white">
            <Badge className="bg-green-500 hover:bg-green-600 border-none mb-2 shadow-sm">94% {isEs ? 'Encaja' : 'Match'}</Badge>
            <h2 className="text-xl font-bold leading-tight shadow-sm">Carrer de Bailèn, 124</h2>
            <p className="text-sm opacity-90 shadow-sm">Eixample Dret • €450,000</p>
         </div>
      </div>

      <div className="p-4 space-y-4">
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm">
          <h3 className="font-serif text-lg mb-3 flex items-center gap-2">
            The Verdict <Sparkles className="w-4 h-4 text-amber-400" />
          </h3>
          <p className="text-sm text-stone-600 leading-relaxed mb-3">
            A rare find in Eixample. Good bones, high ceilings, and correctly priced. However, the back terrace faces a school yard (noise risk 8:30-17:00).
          </p>
          <div className="flex gap-2 flex-wrap">
             <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">Underpriced</Badge>
             <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">Noise Risk</Badge>
             <Badge variant="outline" className="border-stone-200 text-stone-600">High Ceilings</Badge>
          </div>
        </div>
        <div className="space-y-2">
           <h4 className="text-xs font-bold text-stone-400 uppercase tracking-wider">Analysis Highlights</h4>
           <div className="flex items-center gap-3 p-3 bg-white rounded-lg border border-stone-100">
              <div className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center text-stone-600 text-xs font-bold">1</div>
              <div className="text-sm">
                 <span className="font-medium text-stone-900">Gentrification:</span> Low risk. Stable area.
              </div>
           </div>
           <div className="flex items-center gap-3 p-3 bg-white rounded-lg border border-stone-100">
              <div className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center text-stone-600 text-xs font-bold">2</div>
              <div className="text-sm">
                 <span className="font-medium text-stone-900">Airbnb:</span> <span className="text-red-600 font-bold">High density (15%)</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

// 3. Mock Renovation Tiers (Mobile)
const tierConfig = {
  estandar: { name: "Estándar", uiName: "Livable", color: "border-blue-200 hover:border-blue-400" },
  optimo: { name: "Óptimo", uiName: "Comfortable", color: "border-green-200 hover:border-green-400" }
};

export const MockRenovationTiers = () => {
  const tiers = {
    estandar: {
      tier: 'estandar', uiName: "Livable", costRange: [25000, 35000], timelineWeeks: [3, 4],
      keyWorkItems: ["Paint & smooth walls", "Sand floors", "Basic kitchen update"]
    },
    optimo: {
      tier: 'optimo', uiName: "Comfortable", costRange: [45000, 60000], timelineWeeks: [6, 8],
      keyWorkItems: ["Open kitchen layout", "New bathroom", "AC installation", "Double glazed windows"]
    }
  };

  const formatCostRange = (range: number[]) => `€${Math.round(range[0] / 1000)}k–€${Math.round(range[1] / 1000)}k`;
  const formatTimeline = (weeks: number[]) => `${weeks[0]}–${weeks[1]} semanas`;

  return (
    <div className="flex flex-col h-full bg-stone-50 font-sans">
       <div className="pt-12 pb-4 px-4 bg-white border-b border-stone-200 sticky top-0 z-10">
         <h2 className="text-lg font-bold text-stone-900">Renovation Potential</h2>
         <p className="text-xs text-stone-500">Estimated based on current market rates</p>
       </div>
       <div className="p-4 space-y-4 overflow-y-auto">
         {(['estandar', 'optimo'] as const).map((tierKey) => {
            const tier = tiers[tierKey];
            const config = tierConfig[tierKey];
            return (
              <Card key={tierKey} className={cn("group cursor-pointer hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5 border overflow-hidden", config.color)}>
                <div className="relative">
                  <div className="aspect-[4/3] relative overflow-hidden bg-muted">
                    <div className="w-full h-full bg-gradient-to-br from-stone-200 to-stone-300 flex items-center justify-center">
                        <span className="text-muted-foreground text-sm">AI Render Preview</span>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <div className="absolute top-3 left-3">
                      <span className="bg-white text-black px-2 py-1 rounded text-sm font-medium">{config.uiName}</span>
                    </div>
                  </div>
                  <div className="p-4 pb-4">
                    <div className="flex justify-between items-center mb-3">
                      <div><div className="text-xs text-muted-foreground mb-1">Costo total</div><div className="font-semibold">{formatCostRange(tier.costRange)}</div></div>
                      <div className="text-right"><div className="text-xs text-muted-foreground mb-1">Duración</div><div className="font-semibold">{formatTimeline(tier.timelineWeeks)}</div></div>
                    </div>
                    <div className="space-y-1 mb-3">
                        <div className="text-xs text-muted-foreground mb-1">Trabajos principales:</div>
                        <ul className="text-xs text-foreground space-y-0.5">
                          {tier.keyWorkItems.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-1.5"><span className="text-muted-foreground mt-0.5">•</span><span className="line-clamp-1">{item}</span></li>
                          ))}
                        </ul>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-primary mt-3 pt-3 border-t">
                      <span>Ver detalles</span>
                      <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </div>
              </Card>
            );
         })}
       </div>
    </div>
  );
};

// 4. Mock Agent Dashboard (Expanded)
export const MockAgentDashboard = () => {
    return (
        <div className="flex h-full min-h-[600px] font-sans text-stone-900 bg-white">
            {/* Sidebar */}
            <div className="w-64 bg-stone-50 border-r border-stone-200 p-6 flex flex-col gap-6 flex-shrink-0">
                <div className="flex items-center gap-3 font-bold text-stone-900 mb-4">
                   <div className="w-8 h-8 bg-stone-900 rounded-full flex items-center justify-center text-white text-sm">L</div>
                   <span className="text-lg">Leo.Agent</span>
                </div>
                <div className="space-y-2">
                    <div className="flex items-center gap-3 text-sm font-medium bg-white border border-stone-200 shadow-sm px-4 py-2.5 rounded-lg text-stone-900">
                        <User className="w-4 h-4" /> Clients
                    </div>
                    <div className="flex items-center gap-3 text-sm font-medium text-stone-500 px-4 py-2.5 rounded-lg hover:bg-stone-100 cursor-pointer">
                        <Calendar className="w-4 h-4" /> Viewings
                    </div>
                    <div className="flex items-center gap-3 text-sm font-medium text-stone-500 px-4 py-2.5 rounded-lg hover:bg-stone-100 cursor-pointer">
                        <Layers className="w-4 h-4" /> Properties
                    </div>
                </div>
                
                <div className="mt-auto">
                    <div className="bg-stone-900 text-white rounded-xl p-4 text-sm shadow-lg">
                        <div className="font-bold mb-2 flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Weekly Insight</div>
                        <p className="opacity-80 leading-relaxed">Poblenou prices dropped 2% this week. Good time for client Marc.</p>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 p-10 overflow-y-auto bg-white">
                 <div className="flex justify-between items-end mb-10">
                    <div>
                         <h2 className="text-3xl font-bold font-serif mb-2 text-stone-900">Client Roster</h2>
                         <p className="text-stone-500">3 active clients • 2 pending onboarding</p>
                    </div>
                    <Button className="bg-stone-900 text-white rounded-full px-6 h-10 hover:bg-stone-800 shadow-md">Add Client</Button>
                 </div>

                 <div className="grid grid-cols-1 gap-6 max-w-4xl">
                     {/* Client Card 1 - Expanded */}
                     <div className="p-6 rounded-2xl border border-stone-200 shadow-sm bg-white hover:shadow-md transition-all duration-300">
                         <div className="flex items-start justify-between mb-6">
                             <div className="flex gap-5">
                                 <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 font-bold text-xl">SP</div>
                                 <div>
                                     <h3 className="font-bold text-xl text-stone-900">Sarah Parker</h3>
                                     <div className="flex items-center gap-2 text-stone-500 mt-1">
                                         <MapPin className="w-4 h-4" /> Gracia • €450k-500k
                                     </div>
                                     
                                     {/* Preferences Tags */}
                                     <div className="flex flex-wrap gap-2 mt-3">
                                         <Badge variant="secondary" className="bg-stone-100 text-stone-600 hover:bg-stone-200 font-normal">Needs Terrace</Badge>
                                         <Badge variant="secondary" className="bg-stone-100 text-stone-600 hover:bg-stone-200 font-normal">No Ground Floor</Badge>
                                         <Badge variant="secondary" className="bg-stone-100 text-stone-600 hover:bg-stone-200 font-normal">Quiet Street</Badge>
                                     </div>
                                 </div>
                             </div>
                             <div className="flex gap-2">
                                 <Button variant="outline" className="h-9 text-sm border-stone-200">View Notes</Button>
                                 <Button className="h-9 text-sm bg-stone-900 text-white hover:bg-stone-800 shadow-sm">Send Shortlist (3)</Button>
                             </div>
                         </div>
                         
                         {/* Smart Recommendations Preview */}
                         <div className="bg-stone-50/50 rounded-xl p-4 border border-stone-100">
                             <div className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                 <Sparkles className="w-3 h-3 text-amber-500" /> Top Match
                             </div>
                             <div className="flex gap-4 items-center bg-white p-3 rounded-lg border border-stone-100 shadow-sm">
                                 <div className="w-20 h-16 bg-stone-200 rounded-md overflow-hidden flex-shrink-0">
                                     <div className="w-full h-full bg-gradient-to-br from-stone-300 to-stone-400" />
                                 </div>
                                 <div className="flex-1 min-w-0">
                                     <div className="font-bold text-stone-900">Carrer de Verdi, 45</div>
                                     <div className="text-sm text-stone-500 truncate">96% Match • Silent street • Terrace potential</div>
                                 </div>
                                 <div className="text-green-600 font-bold text-lg px-2">€485k</div>
                             </div>
                         </div>
                     </div>

                     {/* Client Card 2 */}
                     <div className="p-6 rounded-2xl border border-stone-200 shadow-sm bg-white hover:shadow-md transition-all duration-300 opacity-90">
                         <div className="flex items-center justify-between">
                             <div className="flex items-center gap-5">
                                 <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xl">MJ</div>
                                 <div>
                                     <h3 className="font-bold text-xl text-stone-900">Marc Johnson</h3>
                                     <div className="flex items-center gap-2 text-stone-500 mt-1">
                                         <MapPin className="w-4 h-4" /> Poblenou • €600k+
                                     </div>
                                 </div>
                             </div>
                              <div className="text-right">
                                 <div className="inline-flex items-center gap-2 text-sm font-medium text-stone-600 bg-stone-100 px-4 py-2 rounded-full border border-stone-200">
                                     <Calendar className="w-4 h-4" /> 
                                     <div className="flex flex-col items-start leading-none">
                                         <span className="text-[10px] text-stone-400 uppercase">Viewing</span>
                                         <span>Tomorrow 10:00 AM</span>
                                     </div>
                                 </div>
                             </div>
                         </div>
                     </div>
                 </div>
            </div>
        </div>
    )
}

// 5. Mock Email Alert (Enhanced)
export const MockEmailAlert = () => {
  return (
    <div className="bg-white w-full h-full flex flex-col font-sans text-stone-900">
        {/* Email Client Header (Mock iOS Mail) */}
        <div className="pt-12 pb-3 px-4 border-b border-gray-200 bg-gray-50/90 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
            <div className="flex items-center gap-1 text-blue-500 font-medium text-base">
                <ChevronDown className="w-5 h-5 rotate-90" />
                Inbox
            </div>
            <div className="text-xs text-gray-500 font-semibold">Today, 9:41 AM</div>
            <div className="w-16 flex justify-end text-blue-500">
                <div className="w-5 h-5 flex flex-col justify-center gap-1 items-end">
                    <div className="w-4 h-0.5 bg-blue-500 rounded-full"></div>
                    <div className="w-3 h-0.5 bg-blue-500 rounded-full"></div>
                </div>
            </div>
        </div>

        {/* Email Body */}
        <div className="flex-1 overflow-y-auto bg-white p-0">
            {/* Sender Info */}
            <div className="px-5 py-4 border-b border-gray-100">
                <div className="flex justify-between items-start mb-1">
                    <div className="font-bold text-lg text-stone-900">Leo.casa</div>
                    <div className="text-gray-400 text-xs">9:41 AM</div>
                </div>
                <div className="text-gray-500 text-sm mb-1">To: You</div>
                <div className="text-stone-900 font-medium text-base">3 new matches for your Tuesday 🏠</div>
            </div>

            {/* Email Content Area */}
            <div className="p-5 space-y-6">
                <p className="text-stone-600 text-sm leading-relaxed">
                    Good morning, Sarah. I scanned 142 new listings today. Only these 3 matched your need for <strong>natural light</strong> and a <strong>quiet street</strong> in Gracia.
                </p>

                {/* Property Card */}
                <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
                    <div className="h-48 relative group cursor-pointer">
                        <Image
                          src={LANDING_IMAGES.interiorApartment}
                          alt="Carrer de Bailèn, 124"
                          fill
                          className="object-cover"
                          sizes="400px"
                        />
                        <div className="absolute top-3 left-3 bg-green-500 text-white px-2.5 py-1 rounded-md text-xs font-bold shadow-sm flex items-center gap-1">
                            <Sparkles className="w-3 h-3" /> 94% Match
                        </div>
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 via-black/40 to-transparent p-4 pt-12 text-white">
                            <div className="font-bold text-xl leading-tight mb-0.5">Carrer de Bailèn, 124</div>
                            <div className="text-white/90 text-sm font-medium opacity-90">€450,000 • Eixample Dret</div>
                        </div>
                    </div>
                    
                    <div className="p-4 bg-white">
                        <div className="flex gap-2 mb-4 overflow-x-auto scrollbar-hide pb-1">
                            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 shrink-0">Underpriced</Badge>
                            <Badge variant="outline" className="bg-stone-50 text-stone-600 border-stone-200 shrink-0">Quiet Street</Badge>
                            <Badge variant="outline" className="bg-stone-50 text-stone-600 border-stone-200 shrink-0">High Ceilings</Badge>
                        </div>
                        
                        <div className="space-y-3 mb-5">
                            <div className="flex gap-3 items-start">
                                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0 mt-0.5">
                                    <Check className="w-3.5 h-3.5 text-green-700" />
                                </div>
                                <p className="text-sm text-stone-600 leading-snug">
                                    <span className="font-medium text-stone-900">Why it fits:</span> Perfect 12m commute, structural integrity confirmed (1985 build), and away from main roads.
                                </p>
                            </div>
                            <div className="flex gap-3 items-start">
                                <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
                                    <Info className="w-3.5 h-3.5 text-amber-700" />
                                </div>
                                <p className="text-sm text-stone-600 leading-snug">
                                    <span className="font-medium text-stone-900">Heads up:</span> Back terrace faces a school yard (noise 8am-5pm).
                                </p>
                            </div>
                        </div>

                        <Button className="w-full bg-stone-900 text-white h-10 text-sm font-medium hover:bg-stone-800 shadow-sm rounded-lg">
                            Analyze Listing
                        </Button>
                    </div>
                </div>

                {/* Secondary Card (Preview) */}
                <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden opacity-60 pointer-events-none">
                    <div className="h-12 bg-stone-100 flex items-center px-4 border-b border-stone-100">
                        <div className="w-24 h-3 bg-stone-200 rounded-full"></div>
                    </div>
                    <div className="p-4">
                        <div className="h-4 w-3/4 bg-stone-100 rounded mb-2"></div>
                        <div className="h-3 w-1/2 bg-stone-100 rounded"></div>
                    </div>
                </div>
                
                <div className="text-center pt-2 pb-6">
                    <span className="text-xs text-gray-400 font-medium cursor-pointer hover:text-gray-600 transition-colors">See all 3 matches →</span>
                </div>
            </div>
        </div>
        
        {/* Bottom Toolbar (Mock iOS Mail) */}
        <div className="h-12 border-t border-gray-200 bg-gray-50 flex items-center justify-between px-6 text-blue-500 sticky bottom-0">
            <Mail className="w-5 h-5" />
            <div className="w-5 h-5" /> {/* Spacer */}
            <div className="w-5 h-5" /> {/* Spacer */}
        </div>
    </div>
  );
}

// 6. Mock Renovation Modal (Desktop) - Replicating actual component structure
export const MockRenovationModal = () => {
    return (
        <div className="bg-white h-full flex flex-col font-sans text-stone-900">
            {/* Header */}
            <div className="px-6 py-4 border-b bg-stone-50/70 backdrop-blur flex-shrink-0 z-10 flex items-center justify-between">
                <div>
                    <div className="text-sm text-stone-500 mb-1">Renovation Tier</div>
                    <h2 className="text-2xl font-bold text-stone-900">Comfortable</h2>
                </div>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-stone-200 rounded-full">
                    <X className="h-4 w-4" />
                </Button>
            </div>

            {/* Content Grid */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full overflow-y-auto p-6">
                    <div className="grid grid-cols-8 gap-6 h-full">
                        {/* Left: Carousel (5 cols) */}
                        <div className="col-span-5 flex flex-col">
                            <div className="bg-stone-100 rounded-xl border border-stone-200 flex-1 relative overflow-hidden shadow-inner min-h-[300px]">
                                {/* Placeholder Carousel Image */}
                                <div className="absolute inset-0 bg-gradient-to-br from-stone-200 to-stone-300 flex items-center justify-center text-stone-500">
                                    <div className="text-center">
                                        <div className="mb-2 font-medium">AI Render Preview</div>
                                        <div className="text-xs opacity-70">Living Room + Open Kitchen</div>
                                    </div>
                                </div>
                                
                                {/* Labels */}
                                <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-1.5 rounded-md text-sm font-medium backdrop-blur-sm">Before</div>
                                <div className="absolute top-4 right-4 bg-black/70 text-white px-3 py-1.5 rounded-md text-sm font-medium backdrop-blur-sm">After</div>
                                
                                {/* Controls */}
                                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2">
                                    <div className="w-2 h-2 rounded-full bg-white shadow-sm cursor-pointer"></div>
                                    <div className="w-2 h-2 rounded-full bg-white/50 shadow-sm cursor-pointer"></div>
                                    <div className="w-2 h-2 rounded-full bg-white/50 shadow-sm cursor-pointer"></div>
                                </div>
                            </div>
                            <div className="mt-4 text-center text-sm text-stone-500 bg-stone-50 py-2 rounded-lg border border-stone-100">
                                Cluster: <strong className="text-stone-700">Living Room + Open Kitchen</strong>
                            </div>
                        </div>

                        {/* Right: Timeline & Scope (3 cols) */}
                        <div className="col-span-3 overflow-y-auto pr-2 space-y-8">
                            
                            {/* Phase 1 */}
                            <div className="relative pl-6 border-l-2 border-stone-200 pb-8">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-blue-500 border-4 border-white shadow-sm"></div>
                                <div className="mb-3">
                                    <h3 className="font-bold text-stone-900">Demolition & Prep</h3>
                                    <span className="text-xs font-medium text-stone-500 bg-stone-100 px-2 py-0.5 rounded">Week 1-2</span>
                                </div>
                                
                                <div className="space-y-2 mb-4">
                                    <div className="flex items-start gap-2 text-sm text-stone-600 bg-white p-2.5 rounded-lg border border-stone-100 shadow-sm hover:border-blue-200 transition-colors cursor-default">
                                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0"></div>
                                        <span className="leading-snug">Remove partition wall between kitchen/living</span>
                                    </div>
                                    <div className="flex items-start gap-2 text-sm text-stone-600 bg-white p-2.5 rounded-lg border border-stone-100 shadow-sm hover:border-blue-200 transition-colors cursor-default">
                                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0"></div>
                                        <span className="leading-snug">Clear debris & transport</span>
                                    </div>
                                </div>

                                <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 flex items-start gap-3">
                                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                                    <div>
                                        <div className="text-xs font-bold text-amber-800 uppercase tracking-wide mb-0.5">Permit Required</div>
                                        <div className="text-xs text-amber-700">Assabentat (Immediate)</div>
                                    </div>
                                </div>
                            </div>

                            {/* Phase 2 */}
                            <div className="relative pl-6 border-l-2 border-stone-200 pb-8">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-stone-300 border-4 border-white shadow-sm"></div>
                                <div className="mb-3">
                                    <h3 className="font-bold text-stone-900">Installations</h3>
                                    <span className="text-xs font-medium text-stone-500 bg-stone-100 px-2 py-0.5 rounded">Week 3-4</span>
                                </div>
                                
                                <div className="space-y-2">
                                    <div className="flex items-start gap-2 text-sm text-stone-600 bg-white p-2.5 rounded-lg border border-stone-100 shadow-sm">
                                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-stone-400 shrink-0"></div>
                                        <span className="leading-snug">New electrical circuits (kitchen)</span>
                                    </div>
                                    <div className="flex items-start gap-2 text-sm text-stone-600 bg-white p-2.5 rounded-lg border border-stone-100 shadow-sm">
                                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-stone-400 shrink-0"></div>
                                        <span className="leading-snug">Plumbing rough-ins</span>
                                    </div>
                                     <div className="flex items-start gap-2 text-sm text-stone-600 bg-white p-2.5 rounded-lg border border-stone-100 shadow-sm">
                                        <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-stone-400 shrink-0"></div>
                                        <span className="leading-snug">AC Ducts installation</span>
                                    </div>
                                </div>
                            </div>

                             {/* Phase 3 */}
                            <div className="relative pl-6 border-l-2 border-stone-200">
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-stone-300 border-4 border-white shadow-sm"></div>
                                <div className="mb-3">
                                    <h3 className="font-bold text-stone-900">Finishes</h3>
                                    <span className="text-xs font-medium text-stone-500 bg-stone-100 px-2 py-0.5 rounded">Week 5-6</span>
                                </div>
                                <div className="text-xs text-stone-400 italic pl-1">View full details...</div>
                            </div>

                        </div>
                    </div>
                </div>
            </div>

            {/* Footer Summary */}
            <div className="border-t bg-white p-6 flex-shrink-0">
                <div className="grid grid-cols-8 gap-6">
                    <div className="col-span-5"></div>
                    <div className="col-span-3 flex items-center justify-between">
                        <div>
                            <div className="text-xs text-stone-500 uppercase tracking-wider font-medium mb-1">Total Estimate</div>
                            <div className="text-xl font-bold text-stone-900">€45k - €60k</div>
                        </div>
                        <Button className="bg-stone-900 text-white hover:bg-stone-800 shadow-md">
                            Ask Agent
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}

// 7. Waveform Component
export const VoiceWaveform = () => {
  const [mounted, setMounted] = React.useState(false);
  const [bars, setBars] = React.useState<Array<{height: string, delay: string, opacity: number}>>([]);

  React.useEffect(() => {
    setMounted(true);
    setBars([...Array(20)].map((_, i) => ({
        height: `${Math.max(4, Math.random() * 48)}px`,
        delay: `${i * 0.05}s`,
        opacity: Math.max(0.2, Math.random())
    })));
  }, []);

  if (!mounted) return <div className="flex items-center justify-center gap-1 h-12" />;

  return (
    <div className="flex items-center justify-center gap-1 h-12">
      {bars.map((bar, i) => (
        <div 
          key={i} 
          className="w-1.5 bg-stone-900 rounded-full animate-[waveform_1.2s_ease-in-out_infinite]"
          style={{ 
            height: bar.height,
            animationDelay: bar.delay,
            opacity: bar.opacity
          }} 
        />
      ))}
    </div>
  );
};

export const MockRenovationPlanner = MockRenovationModal;
