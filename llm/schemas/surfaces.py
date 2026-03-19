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


# ── 7. Birth Chart Core (expanded per PRD §7.3, §14-18) ───────────
# PRD requires: overview, core foundations, personality, emotional nature,
# major gifts, key yogas, karmic lessons, relationships, career/calling,
# wealth, health/energy, spiritual path, current dasha chapter,
# current phase (work/wealth/success), late-life arc, final synthesis

class BirthChartCore(BaseModel):
    opening_essence: str = Field(description="The overture -- who this person is at their core. Should feel like a portrait, not a chart description. STRICT 50-100 words. Cut ruthlessly.")
    core_signature: str = Field(description="Core foundations -- lagna, moon, key planetary patterns woven into human meaning. Not a list of placements. STRICT 45-90 words.")
    temperament: str = Field(description="How this person moves through the world -- their pace, style, presence. Personality as felt experience, not trait list. STRICT 45-110 words.")
    emotional_nature: str = Field(description="The inner world -- how they feel, what they need emotionally, their relationship with vulnerability. STRICT 45-110 words.")
    key_yogas: str = Field(description="Major yogas explained as lived gifts and tensions -- what they mean in daily life. No jargon without translation. No raw conjunction/aspect terms. STRICT 60-150 words.")
    strengths_and_blessings: str = Field(description="Natural advantages, innate gifts, what comes easily. Specific to this chart, not generic compliments. STRICT 45-100 words.")
    growth_edges: str = Field(description="Where life asks this person to stretch -- framed with dignity and care, not as flaws. STRICT 45-100 words.")
    relationship_patterning: str = Field(description="How they love, attach, and partner. What they need and what they offer. Patterns, not predictions. STRICT 45-110 words.")
    work_and_calling: str = Field(description="Vocation, contribution, and what kind of work feeds their soul. Career direction from the chart, not job titles. STRICT 45-110 words.")
    wealth_and_resources: str = Field(description="Relationship with money, material stability, and accumulation patterns. No specific financial predictions. STRICT 40-90 words.")
    health_and_energy: str = Field(description="Energy tendencies, stress patterns, vitality rhythm. NEVER name diseases or use the word 'diagnosis'. Frame as self-care wisdom. STRICT 40-90 words.")
    spiritual_orientation: str = Field(description="Spiritual path, inner growth direction, what kind of meaning-making feeds them. STRICT 40-100 words.")
    current_dasha_chapter: str = Field(description="Current dasha translated as a meaningful life chapter -- what is ripening, being tested, opening. No raw dasha labels. STRICT 55-125 words.")
    current_phase: str = Field(description="Current life phase across work, wealth, relationships. Name the phase clearly. STRICT 45-105 words.")
    late_life_arc: str = Field(description="How the chart matures with age -- what ripens later, what kind of elder self is emerging. STRICT 40-95 words.")
    closing_integration: str = Field(description="Final synthesis -- the one deeper pattern that runs through the whole chart. Should feel like a quiet revelation. STRICT 35-85 words.")

    def validate_lengths(self) -> list[str]:
        warnings = []
        warnings += validate_word_range(self.opening_essence, 50, 100, "opening_essence")
        warnings += validate_word_range(self.core_signature, 45, 90, "core_signature")
        warnings += validate_word_range(self.temperament, 45, 110, "temperament")
        warnings += validate_word_range(self.emotional_nature, 45, 110, "emotional_nature")
        warnings += validate_word_range(self.key_yogas, 60, 150, "key_yogas")
        warnings += validate_word_range(self.strengths_and_blessings, 45, 100, "strengths_and_blessings")
        warnings += validate_word_range(self.growth_edges, 45, 100, "growth_edges")
        warnings += validate_word_range(self.relationship_patterning, 45, 110, "relationship_patterning")
        warnings += validate_word_range(self.work_and_calling, 45, 110, "work_and_calling")
        warnings += validate_word_range(self.wealth_and_resources, 40, 90, "wealth_and_resources")
        warnings += validate_word_range(self.health_and_energy, 40, 90, "health_and_energy")
        warnings += validate_word_range(self.spiritual_orientation, 40, 100, "spiritual_orientation")
        warnings += validate_word_range(self.current_dasha_chapter, 55, 125, "current_dasha_chapter")
        warnings += validate_word_range(self.current_phase, 45, 105, "current_phase")
        warnings += validate_word_range(self.late_life_arc, 40, 95, "late_life_arc")
        warnings += validate_word_range(self.closing_integration, 35, 85, "closing_integration")
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


# ── Surface → Schema mapping ──────────────────────────────────────

SURFACE_SCHEMAS: dict[str, type[BaseModel]] = {
    "now_collapsed": NowCollapsed,
    "now_expanded": NowExpanded,
    "mandala_cards": MandalaCards,
    "mandala_deep_read": MandalaDeepRead,
    "union_snapshot": UnionSnapshot,
    "union_deep_read": UnionDeepRead,
    "birth_chart_core": BirthChartCore,
    "weekly_overview": WeeklyOverview,
    "monthly_overview": MonthlyOverview,
    "chart_reveal": ChartReveal,
}
