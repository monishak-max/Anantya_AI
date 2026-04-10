# SDUI Strategy for Now Tab — Generic Section + Card Architecture

## Context

The Now tab renders a birth chart reading. The current JSON is content-only with no layout hints. We need a generic SDUI system where:
- **One section shape** — every section has the same structure
- **One card shape** — every card has the same structure
- **Field presence drives rendering** — if a field is null/absent, that element doesn't render
- **Section order = JSON array order** — backend controls layout, no app updates needed
- **Card count drives scroll behavior** — 0 cards = content only, 1 card = single inline card, 2+ cards = horizontal scroll carousel
- **Card tap → full-screen detail view**

---

## The Two Building Blocks

### Section (the page is just an array of these)

```
┌─────────────────────────────────┐
│ LABEL (small caps)              │  ← optional
│ Title                           │  ← optional
│ Subtitle                        │  ← optional
│ Description paragraph           │  ← optional
│                                 │
│ ┌─────────────────────────────┐ │
│ │ MEDIA                       │ │  ← optional: image URL, Rive asset,
│ │ (image / custom component)  │ │     or custom component (phase bar,
│ └─────────────────────────────┘ │     timeline chart) with component data
│                                 │
│ [Card] [Card] [Card] →          │  ← 0, 1, or N cards
│                                 │     0 = no cards area
│                                 │     1 = single full-width card
│                                 │     2+ = horizontal scroll carousel
└─────────────────────────────────┘
```

### Card (uniform inner layout)

```
┌─────────────────────────────┐
│ ┌─────────────────────────┐ │
│ │ IMAGE (header)          │ │  ← optional
│ └─────────────────────────┘ │
│ ICON 🌙                     │  ← optional (SF Symbol or emoji)
│ Title                       │  ← optional
│ Subtitle                    │  ← optional
│ Description paragraph       │  ← optional (truncated to max_lines)
│                             │
│ • pointer 1                 │  ← optional bullet list
│ • pointer 2                 │
│                             │
│ ── headline label ──        │  ← optional key-value pairs (bold label)
│ headline value text         │
│                             │
│ ── subheadline label ──     │  ← optional secondary key-value pairs
│ subheadline value text      │
│                             │
│ ┌──────────┬──────────┐     │
│ │  left     │  right   │     │  ← optional side-by-side comparisons
│ └──────────┴──────────┘     │
│                             │
│ [CTA Button / Link →]      │  ← optional
└─────────────────────────────┘
```

---

## JSON Schema

### Top Level

```json
{
  "ok": true,
  "birth_chart": {
    "title": "The Strength That Learns Where to Land",
    "model": "claude-opus-4-6+claude-sonnet-4-6",
    "sections": [ ... ]
  }
}
```

### Section

```json
{
  "id": "unique_id",
  "label": "PLANETARY MOVEMENTS",
  "title": "Your Forces",
  "subtitle": "The planets shaping you",
  "description": "Long paragraph...",
  "media": {
    "type": "image | rive | phase_bar | timeline_chart",
    "url": "https://...",
    "data": { ... }
  },
  "cards": [ ... ],
  "max_lines": 4,
  "cta": {
    "text": "See details",
    "action": "see_details"
  }
}
```

All fields optional except `id` and `cards` (which can be empty `[]`).

### Card

```json
{
  "id": "card_id",
  "image": "https://...",
  "icon": "moon.fill",
  "title": "Moon",
  "subtitle": "Your force",
  "description": "This is your fire. You are built to act, to move...",
  "max_lines": 3,
  "pointers": [
    "Less tolerance for what feels off",
    "Pressure to make clearer decisions"
  ],
  "headlines": [
    { "label": "what works", "value": "Challenge, pressure, real stakes" },
    { "label": "what drains", "value": "Routine without purpose" }
  ],
  "subheadlines": [
    { "label": "when blocked", "value": "Your speed becomes reckless..." }
  ],
  "comparisons": [
    { "left": "You are built for movement", "right": "This is not about proving" }
  ],
  "cta": {
    "text": "Read more",
    "action": "detail"
  },
  "detail": {
    "title": "Moon — Your Force",
    "body": "Full sacred capacity text... distortion text... purified expression..."
  }
}
```

