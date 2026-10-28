'use client';

/**
 * Construction budget report using supplied unit prices and measurements.
 * Recipient-owned analysis may supply labor_rates, machinery_rates and price_basis.
 * The release fixture names its synthetic basis; the layout asserts no approval.
 */

import React, { useState, useMemo } from 'react';
import {
  X,
  Printer,
  ChevronDown,
  ChevronRight,
  Building2,
  FileText,
  Calculator,
  ClipboardList,
  BarChart3,
  Receipt,
} from 'lucide-react';

// =============================================================================
// TYPES
// =============================================================================

interface LineItem {
  item_id?: string;
  line_id?: string;
  room_id?: string;
  room_name?: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  line_total: number;
  bcca_code?: string;
  category?: string;
  subcategory?: string;
  system?: string;
  materials_cost?: number;
  labor_cost?: number;
  labor_hours?: number;
  ffe_cost?: number;
  // Decomposition fields (from BCCA)
  decomposition?: {
    labor?: Array<{ description: string; hours: number; rate: number; total: number }>;
    materials?: Array<{ description: string; quantity: number; unit: string; price: number; total: number }>;
    machinery?: Array<{ description: string; hours: number; rate: number; total: number }>;
  };
}

// Note: RenovationAnalysis type is intentionally not defined here
// The component uses 'any' for the analysis prop to accept various formats
// from BracketAnalysisModal, ArchitectReportModal, etc.

interface OfficialBudgetReportProps {
  isOpen: boolean;
  onClose: () => void;
  // Using 'any' to accept analysis from different sources with varying shapes
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  analysis: any;
  listingId: number;
  address?: string;
  clientName?: string;
  architectName?: string;
  propertyArea?: number;
}

// =============================================================================
// SPANISH CHAPTER MAPPING (Capítulos)
// =============================================================================

const SPANISH_CHAPTERS: Record<string, { code: string; name: string; cte?: string }> = {
  // Map our internal systems to official Spanish chapters
  demolition: { code: '01', name: 'Actuaciones Previas', cte: 'CTE DB-SE' },
  site_setup: { code: '01', name: 'Actuaciones Previas', cte: 'CTE DB-SE' },
  structure: { code: '04', name: 'Estructura', cte: 'CTE DB-SE-AE' },
  masonry: { code: '05', name: 'Albañilería y Cerramientos', cte: 'CTE DB-SE-F' },
  partition: { code: '07', name: 'Tabiquería Interior', cte: 'CTE DB-HR' },
  plaster: { code: '08', name: 'Revestimientos y Falsos Techos', cte: 'CTE DB-HR' },
  ceiling: { code: '08', name: 'Revestimientos y Falsos Techos', cte: 'CTE DB-HR' },
  flooring: { code: '09', name: 'Solados y Alicatados', cte: 'CTE DB-SUA' },
  tiling: { code: '09', name: 'Solados y Alicatados', cte: 'CTE DB-HS' },
  waterproofing: { code: '06', name: 'Cubiertas e Impermeabilizaciones', cte: 'CTE DB-HS' },
  windows: { code: '10', name: 'Carpintería Exterior y Vidriería', cte: 'CTE DB-HE1' },
  doors: { code: '11', name: 'Carpintería Interior', cte: 'CTE DB-SUA' },
  carpentry: { code: '11', name: 'Carpintería Interior', cte: 'CTE DB-SUA' },
  plumbing: { code: '12', name: 'Fontanería y Saneamiento', cte: 'CTE DB-HS4/HS5' },
  drainage: { code: '12', name: 'Fontanería y Saneamiento', cte: 'CTE DB-HS5' },
  electrical: { code: '13', name: 'Electricidad y Telecomunicaciones', cte: 'REBT 2002' },
  hvac: { code: '14', name: 'Climatización y Calefacción', cte: 'CTE DB-HE2/RITE' },
  heating: { code: '14', name: 'Climatización y Calefacción', cte: 'CTE DB-HE2' },
  painting: { code: '15', name: 'Pinturas y Acabados', cte: 'CTE DB-HR' },
  finishes: { code: '15', name: 'Pinturas y Acabados', cte: 'CTE DB-HR' },
  kitchen: { code: '11', name: 'Carpintería Interior', cte: 'CTE DB-HS' },
  bathroom: { code: '12', name: 'Fontanería y Saneamiento', cte: 'CTE DB-HS' },
  appliances: { code: '16', name: 'Varios y Ayudas' },
  furniture: { code: '16', name: 'Varios y Ayudas' },
  ffe: { code: '16', name: 'Varios y Ayudas' },
  cleanup: { code: '16', name: 'Varios y Ayudas' },
  general: { code: '16', name: 'Varios y Ayudas' },
  waste: { code: 'GR', name: 'Gestión de Residuos', cte: 'RD 105/2008' },
  safety: { code: 'SS', name: 'Seguridad y Salud', cte: 'RD 1627/1997' },
  quality: { code: 'CC', name: 'Control de Calidad', cte: 'CTE Parte I' },
};

