"""
Pydantic models for every Astro product surface.
Word-count ranges from 1.0/docs/03_output_schemas.md.
These are used both as structured output schemas for the LLM
and as post-generation validators.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


# ── Helpers ────────────────────────────────────────────────────────

def word_count(text: str) -> int:
    return len(text.split())


def validate_word_range(text: str, min_words: int, max_words: int, field_name: str) -> list[str]:
    """Returns list of warnings (not errors) for word count violations."""
    wc = word_count(text)
    warnings = []
    if wc < min_words:
        warnings.append(f"{field_name}: {wc} words (min {min_words})")
    elif wc > max_words:
        warnings.append(f"{field_name}: {wc} words (max {max_words})")
    return warnings


# ── 1. Now Collapsed ──────────────────────────────────────────────

class NowCollapsed(BaseModel):
    astro_signature: str = Field(description="Format: 'Month Day · ☽ degree' (e.g. 'March 11 · ☽ 14°'). A design element, not a data dump. 4-10 words after date. No dasha labels, house numbers, or conjunctions.")
    headline: str = Field(description="One distilled truth the member carries all day. Singular, memorable, emotionally clear. 7-14 words.")
    support_text: str = Field(description="Clarify the signal without over-explaining. 2-3 sentences max. No generic positivity. STRICT 18-38 words.")
    do_today: str = Field(description="One specific, graceful action — not vague wellness advice. 4-10 words.")
    reflection: str = Field(description="A question that lands. Introspective, elegant, non-therapeutic. 6-16 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.headline, 7, 14, "headline")
        warnings += validate_word_range(self.support_text, 18, 38, "support_text")
        warnings += validate_word_range(self.do_today, 4, 10, "do_today")
        warnings += validate_word_range(self.reflection, 6, 16, "reflection")
        return warnings


# ── 2. Now Expanded ───────────────────────────────────────────────

class NowExpanded(BaseModel):
    astro_signature: str = Field(description="Format: 'Month Day · ☽ Moon in [Sign] - [degree]°'. Clean, minimal. No dasha labels or house numbers.")
    opening_paragraph: str = Field(description="Expand the day's thesis in a refined, emotionally legible way. A deeper breath, not a report. 28-55 words.")
    what_this_means_body: str = Field(description="Explain the active pattern in plain, premium language. What is actually happening in the member's life. 35-80 words.")
    resistance_body: str = Field(description="Name likely avoidance, hesitation, or distortion patterns. Humane, not clinical — real behaviors the member might recognize. 25-70 words.")
    guidance_body: str = Field(description="Orient toward wise movement. Specific and steady, not generic. 18-50 words.")
    closing_anchor: Optional[str] = Field(default=None, description="One concise, memorable, calm line. Poetic, not preachy. 4-12 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.opening_paragraph, 28, 55, "opening_paragraph")
        warnings += validate_word_range(self.what_this_means_body, 35, 80, "what_this_means_body")
        warnings += validate_word_range(self.resistance_body, 25, 70, "resistance_body")
        warnings += validate_word_range(self.guidance_body, 18, 50, "guidance_body")
        if self.closing_anchor:
            warnings += validate_word_range(self.closing_anchor, 4, 12, "closing_anchor")
        return warnings


# ── 3. Mandala Card (single) ──────────────────────────────────────

class MandalaCard(BaseModel):
    activation_marker: str = Field(description="Format: '[Planet] in [ordinal] · [duration]' (e.g. 'Mars in 4th · 11 days'). A label, not an explanation. 4-12 words.")
    card_title: str = Field(description="Translated human meaning — not raw astrology. Not 'Mars transits 4th house' but 'Your inner foundations are being stirred'. 5-12 words.")
    card_body: str = Field(description="How this shows up in daily life — concrete, recognizable, not abstract. MUST be 18-45 words. This is a card, not an essay.")
    cta: Optional[str] = Field(default=None, description="2-5 words, e.g. 'Read More'")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.activation_marker, 4, 12, "activation_marker")
        warnings += validate_word_range(self.card_title, 5, 12, "card_title")
        warnings += validate_word_range(self.card_body, 18, 45, "card_body")
        if self.cta:
            warnings += validate_word_range(self.cta, 2, 5, "cta")
        return warnings


class MandalaCards(BaseModel):
    cards: list[MandalaCard] = Field(description="3-7 activation cards, no duplicate themes")

    def validate_lengths(self) -> list[str]:
        warnings = []
        if len(self.cards) < 3:
            warnings.append(f"cards: only {len(self.cards)} cards (min 3)")
        elif len(self.cards) > 7:
            warnings.append(f"cards: {len(self.cards)} cards (max 7)")
        for i, card in enumerate(self.cards):
            for w in card.validate_lengths():
                warnings.append(f"card[{i}].{w}")
        return warnings


# ── 4. Mandala Deep Read ──────────────────────────────────────────

class MandalaDeepRead(BaseModel):
    title: str = Field(description="Translated human title for this activation — what it touches in life. 5-14 words.")
    activation_summary: str = Field(description="What is happening astrologically, translated into felt experience. 20-45 words.")
    life_area_section: str = Field(description="Where this lands in the member's life — name the concrete area (home, work, relationships, creativity, purpose). 35-75 words.")
    inner_expression_section: str = Field(description="How it may feel emotionally or psychologically. Name real behaviors and inner states, not abstractions. 30-70 words.")
    guidance_section: str = Field(description="How to move with this wisely. Specific, grounded, actionable orientation. 20-55 words.")
    time_note: Optional[str] = Field(default=None, description="How long this influence lasts and what phase it is in. 6-20 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.title, 5, 14, "title")
        warnings += validate_word_range(self.activation_summary, 20, 45, "activation_summary")
        warnings += validate_word_range(self.life_area_section, 35, 75, "life_area_section")
        warnings += validate_word_range(self.inner_expression_section, 30, 70, "inner_expression_section")
        warnings += validate_word_range(self.guidance_section, 20, 55, "guidance_section")
        if self.time_note:
            warnings += validate_word_range(self.time_note, 6, 20, "time_note")
        return warnings


# ── 5. Union Snapshot ─────────────────────────────────────────────

class UnionSnapshot(BaseModel):
    bond_summary: str = Field(description="One elegant sentence capturing the essence of their connection. Intimate, not generic romance copy. 10-22 words.")
    emotional_dynamic: str = Field(description="How the emotional rhythm between them works — what kind of feeling space they create together. 18-45 words.")
    support_line: str = Field(description="What flows naturally between them — what they don't have to try at. 12-30 words.")
    friction_line: str = Field(description="Where awareness deepens the bond. Fair, calm, not alarming. 12-30 words.")
    invitation: Optional[str] = Field(default=None, description="An open door to explore deeper. Not a sales pitch. 6-18 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.bond_summary, 10, 22, "bond_summary")
        warnings += validate_word_range(self.emotional_dynamic, 18, 45, "emotional_dynamic")
        warnings += validate_word_range(self.support_line, 12, 30, "support_line")
        warnings += validate_word_range(self.friction_line, 12, 30, "friction_line")
        if self.invitation:
            warnings += validate_word_range(self.invitation, 6, 18, "invitation")
        return warnings


# ── 6. Union Deep Read ────────────────────────────────────────────

class UnionDeepRead(BaseModel):
    overall_dynamic: str = Field(description="The big picture of this bond — what kind of relationship this is at its core. Narrative, not score. 45-90 words.")
    emotional_rhythm: str = Field(description="How emotions move between them — who leads, who receives, where they sync and where they miss. 35-75 words.")
    communication_pattern: str = Field(description="How they process and exchange — where words flow and where silence builds. 35-75 words.")
    affection_and_attraction: str = Field(description="The quality of magnetism and warmth — what draws them together and how intimacy expresses. 35-75 words.")
    values_and_path_alignment: str = Field(description="Where their life directions converge and diverge — shared vision vs individual pull. 35-75 words.")
    friction_zones: str = Field(description="Where tension lives — framed with dignity and fairness. Not problems but growth edges. 35-75 words.")
    karmic_lesson: str = Field(description="What this bond is teaching both people — the deeper pattern beneath the surface. 30-70 words.")
    growth_potential: str = Field(description="What becomes possible if both people meet the bond with awareness and maturity. 30-70 words.")
    closing_guidance: str = Field(description="One grounded, wise orientation for how to hold this relationship well. 20-55 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.overall_dynamic, 45, 90, "overall_dynamic")
        warnings += validate_word_range(self.emotional_rhythm, 35, 75, "emotional_rhythm")
        warnings += validate_word_range(self.communication_pattern, 35, 75, "communication_pattern")
        warnings += validate_word_range(self.affection_and_attraction, 35, 75, "affection_and_attraction")
        warnings += validate_word_range(self.values_and_path_alignment, 35, 75, "values_and_path_alignment")
        warnings += validate_word_range(self.friction_zones, 35, 75, "friction_zones")
        warnings += validate_word_range(self.karmic_lesson, 30, 70, "karmic_lesson")
        warnings += validate_word_range(self.growth_potential, 30, 70, "growth_potential")
        warnings += validate_word_range(self.closing_guidance, 20, 55, "closing_guidance")
        return warnings


# ── 7. Birth Chart Core (Anantya full sacred study) ─────────────────

class StudyForce(BaseModel):
    name: str = Field(description="The sacred force, yoga, or shaping combination name. Keep Sanskrit terms where relevant.")
    subtitle: str = Field(description="A short living explanation in plain language. MUST be 6-18 words. Never fewer than 6.", default="")
    sacred_capacity: str = Field(description="What beautiful power this force places in the life. HARD LIMIT: 35-95 words. Do not exceed 95.", default="")
    distortion: str = Field(description="How this same force becomes costly when misused or strained. HARD LIMIT: 25-85 words. Do not exceed 85.", default="")
    purified_expression: str = Field(description="What this force becomes when lived truthfully. HARD LIMIT: 20-70 words. Do not exceed 70.", default="")

    model_config = {"populate_by_name": True}

    def __init__(self, **data):
        # Accept 'body'/'description'/'capacity' as aliases
        if "body" in data and "sacred_capacity" not in data:
            data["sacred_capacity"] = data.pop("body")
        if "capacity" in data and "sacred_capacity" not in data:
            data["sacred_capacity"] = data.pop("capacity")
        if "shadow" in data and "distortion" not in data:
            data["distortion"] = data.pop("shadow")
        super().__init__(**data)

    def validate_lengths(self) -> list[str]:
        warnings = []
        if self.subtitle:
            warnings += validate_word_range(self.subtitle, 6, 18, "subtitle")
        if self.sacred_capacity:
            warnings += validate_word_range(self.sacred_capacity, 35, 95, "sacred_capacity")
        if self.distortion:
            warnings += validate_word_range(self.distortion, 25, 85, "distortion")
        if self.purified_expression:
            warnings += validate_word_range(self.purified_expression, 20, 70, "purified_expression")
        return warnings


class TimingCurrent(BaseModel):
    name: str = Field(description="Mahadasha or bhukti name, or other timing current heading.")
    subtitle: str = Field(description="A short living explanation of what this chapter is about. MUST be 6-18 words. Never fewer than 6.", default="")
    chapter_body: str = Field(description="How this timing current shapes the life in lived terms. HARD LIMIT: 45-140 words. Do not exceed 140.", default="")

    model_config = {"populate_by_name": True}

    def __init__(self, **data):
        # Accept 'body' as alias for 'chapter_body'
        if "body" in data and "chapter_body" not in data:
            data["chapter_body"] = data.pop("body")
        super().__init__(**data)

    def validate_lengths(self) -> list[str]:
        warnings = []
        if self.subtitle:
            warnings += validate_word_range(self.subtitle, 6, 18, "subtitle")
        if self.chapter_body:
            warnings += validate_word_range(self.chapter_body, 45, 140, "chapter_body")
        return warnings


class LifePhase(BaseModel):
    title: str = Field(description="Phase title for this life chapter. 2-8 words.", alias="title")
    age_range: str = Field(description="Age span label such as '0-18'.", default="")
    body: str = Field(description="How this life chapter feels and what it is doing. HARD LIMIT: 30-90 words. Do not exceed 90.", default="")

    model_config = {"populate_by_name": True}

    def __init__(self, **data):
        # Accept various LLM output field names as aliases
        if "name" in data and "title" not in data:
            data["title"] = data.pop("name")
        if "phase" in data and "title" not in data:
            data["title"] = data.pop("phase")
        if "chapter_body" in data and "body" not in data:
            data["body"] = data.pop("chapter_body")
        if "subtitle" in data and "body" not in data:
            data["body"] = data.pop("subtitle")
        super().__init__(**data)

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.title, 2, 8, "title")
        if self.body:
            warnings += validate_word_range(self.body, 30, 90, "body")
        return warnings


class BirthChartCore(BaseModel):
    title: str = Field(description="The title of the life story. Beautiful, elevated, and destiny-led. 3-10 words.")
    opening_promise: str = Field(description="What this life came here to embody. Uplifting, direct, and sacred. 60-140 words.")
    entrusted_beauty: str = Field(description="The beauty, dignity, and entrusted force of the life before naming the knot. 60-140 words.")
    central_knot: str = Field(description="The one great knot of the life. Specific, direct, and lived. 55-130 words.")
    great_yogas: list[StudyForce] = Field(description="The great yogas moving through this life. Each must be named individually.")
    finer_yogas: list[StudyForce] = Field(description="The finer yogas that still shape the life and must each be honored individually.")
    deeper_shaping_forces: list[StudyForce] = Field(description="Conjunctions, lordship truths, axis burdens, and other life-shaping combinations. Each must be named individually.")
    great_timing_currents: list[TimingCurrent] = Field(description="Mahadashas, active bhuktis, and major timing bodies written as living chapters.")
    life_phases: list[LifePhase] = Field(description="The major life chapters from early life through late life.")
    present_threshold: str = Field(description="What is being asked of the life now. 55-140 words.")
    love: str = Field(description="Love in this specific life. Direct, specific, and unmistakably personal. HARD LIMIT: 60-140 words. Do not exceed 140.")
    work: str = Field(description="Work in this specific life. Direct, specific, and unmistakably personal. HARD LIMIT: 60-140 words. Do not exceed 140.")
    embodiment: str = Field(description="What the soul came here to embody when the life ripens. 60-140 words.")
    closing_destiny: str = Field(description="A final destiny-led closing that returns the life to beauty and purpose. 35-90 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.title, 3, 10, "title")
        warnings += validate_word_range(self.opening_promise, 60, 140, "opening_promise")
        warnings += validate_word_range(self.entrusted_beauty, 60, 140, "entrusted_beauty")
        warnings += validate_word_range(self.central_knot, 55, 130, "central_knot")
        for i, item in enumerate(self.great_yogas):
            for w in item.validate_lengths(): warnings.append(f"great_yogas[{i}].{w}")
        for i, item in enumerate(self.finer_yogas):
            for w in item.validate_lengths(): warnings.append(f"finer_yogas[{i}].{w}")
        for i, item in enumerate(self.deeper_shaping_forces):
            for w in item.validate_lengths(): warnings.append(f"deeper_shaping_forces[{i}].{w}")
        for i, item in enumerate(self.great_timing_currents):
            for w in item.validate_lengths(): warnings.append(f"great_timing_currents[{i}].{w}")
        for i, item in enumerate(self.life_phases):
            for w in item.validate_lengths(): warnings.append(f"life_phases[{i}].{w}")
        warnings += validate_word_range(self.present_threshold, 55, 140, "present_threshold")
        warnings += validate_word_range(self.love, 60, 140, "love")
        warnings += validate_word_range(self.work, 60, 140, "work")
        warnings += validate_word_range(self.embodiment, 60, 140, "embodiment")
        warnings += validate_word_range(self.closing_destiny, 35, 90, "closing_destiny")
        return warnings


# ── 8. Weekly Overview ────────────────────────────────────────────

class WeeklyOverview(BaseModel):
    opening_summary: str = Field(description="The week's overarching tone and direction. Strategic, not just a longer daily reading. 35-75 words.")
    main_themes: str = Field(description="The 2-3 dominant themes shaping this week — what life areas are active and how they connect. 40-95 words.")
    work_and_purpose: str = Field(description="How the week lands in work, career, and contribution. Practical and orienting. 25-65 words.")
    relationships: str = Field(description="Relational weather — what is flowing, what needs attention. 25-65 words.")
    inner_state: str = Field(description="Emotional and psychological texture of the week — how the member may feel inside. 25-65 words.")
    timing_note: str = Field(description="Specific days or windows within the week that carry particular weight. Brief and useful. 12-35 words.")
    guidance: str = Field(description="One orienting posture for the whole week. Wise, specific, not generic. 20-50 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.opening_summary, 35, 75, "opening_summary")
        warnings += validate_word_range(self.main_themes, 40, 95, "main_themes")
        warnings += validate_word_range(self.work_and_purpose, 25, 65, "work_and_purpose")
        warnings += validate_word_range(self.relationships, 25, 65, "relationships")
        warnings += validate_word_range(self.inner_state, 25, 65, "inner_state")
        warnings += validate_word_range(self.timing_note, 12, 35, "timing_note")
        warnings += validate_word_range(self.guidance, 20, 50, "guidance")
        return warnings


# ── 9. Monthly Overview ───────────────────────────────────────────

class MonthlyOverview(BaseModel):
    opening_summary: str = Field(description="The month's overarching arc — what opens, what closes, what asks for patience. A wider lens than weekly. 45-90 words.")
    main_themes: str = Field(description="The dominant themes shaping this month — major transits, dasha developments, and life area emphasis. 55-110 words.")
    work_and_purpose: str = Field(description="How the month shapes work, career, ambition, and contribution. Strategic and grounded. 30-75 words.")
    relationships: str = Field(description="Relational arc of the month — what deepens, what shifts, what needs tending. 30-75 words.")
    inner_state: str = Field(description="Emotional and psychological arc — the month's inner weather and how it evolves. 30-75 words.")
    timing_notes: str = Field(description="Key dates, windows, or phases within the month that carry particular weight. 18-45 words.")
    guidance: str = Field(description="One wise orientation for how to hold the whole month. Specific, grounded, memorable. 25-60 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.opening_summary, 45, 90, "opening_summary")
        warnings += validate_word_range(self.main_themes, 55, 110, "main_themes")
        warnings += validate_word_range(self.work_and_purpose, 30, 75, "work_and_purpose")
        warnings += validate_word_range(self.relationships, 30, 75, "relationships")
        warnings += validate_word_range(self.inner_state, 30, 75, "inner_state")
        warnings += validate_word_range(self.timing_notes, 18, 45, "timing_notes")
        warnings += validate_word_range(self.guidance, 25, 60, "guidance")
        return warnings


# ── 10. Chart Reveal ─────────────────────────────────────────────

class ChartReveal(BaseModel):
    headline: str = Field(description="One sentence portrait of this person — who they are at their core. Must synthesize multiple chart factors (not just Moon sign). Warm, precise, felt. 12-25 words.")
    traits: list[str] = Field(description="Exactly 3 specific, felt qualities. Each drawn from a different part of the chart. Not compliments — recognitions. Each trait 6-14 words.")
    soul_line: str = Field(description="A poetic closing line about this soul's arrival — what this life came to explore. 8-18 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.headline, 12, 25, "headline")
        if len(self.traits) != 3:
            warnings.append(f"traits: {len(self.traits)} items (expected exactly 3)")
        for i, trait in enumerate(self.traits):
            warnings += validate_word_range(trait, 6, 14, f"traits[{i}]")
        warnings += validate_word_range(self.soul_line, 8, 18, "soul_line")
        return warnings


# ── Birth Chart Parallel Sections ────────────────────────────────

class BirthChartYogasSection(BaseModel):
    great_yogas: list[StudyForce] = Field(description="The great yogas moving through this life. Each must be named individually.")
    finer_yogas: list[StudyForce] = Field(description="The finer yogas that still shape the life and must each be honored individually.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        for i, item in enumerate(self.great_yogas):
            for w in item.validate_lengths(): warnings.append(f"great_yogas[{i}].{w}")
        for i, item in enumerate(self.finer_yogas):
            for w in item.validate_lengths(): warnings.append(f"finer_yogas[{i}].{w}")
        return warnings


class BirthChartForcesSection(BaseModel):
    deeper_shaping_forces: list[StudyForce] = Field(description="Conjunctions, lordship truths, axis burdens, and other life-shaping combinations. Each must be named individually.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        for i, item in enumerate(self.deeper_shaping_forces):
            for w in item.validate_lengths(): warnings.append(f"deeper_shaping_forces[{i}].{w}")
        return warnings


class BirthChartTimingSection(BaseModel):
    great_timing_currents: list[TimingCurrent] = Field(description="Mahadashas, active bhuktis, and major timing bodies written as living chapters.")
    life_phases: list[LifePhase] = Field(description="The major life chapters from early life through late life.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        for i, item in enumerate(self.great_timing_currents):
            for w in item.validate_lengths(): warnings.append(f"great_timing_currents[{i}].{w}")
        for i, item in enumerate(self.life_phases):
            for w in item.validate_lengths(): warnings.append(f"life_phases[{i}].{w}")
        return warnings


class BirthChartSynthesisSection(BaseModel):
    title: str = Field(description="The title of the life story. Beautiful, elevated, and destiny-led. 3-10 words.")
    opening_promise: str = Field(description="What this life came here to embody. Uplifting, direct, and sacred. 60-140 words.")
    entrusted_beauty: str = Field(description="The beauty, dignity, and entrusted force of the life before naming the knot. 60-140 words.")
    central_knot: str = Field(description="The one great knot of the life. Specific, direct, and lived. 55-130 words.")
    present_threshold: str = Field(description="What is being asked of the life now. 55-140 words.")
    love: str = Field(description="Love in this specific life. Direct, specific, and unmistakably personal. HARD LIMIT: 60-140 words. Do not exceed 140.")
    work: str = Field(description="Work in this specific life. Direct, specific, and unmistakably personal. HARD LIMIT: 60-140 words. Do not exceed 140.")
    embodiment: str = Field(description="What the soul came here to embody when the life ripens. 60-140 words.")
    closing_destiny: str = Field(description="A final destiny-led closing that returns the life to beauty and purpose. 35-90 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.title, 3, 10, "title")
        warnings += validate_word_range(self.opening_promise, 60, 140, "opening_promise")
        warnings += validate_word_range(self.entrusted_beauty, 60, 140, "entrusted_beauty")
        warnings += validate_word_range(self.central_knot, 55, 130, "central_knot")
        warnings += validate_word_range(self.present_threshold, 55, 140, "present_threshold")
        warnings += validate_word_range(self.love, 60, 140, "love")
        warnings += validate_word_range(self.work, 60, 140, "work")
        warnings += validate_word_range(self.embodiment, 60, 140, "embodiment")
        warnings += validate_word_range(self.closing_destiny, 35, 90, "closing_destiny")
        return warnings


# ── Surface → Schema mapping ──────────────────────────────────────

SURFACE_SCHEMAS: dict[str, type[BaseModel]] = {
    "now_collapsed": NowCollapsed,
    "now_expanded": NowExpanded,
    "mandala_cards": MandalaCards,
    "mandala_deep_read": MandalaDeepRead,
    "union_snapshot": UnionSnapshot,
    "union_deep_read": UnionDeepRead,
    "birth_chart_core": BirthChartCore,
    "birth_chart_yogas": BirthChartYogasSection,
    "birth_chart_forces": BirthChartForcesSection,
    "birth_chart_timing": BirthChartTimingSection,
    "birth_chart_synthesis": BirthChartSynthesisSection,
    "weekly_overview": WeeklyOverview,
    "monthly_overview": MonthlyOverview,
    "chart_reveal": ChartReveal,
}