All fields optional except `id`.

### Rendering Rules (client-side, no `type` field needed)

| Condition | Behavior |
|-----------|----------|
| `section.label != null` | Render small caps label above title |
| `section.title != null` | Render section title |
| `section.description != null` | Render body text (truncated if `max_lines` set) |
| `section.media != null` | Render image or custom component |
| `section.cards.count == 0` | No card area |
| `section.cards.count == 1` | Single full-width card, no scroll |
| `section.cards.count >= 2` | Horizontal scroll carousel (~85% card width, peek next) |
| `section.cta != null` | Render section-level CTA link |
| `card.image != null` | Show header image |
| `card.icon != null` | Show icon (left of title, or standalone) |
| `card.pointers != null` | Render bullet list |
| `card.headlines != null` | Render bold label:value pairs |
| `card.subheadlines != null` | Render secondary label:value pairs |
| `card.comparisons != null` | Render side-by-side left/right columns |
| `card.cta != null` | Render CTA button/link |
| `card.cta.action == "detail"` | Tap opens full-screen detail sheet using `card.detail` |
| `card.max_lines > 0` | Truncate description with "Read more" |

**This is the entire SDUI contract.** No type enums, no style objects. Just: **if the field exists, render it.**

---

## Complete sections[] Example

```json
{
  "sections": [
    {
      "id": "welcome",
      "title": "I am Anantya",
      "subtitle": "Welcome Seeker",
      "description": "This life came here to turn sacred force into rightful consequence...",
      "max_lines": 4,
      "cta": { "text": "See details", "action": "expand" },
      "cards": []
    },

    {
      "id": "current_phase",
      "label": "YOUR CURRENT PHASE",
      "title": "Forging",
      "media": {
        "type": "phase_bar",
        "data": {
          "current_age": 28,
          "phases": [
            { "name": "emergence", "start": 0, "end": 18 },
            { "name": "forging", "start": 18, "end": 38, "is_current": true },
            { "name": "visibility", "start": 38, "end": 44 },
            { "name": "interior", "start": 44, "end": 54 }
          ]
        }
      },
      "cards": []
    },

    {
      "id": "phase_insight",
      "title": "You are learning how to use your energy cleanly",
      "cards": [{
        "id": "insight_card",
        "pointers": [
          "Less tolerance for what feels off",
          "Pressure to make clearer decisions",
          "Energy feels more expensive than before"
        ],
        "headlines": [
          { "label": "Reactive", "value": "Deliberate" }
        ]
      }]
    },

    {
      "id": "affirmation",
      "description": "Use your energy only where it matters.",
      "cards": []
    },

    {
      "id": "practical_truth",
      "label": "HOW PHASE IMPACTS",
      "title": "Practical Truth",
      "description": "Your life becomes stronger when standards, effort, and inner clarity stop pulling in different directions.",
      "max_lines": 3,
      "cta": { "text": "Read more", "action": "expand" },
      "cards": []
    },

    {
      "id": "work",
      "title": "Work",
      "description": "You are built for movement and consequence. You need work that lets truth to speak.",
      "max_lines": 3,
      "cards": [{
        "id": "work_card",
        "headlines": [
          { "label": "what works", "value": "Challenge, pressure, real stakes" },
          { "label": "what drains", "value": "Dead process, empty credentials, work that uses your strength but never honors it" }
        ],
        "cta": { "text": "Read more", "action": "expand" }
      }]
    },

    {
      "id": "great_yogas",
      "label": "PLANETARY MOVEMENTS",
      "title": "Your Forces",
      "description": "Your life becomes stronger when standards, effort, and inner clarity stop pulling in different directions.",
      "cards": [
        {
          "id": "yoga_moon",
          "icon": "moon.fill",
          "title": "Moon",
          "subtitle": "Your force",
          "description": "This is your fire. You are built to act, to move, to lead.",
          "max_lines": 3,
          "headlines": [
            { "label": "what works", "value": "You are decisive, courageous, and..." }
          ],
          "subheadlines": [
            { "label": "when blocked", "value": "Your speed becomes reckless when..." }
          ],
          "cta": { "text": "Read more", "action": "detail" },
          "detail": {
            "title": "Raja Yoga (Venus)",
            "body": "Venus holds a rare structural position in this chart..."
          }
        },
        {
          "id": "yoga_mars",
          "icon": "flame.fill",
          "title": "Mars",
          "subtitle": "Your drive",
          "description": "...",
          "max_lines": 3,
          "headlines": [{ "label": "what works", "value": "..." }],
          "subheadlines": [{ "label": "when blocked", "value": "..." }],
          "cta": { "text": "Read more", "action": "detail" },
          "detail": { "title": "Raja Yoga (Mars-Venus)", "body": "..." }
        }
      ]
    },

    {
      "id": "timing_currents",
      "label": "DASHA NAVIGATION",
      "title": "Life Trajectory",
      "description": "Your life does not move in a straight line. It rises, bends, and rises again.",
      "media": {
        "type": "timeline_chart",
        "data": {
          "periods": [
            { "name": "Venus", "start_age": 18, "end_age": 38, "is_current": false },
            { "name": "Sun", "start_age": 38, "end_age": 44, "is_current": true },
            { "name": "Moon", "start_age": 44, "end_age": 54, "is_current": false }
          ]
        }
      },
      "cards": []
    },

    {
      "id": "finer_yogas",
      "label": "SHADOW SYSTEM",
      "title": "Your Patterns",
      "cards": [
        {
          "id": "pattern_instability",
          "title": "Instability",
          "description": "When things feel uncertain, you move faster.",
          "max_lines": 3,
          "headlines": [
            { "label": "what you do", "value": "..." },
            { "label": "what is happening", "value": "..." }
          ],
          "subheadlines": [
            { "label": "what it costs", "value": "..." },
            { "label": "what changes it", "value": "..." }
          ],
          "cta": { "text": "Read more", "action": "detail" },
          "detail": { "title": "Dhana Yoga (2nd-11th)", "body": "..." }
        },
        {
          "id": "pattern_dissolution",
          "title": "Dissolution",
          "description": "...",
          "max_lines": 3,
          "cta": { "text": "Read more", "action": "detail" },
          "detail": { "title": "Sunapha Yoga", "body": "..." }
        }
      ]
    },

    {
      "id": "closing",
      "description": "You are not here to become less intense. You are here to become more deliberate...",
      "cards": []
    }
  ]
}
```

