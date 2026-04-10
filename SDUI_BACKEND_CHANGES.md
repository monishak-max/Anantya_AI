# SDUI Backend Changes — Anantya_AI-main

## Current Architecture

The backend is **Python/Flask** with a 3+1 parallel AI architecture:
- **Phase 1** (3x Sonnet parallel): `birth_chart_yogas`, `birth_chart_forces`, `birth_chart_timing`
- **Phase 2** (1x Opus sequential): `birth_chart_synthesis` (narrative wrapper)
- **Merge**: `pipeline.py::_merge_birth_chart_sections()` → flat dict (line 389)
- **Return**: `web/app.py` line 183 → `jsonify({"ok": True, "birth_chart": result.data, "model": result.model})`

### Key Files

| File | Purpose |
|------|---------|
| `Anantya_AI-main/llm/schemas/surfaces.py` | Pydantic models: `BirthChartCore`, `StudyForce`, `TimingCurrent`, `LifePhase`, section schemas |
| `Anantya_AI-main/llm/pipeline.py` | `_merge_birth_chart_sections()` at line 389, `generate_birth_chart()` at line 227 |
| `Anantya_AI-main/web/app.py` | `/api/birth-chart` endpoint at line 171 |
| `Anantya_AI-main/llm/schemas/inputs.py` | `BirthChartInput`, `BirthChartSynthesisInput`, etc. |
| `Anantya_AI-main/llm/prompts/assembler.py` | `assemble_prompt()` + `build_schema_instruction()` |
| `Anantya_AI-main/1.0/prompts/features/birth_chart_synthesis.txt` | Synthesis prompt (narrative) |
| `Anantya_AI-main/1.0/prompts/features/birth_chart_yogas.txt` | Yogas prompt |
| `Anantya_AI-main/1.0/prompts/features/birth_chart_forces.txt` | Forces prompt |

---

## Changes Required

### 1. New File: `llm/sdui.py` — Section Builder

Transforms the merged flat birth chart dict into an ordered `sections[]` array.

