/**
 * Renovation Pipeline V2 - TypeScript Types
 * ==========================================
 * 
 * These types MUST match the Python schemas in:
 * backend/pipeline/schemas/renovation.py
 * 
 * Used by:
 * - Card 1: ConditionCard.tsx
 * - Card 2: ScopesCard.tsx
 * - Card 3: PricingCard.tsx
 */

// =============================================================================
// ENUMS
// =============================================================================

export type TriggerType = 'implied_by_age' | 'visual_match';

export type PackageType = 'ESSENTIAL' | 'MODERN';

export type DefectCategory = 
  | 'SAFETY' 
  | 'LEGAL' 
  | 'STRUCTURAL' 
  | 'HYGIENE'    // → ESSENTIAL
  | 'ENERGY' 
  | 'COMFORT' 
  | 'ACOUSTIC';  // → MODERN

export type SystemType = 
  | 'electrical' 
  | 'plumbing' 
  | 'envelope' 
  | 'structure' 
  | 'finishes' 
  | 'hvac' 
  | 'ventilation';

// =============================================================================
// PHASE 1: CONDITION ASSESSMENT
// =============================================================================

export interface DetectedCondition {
  rule_id: string;
  trigger_type: TriggerType;
  system: SystemType;
  observation: string;
  confidence: 'High' | 'Medium' | 'Low';
  risk_label: string;
  risk_description: string;
  category: DefectCategory;  // Package is determined in Phase 2 based on category
  visual_evidence?: string;
}

export interface RoomAssessment {
  room_id: string;
  room_type: string;
  room_name: string;
  photo_urls: string[];
  detected_conditions: DetectedCondition[];
}

export interface ConditionAssessmentResult {
  listing_id: number;
  year_built: number;
  room_assessments: RoomAssessment[];
  created_at?: string;
}

// Helper type for UI
export interface ConditionCardData {
  hasData: boolean;
  isLoading: boolean;
  error?: string;
  data?: ConditionAssessmentResult;
}

// =============================================================================
// PHASE 2: PACKAGE SCOPES
// =============================================================================

export interface ScopeTask {
  task_id: string;
  title: string;
  bcca_keyword: string;
  defect_source: string;
  trigger_type: TriggerType;
  risk_label: string;
  regulation: string;
  category: DefectCategory;
  room: string;
  inherited_from?: string;
  spec_upgrade?: string;
}

export interface RoomScope {
  room_id: string;
  room_name: string;
  tasks: ScopeTask[];
}

export interface PackageScope {
  package_type: PackageType;
  name: string;
  goal: string;
  standard: string;
  room_scopes: RoomScope[];
}

export interface PackageScopesResult {
  listing_id: number;
  essential: PackageScope;
  modern: PackageScope;
  created_at?: string;
}

// Helper type for UI
export interface ScopesCardData {
  hasData: boolean;
  isLoading: boolean;
  error?: string;
  data?: PackageScopesResult;
  conditionAssessmentComplete: boolean;
}

// =============================================================================
// PHASE 3: PRICING
// =============================================================================

export interface BoQLine {
  bcca_code: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price: number;
  total: number;
  task_id: string;
  room: string;
}

export interface TradeBreakdown {
  trade: string;
  trade_code: string;
  lines: BoQLine[];
  subtotal: number;
}

export interface RoomPricing {
  room_id: string;
  room_name: string;
  lines: BoQLine[];
  subtotal: number;
}

export interface PackagePricing {
  package_type: PackageType;
  total_pem: number;
  total_pec: number;
  trade_breakdown: TradeBreakdown[];
  room_breakdown: RoomPricing[];
  boq_lines: BoQLine[];
}

export interface PackagePricingResult {
  listing_id: number;
  essential: PackagePricing;
  modern: PackagePricing;
  created_at?: string;
}

// Helper type for UI
export interface PricingCardData {
  hasData: boolean;
  isLoading: boolean;
  error?: string;
  data?: PackagePricingResult;
  packageScopesComplete: boolean;
}

// =============================================================================
// RULES ENGINE (for reference)
// =============================================================================

export interface ConditionAssessmentRule {
  prompt_instruction: string;
  risk_label: string;
  risk_description: string;
}

export interface RemedialAction {
  task_id: string;
  bcca_keyword: string;
  package: PackageType;
  category: DefectCategory;
}

export interface Rule {
  id: string;
  system: SystemType;
  room_types: string[];
  year_trigger: number;
  visual_triggers: string[];
  condition_assessment: ConditionAssessmentRule;
  remedial_action: RemedialAction;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

export interface ConditionAssessmentResponse {
  success: boolean;
  hasData: boolean;
  data?: ConditionAssessmentResult;
  error?: string;
}

export interface PackageScopesResponse {
  success: boolean;
  hasData: boolean;
  data?: PackageScopesResult;
  error?: string;
  conditionAssessmentComplete: boolean;
}

export interface PackagePricingResponse {
  success: boolean;
  hasData: boolean;
  data?: PackagePricingResult;
  error?: string;
  packageScopesComplete: boolean;
}