---

## SwiftUI Architecture

### Models (`BirthChartReading.swift`)

```swift
struct BirthChartReading: Codable {
    let ok: Bool
    let birthChart: BirthChartContent
    enum CodingKeys: String, CodingKey {
        case ok
        case birthChart = "birth_chart"
    }
}

struct BirthChartContent: Codable {
    let title: String
    let model: String
    let sections: [Section]
}

struct Section: Codable, Identifiable {
    let id: String
    let label: String?
    let title: String?
    let subtitle: String?
    let description: String?
    let media: Media?
    let cards: [Card]
    let maxLines: Int?
    let cta: CTA?
    enum CodingKeys: String, CodingKey {
        case id, label, title, subtitle, description, media, cards, cta
        case maxLines = "max_lines"
    }
}

struct Card: Codable, Identifiable {
    let id: String
    let image: String?
    let icon: String?
    let title: String?
    let subtitle: String?
    let description: String?
    let maxLines: Int?
    let pointers: [String]?
    let headlines: [LabelValue]?
    let subheadlines: [LabelValue]?
    let comparisons: [Comparison]?
    let cta: CTA?
    let detail: CardDetail?
    enum CodingKeys: String, CodingKey {
        case id, image, icon, title, subtitle, description, pointers
        case headlines, subheadlines, comparisons, cta, detail
        case maxLines = "max_lines"
    }
}

struct Media: Codable {
    let type: String
    let url: String?
    let data: AnyCodable?
}

struct LabelValue: Codable, Identifiable {
    var id: String { label }
    let label: String
    let value: String
}

struct Comparison: Codable, Identifiable {
    var id: String { left }
    let left: String
    let right: String
}

struct CTA: Codable {
    let text: String
    let action: String
}

struct CardDetail: Codable {
    let title: String?
    let body: String
}
```