```python
"""
SDUI section builder — transforms flat birth chart dict into sections[] array.
Pure transformation, no AI calls, no latency cost.
"""
from datetime import date


def calculate_age(birth_date_str: str) -> int:
    """Calculate age from ISO date string."""
    birth = date.fromisoformat(birth_date_str)
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def build_phase_bar(life_phases: list[dict], user_age: int) -> dict:
    """Build phase_bar media object from life_phases + user age."""
    phases = []
    for phase in life_phases:
        parts = phase.get("age_range", "0-0").split("-")
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 else start + 10
        phases.append({
            "name": phase.get("title", "").lower(),
            "start": start,
            "end": end,
            "is_current": start <= user_age <= end,
        })
    return {
        "type": "phase_bar",
        "data": {"current_age": user_age, "phases": phases},
    }


def build_timeline_data(timing_currents: list[dict], life_phases: list[dict]) -> dict:
    """Build timeline_chart media object from timing currents."""
    periods = []
    for tc in timing_currents:
        # Try to extract age range from life phases matching this period
        periods.append({
            "name": tc.get("name", ""),
            "subtitle": tc.get("subtitle", ""),
            "is_current": False,  # TODO: derive from user's current dasha
        })
    return {
        "type": "timeline_chart",
        "data": {"periods": periods},
    }


def build_yoga_cards(yogas: list[dict], prefix: str) -> list[dict]:
    """Transform StudyForce items into SDUI card objects."""
    cards = []
    for i, yoga in enumerate(yogas):
        card = {
            "id": f"{prefix}_{i}",
            "title": yoga.get("card_title") or yoga.get("name", ""),
            "subtitle": yoga.get("subtitle", ""),
            "description": yoga.get("card_description") or _truncate(yoga.get("sacred_capacity", ""), 60),
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "detail"},
            "detail": {
                "title": yoga.get("name", ""),
                "body": _join_prose(
                    yoga.get("sacred_capacity", ""),
                    yoga.get("distortion", ""),
                    yoga.get("purified_expression", ""),
                ),
            },
        }

        # Structured details if AI generated them
        if yoga.get("details"):
            card["headlines"] = [
                {"label": d["label"], "value": d["value"]}
                for d in yoga["details"][:2]
            ]
            card["subheadlines"] = [
                {"label": d["label"], "value": d["value"]}
                for d in yoga["details"][2:]
            ]
        else:
            # Fallback: map existing prose fields to headlines
            if yoga.get("distortion"):
                card["headlines"] = [{"label": "when distorted", "value": _truncate(yoga["distortion"], 40)}]
            if yoga.get("purified_expression"):
                card["subheadlines"] = [{"label": "when purified", "value": _truncate(yoga["purified_expression"], 40)}]

        # Comparisons (if AI generated them)
        if yoga.get("comparisons"):
            card["comparisons"] = yoga["comparisons"]

        cards.append(card)
    return cards


def build_sdui_sections(data: dict, user_age: int) -> list[dict]:
    """
    Transform flat birth chart dict into ordered sections[] array.
    This is the main entry point — called from web/app.py after merge.
    """
    sections = []

    # 1. Hero / Welcome
    sections.append({
        "id": "welcome",
        "title": "I am Anantya",
        "subtitle": "Welcome Seeker",
        "description": data.get("opening_promise", ""),
        "max_lines": 4,
        "cta": {"text": "See details", "action": "expand"},
        "cards": [],
    })

    # 2. Current Phase (progress bar)
    life_phases = data.get("life_phases", [])
    current_phase = next(
        (p for p in life_phases if _is_current_phase(p, user_age)),
        life_phases[0] if life_phases else {"title": "Unknown"},
    )
    sections.append({
        "id": "current_phase",
        "label": "YOUR CURRENT PHASE",
        "title": current_phase.get("title", ""),
        "media": build_phase_bar(life_phases, user_age),
        "cards": [],
    })

    # 3. Phase Insight (if AI generated insights)
    if data.get("insights"):
        insight_card = {
            "id": "insight_card",
            "pointers": data["insights"],
        }
        if data.get("polarity_left") and data.get("polarity_right"):
            insight_card["headlines"] = [
                {"label": data["polarity_left"], "value": data["polarity_right"]}
            ]
        sections.append({
            "id": "phase_insight",
            "title": data.get("phase_insight_title", "What you are learning now"),
            "cards": [insight_card],
        })

    # 4. Affirmation (if AI generated it)
    if data.get("affirmation"):
        sections.append({
            "id": "affirmation",
            "description": data["affirmation"],
            "cards": [],
        })

    # 5. Entrusted Beauty
    if data.get("entrusted_beauty"):
        sections.append({
            "id": "entrusted_beauty",
            "title": "Entrusted Beauty",
            "description": data["entrusted_beauty"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 6. Central Knot
    if data.get("central_knot"):
        sections.append({
            "id": "central_knot",
            "title": "Central Knot",
            "description": data["central_knot"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 7. Present Threshold
    if data.get("present_threshold"):
        sections.append({
            "id": "present_threshold",
            "title": "Present Threshold",
            "description": data["present_threshold"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 8. Deeper Shaping Forces (HOW PHASE IMPACTS)
    forces = data.get("deeper_shaping_forces", [])
    if forces:
        sections.append({
            "id": "deeper_forces",
            "label": "HOW PHASE IMPACTS",
            "title": "Your Shaping Forces",
            "cards": build_yoga_cards(forces, "force"),
        })

    # 9. Love
    if data.get("love"):
        sections.append({
            "id": "love",
            "title": "Love",
            "description": data["love"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 10. Work
    if data.get("work"):
        sections.append({
            "id": "work",
            "title": "Work",
            "description": data["work"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 11. Great Yogas (PLANETARY MOVEMENTS carousel)
    yogas = data.get("great_yogas", [])
    if yogas:
        sections.append({
            "id": "great_yogas",
            "label": "PLANETARY MOVEMENTS",
            "title": "Your Forces",
            "cards": build_yoga_cards(yogas, "yoga"),
        })

    # 12. Great Timing Currents (DASHA NAVIGATION timeline)
    timing = data.get("great_timing_currents", [])
    if timing:
        sections.append({
            "id": "timing_currents",
            "label": "DASHA NAVIGATION",
            "title": "Life Trajectory",
            "description": "Your life does not move in a straight line. It rises, bends, and rises again.",
            "media": build_timeline_data(timing, life_phases),
            "cards": [],
        })

    # 13. Finer Yogas (SHADOW SYSTEM carousel)
    finer = data.get("finer_yogas", [])
    if finer:
        sections.append({
            "id": "finer_yogas",
            "label": "SHADOW SYSTEM",
            "title": "Your Patterns",
            "cards": build_yoga_cards(finer, "pattern"),
        })

    # 14. Embodiment
    if data.get("embodiment"):
        sections.append({
            "id": "embodiment",
            "title": "Embodiment",
            "description": data["embodiment"],
            "max_lines": 3,
            "cta": {"text": "Read more", "action": "expand"},
            "cards": [],
        })

    # 15. Closing
    if data.get("closing_destiny"):
        sections.append({
            "id": "closing",
            "description": data["closing_destiny"],
            "cards": [],
        })

    return sections


# ── Helpers ─────────────────────────────────────────────────────

def _truncate(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _join_prose(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def _is_current_phase(phase: dict, user_age: int) -> bool:
    parts = phase.get("age_range", "0-0").split("-")
    start = int(parts[0])
    end = int(parts[1]) if len(parts) > 1 else start + 10
    return start <= user_age <= end
```

