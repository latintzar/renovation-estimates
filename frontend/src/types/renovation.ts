/**
 * Renovation Report Types
 * =======================
 * 
 * Types for the Pre-Inspection Report feature.
 * Two packages: Essential (Safety) and Modern (Comfort).
 */

export interface RenovationItem {
  rule_id: string;
  item_name: string;
  bcca_code?: string;
  bcca_description?: string;
  unit?: string;
  unit_price: number;
  quantity: number;
  total: number;
  room?: string;
  category: 'ESSENTIAL' | 'MODERN';
  regulation?: string;
  buyer_warning: string;
}

export interface RenovationPackage {
  total: number;
  description: string;
  complianceNote?: string;
  items: RenovationItem[];
}

export interface DetectedCondition {
  condition_id: string;
  room: string;
  description: string;
  visual_evidence: string;
  confidence: number;
}

export interface RoomDetail {
  room: string;
  photo_count: number;
  conditions_detected: {
    description: string;
    evidence: string;
    confidence: number;
  }[];
  essential_items: {
    item: string;
    cost: number;
    reason: string;
  }[];
  modern_items: {
    item: string;
    cost: number;
    reason: string;
  }[];
}

export interface RenovationReport {
  success: boolean;
  hasReport: boolean;
  message?: string;
  summary?: string;
  yearEstimated?: number;
  yearConfidence?: number;
  packages?: {
    essential: RenovationPackage;
    modern: RenovationPackage;
  };
  roomDetails?: RoomDetail[];
  detectedConditions?: DetectedCondition[];
  generatedAt?: string;
}

// UI configuration for packages
export interface PackageConfig {
  key: 'essential' | 'modern';
  icon: string; // Lucide icon name
  title: string;
  subtitle: string;
  borderColor: string;
  bgColor: string;
  iconBg: string;
  iconColor: string;
}

export const PACKAGE_CONFIG: Record<'essential' | 'modern', PackageConfig> = {
  essential: {
    key: 'essential',
    icon: 'Shield',
    title: 'Cumplimiento y Seguridad',
    subtitle: 'Deuda técnica obligatoria',
    borderColor: 'border-orange-200',
    bgColor: 'bg-orange-50',
    iconBg: 'bg-orange-100',
    iconColor: 'text-orange-600',
  },
  modern: {
    key: 'modern',
    icon: 'Zap',
    title: 'Estándares Modernos',
    subtitle: 'Eficiencia energética y confort',
    borderColor: 'border-emerald-200',
    bgColor: 'bg-emerald-50',
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
  },
};

