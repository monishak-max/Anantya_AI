"""
SDUI section builder -- transforms flat birth chart dict into exactly 4 sections.

Section 1: YOUR CURRENT PHASE (phase bar + insight card + affirmation)
Section 2: HOW PHASE IMPACTS (Work + Love carousel)
Section 3: PLANETARY MOVEMENTS (yoga/force cards carousel)
Section 4: THE LESSON (closing destiny)

Pure transformation, no AI calls, no latency cost.
"""
from __future__ import annotations

from datetime import date


def calculate_age(birth_date_str: str) -> int:
    birth = date.fromisoformat(birth_date_str)
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def build_sdui_sections(data: dict, user_age: int) -> list[dict]:
    sections = []

    # ── SECTION 1: YOUR CURRENT PHASE ─────────────────────────────
    life_phases = data.get("life_phases", [])
    current_phase = next(
        (p for p in life_phases if _is_current_phase(p, user_age)),
        life_phases[0] if life_phases else {"title": "Unknown", "age_range": "0-100"},
    )
    parts = current_phase.get("age_range", "0-100").split("-")
    try:
        phase_start = int(parts[0])
        phase_end = int(parts[1]) if len(parts) > 1 else phase_start + 10
    except ValueError:
        phase_start, phase_end = 0, 100

    # Insight card (pointers + polarity)
    insight_card = None
    if data.get("insights"):
        insight_card = {
            "id": "insight_card",
            "pointers": data["insights"],
        }
        if data.get("polarity_left") and data.get("polarity_right"):
            insight_card["headlines"] = [
                {"label": data["polarity_left"], "value": data["polarity_right"]}
            ]

    section1 = {
        "id": "current_phase",
        "label": "YOUR CURRENT PHASE",
        "title": current_phase.get("title", ""),
        "media": {
            "type": "phase_bar",
            "data": {
                "current_age": user_age,
                "remaining_years": max(0, phase_end - user_age),
                "phase_start": phase_start,
                "phase_end": phase_end,
            },
        },
        "cards": [insight_card] if insight_card else [],
    }

    # Add phase insight title above the card
    if data.get("phase_insight_title"):
        section1["insight_label"] = "Right now, you may feel"
        section1["insight_title"] = data["phase_insight_title"]

    # Affirmation below the card
    if data.get("affirmation"):
        section1["affirmation"] = data["affirmation"]

    # Dive deeper CTA
    section1["cta"] = {"text": "Dive deeper", "action": "expand"}

    sections.append(section1)

    # ── SECTION 2: HOW PHASE IMPACTS ──────────────────────────────
    impact_cards = []
    if data.get("work"):
        work_card = {
            "id": "work_card",
            "icon": "briefcase.fill",
            "title": "Work",
            "description": _truncate(data["work"], 30),
            "max_lines": 4,
            "cta": {"text": "Read more", "action": "detail"},
            "detail": {"title": "Work", "body": data["work"]},
        }
        # Add headlines from work content
        work_card["headlines"] = [
            {"label": "What works", "value": _extract_theme(data["work"], "strength")},
            {"label": "What drains", "value": _extract_theme(data["work"], "drain")},
        ]
        impact_cards.append(work_card)

    if data.get("love"):
        love_card = {
            "id": "love_card",
            "icon": "heart.fill",
            "title": "Love",
            "description": _truncate(data["love"], 30),
            "max_lines": 4,
            "cta": {"text": "Read more", "action": "detail"},
            "detail": {"title": "Love", "body": data["love"]},
        }
        impact_cards.append(love_card)

    if impact_cards:
        sections.append({
            "id": "practical_truth",
            "label": "HOW PHASE IMPACTS",
            "title": "Practical Truth",
            "description": data.get("present_threshold", "")[:150] if data.get("present_threshold") else "",
            "max_lines": 3,
            "cards": impact_cards,
        })

    # ── SECTION 3: PLANETARY MOVEMENTS ────────────────────────────
    all_yogas = []
    for yoga in data.get("great_yogas", []):
        all_yogas.append(_build_yoga_card(yoga, f"yoga_{len(all_yogas)}"))
    for yoga in data.get("finer_yogas", []):
        all_yogas.append(_build_yoga_card(yoga, f"pattern_{len(all_yogas)}"))
    for force in data.get("deeper_shaping_forces", []):
        all_yogas.append(_build_yoga_card(force, f"force_{len(all_yogas)}"))

    if all_yogas:
        sections.append({
            "id": "planetary_movements",
            "label": "PLANETARY MOVEMENTS",
            "title": "Your Forces",
            "cards": all_yogas,
        })

    # ── SECTION 4: THE LESSON ─────────────────────────────────────
    if data.get("closing_destiny"):
        sections.append({
            "id": "the_lesson",
            "label": "THE LESSON",
            "description": data["closing_destiny"],
            "cards": [],
        })

    return sections


# ── Helpers ─────────────────────────────────────────────────────

def _build_yoga_card(yoga: dict, card_id: str) -> dict:
    card = {
        "id": card_id,
        "title": yoga.get("card_title") or _short_name(yoga.get("name", "")),
        "subtitle": yoga.get("name", ""),
        "description": yoga.get("card_description") or _truncate(yoga.get("sacred_capacity", ""), 30),
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

    # Only show structured details if the LLM actually generated them.
    # Never truncate prose into fake headlines -- it reads as nonsense.
    if yoga.get("details"):
        card["headlines"] = [{"label": d["label"], "value": d["value"]} for d in yoga["details"][:2]]
        if len(yoga["details"]) > 2:
            card["subheadlines"] = [{"label": d["label"], "value": d["value"]} for d in yoga["details"][2:]]

    return card


def _short_name(name: str) -> str:
    """Extract a short user-friendly name from a yoga/force name."""
    # "Raja Yoga (Venus)" -> "Your force"
    # "Jupiter and Ketu in the self" -> "Jupiter-Ketu"
    if "moon" in name.lower():
        return "Moon"
    if "sun" in name.lower():
        return "Sun"
    if "mars" in name.lower():
        return "Mars"
    if "venus" in name.lower():
        return "Venus"
    if "jupiter" in name.lower():
        return "Jupiter"
    if "saturn" in name.lower():
        return "Saturn"
    if "rahu" in name.lower():
        return "Rahu"
    if "ketu" in name.lower():
        return "Ketu"
    if "mercury" in name.lower():
        return "Mercury"
    words = name.split()
    return " ".join(words[:2]) if len(words) > 2 else name


def _extract_theme(text: str, theme_type: str) -> str:
    """Extract a short theme from longer text."""
    sentences = text.replace(".", ". ").split(". ")
    if theme_type == "strength" and len(sentences) > 0:
        return _truncate(sentences[0], 10)
    if theme_type == "drain" and len(sentences) > 2:
        return _truncate(sentences[-2], 10)
    return _truncate(text, 10)


def _truncate(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _join_prose(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def _is_current_phase(phase: dict, user_age: int) -> bool:
    parts = phase.get("age_range", "0-0").split("-")
    try:
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 else start + 10
    except ValueError:
        return False
    return start <= user_age <= end
