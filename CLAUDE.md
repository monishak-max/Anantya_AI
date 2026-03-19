# Astro App — Project Instructions

## What this is
A premium Vedic astrology companion app rooted in Jyotish. The product philosophy is "ancient intelligence, modern expression." The member should feel seen, guided, clarified, and steadied — never lectured or frightened.

## What I'm building
The AI layer that powers all readings in the app. It takes the user's natal Moon data, current transits, and dasha period as structured input, runs it through a modular prompt stack (identity + knowledge framework + ethics + feature-specific instructions), and outputs formatted content — like "Today pulls you toward visibility, whether you're ready or not" with the support text, do-today action, reflection prompt, and the full Dive Deeper expansion with "What this means" and "The Resistance" sections. Each surface (Now, Mandala, Union) has its own prompt module and strict output schema with word-count targets matched to the UI. The job is the prompt architecture, the LLM integration, the input/output pipeline, and making sure the voice feels like one coherent awakened intelligence — not a horoscope bot.

## User inputs (onboarding)
Three inputs collected at signup:
1. **Birth date** (DOB)
2. **Birth time** (with "I'm not sure" fallback)
3. **Place of birth** (autocomplete location search)

From these three, the system computes the full natal chart — Moon sign, nakshatra, lagna, all planet placements, houses, dashas, etc.

## Core principle
The Moon is the primary anchor. Everything flows from the natal Moon sign, Moon nakshatra, and Moon-based systems (Vimshottari Dasha, transits from Moon, nakshatra compatibility). Lagna and other factors are secondary/premium layers.

## Tech stack
- **Frontend:** TBD (awaiting platform decision — likely React Native or SwiftUI)
- **Backend:** Supabase (Postgres + Auth + Edge Functions + Storage)
- **AI layer:** LLM-powered content generation using a modular prompt architecture (see `1.0/prompts/`)
- **Astro computation:** TBD (needs ephemeris engine for chart calculations)

## Project structure
```
astro_app/
├── 1.0/                          # Prompt architecture pack v1
│   ├── prompts/core/             # 5 core prompts (identity, knowledge, translation, ethics, reasoning)
│   ├── prompts/features/         # 8 feature prompts (one per product surface)
│   ├── docs/                     # Design docs (master prompt, knowledge map, output schemas)
│   └── config/                   # Assembly order + JSON schema reference
├── questions_for_manager.md      # Open decisions tracker
└── CLAUDE.md                     # This file
```

## Product surfaces (3 tabs + premium)
1. **Now** — daily insight (collapsed card + expanded "Dive Deeper" sheet)
2. **Mandala** — user's natal chart + active transit cards (3-7 cards)
3. **Union** — relationship compatibility (snapshot + deep read)
4. **Premium:** Birth chart (Janam Patri), Weekly/Monthly overviews

## Prompt architecture
Prompts are assembled at runtime in this order:
1. Core identity → 2. Knowledge framework → 3. Translation layer → 4. Ethics guardrails → 5. Reasoning contract → 6. Feature prompt → 7. Structured astro data → 8. Output schema

All core prompts load for every request. Feature prompts swap per surface. See `1.0/config/prompt_stack_example.yaml`.

## Output schemas
Every surface has exact field names and word-count targets defined in `1.0/docs/03_output_schemas.md`. Respect these constraints — the UI is designed around whitespace and compression.

Key targets:
- Now collapsed: headline 7-14 words, support 18-34 words
- Now expanded: opening 28-55 words, resistance 25-70 words
- Mandala cards: 3-7 max, no duplicate themes
- Birth chart: 700-1,400 words total

## Knowledge systems (10 layers)
Jyotish is the engine. The other 9 layers enrich it:
1. **Jyotish** — primary (planets, houses, signs, nakshatras, transits, timing)
2. **Nakshatra** — soul texture, emotional depth
3. **Dasha** — life chapters, karmic timing
4. **Gochar (transits)** — present-moment weather
5. **Dharma** — ethical compass (shapes voice, rarely named)
6. **Karma** — patterns, not punishment
7. **Gunas** — inner state quality (translate, don't label)
8. **Purusharthas** — life aim emphasis
9. **Spiritual psychology** — meaning-making from Gita etc.
10. **Kundali matching** — relational layer for Union

## Voice and tone rules
- Calm, clear, elegant, warm, perceptive
- No fear, no doom, no superstition theater
- No generic horoscope filler
- No karma-shaming
- Preserve member agency always
- Backend thinks in Sanskrit; frontend speaks modern English
- Prefer: energy, timing, rhythm, visibility, readiness, alignment, emotional weather
- Avoid raw Sanskrit in free surfaces; introduce carefully in premium

## Ethics guardrails (non-negotiable)
- Never predict death, catastrophe, curses
- Never speak in absolutes
- Never use karma as punishment
- Never make the member feel trapped by their chart
- Use hedging: "this may show up as...", "one likely expression is..."
- Balance outer events with inner posture

## Frontend language translation
The app serves a global/Western audience. Never assume Hindu knowledge.
- NOT "tamas is high" → "the pull may be toward numbness or delay"
- NOT "Saturn dasha" → "a season of consolidation"
- NOT "7th house activated" → "relationships are being stirred"

## Member-facing vs internal-only
- **Internal only (short surfaces):** raw graha/bhava mechanics, technical dasha labels, heavy Sanskrit, micro-predictions
- **Sometimes member-facing:** karma, dharma, nakshatra, Jyotish (with context)
- **Acceptable in premium:** grahas, bhavas, dashas, lagna, nakshatra names, yogas

## Free vs Paid boundary
- **Free:** meaningful but distilled, one central signal, limited technical depth
- **Paid:** more personalization, chart precision, richer timing, deeper relational/natal reads

## Red lines (never output)
- Catastrophe/death predictions
- Curse language
- Manipulative scarcity
- "Soulmate certainty" claims
- Deterministic absolutes
- Generic filler that weakens premium feel

## Open decisions (see questions_for_manager.md)
- Platform (iOS only? React Native? SwiftUI?)
- Astrology computation engine (Swiss Ephemeris? API?)
- Knowledge base source (advisor? texts? LLM-only?)
- Auth method
- Free vs paid split
- Content refresh cadence
- Birth time unknown handling

## Development conventions
- When building Supabase schemas, use snake_case for all table and column names
- Use Row Level Security (RLS) on all user-facing tables
- Edge Functions for LLM prompt assembly and astro computation
- Store generated readings with timestamps for cache invalidation
- All dates/times stored in UTC with user timezone offset
- Natal chart data computed once at onboarding, stored permanently
- Transit data refreshed on a schedule (not per-request)
