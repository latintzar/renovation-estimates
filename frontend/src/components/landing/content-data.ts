// Leo.casa Landing Page Content Data
// This file contains all the copy for the landing page, organized by persona

export type Persona = 'renters' | 'buyers' | 'buyer-agents' | 'relocation';

// ============================================================================
// RENTERS CONTENT
// ============================================================================
export const rentersContent = {
  hero: {
    eyebrow: "For people who rent in the city",
    headline: "Tell Leo how you live — he finds the rentals worth rearranging your day for.",
    subcopy: "Leo learns your routine, your budget, the streets you love and the things you can't stand. He scans new listings across agencies and portals and only sends the places that actually feel like \"you\".",
    primaryCta: "Talk to Leo about your next move",
    secondaryCta: "See how Leo works",
  },
  howItWorks: {
    title: "How Leo fits into your next move",
    steps: [
      {
        number: 1,
        title: "Tell Leo how you live",
        description: "Share where you need to be, how you move around the city, what kind of buildings you like, and what you're done compromising on.",
        detail: "You can type or talk — Leo asks the questions that make your \"ideal flat\" more than just filters.",
      },
      {
        number: 2,
        title: "Get rentals worth leaving the sofa for",
        description: "Leo follows new listings as they appear on agency sites and portals.",
        detail: "When something matches your lifestyle, your budget and your taste, you get:",
        bullets: [
          "the listing link",
          "a quick explanation of why it fits",
          "the phone or WhatsApp contact to book a viewing fast.",
        ],
      },
      {
        number: 3,
        title: "View, react, and let Leo sharpen your taste",
        description: "After you visit a place, you send Leo:",
        bullets: [
          "a quick \"how it felt\"",
          "a couple of notes",
          "optional photos from your visit",
        ],
        detail: "Leo learns from every reaction and quietly adjusts what it looks for, where it looks, and how it reads images for the next round.",
      },
    ],
  },
  whatLeoChecks: {
    title: "What Leo pays attention to before you spend a Saturday on a viewing",
    categories: [
      {
        name: "City & access",
        items: [
          "Distance to your work or campus",
          "How you'd actually get there (walking, public transport, bike)",
          "Connection to the places you go most — gym, friends, sports, nightlife",
        ],
      },
      {
        name: "Street & building",
        items: [
          "Traffic and street noise",
          "Bars and terraces nearby",
          "General feel of the block and entrance",
          "Floor level and lift vs stairs",
        ],
      },
      {
        name: "Look & feel",
        items: [
          "Likely natural light in the main rooms",
          "Whether the layout feels open or chopped up",
          "Signs of staging vs. real lived-in space",
          "Overall vibe from the listing photos",
        ],
      },
      {
        name: "Age & structure",
        items: [
          "Building year and construction type from cadastro",
          "Known issues for buildings of that era (aluminosis, asbestos)",
          "ITE status and recent inspections",
          "Community complaints and neighbourhood reputation",
        ],
      },
    ],
    callout: "You don't have to guess from thumbnails. Leo reads the data, the photos and the context to decide what's worth your time.",
  },
  viewingDay: {
    title: "On viewing day, you focus on how it feels. Leo learns from what you notice.",
    description: "When you go to see a place, your job is simple: notice how it feels to be there.",
    afterViewing: "After the viewing, you send Leo:",
    bullets: [
      "a quick rating of how much it felt like \"home\"",
      "a few taps on things you liked or disliked (light, noise, layout, area)",
      "any photos you took that capture the reality",
    ],
    detail: "Leo uses all of this to adjust what it recommends next, so each round of places feels closer to what you actually want, not what you thought you wanted on paper.",
    cta: "See a sample feedback screen",
  },
  movingProfile: {
    title: "One profile that follows you between flats",
    description: "Most portals forget you the moment you sign a lease. Leo does the opposite.",
    detail: "Every move teaches Leo more about how you live:",
    bullets: [
      "what kind of streets you actually stay in",
      "which layouts you keep rejecting",
      "where you're willing to compromise",
    ],
    actions: [
      "**start a search** when you're thinking of moving",
      "**pause** once you've found a place",
      "**reactivate** next time life changes and you're ready to move again",
    ],
    callout: "Whether it's your second rental or your seventh, you don't have to explain yourself from scratch.",
  },
  whoThisIsFor: {
    title: "Who Leo helps most when renting",
    items: [
      "People who are tired of scrolling through hundreds of identical listings",
      "People with specific routines or hobbies that normal filters can't capture",
      "People changing neighbourhood or city and wanting to avoid nasty surprises",
      "People who expect to move again and want a smarter way to do it each time",
    ],
    cta: "Start with a short chat",
  },
  testimonials: {
    title: "What renters say about using Leo",
    quotes: [
      "It felt like having a friend who already knew which flats were obviously wrong for me.",
      "The first batch of places already made more sense than weeks on portals.",
      "Telling Leo what I didn't like after a viewing helped me understand my own taste.",
      "The next time I move, I'm not starting from zero again — that's the best part.",
    ],
    cta: "Talk to Leo",
  },
};