### Views

**NowView.swift** — page compositor:
```swift
struct NowView: View {
    @StateObject var viewModel = NowViewModel()
    var body: some View {
        ScrollView {
            LazyVStack(spacing: DesignSystem.Layout.sectionSpacing) {
                UserHeaderView()
                BirthChartRiveView()
                ForEach(viewModel.reading?.birthChart.sections ?? []) { section in
                    SectionView(section: section)
                }
            }
        }
        .anantyaBackground()
    }
}
```

**SectionView.swift** — ONE generic section renderer:
```swift
struct SectionView: View {
    let section: Section
    @State private var isExpanded = false
    var body: some View {
        VStack(alignment: .leading, spacing: DesignSystem.Layout.itemSpacing) {
            if let label = section.label {
                Text(label)
                    .font(.quicksand(size: DesignSystem.FontSize.caption, weight: .semibold))
                    .foregroundColor(DesignSystem.Colors.tertiary)
                    .tracking(1.5)
            }
            if let title = section.title {
                Text(title)
                    .font(.moranga(size: DesignSystem.FontSize.title, weight: .bold))
                    .foregroundColor(DesignSystem.Colors.primary)
            }
            if let subtitle = section.subtitle {
                Text(subtitle)
                    .font(.quicksand(size: DesignSystem.FontSize.subheadline))
                    .foregroundColor(DesignSystem.Colors.secondary)
            }
            if let description = section.description {
                ExpandableText(text: description, maxLines: section.maxLines, isExpanded: $isExpanded)
            }
            if let media = section.media {
                MediaView(media: media)
            }
            if section.cards.count == 1 {
                CardView(card: section.cards[0])
            } else if section.cards.count >= 2 {
                CardCarousel(cards: section.cards)
            }
            if let cta = section.cta, cta.action == "expand" {
                Button(cta.text) { isExpanded.toggle() }
                    .font(.quicksand(size: DesignSystem.FontSize.footnote, weight: .semibold))
                    .foregroundColor(DesignSystem.Colors.secondary)
            }
        }
        .screenPadding()
    }
}
```

**CardView.swift** — ONE generic card renderer:
```swift
struct CardView: View {
    let card: Card
    @State private var isExpanded = false
    @State private var showDetail = false
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let image = card.image {
                AsyncImage(url: URL(string: image)) { phase in ... }
                    .frame(height: 160)
                    .clipShape(RoundedRectangle(cornerRadius: DesignSystem.Radius.medium))
            }
            if let icon = card.icon {
                Image(systemName: icon).font(.system(size: 24)).foregroundColor(DesignSystem.Colors.secondary)
            }
            if let title = card.title {
                Text(title).font(.moranga(size: DesignSystem.FontSize.title3, weight: .semibold))
            }
            if let subtitle = card.subtitle {
                Text(subtitle).font(.quicksand(size: DesignSystem.FontSize.footnote)).foregroundColor(DesignSystem.Colors.tertiary)
            }
            if let desc = card.description {
                ExpandableText(text: desc, maxLines: card.maxLines, isExpanded: $isExpanded)
            }
            if let pointers = card.pointers {
                ForEach(pointers, id: \.self) { point in
                    HStack(alignment: .top, spacing: 8) { Text("•"); Text(point) }
                        .font(.quicksand(size: DesignSystem.FontSize.body))
                        .foregroundColor(DesignSystem.Colors.secondary)
                }
            }
            if let headlines = card.headlines {
                ForEach(headlines) { pair in LabelValueView(pair: pair, isBold: true) }
            }
            if let subheadlines = card.subheadlines {
                ForEach(subheadlines) { pair in LabelValueView(pair: pair, isBold: false) }
            }
            if let comparisons = card.comparisons {
                HStack(alignment: .top, spacing: 12) {
                    ForEach(comparisons) { comp in
                        VStack(alignment: .leading) { Text(comp.left); Text(comp.right) }.frame(maxWidth: .infinity)
                    }
                }
            }
            if let cta = card.cta {
                Button(cta.text) {
                    if cta.action == "detail" { showDetail = true }
                    else if cta.action == "expand" { isExpanded.toggle() }
                }.font(.quicksand(size: DesignSystem.FontSize.footnote, weight: .semibold))
            }
        }
        .padding(DesignSystem.Layout.itemSpacing)
        .background(DesignSystem.Colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: DesignSystem.Radius.medium))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 4)
        .fullScreenCover(isPresented: $showDetail) {
            if let detail = card.detail { CardDetailSheet(detail: detail) }
        }
    }
}
```