---

### 2. Modify: `web/app.py` — Endpoint Change

**File**: `Anantya_AI-main/web/app.py`
**Line**: 171-186

```python
# BEFORE (line 183):
return jsonify({"ok": True, "birth_chart": result.data, "model": result.model})

# AFTER:
from llm.sdui import build_sdui_sections, calculate_age

@app.route("/api/birth-chart", methods=["POST"])
def generate_birth_chart():
    try:
        data = request.json
        result = pipeline.generate_birth_chart(
            name=data["name"],
            birth_date=date.fromisoformat(data["birth_date"]),
            birth_time=data["birth_time"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            external_modifiers=_modifiers(data),
        )
        user_age = calculate_age(data["birth_date"])
        sections = build_sdui_sections(result.data, user_age)
        return jsonify({
            "ok": True,
            "birth_chart": {
                "title": result.data.get("title", ""),
                "model": result.model,
                "sections": sections,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500
```

---

### 3. Modify: `llm/schemas/surfaces.py` — New Pydantic Fields

**Add to `BirthChartSynthesisSection`** (line 396):

```python
class BirthChartSynthesisSection(BaseModel):
    # ... existing fields (title, opening_promise, entrusted_beauty, etc.) ...

    # NEW: SDUI-specific fields
    phase_insight_title: Optional[str] = Field(
        default=None,
        description="One sentence about what the user is currently learning. 8-16 words. E.g., 'You are learning how to use your energy cleanly'."
    )
    insights: Optional[list[str]] = Field(
        default=None,
        description="Exactly 3 bullet-point insights about the current phase. Each 5-12 words. Short, felt, recognizable."
    )
    affirmation: Optional[str] = Field(
        default=None,
        description="One powerful affirmation sentence about the current threshold. 6-14 words. Not generic — specific to this chart."
    )
    polarity_left: Optional[str] = Field(
        default=None,
        description="Left polarity tag — what the life is moving FROM. 1-3 words. E.g., 'Reactive', 'Over-functioning'."
    )
    polarity_right: Optional[str] = Field(
        default=None,
        description="Right polarity tag — what the life is moving TOWARD. 1-3 words. E.g., 'Deliberate', 'Chosen restraint'."
    )
```

**Add to `StudyForce`** (around line 175):

