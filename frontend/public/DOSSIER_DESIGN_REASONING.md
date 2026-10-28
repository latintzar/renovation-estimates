# Dossier Design Reasoning

## What's wrong now
- Looks like a generic vibe-coded React dashboard
- Fonts are wrong (was Newsreader/Inter, needs Playfair Display / Source Sans 3)
- Too many small boxes with stats — feels like a SaaS metrics page
- "Intel briefing" / numbered cards feel empty and decorative, not useful
- No visual warmth — doesn't feel like Leo brand (cream, terracotta, serif headings)
- The dossier header is disconnected from the rest of the Leo app style

## What drugsand.me does right
- Giant serif numbers (1, 2, 3) that immediately grab you
- Each number is ONE clear action/takeaway, not a metric
- Below the numbers: actual prose paragraphs that EXPLAIN and EDUCATE
- Tab-style links for deep dives (Effects, Risks, Harm Reduction, The Law)
- References section at the bottom with real citations
- Overall: the page TEACHES you, it doesn't just show you stats

## What the Reddit thread reveals people actually need
- "You need to do your research and have some semblance of knowledge" — the dossier IS that research, done for you
- "When all three quotes suggest completely different approaches" — the dossier should help you COMPARE approaches
- "How are normal homeowners supposed to navigate this?" — the dossier navigates for you
- "Has anyone ever tried paying a retired plumber just to look at quotes?" — that's literally our expert review step

## Key insight
The dossier isn't a dashboard. It's a DOCUMENT. Like a briefing memo from a smart friend.
The user should feel like they just read a 2-page article that made them 10x smarter about their problem.

## What the Leo Copilot app does right (header patterns)
- **Room screens**: Photo at top (full bleed), serif title (Playfair Display 600, ~28px), clean body below
- **Home hero**: Image with gradient fade, serif title with text shadow, pills for navigation
- All screens use: cream background (#FDFBF7), terracotta accents (#da654d), Playfair Display for headings, generous padding

## The design

### Header (top of dossier, below Safari chrome)
Match the Expo app listing screen style:
- Warm gradient bar (#da654d → #c44e38) with Leo logo + "Your Home Dossier" in small caps + boiler topic in large Playfair Display serif

### Body sections (each has clear utility)

**Section 1: "What's happening" — The diagnosis**
A terracotta-accented callout. One sentence: "E119 = low water pressure. Not a hardware failure."
This is the EDUCATION part. The user instantly knows what the error code means.

**Section 2: "Compare approaches" — The comparison**
Two-column with left border color. Red = upsell, Green = correct fix. This directly addresses the Reddit pain point of "3 quotes, 3 different answers."
Below each: WHY it's wrong/right, citing the manual page.

**Section 3: "What to do" — The action**
Numbered steps (1, 2, 3) in Playfair Display serif, each with a single actionable sentence in Source Sans 3. This is the drugsand.me style — big numbers, clear actions.

**Section 4: Sources**
Small footer with linked source names. Proves this isn't AI hallucination.

### What NOT to do
- No "Fair price" / "DIY time" / "Manual ref" stat boxes — that's SaaS dashboard energy
- No "YOUR INTEL BRIEFING" badge — that's cringe
- No empty white cards with tiny text — that's basic React
- The content should FILL the phone and feel dense with value