// ============================================================================
// BUYERS CONTENT
// ============================================================================
export const buyersContent = {
  hero: {
    eyebrow: "For people buying a home",
    headline: "Tell Leo how you live — get homes worth seeing and a checklist for each serious viewing.",
    subcopy: "Leo learns what \"home\" means to you, scans new listings, and flags the ones that fit your life. For each place you're serious about, he prepares a viewing checklist so you know what to check, what to ask, and what might cost you later.",
    primaryCta: "Talk to Leo about your search",
    secondaryCta: "See a sample viewing checklist",
  },
  howItWorks: {
    title: "A clearer way to move from \"maybe\" to \"let's buy it\"",
    steps: [
      {
        number: 1,
        title: "Share how you live and what home should unlock",
        description: "You tell Leo:",
        bullets: [
          "where you want to be",
          "how you move through the city",
          "who will live there",
          "what you want this move to change in your life",
        ],
        detail: "Leo turns that into a clear idea of what you need from a home — not just how many rooms.",
      },
      {
        number: 2,
        title: "Get homes that match your life, not just your filters",
        description: "Leo scans new listings and surfaces the ones that:",
        bullets: [
          "fit your budget and target areas",
          "align with your daily routine and lifestyle",
          "have layouts and light that suit the way you actually use space",
        ],
        detail: "You receive:",
        secondBullets: [
          "the listing link",
          "the agent's contact",
          "a short explanation of why this one is worth a closer look.",
        ],
      },
      {
        number: 3,
        title: "For each serious candidate, get a tailored viewing checklist",
        description: "When a place looks promising, Leo prepares a checklist specific to:",
        bullets: [
          "the building's age and type",
          "what can be inferred from legal and public data",
          "the street, neighbourhood and environment",
          "your appetite for renovation and long-term plans",
        ],
        detail: "So you don't just \"have a look\" — you walk in knowing exactly what to pay attention to.",
      },
    ],
  },
  whatLeoLooksInto: {
    title: "What Leo considers before you step into a potential home",
    categories: [
      {
        name: "The building and its story",
        items: [
          "Approximate year and construction type",
          "Clues from official records about size and use",
          "Signs that future works might be coming",
        ],
      },
      {
        name: "The flat itself",
        items: [
          "Likely light in the main rooms",
          "Relationship between rooms (flow, usability, privacy)",
          "Floor level and trade-offs (noise vs stairs vs lift)",
        ],
      },
      {
        name: "The surroundings",
        items: [
          "Everyday access to work, school, or key places in your life",
          "Street character and likely noise patterns",
          "General feel of the immediate area",
        ],
      },
      {
        name: "Your plans",
        items: [
          "Whether the place seems to fit \"as is\" or might need changes",
          "Whether the layout appears friendly to typical renovations",
          "How the home might feel for you in a few years, not just on move-in day",
        ],
      },
    ],
    callout: "The goal isn't to replace professionals or official checks — it's to help you focus your energy on a smaller set of homes that are truly worth investigating properly.",
  },
  viewingChecklist: {
    title: "What you walk in with when you use Leo",
    description: "For each home you're seriously considering, Leo prepares a checklist structured around:",
    bullets: [
      "**What to look at** in each key room",
      "**What to pay attention to** in the building and street",
      "**What to ask** the agent or owner",
      "**What to note down** for later comparison",
    ],
    reflects: [
      "the specifics of that property",
      "the kind of risks more common to that building type or area",
      "your tolerance for work and change",
    ],
    detail: "You can open it on your phone during the visit and tick things off as you go, adding your own notes and photos.",
    cta: "See an example",
  },
  afterViewing: {
    title: "After the viewing, Leo helps you compare and decide",
    description: "Once you've seen a place, you can:",
    bullets: [
      "record whether it felt like a serious contender",
      "note what you liked and what bothered you",
      "attach photos that show important details",
    ],
    leoActions: [
      "updates how it evaluates future homes",
      "helps you compare candidates on the things that matter to you",
      "highlights patterns that are emerging in what you keep accepting or rejecting",
    ],
    detail: "Over time, the homes you're shown become more aligned with the reality of your choices, not just your initial description.",
  },
  renovationHelp: {
    title: "When a place \"almost\" works, Leo can help you explore options",
    description: "If you're open to doing some work, you can ask Leo to outline a few renovation paths, such as:",
    paths: [
      "a minimal refresh to make it liveable",
      "a comfort upgrade to match your lifestyle",
      "a more transformative project if the structure allows",
    ],
    leoSketches: [
      "what would change in the space",
      "how it might affect how you use the home",
      "a rough sense of cost and complexity",
    ],
    callout: "This doesn't replace architects or contractors — it gives you a clearer starting point to discuss with them.",
    cta: "Talk to Leo about a property you're considering",
  },
  whoThisIsFor: {
    title: "Who Leo is built for when buying",
    items: [
      "People who don't want to fall in love with a listing before understanding its realities",
      "People who prefer to see fewer, better-matched homes rather than every possible option",
      "People who want structured checklists and notes, but not a dry spreadsheet",
      "People who care as much about daily life in the home as about the price",
    ],
  },
  testimonials: {
    title: "What buyers say",
    quotes: [
      "The checklist made me feel prepared instead of overwhelmed.",
      "I realised quickly which types of buildings I should stop wasting my energy on.",
      "Seeing Leo's why-this-matters notes next to my own feelings made decisions much clearer.",
    ],
    cta: "Start a conversation with Leo",
  },
};