**CardCarousel.swift** — horizontal scroll:
```swift
struct CardCarousel: View {
    let cards: [Card]
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            LazyHStack(spacing: DesignSystem.Layout.itemSpacing) {
                ForEach(cards) { card in
                    CardView(card: card).frame(width: UIScreen.main.bounds.width * 0.85)
                }
            }
            .scrollTargetLayout()
        }
        .scrollTargetBehavior(.viewAligned)
    }
}
```

**MediaView.swift** — the only type switch:
```swift
struct MediaView: View {
    let media: Media
    var body: some View {
        switch media.type {
        case "image":     AsyncImage(url: URL(string: media.url ?? "")) { phase in ... }
        case "rive":      RiveViewModel(fileName: media.url ?? "").view()
        case "phase_bar": PhaseBarView(data: media.data)
        case "timeline_chart": TimelineChartView(data: media.data)
        default: EmptyView()
        }
    }
}
```

### Component Summary

| Component | Purpose |
|-----------|---------|
| `SectionView` | Generic section renderer |
| `CardView` | Generic card renderer |
| `CardCarousel` | Horizontal scroll wrapper for 2+ cards |
| `ExpandableText` | Truncate to max_lines + "Read more" |
| `LabelValueView` | Label:value pair rendering |
| `ComparisonView` | Side-by-side left/right columns |
| `MediaView` | Type switch for image/rive/custom |
| `CardDetailSheet` | Full-screen detail on card tap |
| `PhaseBarView` | Custom: age progress bar |
| `TimelineChartView` | Custom: dasha timeline |

**10 components for the entire Now tab.**

---

## Files to Create

### iOS (`anantya-ios/Anantya/`)
- `Models/BirthChartReading.swift`
- `Views/BirthChart/SectionView.swift`
- `Views/BirthChart/CardView.swift`
- `Views/BirthChart/CardCarousel.swift`
- `Views/BirthChart/CardDetailSheet.swift`
- `Views/BirthChart/MediaView.swift`
- `Components/Cards/ExpandableText.swift`
- `Components/Cards/LabelValueView.swift`
- `Components/Charts/PhaseBarView.swift`
- `Components/Charts/TimelineChartView.swift`
- `ViewModels/NowViewModel.swift`

### Modified
- `Views/Main/NowView.swift`

### Backend (`Anantya_AI-main/`)
- See `SDUI_BACKEND_CHANGES.md` for complete backend changes

---

## Key Answers

| Question | How the Generic System Handles It |
|----------|----------------------------------|
| **Horizontal scroll or single card?** | `cards.count`: 0=none, 1=single, 2+=horizontal scroll |
| **Image in card header on/off?** | `card.image` present → show, null → hide |
| **Icon on/off?** | `card.icon` present → show, null → hide |
| **Pointers appear or not?** | `card.pointers` present → show, null → skip |
| **Section ordering?** | Array index in `sections[]` — backend controls |
| **Expandable text?** | `max_lines` present → truncate + "Read more", null → show all |
| **Custom component?** | `section.media.type` — the ONLY type switch |
| **Card tap behavior?** | `card.cta.action == "detail"` → full-screen sheet |
