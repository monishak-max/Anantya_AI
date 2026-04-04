# Anantya API Reference -- iOS Integration Guide

## Base URL
```
Dev/Staging: https://peppery-frieda-pseudozealously.ngrok-free.dev
```

All endpoints accept `POST` with `Content-Type: application/json`.
All responses return `{"ok": true, ...data}` on success or `{"ok": false, "error": "message"}` on failure.

---

## Common Request Fields (all endpoints)

Every endpoint that generates content requires the member's birth data:

```json
{
  "name": "Dhairya",
  "birth_date": "1998-01-15",
  "birth_time": "10:30",
  "lat": 19.076,
  "lng": 72.878
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Member's first name |
| `birth_date` | string | Yes | ISO format: `YYYY-MM-DD` |
| `birth_time` | string | Yes | 24h format: `HH:MM`. Use `"12:00"` if unknown |
| `lat` | float | Yes | Birth location latitude |
| `lng` | float | Yes | Birth location longitude |
| `external_modifiers` | array | No | Optional: remedies, gemstones, life stage context |

---

## App Flow & Screens

### Onboarding Flow
```
1. Enter name
2. Enter birth date
3. Enter birth time (or "I'm not sure" -> defaults to noon)
4. Enter birth place (autocomplete -> lat/lng)
5. Compute chart -> Show Chart Reveal
```

### Main App Tabs
```
Tab 1: NOW      -> Daily insight (collapsed card + dive deeper)
Tab 2: MANDALA  -> Natal chart wheel + activation cards (tap for deep read)
Tab 3: UNION    -> Relationship compatibility
Tab 4: PROFILE  -> Birth chart (sacred study) + weekly/monthly overviews
```

---

## Endpoints

### 1. `POST /api/chart` -- Compute Chart (no LLM)

**When to call:** After onboarding, before anything else. Returns raw chart data for the profile screen.

**Response time:** < 1 second (no LLM, pure computation)

**Request:**
```json
{
  "name": "Dhairya",
  "birth_date": "1998-01-15",
  "birth_time": "10:30",
  "lat": 19.076,
  "lng": 72.878
}
```

**Response:**
```json
{
  "ok": true,
  "chart": {
    "name": "Dhairya",
    "lagna_sign": "Aquarius",
    "moon": {
      "sign": "Cancer",
      "degree": 29.79,
      "nakshatra": "Ashlesha",
      "pada": 4
    },
    "dasha": {
      "mahadasha": "Sun",
      "antardasha": "Mars",
      "maha_start": "2025-04-20",
      "maha_end": "2031-04-21"
    },
    "today_moon": {
      "sign": "Pisces",
      "nakshatra": "Uttara Bhadrapada",
      "house_from_natal": 9
    },
    "planets": {
      "Sun": { "sign": "Capricorn", "degree": 1.01, "nakshatra": "Uttara Ashadha", "house": 7, "retrograde": false, "navamsha_sign": "Capricorn" },
      "Moon": { "sign": "Cancer", "degree": 29.79, "nakshatra": "Ashlesha", "house": 1, "retrograde": false, "navamsha_sign": "Pisces" },
      "Mars": { "sign": "Capricorn", "degree": 28.14, "nakshatra": "Dhanishta", "house": 7, "retrograde": false, "navamsha_sign": "Virgo" },
      "Mercury": { "sign": "Sagittarius", "degree": 9.4, "nakshatra": "Mula", "house": 6, "retrograde": false, "navamsha_sign": "Gemini" },
      "Jupiter": { "sign": "Aquarius", "degree": 1.49, "nakshatra": "Dhanishta", "house": 8, "retrograde": false, "navamsha_sign": "Libra" },
      "Venus": { "sign": "Capricorn", "degree": 3.07, "nakshatra": "Uttara Ashadha", "house": 7, "retrograde": false, "navamsha_sign": "Capricorn" },
      "Saturn": { "sign": "Pisces", "degree": 20.51, "nakshatra": "Revati", "house": 9, "retrograde": false, "navamsha_sign": "Capricorn" },
      "Rahu": { "sign": "Leo", "degree": 19.15, "nakshatra": "Purva Phalguni", "house": 2, "retrograde": false, "navamsha_sign": "Virgo" },
      "Ketu": { "sign": "Aquarius", "degree": 19.15, "nakshatra": "Shatabhisha", "house": 8, "retrograde": false, "navamsha_sign": "Pisces" }
    }
  }
}
```

**iOS usage:** Call once at onboarding. Cache the response locally. Use `chart.moon.sign`, `chart.lagna_sign`, `chart.planets` to populate the profile header and zodiac wheel.

---

### 2. `POST /api/chart-reveal` -- First Content Member Sees

**When to call:** Immediately after chart computation. This is the onboarding "wow" moment.

**Response time:** 3-6 seconds (Sonnet)

**Response:**
```json
{
  "ok": true,
  "reveal": {
    "headline": "A mind built for distance and depth, carrying more feeling than most people ever see",
    "traits": [
      "You protect people quietly, long before they ask for it",
      "Your standards are high and mostly unspoken, which confuses people",
      "You hold a lot beneath the surface and call it composure"
    ],
    "soul_line": "This life came to build something real from the inside out."
  },
  "model": "claude-sonnet-4-6"
}
```

**iOS usage:** Show as the first screen after onboarding. Headline at top, 3 traits as a list, soul_line near the birth date. This builds trust.

---

### 3. `POST /api/now` -- Daily Insight (Now Tab)

**When to call:** Every time the member opens the app. Returns both collapsed card and expanded view.

**Response time:** 8-15 seconds (2 Haiku calls: collapsed + expanded)

**Response:**
```json
{
  "ok": true,
  "collapsed": {
    "astro_signature": "April 4 . 10 Pisces",
    "headline": "What you value is asking to be named today.",
    "support_text": "Something you have been circling is ready to surface. Trust what rises.",
    "do_today": "Name one thing you actually want.",
    "reflection": "What would shift if you stopped managing and started choosing?"
  },
  "expanded": {
    "astro_signature": "April 4 . Moon in Pisces - 10.2",
    "opening_paragraph": "Today carries a contemplative pull toward meaning...",
    "what_this_means_body": "Your sense of direction is being stirred...",
    "resistance_body": "You might try to think your way out of what you are feeling...",
    "guidance_body": "Sit with one question that matters. Not to solve it. Just to let it breathe.",
    "closing_anchor": "What you are reaching for is real."
  },
  "model": "claude-haiku-4-5-20251001"
}
```

**iOS usage:**
- Show `collapsed` as the main card on the Now tab
- "Dive Deeper" button opens a sheet/modal with `expanded` content
- Refresh daily (cache for 24h per member)

---

### 4. `POST /api/mandala` -- Activation Cards (Mandala Tab)

**When to call:** When member taps the Mandala tab. Shows what transits are currently active.

**Response time:** 10-18 seconds (Sonnet)

**Response:**
```json
{
  "ok": true,
  "cards": [
    {
      "activation_marker": "Jupiter in 1st . exact on natal Moon",
      "card_title": "A new chapter is opening directly through you",
      "card_body": "Jupiter is sitting right where your Moon lives. This is rare and personal. Something is expanding from the inside out.",
      "cta": "Explore this further"
    },
    {
      "activation_marker": "Saturn in 2nd . 11 months",
      "card_title": "Your voice and values are being restructured",
      "card_body": "What you say, what you earn, and what you stand for are all being tested. The pressure is real but the clarity that follows will be permanent.",
      "cta": "Explore this further"
    }
  ],
  "model": "claude-sonnet-4-6"
}
```

**iOS usage:**
- Show zodiac wheel at top (from `/api/chart` data)
- Cards stacked below the wheel (3-7 cards)
- Each card's "Explore this further" calls `/api/mandala-deep`

---

### 5. `POST /api/mandala-deep` -- Deep Read on One Card

**When to call:** When member taps "Explore this further" on a mandala card.

**Response time:** 8-15 seconds (Sonnet)

**Additional field:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `activation_planet` | string | No | Planet name from the card (e.g. "Jupiter", "Saturn"). Defaults to "Saturn" |

**Response:**
```json
{
  "ok": true,
  "deep_read": {
    "title": "The expansion that begins from within",
    "activation_summary": "Jupiter is sitting exactly on your natal Moon...",
    "life_area_section": "This lands in the most personal territory...",
    "inner_expression_section": "You may feel a quiet optimism...",
    "guidance_section": "Let yourself believe in what is opening. Do not shrink it with caution.",
    "time_note": "This influence is active for the next 3 months."
  },
  "model": "claude-sonnet-4-6"
}
```

**iOS usage:** Show as a slide-up sheet or full-screen detail view when card is tapped.

---

### 6. `POST /api/union` -- Compatibility Snapshot (Union Tab)

**When to call:** When member enters partner details on the Union tab.

**Response time:** 5-10 seconds (Sonnet)

**Additional fields:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `partner_name` | string | Yes | Partner's first name |
| `partner_birth_date` | string | Yes | ISO format |
| `partner_birth_time` | string | Yes | 24h format |
| `partner_lat` | float | Yes | Partner birth latitude |
| `partner_lng` | float | Yes | Partner birth longitude |

**Response:**
```json
{
  "ok": true,
  "union": {
    "bond_summary": "Two people who protect each other in ways that are rarely spoken aloud.",
    "emotional_dynamic": "The emotional rhythm between you moves between steady warmth and charged silence...",
    "support_line": "What flows naturally: shared ambition, mutual respect for privacy, and quiet loyalty.",
    "friction_line": "Where awareness deepens: different speeds of emotional processing and different thresholds for vulnerability.",
    "invitation": "Explore the full compatibility reading"
  },
  "model": "claude-sonnet-4-6"
}
```

---

### 7. `POST /api/union-deep` -- Premium Compatibility (Union Deep Read)

**When to call:** Premium feature. Full relationship reading.

**Response time:** 30-60 seconds (Opus)

**Same additional fields as `/api/union`.**

**Response:**
```json
{
  "ok": true,
  "union_deep": {
    "overall_dynamic": "...",
    "emotional_rhythm": "...",
    "communication_pattern": "...",
    "affection_and_attraction": "...",
    "values_and_path_alignment": "...",
    "friction_zones": "...",
    "karmic_lesson": "...",
    "growth_potential": "...",
    "closing_guidance": "..."
  },
  "model": "claude-opus-4-6"
}
```

---

### 8. `POST /api/birth-chart` -- Sacred Life Study (Premium)

**When to call:** Premium feature. The crown jewel. One-time generation per member.

**Response time:** 60-120 seconds (Opus). Show a meaningful loading state.

**Response:**
```json
{
  "ok": true,
  "birth_chart": {
    "title": "The Refiner Who Came to Build",
    "opening_promise": "You came here to turn intelligence into consequence...",
    "entrusted_beauty": "Before any difficulty is named, this must be said: you carry a rare combination...",
    "central_knot": "The knot is this: you keep giving your sacred force to what no longer deserves it...",
    "great_yogas": [
      {
        "name": "Raja Yoga through Jupiter",
        "subtitle": "authority earned through wisdom",
        "sacred_capacity": "Jupiter rules both kendra and trikona, giving this life genuine potential for rise...",
        "distortion": "Can become over-identified with being the responsible one...",
        "purified_expression": "Ripens into leadership that serves truth, not just duty."
      }
    ],
    "finer_yogas": [ ... ],
    "deeper_shaping_forces": [ ... ],
    "great_timing_currents": [
      {
        "name": "Venus Mahadasha (2005-2025)",
        "subtitle": "twenty years of learning what beauty really costs",
        "chapter_body": "The last twenty years were shaped by Venus..."
      }
    ],
    "life_phases": [
      {
        "title": "Early life and formation",
        "age_range": "0-18",
        "body": "The earliest years were shaped by..."
      }
    ],
    "present_threshold": "Right now, you are being asked whether you can let what is good actually land...",
    "love": "Love in this life is not simple...",
    "work": "Work in this life has always been about proving you can endure...",
    "embodiment": "When this life ripens fully, the refiner becomes the builder...",
    "closing_destiny": "You were not given this much intelligence just to keep things running for others..."
  },
  "model": "claude-opus-4-6"
}
```

**iOS usage:**
- Generate once, cache permanently (birth chart never changes)
- Show as a scrollable long-form reading with distinct sections
- Design as a "sacred editorial object" -- spacing, hierarchy, visual calm
- Loading state should feel intentional: "Anantya is studying your chart..."

---

### 9. `POST /api/weekly-overview` -- Weekly Compass

**When to call:** Once per week (cache for 7 days).

**Response time:** 10-18 seconds (Sonnet)

**Response:**
```json
{
  "ok": true,
  "weekly": {
    "opening_summary": "This week carries a theme of recalibration...",
    "main_themes": "Two dominant currents are moving: career visibility and inner questioning...",
    "work_and_purpose": "Work asks for direct action early in the week...",
    "relationships": "Relationships benefit from honesty over harmony this week...",
    "inner_state": "You may feel pulled between expansion and caution...",
    "timing_note": "Wednesday and Thursday carry the most consequential energy.",
    "guidance": "Move toward what is true, not what is comfortable."
  },
  "model": "claude-sonnet-4-6"
}
```

---

### 10. `POST /api/monthly-overview` -- Monthly Arc

**When to call:** Once per month (cache for 30 days).

**Response time:** 10-18 seconds (Sonnet)

**Response:**
```json
{
  "ok": true,
  "monthly": {
    "opening_summary": "April opens with a question about authority...",
    "main_themes": "The month is shaped by three currents...",
    "work_and_purpose": "Career momentum builds in the first two weeks...",
    "relationships": "Relationships ask for more honesty this month...",
    "inner_state": "Internally, this month carries weight but also clarity...",
    "timing_notes": "April 8-12: strongest window for decisions. April 20-23: rest and reflection.",
    "guidance": "Build from what is true. Release what you are maintaining out of loyalty alone."
  },
  "model": "claude-sonnet-4-6"
}
```

---

### 11. `GET /api/geocode?q=Mumbai` -- Place Autocomplete

**When to call:** During onboarding as the member types birth place.

**Response time:** < 1 second

**Response:**
```json
{
  "ok": true,
  "results": [
    { "display": "Mumbai, Maharashtra, India", "lat": "19.0759837", "lng": "72.8776559" },
    { "display": "Mumbai Suburban, Maharashtra, India", "lat": "19.1", "lng": "72.9" }
  ]
}
```

---

## Screen-to-API Mapping

| Screen | API Calls | Cache Strategy |
|--------|-----------|---------------|
| **Onboarding** | `/api/geocode` (typing) -> `/api/chart` (submit) -> `/api/chart-reveal` | Chart: permanent. Reveal: permanent. |
| **Now Tab (open)** | `/api/now` | 24 hours |
| **Now Tab (dive deeper)** | Already in `/api/now` response | Same as above |
| **Mandala Tab** | `/api/mandala` | 24 hours |
| **Mandala (tap card)** | `/api/mandala-deep` | 24 hours per card |
| **Union Tab (enter partner)** | `/api/union` | Per partner, permanent |
| **Union (deep read)** | `/api/union-deep` | Per partner, permanent |
| **Profile (birth chart)** | `/api/birth-chart` | Permanent (generate once) |
| **Profile (weekly)** | `/api/weekly-overview` | 7 days |
| **Profile (monthly)** | `/api/monthly-overview` | 30 days |

---

## Model Routing & Response Times

| Surface | Model | Tier | Typical Time | Cost/call |
|---------|-------|------|-------------|-----------|
| Chart compute | None (DE440) | -- | < 1s | $0 |
| Chart Reveal | Sonnet | Standard | 3-6s | $0.02 |
| Now Collapsed | Haiku | Daily | 3-5s | $0.005 |
| Now Expanded | Haiku | Daily | 5-8s | $0.007 |
| Mandala Cards | Sonnet | Standard | 10-18s | $0.03 |
| Mandala Deep | Sonnet | Standard | 8-15s | $0.02 |
| Union Snapshot | Sonnet | Standard | 5-10s | $0.02 |
| Union Deep | Opus | Premium | 30-60s | $0.18 |
| Birth Chart | Opus | Premium | 60-120s | $0.90 |
| Weekly | Sonnet | Standard | 10-18s | $0.03 |
| Monthly | Sonnet | Standard | 10-18s | $0.03 |
| Geocode | None (OSM) | -- | < 1s | $0 |

---

## Error Handling for iOS

All errors return `{"ok": false, "error": "message"}` with appropriate HTTP status codes.

| Status | Meaning | iOS Action |
|--------|---------|-----------|
| 200 | Success | Parse response |
| 500 | Server error | Show "Something went wrong. Try again." |
| 503 | Opus overloaded | Show "Your reading is being prepared. Please try again in a minute." + retry button |
| 504 | Timeout (birth chart) | Show "Your sacred study takes deep computation. Please wait..." + auto-retry |

**Important for birth chart:** Set iOS URLSession timeout to at least 180 seconds. The sacred study can take 60-120s on Opus. Show a meaningful loading state, not a spinner.

---

## Profile Preview (what shows before any LLM call)

The profile screen can be populated immediately from `/api/chart` (no LLM needed):

```
Profile Header:
  Name: Dhairya
  Sun: Capricorn
  Moon: Cancer
  Rising: Aquarius
  Born: January 15, 1998

Current Period:
  Mahadasha: Sun (2025-2031)
  Antardasha: Mars

Today's Moon:
  Sign: Pisces
  Nakshatra: Uttara Bhadrapada
  House from natal: 9th

Planet Positions: (for zodiac wheel)
  Sun: Capricorn 1.01
  Moon: Cancer 29.79
  Mars: Capricorn 28.14
  ...etc
```

This data is instant (no LLM). The birth chart reading, weekly, and monthly are generated on demand when the member scrolls down or taps those sections.