```python
class StudyForce(BaseModel):
    name: str = Field(...)
    subtitle: str = Field(...)
    sacred_capacity: str = Field(...)
    distortion: Optional[str] = Field(...)
    purified_expression: Optional[str] = Field(...)

    # NEW: SDUI card fields
    card_title: Optional[str] = Field(
        default=None,
        description="User-friendly 1-2 word name for the card. E.g., 'Moon', 'Instability', 'Your Force'. Not the technical yoga name."
    )
    card_description: Optional[str] = Field(
        default=None,
        description="2-3 sentence preview for the card. 15-40 words. What the reader sees before tapping 'Read more'."
    )
    details: Optional[list[dict]] = Field(
        default=None,
        description="2-4 structured pairs for card display. Each has 'label' (e.g., 'what works', 'when blocked') and 'value' (5-20 words). Labels must be lowercase."
    )
    comparisons: Optional[list[dict]] = Field(
        default=None,
        description="Side-by-side comparison pairs. Each has 'left' and 'right' (5-15 words each). Only include when a meaningful contrast exists."
    )
```

**Update `BirthChartCore`** to include the new synthesis fields (for merged validation).

**Update `_merge_birth_chart_sections()`** in `pipeline.py` to carry through new fields:

```python
# Add to the synthesis merge block (line 398-403):
for field in (
    "title", "opening_promise", "entrusted_beauty", "central_knot",
    "present_threshold", "love", "work", "embodiment", "closing_destiny",
    # NEW SDUI fields
    "phase_insight_title", "insights", "affirmation", "polarity_left", "polarity_right",
):
    merged[field] = synthesis.data.get(field, "" if field not in ("insights",) else None)
```

---

### 4. Modify: AI Prompt Files

#### `1.0/prompts/features/birth_chart_synthesis.txt`

Add to the output instructions section:

```
## SDUI Card Fields (NEW)

In addition to the narrative sections, generate these structured fields for the mobile UI:

**phase_insight_title**: One sentence about what the member is currently learning in their active dasha chapter. 8-16 words. Must feel specific to this chart, not generic. Example: "You are learning how to use your energy cleanly."

**insights**: Exactly 3 bullet-point phrases about the current phase. Each 5-12 words. These appear as bullet points below the phase title. They should be recognizable — things the member would nod at. Not predictions. Not advice. Observations.

**affirmation**: One powerful sentence — the single thing this chart needs to hear right now. 6-14 words. Not a command. Not a platitude. A truth that steadies. Example: "Use your energy only where it matters."

**polarity_left**: The quality the life is moving FROM. 1-3 words. Example: "Reactive", "Over-functioning", "Proving".

**polarity_right**: The quality the life is moving TOWARD. 1-3 words. Example: "Deliberate", "Chosen restraint", "Authorship".
```

#### `1.0/prompts/features/birth_chart_yogas.txt`

Add to the output instructions section:

```
## SDUI Card Fields (NEW)

For each yoga (great and finer), also generate these fields for mobile card display:

**card_title**: A user-friendly 1-2 word name. NOT the technical yoga name. Think: the archetype, the planet, or the felt quality. Examples: "Moon", "Your Force", "Instability", "Dissolution". This is what the member sees on the card before they know the yoga name.

**card_description**: 2-3 sentences previewing this yoga's lived reality. 15-40 words. This is the card body text — it must work as a standalone teaser that makes the member want to read more. Write in second person ("You are built to...").

**details**: 2-4 structured pairs for card display. Each pair has:
- "label": lowercase category (e.g., "what works", "when blocked", "what it costs", "what changes it")
- "value": 5-20 words describing that category for this specific yoga

Example:
[
  {"label": "what works", "value": "Challenge, pressure, real stakes — anything that demands your full force"},
  {"label": "when blocked", "value": "Your speed becomes reckless when it no longer serves the right thing"}
]
```

#### `1.0/prompts/features/birth_chart_forces.txt`

Same additions as yogas, plus:

```
**comparisons** (optional): Include ONLY when a meaningful side-by-side contrast exists for this force. Each comparison has:
- "left": what this force looks like in one mode (5-15 words)
- "right": what it looks like in the other (5-15 words)

Example:
[{"left": "You are built for movement and consequence", "right": "This is not about proving more — it is about choosing where"}]

Only 1-2 comparisons per force. Do not force a comparison where none naturally exists.
```

