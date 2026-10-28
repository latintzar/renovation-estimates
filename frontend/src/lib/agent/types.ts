/**
 * Agent Portal Types
 * ==================
 * 
 * Types for the agent property onboarding flow.
 * The chat-based interface guides agents through collecting
 * all property data needed for renovation analysis.
 */

// ── Onboarding Phases ──────────────────────────────────────

export type OnboardingPhase =
  | 'welcome'
  | 'listing_check'
  | 'basic_info'
  | 'photos'
  | 'photo_review'
  | 'floor_plan'
  | 'room_linking'
  | 'inventory_scan'
  | 'documents'
  | 'room_documents'
  | 'known_issues'
  | 'contacts'
  | 'review'
  | 'complete';

export const PHASE_LABELS: Record<OnboardingPhase, string> = {
  welcome: 'Welcome',
  listing_check: 'Listing',
  basic_info: 'Property Details',
  photos: 'Photos',
  photo_review: 'Photo Review',
  floor_plan: 'Floor Plan',
  room_linking: 'Room Linking',
  inventory_scan: 'Inventory Scan',
  documents: 'Documents',
  room_documents: 'Room Documents',
  known_issues: 'Known Issues',
  contacts: 'Trusted Contacts',
  review: 'Review',
  complete: 'Complete',
};

export const PHASE_ORDER: OnboardingPhase[] = [
  'welcome', 'listing_check', 'basic_info', 'photos', 'photo_review',
  'floor_plan', 'room_linking', 'inventory_scan', 'documents',
  'room_documents', 'known_issues', 'contacts', 'review', 'complete',
];

// ── Agent & Property ───────────────────────────────────────

export interface AgentProfile {
  id: string;
  name: string;
  email: string;
  agency: string;
  avatarUrl?: string;
  phone?: string;
}

export interface AgentProperty {
  id: string;
  address: string;
  city: string;
  status: 'draft' | 'in_progress' | 'ready' | 'analyzing';
  phase: OnboardingPhase;
  completionPct: number;
  imageUrl?: string;
  bedrooms?: number;
  bathrooms?: number;
  sqm?: number;
  price?: number;
  createdAt: Date;
  updatedAt: Date;
}

// ── Chat Messages ──────────────────────────────────────────

export type ChatMessageRole = 'leo' | 'agent' | 'system';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  timestamp: Date;
  toolTrail?: ToolTrailItem[];
  thought?: ThoughtData;
  citations?: CitationItem[];
  confirmedBadge?: ConfirmedBadge;
  suggestedResponses?: SuggestedResponseCardData[];
  component?: ChatComponent;
  suggestedActions?: SuggestedAction[];
  files?: UploadedFile[];
  isTyping?: boolean;
  animate?: boolean;
}

export interface ThoughtData {
  durationSec: number;
  summary: string;
}

export interface CitationItem {
  id: string;
  title: string;
  url: string;
}

export interface ConfirmedBadge {
  detail?: string;
}

export interface SuggestedResponseCardData {
  text: string;
  title?: string;
  subtitle?: string;
}

// ── Tool Trail ─────────────────────────────────────────────

export interface ToolTrailItem {
  id: string;
  icon: string;
  label?: string;
  active?: string;
  done?: string;
  status: 'pending' | 'active' | 'done';
  detail?: string;
  durationMs: number;
  linkedChatId?: string;
  linkedMessageId?: string;
  children?: ToolTrailItem[];
}

// ── Interactive Components ─────────────────────────────────

export type ChatComponentType =
  | 'property_summary'
  | 'photo_clusters'
  | 'floor_plan'
  | 'room_selector'
  | 'document_cards'
  | 'contact_card'
  | 'inventory_list'
  | 'completion_summary';

export interface ChatComponent {
  type: ChatComponentType;
  data: Record<string, unknown>;
}

// ── Suggested Actions ──────────────────────────────────────

export interface SuggestedAction {
  id: string;
  label: string;
  icon?: string;
  style: 'primary' | 'secondary' | 'outline';
}

// ── File Upload ────────────────────────────────────────────

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  thumbnailUrl?: string;
  status: 'uploading' | 'processing' | 'done' | 'error';
  progress: number;
}

// ── Photo Clusters ─────────────────────────────────────────

export interface PhotoCluster {
  id: string;
  roomName: string;
  roomType: string;
  photos: string[];
  status: 'good' | 'needs_more' | 'insufficient';
  linkedFloorPlanRoom?: string;
  sqm?: number;
}

// ── Floor Plan ─────────────────────────────────────────────

export interface FloorPlanRoom {
  id: string;
  label: string;
  sqm: number;
  color: string;
  bounds: { x: number; y: number; width: number; height: number };
  linkedClusterId?: string;
}

// ── Documents ──────────────────────────────────────────────

export interface ClassifiedDocument {
  id: string;
  fileName: string;
  documentType: string;
  classification: 'energy_cert' | 'nota_simple' | 'ibi' | 'community_minutes'
    | 'habitability' | 'insurance' | 'renovation_quote' | 'receipt'
    | 'warranty' | 'inspection' | 'unknown';
  status: 'classified' | 'needs_review' | 'unrecognized';
  extractedFields: Record<string, string>;
  icon: string;
  linkedRoom?: string;
}

// ── Trusted Contacts ───────────────────────────────────────

export interface TrustedContact {
  id: string;
  name: string;
  phone: string;
  trade: string;
  specialty: string;
  yearsKnown: number;
  strengths: string[];
  weaknesses: string[];
  personality: string;
  rating: number;
  voiceNoteDuration?: number;
}

// ── Inventory ──────────────────────────────────────────────

export interface InventoryItem {
  id: string;
  name: string;
  brand?: string;
  model?: string;
  room: string;
  category: 'appliance' | 'fixture' | 'finish' | 'structural';
  condition: 'new' | 'good' | 'fair' | 'poor';
  hasReceipt: boolean;
}

// ── Chat Engine ────────────────────────────────────────────

export interface ConversationStep {
  id: string;
  phase: OnboardingPhase;
  messages: StepMessage[];
  waitForAction?: boolean;
}

export interface StepMessage {
  role: ChatMessageRole;
  content: string;
  delayMs?: number;
  toolTrail?: ToolTrailItem[];
  thought?: ThoughtData;
  citations?: CitationItem[];
  confirmedBadge?: ConfirmedBadge;
  suggestedResponses?: SuggestedResponseCardData[];
  component?: ChatComponent;
  suggestedActions?: SuggestedAction[];
  files?: UploadedFile[];
}

export interface ChatState {
  currentStepIndex: number;
  messages: ChatMessage[];
  phase: OnboardingPhase;
  isTyping: boolean;
  isProcessing: boolean;
}