// ============================================================================
// BUYER AGENTS / PERSONAL SHOPPERS CONTENT
// ============================================================================
export const buyerAgentsContent = {
  hero: {
    eyebrow: "For Personal Shoppers Inmobiliarios",
    headline: "Let Leo handle client taste and property analysis — you focus on the deal and the relationship.",
    subcopy: "Leo interviews your clients, learns their lifestyle and trade-offs, helps you build smarter shortlists, and prepares viewing checklists for the homes that move from \"interesting\" to \"let's go see it\".",
    primaryCta: "Use Leo with a real client",
    secondaryCta: "See a sample client profile",
  },
  howItWorks: {
    title: "A co-pilot for understanding clients and pre-filtering stock",
    steps: [
      {
        number: 1,
        title: "Onboard each client with a smarter interview",
        description: "You can sit with your client and run the interview together, or send them a branded link.",
        leoCaptures: [
          "their routines and habits",
          "how they use their current home",
          "what they want this move to change",
          "their non-negotiables and red lines",
        ],
        detail: "The result is a structured profile you can trust and revisit.",
      },
      {
        number: 2,
        title: "Build shortlists that respect their time and yours",
        description: "You keep using the portals, agency networks and off‑market channels you already have.",
        extensionFeatures: [
          "pick a client in the extension while you browse",
          "see a quick fit hint on each listing card for that client",
          "click **\"Send to Leo\"** on the few properties that deserve a closer look",
        ],
        leoActions: [
          "checks fit against the client's profile",
          "highlights the main reasons it may work",
          "flags potential issues to clarify before you schedule a visit",
        ],
        detail: "You end up with smaller, higher‑quality shortlists that are easier to defend and easier for the client to understand.",
      },
      {
        number: 3,
        title: "Walk into viewings with shared expectations",
        description: "For each serious visit, Leo prepares:",
        bullets: [
          "a checklist your client can follow",
          "extra notes you can see as the expert",
        ],
        detail: "After the visit, you both record impressions in the same place, and Leo uses that to refine future recommendations.",
      },
    ],
  },
  clientProfile: {
    title: "From vague brief to clear, living profile",
    description: "Instead of relying on a few lines of notes, you see:",
    items: [
      "how they balance location vs space",
      "how sensitive they are to noise, light, or building age",
      "how much work they're willing to take on",
      "which past homes they liked and why",
    ],
    persistence: [
      "across cities",
      "across price changes",
      "across future moves",
    ],
    detail: "You can always refer back to it when doubts appear or new options emerge.",
    cta: "Explore an example profile",
  },
  propertyAnalysis: {
    title: "Clear reasons to include or exclude a property",
    description: "For each property you send to Leo, you see:",
    items: [
      "a quick fit summary (\"Strong match on light and layout, weaker on area\")",
      "tags for key aspects (quiet, lively, renovation potential, older building, etc.)",
      "a short bullet list of \"things to verify\" before or during the visit",
    ],
    benefits: [
      "explain your choices to clients",
      "compare similar options",
      "avoid viewing flats that never had a chance",
    ],
    cta: "Try Leo on a current listing",
  },
  viewingDay: {
    title: "Make every visit count",
    description: "Before each viewing, you and your client can open the shared checklist for that home.",
    clientSees: [
      "simple prompts on what to look at and feel in each key space",
      "a few important questions to ask",
    ],
    agentSees: [
      "the same, plus extra technical prompts",
      "a space to note details the client might miss",
    ],
    detail: "After the visit, you both record impressions. Leo notices patterns in what they gravitate to, what they reject, and what they hesitate on — and adjusts future suggestions accordingly.",
  },
  renovationLayer: {
    title: "Use renovation ideas to open or close options, not to oversell them",
    description: "When a property is strong but not quite right \"as is\", Leo can outline:",
    paths: [
      "a simple improvement plan",
      "a more ambitious reconfiguration if feasible",
    ],
    leoProvides: [
      "an overview of what would change",
      "a rough sense of complexity and timing",
    ],
    agentRole: [
      "chooses which scenarios to show",
      "filters out unrealistic options",
      "guides your client through real-world constraints with your own network.",
    ],
  },
  whyUse: {
    title: "Why personal shoppers bring Leo into their process",
    items: [
      "To understand new clients faster and more deeply",
      "To defend their shortlists with clear, structured reasoning",
      "To waste fewer visits on places that were wrong from the start",
      "To have a single place where feedback, notes and patterns live",
      "To differentiate their service with a mix of human judgment and clear analysis",
    ],
    cta: "Talk to Leo about integrating this into your next mandate",
  },
};