---

### 5. Token Budget Adjustments

| Section Call | Current Budget | New Fields | Estimated Increase | New Budget |
|---|---|---|---|---|
| `birth_chart_synthesis` | 3,500 tokens | insights, affirmation, polarity | +100 tokens | 3,700 tokens |
| `birth_chart_yogas` | 2,500 tokens | card_title, card_description, details per yoga | +400 tokens | 3,000 tokens |
| `birth_chart_forces` | 2,500 tokens | card_title, card_description, details, comparisons per force | +500 tokens | 3,100 tokens |
| `birth_chart_timing` | 3,000 tokens | no changes | 0 | 3,000 tokens |

**Update in `llm/core/config.py`** (`MAX_TOKENS` dict).

---

## Existing Field → SDUI Section Mapping

| Existing Field | SDUI Section | Notes |
|---|---|---|
| `opening_promise` | Hero section (description) | Truncated to 4 lines |
| `life_phases[]` | Phase progress (media.data) | Computed into phase_bar |
| `entrusted_beauty` | Narrative section | Expandable |
| `central_knot` | Narrative section | Expandable |
| `present_threshold` | Narrative section | Expandable |
| `love` | Narrative section | Expandable |
| `work` | Narrative section | Expandable |
| `great_yogas[]` | Card carousel (PLANETARY MOVEMENTS) | Horizontal scroll |
| `finer_yogas[]` | Card carousel (SHADOW SYSTEM) | Horizontal scroll |
| `deeper_shaping_forces[]` | Card carousel (HOW PHASE IMPACTS) | Horizontal scroll |
| `great_timing_currents[]` | Timeline (DASHA NAVIGATION) | Custom media component |
| `embodiment` | Narrative section | Expandable |
| `closing_destiny` | Closing section | Full text, no truncation |
| **NEW** `insights[]` | Insight bullets card | 3 bullet points |
| **NEW** `affirmation` | Affirmation section | Single line |
| **NEW** `polarity_left/right` | Insight card headline pair | Spectrum tags |
| **NEW** `card_title` per yoga | Card title in carousel | User-friendly name |
| **NEW** `card_description` per yoga | Card body in carousel | Preview text |
| **NEW** `details[]` per yoga | Card headlines/subheadlines | Structured pairs |
| **NEW** `comparisons[]` per force | Card comparison columns | Side-by-side |

---

## Files Changed Summary

| File | Action | What Changes |
|------|--------|-------------|
| `llm/sdui.py` | **NEW** | Section builder: `build_sdui_sections()` |
| `web/app.py` | **MODIFY** line 171-186 | Wrap response in sections |
| `llm/schemas/surfaces.py` | **MODIFY** | Add SDUI fields to `StudyForce`, `BirthChartSynthesisSection`, `BirthChartCore` |
| `llm/pipeline.py` | **MODIFY** line 398-403 | Carry new fields through merge |
| `llm/core/config.py` | **MODIFY** | Bump token budgets for yogas/forces/synthesis |
| `1.0/prompts/features/birth_chart_synthesis.txt` | **MODIFY** | Add insights/affirmation/polarity instructions |
| `1.0/prompts/features/birth_chart_yogas.txt` | **MODIFY** | Add card_title/card_description/details instructions |
| `1.0/prompts/features/birth_chart_forces.txt` | **MODIFY** | Add card_title/card_description/details/comparisons instructions |

---

## Verification

1. Run `python -m llm.run_test` with a test birth chart — verify new fields appear in output
2. Validate `build_sdui_sections()` transforms flat dict correctly (unit test)
3. Hit `/api/birth-chart` endpoint — verify response has `sections[]` structure
4. Check each section has correct `id`, `type`-free structure, correct card count
5. Verify carousel sections (great_yogas, finer_yogas) have 2+ cards
6. Verify narrative sections have `max_lines` and `cta`
7. Verify phase_bar media has correct `current_age` and `is_current` flag
8. Compare JSON output against `anantya-docs/architecture/SDUI_STRATEGY.md` schema
