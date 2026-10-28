"use client";

import React, { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { useDictionary } from "@/contexts/DictionaryContext";
import { 
  Heart, 
  MessageCircle, 
  Send, 
  Building2, 
  MapPin, 
  Euro, 
  Bed, 
  Square, 
  Clock,
  ThumbsUp,
  ThumbsDown,
  Camera,
  FileText,
  Hammer,
  ChevronRight,
  Check,
  Sparkles
} from "lucide-react";
import { LANDING_IMAGES } from "./LandingImages";

/**
 * ClientPortalMockup - Shows the agent's client-facing property shortlist
 * Features: Agency branding, client profile, property cards with like/comment, visit notes
 */
export const ClientPortalMockup = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  const [selectedProperty, setSelectedProperty] = useState(0);
  
  const client = {
    name: "María García",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop&crop=face",
    budget: "€400k–€520k",
    area: "Eixample, Gràcia",
    beds: "3+",
    mustHaves: isEs 
      ? ["Mucha luz natural", "Balcón o terraza", "Cerca del metro"]
      : ["Lots of natural light", "Balcony or terrace", "Near metro"],
    dealbreakers: isEs
      ? ["Planta baja", "Sin ascensor > 3ª planta"]
      : ["Ground floor", "No elevator > 3rd floor"]
  };
  
  const properties = [
    {
      id: 1,
      address: "Bailèn 124",
      area: "Eixample",
      price: "€485,000",
      beds: 3,
      sqm: 95,
      year: 1985,
      match: 91,
      image: LANDING_IMAGES.realityNiceLight,
      liked: true,
      comment: isEs ? "Me encanta la luz!" : "Love the light!",
      agentNote: isEs ? "ITE OK. Comunidad €80/mes" : "ITE OK. Community €80/mo",
      visitNotes: isEs ? "Revisar presión agua, preguntar por vecinos" : "Check water pressure, ask about neighbors"
    },
    {
      id: 2,
      address: "Aragó 89",
      area: "Gràcia",
      price: "€520,000",
      beds: 3,
      sqm: 105,
      year: 1972,
      match: 87,
      image: LANDING_IMAGES.interiorApartment,
      liked: null,
      comment: null,
      agentNote: isEs ? "Necesita reforma cocina" : "Kitchen needs renovation",
      visitNotes: null
    },
    {
      id: 3,
      address: "València 201",
      area: "Sant Antoni",
      price: "€495,000",
      beds: 3,
      sqm: 88,
      year: 1990,
      match: 84,
      image: LANDING_IMAGES.propertyCardApartment,
      liked: false,
      comment: isEs ? "Demasiado ruidoso" : "Too noisy",
      agentNote: isEs ? "Reformado 2020" : "Renovated 2020",
      visitNotes: null
    },
  ];
  
  const selected = properties[selectedProperty];
  
  return (
    <div className={cn("bg-white rounded-2xl border border-stone-200 shadow-xl overflow-hidden max-w-4xl mx-auto", className)}>
      {/* Agency Header */}
      <div className="bg-gradient-to-r from-stone-900 to-stone-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="text-white font-medium text-sm">Inmobiliaria Ejemplo</div>
            <div className="text-stone-400 text-xs">{isEs ? 'Portal del cliente' : 'Client portal'}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-white/20">
            <Image src={client.avatar} alt={client.name} width={32} height={32} className="object-cover" />
          </div>
          <span className="text-white text-sm font-medium">{client.name}</span>
        </div>
      </div>
      
      <div className="flex flex-col md:flex-row">
        {/* Left: Client Profile */}
        <div className="md:w-72 border-r border-stone-100 bg-stone-50/50 p-4">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-wider text-stone-400 mb-2">
              {isEs ? 'Perfil del cliente' : 'Client profile'}
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-white shadow-sm">
                <Image src={client.avatar} alt={client.name} width={48} height={48} className="object-cover" />
              </div>
              <div>
                <div className="font-medium text-stone-900">{client.name}</div>
                <div className="text-xs text-stone-500">{client.budget}</div>
              </div>
            </div>
          </div>
          
          {/* Quick stats */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <div className="bg-white rounded-lg p-2 border border-stone-100">
              <div className="text-[10px] text-stone-400 uppercase">{isEs ? 'Zona' : 'Area'}</div>
              <div className="text-xs font-medium text-stone-700">{client.area}</div>
            </div>
            <div className="bg-white rounded-lg p-2 border border-stone-100">
              <div className="text-[10px] text-stone-400 uppercase">{isEs ? 'Hab.' : 'Beds'}</div>
              <div className="text-xs font-medium text-stone-700">{client.beds}</div>
            </div>
          </div>
          
          {/* Must haves */}
          <div className="mb-4">
            <div className="text-[10px] uppercase tracking-wider text-emerald-600 mb-1.5 font-medium">
              {isEs ? 'Imprescindibles' : 'Must-haves'}
            </div>
            <div className="space-y-1">
              {client.mustHaves.map((item, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-stone-600">
                  <Check className="w-3 h-3 text-emerald-500" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* Dealbreakers */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-red-600 mb-1.5 font-medium">
              {isEs ? 'Descarta' : 'Dealbreakers'}
            </div>
            <div className="space-y-1">
              {client.dealbreakers.map((item, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-stone-500">
                  <span className="w-3 h-3 flex items-center justify-center text-red-400">✕</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Right: Properties Shortlist */}
        <div className="flex-1 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs uppercase tracking-wider text-stone-400">
              {isEs ? 'Propiedades seleccionadas' : 'Selected properties'}
            </div>
            <div className="text-xs text-stone-500">
              {properties.length} {isEs ? 'inmuebles' : 'properties'}
            </div>
          </div>
          
          {/* Property cards */}
          <div className="space-y-3">
            {properties.map((property, idx) => (
              <div 
                key={property.id}
                onClick={() => setSelectedProperty(idx)}
                className={cn(
                  "flex gap-3 p-3 rounded-xl border cursor-pointer transition-all",
                  selectedProperty === idx 
                    ? "bg-stone-50 border-stone-300 shadow-sm" 
                    : "bg-white border-stone-100 hover:border-stone-200"
                )}
              >
                {/* Property image */}
                <div className="w-20 h-20 rounded-lg overflow-hidden shrink-0 relative">
                  <Image src={property.image} alt={property.address} fill className="object-cover" sizes="80px" />
                  {/* Match badge */}
                  <div className="absolute top-1 left-1 bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">
                    {property.match}%
                  </div>
                </div>
                
                {/* Property info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div>
                      <div className="font-medium text-stone-900 text-sm">{property.address}</div>
                      <div className="text-[10px] text-stone-400">{property.area}</div>
                    </div>
                    <div className="text-sm font-semibold text-stone-800">{property.price}</div>
                  </div>
                  
                  {/* Stats row */}
                  <div className="flex items-center gap-3 text-[10px] text-stone-500 mb-2">
                    <span className="flex items-center gap-0.5">
                      <Bed className="w-3 h-3" /> {property.beds}
                    </span>
                    <span className="flex items-center gap-0.5">
                      <Square className="w-3 h-3" /> {property.sqm}m²
                    </span>
                    <span className="flex items-center gap-0.5">
                      <Clock className="w-3 h-3" /> {property.year}
                    </span>
                  </div>
                  
                  {/* Agent note */}
                  <div className="text-[10px] text-stone-600 bg-amber-50 rounded px-2 py-1 mb-2">
                    <span className="font-medium text-amber-700">{isEs ? 'Agente:' : 'Agent:'}</span> {property.agentNote}
                  </div>
                  
                  {/* Client reaction */}
                  <div className="flex items-center gap-2">
                    {property.liked === true && (
                      <div className="flex items-center gap-1 text-emerald-600 text-[10px]">
                        <ThumbsUp className="w-3 h-3" />
                        <span>{property.comment}</span>
                      </div>
                    )}
                    {property.liked === false && (
                      <div className="flex items-center gap-1 text-red-500 text-[10px]">
                        <ThumbsDown className="w-3 h-3" />
                        <span>{property.comment}</span>
                      </div>
                    )}
                    {property.liked === null && (
                      <div className="flex items-center gap-2">
                        <button className="p-1 rounded hover:bg-stone-100 transition-colors">
                          <ThumbsUp className="w-3.5 h-3.5 text-stone-400" />
                        </button>
                        <button className="p-1 rounded hover:bg-stone-100 transition-colors">
                          <ThumbsDown className="w-3.5 h-3.5 text-stone-400" />
                        </button>
                        <button className="p-1 rounded hover:bg-stone-100 transition-colors">
                          <MessageCircle className="w-3.5 h-3.5 text-stone-400" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {/* Visit notes section for selected property */}
          {selected.visitNotes && (
            <div className="mt-4 p-3 bg-blue-50 rounded-xl border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-medium text-blue-800">
                  {isEs ? 'Notas de visita' : 'Visit notes'} - {selected.address}
                </span>
              </div>
              <p className="text-xs text-blue-700">{selected.visitNotes}</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Footer with actions */}
      <div className="border-t border-stone-100 px-4 py-3 bg-stone-50 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-1.5 text-xs text-stone-600 hover:text-stone-900 transition-colors">
            <Hammer className="w-4 h-4" />
            <span>{isEs ? 'Ver opciones reforma' : 'View reno options'}</span>
          </button>
          <button className="flex items-center gap-1.5 text-xs text-stone-600 hover:text-stone-900 transition-colors">
            <Camera className="w-4 h-4" />
            <span>{isEs ? 'Fotos de visita' : 'Visit photos'}</span>
          </button>
        </div>
        <button className="bg-stone-900 text-white text-xs font-medium px-4 py-2 rounded-full hover:bg-stone-800 transition-colors flex items-center gap-1.5">
          <Send className="w-3.5 h-3.5" />
          {isEs ? 'Enviar al cliente' : 'Send to client'}
        </button>
      </div>
    </div>
  );
};

/**
 * VoiceAgentIntakeMockup - Shows the voice agent UI for client intake
 * Used by Personal Shoppers and Relocation agents to onboard clients
 */
export const VoiceAgentIntakeMockup = ({ className }: { className?: string }) => {
  const { locale } = useDictionary();
  const isEs = locale === 'es';
  
  return (
    <div className={cn("bg-stone-900 rounded-2xl p-6 max-w-sm mx-auto shadow-2xl", className)}>
      {/* Agency branding header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <span className="text-white/80 text-sm">Tu Agencia</span>
        </div>
        <div className="text-stone-500 text-xs">3:12</div>
      </div>
      
      {/* Voice visualization */}
      <div className="flex items-center justify-center mb-8">
        <div className="relative">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
            <div className="flex items-end gap-1 h-10">
              {[0.4, 0.7, 1, 0.8, 0.5, 0.9, 0.6].map((h, i) => (
                <div 
                  key={i} 
                  className="w-1.5 bg-white rounded-full animate-pulse" 
                  style={{ 
                    height: `${h * 40}px`,
                    animationDelay: `${i * 0.1}s`
                  }} 
                />
              ))}
            </div>
          </div>
          {/* Pulse rings */}
          <div className="absolute inset-0 rounded-full border-2 border-emerald-400/30 animate-ping" />
        </div>
      </div>
      
      {/* Leo's question */}
      <div className="bg-emerald-500/20 rounded-2xl p-4 mb-4">
        <div className="flex items-start gap-2">
          <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
            <span className="text-[10px] text-white font-bold">L</span>
          </div>
          <p className="text-white text-sm">
            {isEs 
              ? "¿Cuánto te apetece reformar?"
              : "How much renovation are you open to?"}
          </p>
        </div>
      </div>
      
      {/* Client response */}
      <div className="bg-white/10 rounded-2xl p-4 mb-6">
        <p className="text-white/90 text-sm">
          {isEs 
            ? "Encantado de hacer reforma integral si el precio compensa"
            : "Happy to do full renovation if the price is right"}
        </p>
      </div>
      
      {/* Typing indicators */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
          <span className="text-[10px] text-white font-bold">L</span>
        </div>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <div 
              key={i} 
              className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
      
      {/* Share link */}
      <div className="text-center">
        <div className="text-stone-500 text-[10px] mb-2">
          {isEs ? 'Comparte este enlace con tu cliente' : 'Share this link with your client'}
        </div>
        <div className="bg-white/5 rounded-lg px-3 py-2 text-emerald-400 text-xs font-mono">
          leo.casa/intake/abc123
        </div>
      </div>
    </div>
  );
};

export default ClientPortalMockup;