// ============================================================================
// RELOCATION AGENTS CONTENT
// ============================================================================
export const relocationContent = {
  hero: {
    eyebrow: "For Relocation and Destination Service Providers",
    headline: "Let Leo standardise housing needs, so you can focus on visas, onboarding and families.",
    subcopy: "Leo interviews each assignee or family, turns their lifestyle and constraints into a clear housing profile, and helps you pick options that are more likely to work on the first round of visits.",
    primaryCta: "Use Leo with an assignee",
    secondaryCta: "See a sample housing brief",
  },
  howItWorks: {
    title: "A consistent housing layer across all your moves",
    steps: [
      {
        number: 1,
        title: "Intake: a smarter housing interview",
        description: "Leo speaks with each assignee or family in a simple, guided conversation.",
        briefCaptures: [
          "where they'll work or study",
          "their commuting preferences",
          "family composition and space needs",
          "lifestyle habits (quiet vs lively, car vs public transport, hobbies)",
          "sensitivity to noise, older buildings, stairs, etc.",
        ],
        detail: "Every profile uses the same structure, making it easier to compare and to assign to the right local consultant.",
      },
      {
        number: 2,
        title: "Shortlists that respect both policy and people",
        description: "You plug in your usual sources:",
        sources: [
          "corporate housing partners",
          "agency networks",
          "portals you already use",
        ],
        leoActions: [
          "checks fit against the profile",
          "flags obvious mismatches",
          "highlights a few reasons each option might work",
        ],
        detail: "This helps you present smaller, better targeted shortlists from the first contact.",
      },
      {
        number: 3,
        title: "Viewings that feel purposeful",
        description: "For each property that makes it to a visit, Leo prepares a simple checklist for the assignee.",
        assigneeActions: [
          "walk through the home with prompts in their language",
          "record quick impressions during or after the viewing",
        ],
        detail: "You see their feedback in a structured way, which helps you adjust the next proposals quickly.",
      },
    ],
  },
  housingBrief: {
    title: "From scattered emails to one clear housing profile",
    description: "After Leo's interview, you see:",
    items: [
      "key locations (office, school, regular destinations)",
      "time and mode of transport they're comfortable with",
      "minimum and preferred home features",
      "tone of neighbourhood they're drawn to",
      "specific sensitivities (stairs, noise, building type, etc.)",
    ],
    briefFeatures: [
      "can be shared within your team",
      "stays attached to the assignee over time",
      "can be reused if they move again or extend their stay",
    ],
    cta: "Preview a sample brief",
  },
  localNetwork: {
    title: "Help your local partners work with clearer expectations",
    description: "When you pass a case to a local consultant or partner agency, you can attach:",
    attachments: [
      "the Leo housing profile",
      "a few pre-screened options with fit notes",
    ],
    partnerBenefits: [
      "understand the assignee quickly",
      "propose properties that are more likely to be accepted",
      "use their time on viewings and negotiations instead of guesswork",
    ],
    detail: "Over time, you can also see patterns in what certain segments of assignees tend to accept or reject in each city.",
  },
  feedbackLoop: {
    title: "Learn from each move without extra admin",
    description: "Every time an assignee:",
    actions: [
      "accepts or rejects a property",
      "gives feedback after a viewing",
    ],
    leoRecords: "Leo records this in the same structure as the initial brief.",
    benefits: [
      "understand why certain options work consistently better",
      "refine your guidance for future assignees",
      "adjust your city playbooks based on real choices, not assumptions.",
    ],
  },
  whyUse: {
    title: "Why relocation companies add Leo to their toolkit",
    items: [
      "To standardise housing intake across many consultants and cities",
      "To reduce wasted viewings and \"none of these fit me\" moments",
      "To give assignees a sense of being understood from the beginning",
      "To support local partners with clearer, more actionable briefs",
      "To learn systematically from each relocation rather than starting from zero each time",
    ],
    cta: "Talk to Leo about your current workflow",
  },
};

// ============================================================================
// SHARED CONTENT
// ============================================================================
export const sharedContent = {
  nav: {
    logo: "Leo.casa",
    links: [
      { label: "How Leo works", href: "#how-it-works" },
      { label: "For Renters", href: "#", persona: "renters" as Persona },
      { label: "For Buyers", href: "#", persona: "buyers" as Persona },
      { label: "For Professionals", href: "#professionals" },
    ],
    rightLinks: [
      { label: "Reviews", href: "#reviews" },
      { label: "Sign in", href: "/login" },
    ],
    ctaLabel: "Talk to Leo",
  },
  footer: {
    copyright: "© 2025 Leo.casa — Your AI Home Advisor.",
    links: [
      { label: "Privacy", href: "#" },
      { label: "Cookies", href: "#" },
      { label: "FAQs", href: "#" },
      { label: "Contact", href: "#" },
      { label: "Terms", href: "#" },
    ],
  },
  proLink: "I help people find a place →",
};

