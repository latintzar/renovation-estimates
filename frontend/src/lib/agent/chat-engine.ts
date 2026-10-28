import type { ChatMessage, ChatState, ConversationStep, StepMessage } from "./types";

export const CONVERSATION_STEPS: ConversationStep[] = [
  {
    id: "welcome",
    phase: "welcome",
    messages: [
      {
        role: "leo",
        content:
          "Welcome back Lucia. Let's onboard this Moraira villa the same way we'd prepare a production dossier. Do you have the live listing URL?",
        delayMs: 700,
        suggestedActions: [
          { id: "paste-url", label: "Paste listing URL", icon: "🔗", style: "primary" },
          { id: "manual", label: "No listing, manual flow", icon: "✏️", style: "secondary" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "listing-scrape",
    phase: "listing_check",
    messages: [
      { role: "agent", content: "https://www.idealista.com/inmueble/999900001/", delayMs: 0 },
      {
        role: "leo",
        content: "",
        delayMs: 200,
        toolTrail: [
          { id: "scrape-1", icon: "🔗", label: "Validated URL and domain", status: "done", durationMs: 700, detail: "idealista.com" },
          { id: "scrape-2", icon: "🌐", label: "Scraped listing payload", status: "done", durationMs: 2100, detail: "31 structured fields" },
          { id: "scrape-3", icon: "📸", label: "Fetched listing media", status: "done", durationMs: 1200, detail: "35 photos + floor plan" },
        ],
        thought: {
          durationSec: 9,
          summary:
            "I cross-checked price band, location string, and media count against expected Costa Blanca luxury inventory to reduce bad-ingestion risk.",
        },
      },
      {
        role: "leo",
        content: "Perfect. I parsed the villa and prepared a draft profile.",
        delayMs: 400,
        component: { type: "property_summary", data: {} },
        confirmedBadge: { detail: "Address, beds, baths and asking price auto-ingested from listing." },
      },
      {
        role: "leo",
        content: "Anything to correct before I run room clustering?",
        delayMs: 350,
        suggestedActions: [
          { id: "looks-good", label: "Looks good", style: "primary" },
          { id: "correct", label: "I need to correct details", style: "secondary" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "basic-info",
    phase: "basic_info",
    messages: [
      {
        role: "agent",
        content:
          "Built area should be 412m2, useful around 374m2. Pool system is old and likely needs work. Price target 1.845M is correct.",
      },
      {
        role: "leo",
        content:
          "Updated. That pool-system note is high value for renovation strategy. Next I'll cluster all room media and flag weak coverage.",
        delayMs: 500,
      },
    ],
  },
  {
    id: "photo-clustering",
    phase: "photos",
    messages: [
      {
        role: "leo",
        content: "",
        toolTrail: [
          { id: "cluster-1", icon: "📸", label: "Loaded 35 photos", status: "done", durationMs: 900 },
          { id: "cluster-2", icon: "🧠", label: "Ran Gemini room clustering", status: "done", durationMs: 3200, detail: "gemini-3-pro-preview reasoning pass" },
          { id: "cluster-3", icon: "🏷️", label: "Mapped 9 room groups", status: "done", durationMs: 1000 },
        ],
        thought: { durationSec: 11, summary: "I separate terrace/pool imagery from exterior facade to avoid false room-area assumptions." },
      },
      {
        role: "leo",
        content: "Review clustering. You can move photos if something is off.",
        component: { type: "photo_clusters", data: {} },
      },
      {
        role: "leo",
        content: "Bedroom 2, Bedroom 3 and hallway could use one extra angle each. Continue with current pack?",
        suggestedActions: [
          { id: "continue", label: "Continue", style: "primary" },
          { id: "upload-more", label: "Upload more photos", style: "secondary" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "floor-plan",
    phase: "floor_plan",
    messages: [
      {
        role: "leo",
        content: "",
        toolTrail: [
          { id: "fp-1", icon: "📐", label: "Sent floor plan to RasterScan", status: "done", durationMs: 1700 },
          { id: "fp-2", icon: "🧭", label: "Segmented rooms and bounds", status: "done", durationMs: 2200, detail: "9 regions" },
          { id: "fp-3", icon: "📏", label: "Computed room areas", status: "done", durationMs: 900 },
        ],
      },
      {
        role: "leo",
        content: "Link each photo cluster to its room on the plan.",
        component: { type: "floor_plan", data: { mode: "linking" } },
      },
    ],
    waitForAction: true,
  },
  {
    id: "room-linking",
    phase: "room_linking",
    messages: [
      {
        role: "leo",
        content:
          "Great, all major spaces linked. Built-area tolerance is within expected range for listing data vs segmented plan.",
        confirmedBadge: { detail: "Linked room clusters persisted in chat state for production replay." },
      },
    ],
  },
  {
    id: "inventory-scan",
    phase: "inventory_scan",
    messages: [
      {
        role: "leo",
        content: "",
        toolTrail: [
          { id: "inv-1", icon: "🔍", label: "Detected visible fixtures and appliances", status: "done", durationMs: 2400 },
          { id: "inv-2", icon: "🗂️", label: "Built room inventory list", status: "done", durationMs: 1100 },
        ],
        thought: {
          durationSec: 8,
          summary: "I prioritize high-cost systems (kitchen, bathrooms, pool mechanics, glazing) because they influence renovation budget the most.",
        },
      },
      { role: "leo", content: "Here is the inferred inventory pack.", component: { type: "inventory_list", data: {} } },
      {
        role: "leo",
        content:
          "I flagged possible pool filtration degradation and mixed-condition glazing. Any known issues beyond that?",
        suggestedActions: [
          { id: "share-issues", label: "Share known issues", style: "primary" },
          { id: "no-issues", label: "No extra issues", style: "outline" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "docs-request",
    phase: "documents",
    messages: [
      {
        role: "leo",
        content:
          "Upload key docs: certificado energético, nota simple, IBI, community minutes, insurance and any renovation quotes.",
        suggestedActions: [
          { id: "upload-docs", label: "Upload documents", style: "primary" },
          { id: "skip-docs", label: "Skip for now", style: "outline" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "docs-analysis",
    phase: "documents",
    messages: [
      {
        role: "agent",
        content: "",
        files: [
          { id: "df1", name: "certificado_energetico_moraira_2025.pdf", size: 1200000, type: "application/pdf", status: "done", progress: 100 },
          { id: "df2", name: "nota_simple_registro_alicante_2026.pdf", size: 970000, type: "application/pdf", status: "done", progress: 100 },
          { id: "df3", name: "recibo_ibi_2025_moraira.pdf", size: 320000, type: "application/pdf", status: "done", progress: 100 },
          { id: "df4", name: "acta_comunidad_portet_dic_2025.pdf", size: 2100000, type: "application/pdf", status: "done", progress: 100 },
        ],
      },
      {
        role: "leo",
        content: "",
        toolTrail: [
          { id: "docs-1", icon: "📥", label: "Received and indexed 4 files", status: "done", durationMs: 900 },
          { id: "docs-2", icon: "📄", label: "Ran document classification + extraction", status: "done", durationMs: 4200 },
        ],
        citations: [
          { id: "c1", title: "Registro de la Propiedad de Teulada reference", url: "https://sede.registradores.org" },
          { id: "c2", title: "IBI municipality format reference", url: "https://teulada-moraira.es" },
        ],
      },
      { role: "leo", content: "Document classification complete.", component: { type: "document_cards", data: {} } },
      {
        role: "leo",
        content:
          "Community minutes show a EUR 4,200 derrama for pool infrastructure. That aligns with the visual pool-system wear.",
      },
    ],
  },
  {
    id: "room-docs",
    phase: "room_documents",
    messages: [
      {
        role: "leo",
        content: "Do you have room-level receipts (kitchen appliances, pool maintenance, glazing replacement)?",
        suggestedActions: [
          { id: "has-room-docs", label: "Yes, upload now", style: "primary" },
          { id: "no-room-docs", label: "No room receipts", style: "secondary" },
        ],
      },
    ],
    waitForAction: true,
  },
  {
    id: "contacts",
    phase: "contacts",
    messages: [
      {
        role: "leo",
        content:
          "Last step: trusted contacts. Voice notes are best because I can capture soft signals (reliability, communication style, escalation behavior).",
        suggestedActions: [
          { id: "voice", label: "Record voice note", style: "primary" },
          { id: "type", label: "Type contact details", style: "secondary" },
        ],
      },
      { role: "agent", content: "🎙️ Voice note (0:51)" },
      {
        role: "leo",
        content: "",
        toolTrail: [
          { id: "contacts-1", icon: "🎙️", label: "Transcribed voice note", status: "done", durationMs: 1800 },
          { id: "contacts-2", icon: "🧠", label: "Extracted contact profile", status: "done", durationMs: 1200 },
        ],
      },
      { role: "leo", content: "Captured contact card:", component: { type: "contact_card", data: { contactIndex: 0 } } },
    ],
    waitForAction: true,
  },
  {
    id: "review",
    phase: "review",
    messages: [
      { role: "agent", content: "Looks complete. Finish dossier." },
      { role: "leo", content: "Done. This simulation now mirrors a production-grade onboarding dossier.", component: { type: "completion_summary", data: {} } },
      {
        role: "leo",
        content: "You can reopen anytime, and I’ll resume from this exact state.",
        suggestedActions: [
          { id: "start-analysis", label: "Start analysis", style: "primary" },
          { id: "back-dashboard", label: "Back to dashboard", style: "outline" },
        ],
      },
    ],
    waitForAction: true,
  },
];

// ── Engine Functions ───────────────────────────────────────

let messageCounter = 0;

const generateId = (): string => {
  messageCounter += 1;
  return `msg-${messageCounter}-${Date.now()}`;
};

export const createInitialState = (): ChatState => ({
  currentStepIndex: 0,
  messages: [],
  phase: 'welcome',
  isTyping: false,
  isProcessing: false,
});

export const stepMessageToChatMessage = (
  stepMsg: StepMessage,
): ChatMessage => ({
  id: generateId(),
  role: stepMsg.role,
  content: stepMsg.content,
  timestamp: new Date(),
  toolTrail: stepMsg.toolTrail,
  thought: stepMsg.thought,
  citations: stepMsg.citations,
  confirmedBadge: stepMsg.confirmedBadge,
  suggestedResponses: stepMsg.suggestedResponses,
  component: stepMsg.component,
  suggestedActions: stepMsg.suggestedActions,
  files: stepMsg.files,
  animate: true,
});

export const getCurrentStep = (state: ChatState): ConversationStep | null => CONVERSATION_STEPS[state.currentStepIndex] ?? null;

export const getNextStep = (state: ChatState): ConversationStep | null => CONVERSATION_STEPS[state.currentStepIndex + 1] ?? null;

export const advanceStep = (state: ChatState): ChatState => ({
  ...state,
  currentStepIndex: state.currentStepIndex + 1,
  phase: CONVERSATION_STEPS[state.currentStepIndex + 1]?.phase ?? state.phase,
});

export const getTotalSteps = (): number => CONVERSATION_STEPS.length;

export const getCompletionPct = (stepIndex: number): number =>
  Math.round((stepIndex / CONVERSATION_STEPS.length) * 100);