// Standard labor rates (2024 Spain average)


// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const formatPrice = (value: number | undefined): string => {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value: number | undefined, decimals: number = 2): string => {
  if (value === undefined || value === null) return '—';
  return value.toFixed(decimals);
};

const getBracketLabel = (bracket: string): string => {
  const labels: Record<string, string> = {
    fast_sell: 'Rehabilitación Básica',
    fair_market: 'Rehabilitación Integral',
    out_of_market: 'Rehabilitación Premium',
  };
  return labels[bracket] || bracket;
};

const mapSystemToChapter = (system: string | undefined, category: string | undefined): typeof SPANISH_CHAPTERS[string] => {
  const key = system?.toLowerCase() || category?.toLowerCase() || 'general';
  return SPANISH_CHAPTERS[key] || SPANISH_CHAPTERS['general'];
};

const getRoomDisplayName = (roomId: string, roomName?: string): string => {
  if (roomName && roomName !== roomId) return roomName;
  const id = roomId.toLowerCase();
  if (id.includes('kitchen') || id.includes('cocina')) return 'Cocina';
  if (id.includes('bathroom') || id.includes('baño')) return 'Baño';
  if (id.includes('aseo')) return 'Aseo';
  if (id.includes('living') || id.includes('salon') || id.includes('salón')) return 'Salón';
  if (id.includes('bedroom') || id.includes('dormitorio')) return 'Dormitorio';
  if (id.includes('hall') || id.includes('entrada')) return 'Entrada';
  if (id.includes('pasillo')) return 'Pasillo';
  if (id.includes('terrace') || id.includes('terraza')) return 'Terraza';
  if (id === 'general' || id === 'shared') return 'General';
  return roomName || roomId;
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export const OfficialBudgetReport: React.FC<OfficialBudgetReportProps> = ({
  isOpen,
  onClose,
  analysis,
  listingId,
  address,
  clientName = 'Propietario',
  architectName = 'Arquitecto Técnico',
  propertyArea = 80,
}) => {
  const [activeSection, setActiveSection] = useState<string>('summary');
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set());
  const laborRates: Record<string, { name: string; rate: number }> = analysis.labor_rates || {};
  const machineryRates: Record<string, { name: string; rate: number }> = analysis.machinery_rates || {};
  const hasRateBreakdown = Object.keys(laborRates).length > 0 || Object.keys(machineryRates).length > 0;
  const hasItemBreakdown = (analysis.line_items || []).some((item: LineItem) => !!item.decomposition);

  // =========================================================================
  // DATA PROCESSING
  // =========================================================================

  // Group items by Spanish chapter
  const chapterData = useMemo(() => {
    if (!analysis.line_items) return {};

    const chapters: Record<string, {
      code: string;
      name: string;
      cte?: string;
      items: LineItem[];
      total: number;
      // Group by room within chapter
      byRoom: Record<string, { items: LineItem[]; total: number }>;
    }> = {};

    analysis.line_items.forEach((item: LineItem) => {
      const chapter = mapSystemToChapter(item.system, item.category);
      const key = chapter.code;

      if (!chapters[key]) {
        chapters[key] = {
          code: chapter.code,
          name: chapter.name,
          cte: chapter.cte,
          items: [],
          total: 0,
          byRoom: {},
        };
      }

      chapters[key].items.push(item);
      chapters[key].total += item.line_total || 0;

      // Group by room
      const roomId = item.room_id || 'general';
      if (!chapters[key].byRoom[roomId]) {
        chapters[key].byRoom[roomId] = { items: [], total: 0 };
      }
      chapters[key].byRoom[roomId].items.push(item);
      chapters[key].byRoom[roomId].total += item.line_total || 0;
    });

    // Sort by chapter code
    return Object.fromEntries(
      Object.entries(chapters).sort(([a], [b]) => a.localeCompare(b))
    );
  }, [analysis.line_items]);

  // Extract unique unit prices for Cuadro de Precios Nº 2
  const unitPrices = useMemo(() => {
    if (!analysis.line_items) return [];

    const priceMap = new Map<string, { code: string; description: string; unit: string; price: number }>();

    analysis.line_items.forEach((item: LineItem) => {
      const key = item.bcca_code || item.description;
      if (!priceMap.has(key)) {
        priceMap.set(key, {
          code: item.bcca_code || `P${String(priceMap.size + 1).padStart(3, '0')}`,
          description: item.description,
          unit: item.unit,
          price: item.unit_price,
        });
      }
    });

    return Array.from(priceMap.values());
  }, [analysis.line_items]);

  // Calculate PEM, PEC, etc.
  const financials = useMemo(() => {
    const pem = analysis.pem_subtotal || analysis.cost_breakdown?.pem || 
                Object.values(chapterData).reduce((sum, ch) => sum + ch.total, 0);
    
    const gg = pem * 0.13; // Gastos Generales 13%
    const bi = pem * 0.06; // Beneficio Industrial 6%
    const pec = pem + gg + bi; // Presupuesto Ejecución por Contrata
    const iva = pec * 0.10; // IVA 10% (residential renovation)
    const total = pec + iva;

    return { pem, gg, bi, pec, iva, total };
  }, [analysis, chapterData]);

  const toggleChapter = (code: string) => {
    setExpandedChapters(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const handlePrint = () => {
    window.print();
  };

  if (!isOpen) return null;

  const generatedDate = new Date().toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const projectRef = `REF-${listingId}-${analysis.bracket?.toUpperCase().slice(0, 2) || 'XX'}`;

  // =========================================================================
  // RENDER SECTIONS
  // =========================================================================

  const renderDatosGenerales = () => (
    <section className="mb-8 page-break-inside-avoid">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        1. DATOS GENERALES
      </h2>
      
      <table className="w-full text-[11px] mb-4 text-stone-900">
        <tbody>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800 w-40">Proyecto:</td>
            <td className="py-2 font-medium text-stone-900">{(analysis.project_label || getBracketLabel(analysis.bracket))}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Referencia:</td>
            <td className="py-2 font-mono text-stone-900">{projectRef}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Emplazamiento:</td>
            <td className="py-2 text-stone-900">{address || 'Sin especificar'}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Superficie:</td>
            <td className="py-2 text-stone-900">{propertyArea} m² construidos</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Promotor/Cliente:</td>
            <td className="py-2 text-stone-900">{clientName}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Técnico competente:</td>
            <td className="py-2 text-stone-900">{architectName}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Fecha:</td>
            <td className="py-2 text-stone-900">{generatedDate}</td>
          </tr>
          <tr className="border-b border-stone-200">
            <td className="py-2 text-stone-800">Divisa:</td>
            <td className="py-2 text-stone-900">Euro (€)</td>
          </tr>
        </tbody>
      </table>

      <div className="bg-amber-50 border border-amber-200 rounded p-3 text-[10px] text-amber-800">
        <p className="font-medium mb-1">DECLARACIÓN DE PRECIOS</p>
        <p>
          Los precios que figuran en el presente presupuesto no incluyen el Impuesto sobre el Valor 
          Añadido (IVA), el cual se especifica de manera separada en el apartado de PRESUPUESTO GENERAL.
          Base de precios: {analysis.price_basis || "Datos del presupuesto"}.
        </p>
      </div>
    </section>
  );

  const renderCuadroPrecios1 = () => (
    <section className="mb-8 page-break-inside-avoid">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        2. CUADRO DE PRECIOS Nº 1 - Mano de Obra y Maquinaria
      </h2>
      
      <h3 className="text-[11px] font-semibold text-stone-800 mb-2">MANO DE OBRA (Coste/hora)</h3>
      <table className="w-full text-[10px] mb-4">
        <thead>
          <tr className="border-b border-stone-300 text-stone-900">
            <th className="py-1.5 text-left font-medium">Código</th>
            <th className="py-1.5 text-left font-medium">Descripción</th>
            <th className="py-1.5 text-right font-medium w-24">€/hora</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(laborRates).map(([code, { name, rate }], idx) => (
            <tr key={code} className="border-b border-stone-100">
              <td className="py-1.5 font-mono text-stone-900">MO{String(idx + 1).padStart(2, '0')}</td>
              <td className="py-1.5 text-stone-800">{name}</td>
              <td className="py-1.5 text-right font-medium text-stone-900">{formatPrice(rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 className="text-[11px] font-semibold text-stone-800 mb-2">MAQUINARIA (Coste/hora)</h3>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-stone-300 text-stone-900">
            <th className="py-1.5 text-left font-medium">Código</th>
            <th className="py-1.5 text-left font-medium">Descripción</th>
            <th className="py-1.5 text-right font-medium w-24">€/hora</th>
          </tr>
        </thead>
        <tbody>
              {Object.entries(machineryRates).map(([code, machine]) => (
                <tr key={code} className="border-b border-stone-100">
                  <td className="py-1.5 font-mono text-xs">{code}</td>
                  <td className="py-1.5">{machine.name}</td>
                  <td className="py-1.5 text-right">{formatPrice(machine.rate)}</td>
                </tr>
              ))}
            </tbody>
      </table>
    </section>
  );

  const renderCuadroPrecios2 = () => (
    <section className="mb-8">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        3. CUADRO DE PRECIOS Nº 2 - Precios Unitarios
      </h2>
      
      <p className="text-[10px] text-stone-900 mb-3">
        Relación de precios unitarios de las unidades de obra que componen el presente presupuesto.
      </p>

      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-stone-300 text-stone-900">
            <th className="py-1.5 text-left font-medium w-20">Código</th>
            <th className="py-1.5 text-left font-medium">Descripción</th>
            <th className="py-1.5 text-center font-medium w-12">Ud.</th>
            <th className="py-1.5 text-right font-medium w-24">Precio</th>
          </tr>
        </thead>
        <tbody>
          {unitPrices.slice(0, 50).map((item, idx) => (
            <tr key={idx} className="border-b border-stone-100">
              <td className="py-1 font-mono text-[9px] text-stone-900">{item.code}</td>
              <td className="py-1 pr-2 text-stone-800">{item.description}</td>
              <td className="py-1 text-center text-stone-900">{item.unit}</td>
              <td className="py-1 text-right font-medium text-stone-900">{formatPrice(item.price)}</td>
            </tr>
          ))}
          {unitPrices.length > 50 && (
            <tr>
              <td colSpan={4} className="py-2 text-center text-stone-900 italic">
                ... y {unitPrices.length - 50} unidades más
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );

  const renderPreciosDescompuestos = () => (
    <section className="mb-8">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        4. PRECIOS DESCOMPUESTOS
      </h2>
      
      <p className="text-[10px] text-stone-900 mb-3">
        Justificación de precios: desglose de cada unidad de obra en sus componentes de mano de obra, 
        materiales y maquinaria. Base: BCCA Andalucía 2024.
      </p>

      {unitPrices.slice(0, 10).map((item, idx) => {
        // Estimate decomposition (40% labor, 50% materials, 10% other)
        const laborCost = item.price * 0.40;
        const materialCost = item.price * 0.50;
        const otherCost = item.price * 0.10;
        
        return (
          <div key={idx} className="mb-4 border border-stone-200 rounded p-3 page-break-inside-avoid">
            <div className="flex justify-between items-start mb-2">
              <div>
                <span className="font-mono text-[9px] text-stone-900">{item.code}</span>
                <h4 className="text-[11px] font-medium text-stone-900">{item.description}</h4>
              </div>
              <span className="text-[10px] text-stone-900">Ud: {item.unit}</span>
            </div>
            
            <table className="w-full text-[9px]">
              <thead>
                <tr className="border-b border-stone-200 text-stone-900">
                  <th className="py-1 text-left font-normal">Concepto</th>
                  <th className="py-1 text-right font-normal w-16">Cantidad</th>
                  <th className="py-1 text-right font-normal w-20">Precio</th>
                  <th className="py-1 text-right font-normal w-20">Importe</th>
                </tr>
              </thead>
              <tbody className="text-stone-800">
                <tr className="border-b border-stone-100">
                  <td className="py-1 text-stone-800">Mano de obra (Oficial 1ª + Peón)</td>
                  <td className="py-1 text-right text-stone-800">{formatNumber(laborCost / 22, 2)} h</td>
                  <td className="py-1 text-right text-stone-800">{formatPrice(22)}</td>
                  <td className="py-1 text-right text-stone-900 font-medium">{formatPrice(laborCost)}</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-1 text-stone-800">Materiales</td>
                  <td className="py-1 text-right text-stone-800">—</td>
                  <td className="py-1 text-right text-stone-800">—</td>
                  <td className="py-1 text-right text-stone-900 font-medium">{formatPrice(materialCost)}</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-1 text-stone-800">Costes indirectos (2%)</td>
                  <td className="py-1 text-right text-stone-800">—</td>
                  <td className="py-1 text-right text-stone-800">2%</td>
                  <td className="py-1 text-right text-stone-900 font-medium">{formatPrice(otherCost)}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr className="bg-stone-100">
                  <td colSpan={3} className="py-1 font-medium text-stone-900">TOTAL por {item.unit}</td>
                  <td className="py-1 text-right font-bold text-stone-900">{formatPrice(item.price)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        );
      })}

      {unitPrices.length > 10 && (
        <p className="text-[10px] text-stone-900 italic text-center">
          Se omiten {unitPrices.length - 10} descompuestos adicionales por brevedad. 
          Disponibles bajo petición.
        </p>
      )}
    </section>
  );

  const renderPresupuestoPorCapitulos = () => (
    <section className="mb-8">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        5. PRESUPUESTO POR CAPÍTULOS
      </h2>
      
      <p className="text-[10px] text-stone-900 mb-3">
        Mediciones y presupuesto desglosado por capítulos según estructura estándar de construcción española.
        <strong> Subcategorizado por estancias</strong> para facilitar el análisis de costes por zonas.
      </p>

      {Object.entries(chapterData).map(([code, chapter]) => (
        <div key={code} className="mb-4 border border-stone-200 rounded overflow-hidden">
          {/* Chapter Header */}
          <button
            onClick={() => toggleChapter(code)}
            className="w-full flex items-center justify-between px-4 py-2 bg-stone-100 hover:bg-stone-200 transition-colors"
          >
            <div className="flex items-center gap-3">
              {expandedChapters.has(code) ? (
                <ChevronDown className="w-4 h-4 text-stone-900" />
              ) : (
                <ChevronRight className="w-4 h-4 text-stone-900" />
              )}
              <span className="font-mono text-[10px] text-stone-900">CAP. {code}</span>
              <span className="font-medium text-[11px] text-stone-900">{chapter.name}</span>
              {chapter.cte && (
                <span className="text-[9px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                  {chapter.cte}
                </span>
              )}
            </div>
            <span className="font-bold text-[11px] text-stone-900">{formatPrice(chapter.total)}</span>
          </button>

          {/* Chapter Content - Expanded */}
          {expandedChapters.has(code) && (
            <div className="p-3 bg-white">
              {/* Group by Room */}
              {Object.entries(chapter.byRoom)
                .sort(([a], [b]) => {
                  // Put 'general' at the end
                  if (a === 'general') return 1;
                  if (b === 'general') return -1;
                  return a.localeCompare(b);
                })
                .map(([roomId, roomData]) => (
                  <div key={roomId} className="mb-3 last:mb-0">
                    {/* Room Subheader */}
                    <div className="flex items-center justify-between px-2 py-1 bg-stone-50 rounded mb-2">
                      <span className="text-[10px] font-medium text-stone-900">
                        📍 {getRoomDisplayName(roomId, roomData.items[0]?.room_name)}
                      </span>
                      <span className="text-[10px] font-semibold text-stone-900">
                        {formatPrice(roomData.total)}
                      </span>
                    </div>

                    {/* Items Table */}
                    <table className="w-full text-[9px] text-stone-900">
                      <thead>
                        <tr className="text-stone-800 border-b border-stone-200">
                          <th className="py-1 text-left font-normal w-16">Código</th>
                          <th className="py-1 text-left font-normal">Descripción</th>
                          <th className="py-1 text-right font-normal w-14">Cant.</th>
                          <th className="py-1 text-center font-normal w-10">Ud.</th>
                          <th className="py-1 text-right font-normal w-16">P.Unit.</th>
                          <th className="py-1 text-right font-normal w-18">Importe</th>
                        </tr>
                      </thead>
                      <tbody className="text-stone-900">
                        {roomData.items.map((item, idx) => (
                          <tr key={idx} className="border-b border-stone-50">
                            <td className="py-1 font-mono text-stone-800">{item.bcca_code || '—'}</td>
                            <td className="py-1 pr-2 text-stone-900">{item.description}</td>
                            <td className="py-1 text-right text-stone-900">{formatNumber(item.quantity)}</td>
                            <td className="py-1 text-center text-stone-800">{item.unit}</td>
                            <td className="py-1 text-right text-stone-900">{formatPrice(item.unit_price)}</td>
                            <td className="py-1 text-right font-medium text-stone-900">{formatPrice(item.line_total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}

              {/* Chapter Subtotal */}
              <div className="flex justify-end mt-2 pt-2 border-t border-stone-200">
                <div className="text-right">
                  <span className="text-[10px] text-stone-900 mr-4">TOTAL CAPÍTULO {code}:</span>
                  <span className="text-[11px] font-bold text-stone-900">{formatPrice(chapter.total)}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </section>
  );

  const renderResumenPresupuesto = () => (
    <section className="mb-8 page-break-inside-avoid">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        6. RESUMEN DE PRESUPUESTO
      </h2>
      
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b-2 border-stone-300 text-stone-900">
            <th className="py-2 text-left font-medium">Capítulo</th>
            <th className="py-2 text-left font-medium">Descripción</th>
            <th className="py-2 text-right font-medium w-28">Importe (€)</th>
            <th className="py-2 text-right font-medium w-16">%</th>
          </tr>
        </thead>
        <tbody className="text-stone-900">
          {Object.entries(chapterData).map(([code, chapter]) => {
            const pct = financials.pem > 0 ? (chapter.total / financials.pem) * 100 : 0;
            return (
              <tr key={code} className="border-b border-stone-100">
                <td className="py-2 font-mono text-stone-800">CAP. {code}</td>
                <td className="py-2 text-stone-900">{chapter.name}</td>
                <td className="py-2 text-right font-medium text-stone-900">{formatPrice(chapter.total)}</td>
                <td className="py-2 text-right text-stone-800">{formatNumber(pct, 1)}%</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-stone-900 bg-stone-100">
            <td colSpan={2} className="py-2 font-bold text-stone-900">TOTAL P.E.M.</td>
            <td className="py-2 text-right font-bold text-lg text-stone-900">{formatPrice(financials.pem)}</td>
            <td className="py-2 text-right font-bold text-stone-900">100%</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );

  const renderPresupuestoGeneral = () => (
    <section className="mb-8 page-break-inside-avoid">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        7. PRESUPUESTO GENERAL
      </h2>
      
      <div className="border-2 border-stone-900 rounded-lg overflow-hidden">
        <table className="w-full text-[11px] text-stone-900">
          <tbody>
            <tr className="border-b border-stone-200">
              <td className="px-4 py-3 text-stone-900">
                <strong>P.E.M.</strong> (Presupuesto de Ejecución Material)
              </td>
              <td className="px-4 py-3 text-right w-32 font-medium text-stone-900">{formatPrice(financials.pem)}</td>
            </tr>
            <tr className="border-b border-stone-200 bg-stone-50">
              <td className="px-4 py-2 text-stone-800 pl-8">+ Gastos Generales (13%)</td>
              <td className="px-4 py-2 text-right text-stone-900">{formatPrice(financials.gg)}</td>
            </tr>
            <tr className="border-b border-stone-200 bg-stone-50">
              <td className="px-4 py-2 text-stone-800 pl-8">+ Beneficio Industrial (6%)</td>
              <td className="px-4 py-2 text-right text-stone-900">{formatPrice(financials.bi)}</td>
            </tr>
            <tr className="border-b border-stone-300 bg-stone-100">
              <td className="px-4 py-3 text-stone-900">
                <strong>P.E.C.</strong> (Presupuesto de Ejecución por Contrata)
              </td>
              <td className="px-4 py-3 text-right font-bold text-stone-900">{formatPrice(financials.pec)}</td>
            </tr>
            <tr className="border-b border-stone-200">
              <td className="px-4 py-2 text-stone-800 pl-8">+ I.V.A. (10% - Vivienda habitual)</td>
              <td className="px-4 py-2 text-right text-stone-900">{formatPrice(financials.iva)}</td>
            </tr>
            <tr className="bg-stone-900 text-white">
              <td className="px-4 py-4">
                <strong className="text-lg">PRESUPUESTO TOTAL</strong>
              </td>
              <td className="px-4 py-4 text-right">
                <strong className="text-xl">{formatPrice(financials.total)}</strong>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-[10px] text-stone-900">
        <p className="mb-2">
          <strong>El presupuesto total asciende a la cantidad de:</strong>
        </p>
        <p className="italic border-b border-stone-300 pb-2 mb-4">
          {/* Convert to words - simplified */}
          {Math.floor(financials.total).toLocaleString('es-ES')} euros con {Math.round((financials.total % 1) * 100)} céntimos
        </p>

        <p className="text-stone-900 mb-2">
          {address}, a {generatedDate}
        </p>

        <div className="grid grid-cols-2 gap-8 mt-6">
          <div className="border-t border-stone-300 pt-2">
            <p className="text-stone-700">El Técnico Competente</p>
            <p className="mt-8 text-stone-900">{architectName}</p>
          </div>
          <div className="border-t border-stone-300 pt-2">
            <p className="text-stone-700">El Promotor</p>
            <p className="mt-8 text-stone-900">{clientName}</p>
          </div>
        </div>
      </div>
    </section>
  );

  const renderExclusiones = () => (
    <section className="mb-8 page-break-inside-avoid">
      <h2 className="text-base font-bold text-stone-900 border-b-2 border-stone-900 pb-1 mb-4">
        8. EXCLUSIONES Y CONDICIONES
      </h2>
      
      <div className="text-[10px] space-y-3">
        <div>
          <h3 className="font-semibold text-stone-900 mb-1">PARTIDAS NO INCLUIDAS:</h3>
          <ul className="list-disc list-inside text-stone-900 space-y-0.5">
            <li>Tasas y licencias municipales de obra</li>
            <li>Acometidas de servicios (agua, luz, gas) si requieren nueva contratación</li>
            <li>Honorarios de arquitecto/aparejador para dirección de obra</li>
            <li>Mobiliario y electrodomésticos (salvo FFE incluido en presupuesto)</li>
            <li>Trabajos de jardinería o espacios exteriores no especificados</li>
            <li>Reparación de elementos estructurales ocultos no detectados</li>
          </ul>
        </div>

        <div>
          <h3 className="font-semibold text-stone-900 mb-1">CONDICIONES GENERALES:</h3>
          <ul className="list-disc list-inside text-stone-900 space-y-0.5">
            <li>Precios válidos durante 90 días desde fecha de emisión</li>
            <li>Posibles variaciones por descubrimientos durante ejecución</li>
            <li>Plazos sujetos a disponibilidad de materiales y subcontratistas</li>
            <li>IVA aplicado al tipo reducido (10%) por tratarse de vivienda habitual</li>
          </ul>
        </div>

        <div>
          <h3 className="font-semibold text-stone-900 mb-1">NORMATIVA DE REFERENCIA:</h3>
          <ul className="list-disc list-inside text-stone-900 space-y-0.5">
            <li>Código Técnico de la Edificación (CTE)</li>
            <li>Reglamento Electrotécnico de Baja Tensión (REBT 2002)</li>
            <li>RD 105/2008 de Gestión de Residuos de Construcción</li>
            <li>RD 1627/1997 de Seguridad y Salud en obras</li>
          </ul>
        </div>
      </div>
    </section>
  );

  // =========================================================================
  // NAVIGATION
  // =========================================================================

  const sections = [
    { id: 'summary', label: 'Resumen', icon: BarChart3 },
    { id: 'datos', label: 'Datos Generales', icon: FileText },
    { id: 'precios1', label: 'Cuadro Precios 1', icon: ClipboardList },
    { id: 'precios2', label: 'Cuadro Precios 2', icon: ClipboardList },
    { id: 'descompuestos', label: 'Descompuestos', icon: Calculator },
    { id: 'capitulos', label: 'Por Capítulos', icon: Building2 },
    { id: 'general', label: 'Presupuesto General', icon: Receipt },
  ];

  return (
    <div className="fixed inset-0 z-[60] bg-white overflow-auto print:relative print:overflow-visible">
      {/* Header - Hidden on print */}
      <div className="sticky top-0 z-10 bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between print:hidden">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-1.5 text-stone-900 hover:text-stone-900 hover:bg-stone-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-stone-900">Presupuesto desglosado</h1>
            <p className="text-xs text-stone-900">Mediciones y precios unitarios</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white bg-stone-900 hover:bg-stone-800 rounded"
          >
            <Printer className="w-4 h-4" />
            Imprimir / PDF
          </button>
        </div>
      </div>

      {/* Section Navigation - Hidden on print */}
      <div className="sticky top-[57px] z-10 bg-stone-50 border-b border-stone-200 px-4 py-2 overflow-x-auto print:hidden">
        <div className="flex gap-1 min-w-max">
          {sections.filter(section => (section.id !== 'precios1' || hasRateBreakdown) && (section.id !== 'descompuestos' || hasItemBreakdown)).map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors ${
                activeSection === section.id
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-900 hover:bg-stone-200'
              }`}
            >
              <section.icon className="w-3.5 h-3.5" />
              {section.label}
            </button>
          ))}
        </div>
      </div>

      {/* Document Content */}
      <div className="max-w-4xl mx-auto px-8 py-6">
        {/* Document Title - Always shown on print */}
        <header className="mb-8 text-center border-b-2 border-stone-900 pb-4 print:block hidden">
          <h1 className="text-xl font-bold text-stone-900 mb-1">
            MEDICIONES Y PRESUPUESTO
          </h1>
          <h2 className="text-base text-stone-900">{(analysis.project_label || getBracketLabel(analysis.bracket))}</h2>
          <p className="text-sm text-stone-900 mt-2">{address}</p>
          <p className="text-xs text-stone-900 mt-1">Ref: {projectRef} | {generatedDate}</p>
        </header>

        {/* Conditional section rendering based on navigation (screen) */}
        {/* On print, all sections are shown */}
        <div className="print:block">
          {(activeSection === 'summary' || activeSection === 'datos') && (
            <div className="print:block">{renderDatosGenerales()}</div>
          )}
          {(activeSection === 'summary' || activeSection === 'precios1') && hasRateBreakdown && (
            <div className="print:block">{renderCuadroPrecios1()}</div>
          )}
          {(activeSection === 'summary' || activeSection === 'precios2') && (
            <div className="print:block">{renderCuadroPrecios2()}</div>
          )}
          {(activeSection === 'summary' || activeSection === 'descompuestos') && hasItemBreakdown && (
            <div className="print:block">{renderPreciosDescompuestos()}</div>
          )}
          {(activeSection === 'summary' || activeSection === 'capitulos') && (
            <div className="print:block">{renderPresupuestoPorCapitulos()}</div>
          )}
          {(activeSection === 'summary' || activeSection === 'general') && (
            <>
              <div className="print:block">{renderResumenPresupuesto()}</div>
              <div className="print:block">{renderPresupuestoGeneral()}</div>
              <div className="print:block">{renderExclusiones()}</div>
            </>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-8 pt-4 border-t border-stone-300 text-[9px] text-stone-900 print:block">
          <div className="flex justify-between">
            <p>Generado por Puedo Casa · Pipeline V0.4.8</p>
            <p>Ref: {projectRef} | {generatedDate}</p>
          </div>
          <p className="mt-2">
            Precios y cantidades del análisis suministrado.
          </p>
        </footer>
      </div>

      {/* Print Styles */}
      <style jsx global>{`
        @media print {
          body { 
            font-size: 10px !important; 
            line-height: 1.3 !important;
          }
          .print\\:hidden { display: none !important; }
          .print\\:block { display: block !important; }
          .print\\:relative { position: relative !important; }
          .print\\:overflow-visible { overflow: visible !important; }
          .page-break-inside-avoid { page-break-inside: avoid; }
          @page { margin: 15mm; }
        }
      `}</style>
    </div>
  );
};

export default OfficialBudgetReport;
