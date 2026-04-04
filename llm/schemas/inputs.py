"""
Input data models — what the astro computation engine passes to the LLM layer.
These represent the structured astrological data for each user/reading.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class NatalMoon(BaseModel):
    sign: str = Field(description="Moon sign (rashi), e.g. 'Capricorn'")
    degree: float = Field(description="Degree within sign, 0-30")
    nakshatra: str = Field(description="Nakshatra name, e.g. 'Shravana'")
    nakshatra_pada: Optional[int] = Field(default=None, description="Pada 1-4")


class TransitPlanet(BaseModel):
    planet: str = Field(description="Planet name, e.g. 'Saturn'")
    sign: str = Field(description="Current sign")
    degree: Optional[float] = Field(default=None)
    nakshatra: Optional[str] = Field(default=None)
    house_from_moon: int = Field(description="House number from natal Moon sign (1-12)")
    retrograde: bool = False


class TransitMoon(BaseModel):
    sign: str
    degree: float
    nakshatra: str
    house_from_natal_moon: int = Field(description="House from natal Moon (1-12)")


class DashaPeriod(BaseModel):
    mahadasha: str = Field(description="Major period lord, e.g. 'Saturn'")
    antardasha: str = Field(description="Sub-period lord, e.g. 'Mercury'")
    pratyantar: Optional[str] = Field(default=None, description="Sub-sub period lord")
    period_start: date
    period_end: date


class PlanetPlacement(BaseModel):
    planet: str
    sign: str
    degree: float
    nakshatra: str
    house_from_lagna: int
    house_from_moon: int
    retrograde: bool = False
    is_exalted: bool = False
    is_debilitated: bool = False
    is_own_sign: bool = False
    navamsha_sign: Optional[str] = Field(default=None, description="Navamsha sign placement for premium refinement")


class HouseLordship(BaseModel):
    house: int
    lord: str
    placed_in_house: int
    placed_in_sign: str


class YogaInfo(BaseModel):
    name: str
    category: str
    planets_involved: list[str]
    description: str
    strength: Optional[str] = Field(default=None, description="Internal rating such as strong, moderate, mixed, fragile")
    activation_status: Optional[str] = Field(default=None, description="Internal timing note such as active now, background, delayed, partially active")
    relevance: Optional[str] = Field(default=None, description="Internal translation of why this yoga matters in lived life")


class LagnaInfo(BaseModel):
    sign: str
    degree: float
    nakshatra: str


class PanchangaContext(BaseModel):
    tithi: Optional[str] = None
    vara: Optional[str] = None
    yoga: Optional[str] = None
    karana: Optional[str] = None
    nakshatra: Optional[str] = None
    translated_summary: Optional[str] = Field(default=None, description="Human-language summary of the panchanga tone")


class RuleInterpretation(BaseModel):
    rule_id: str = Field(description="Unique identifier of the matched rule")
    theme: str = Field(description="Thematic label from the rule output")
    life_area: str = Field(description="Life area affected")
    trait: str = Field(description="Core trait description")
    intensity: str = Field(description="low, medium, or high")
    shadow: str = Field(default="", description="Shadow expression of the trait")
    priority: int = Field(description="Rule priority 0-100")
    evidence: str = Field(default="", description="Matched field=value pairs")
    match_summary: str = Field(default="", description="Human-readable one-line explanation of why this rule matched")
    conditions_met: list[str] = Field(default_factory=list, description="List of human-readable conditions that were satisfied")
    tags: list[str] = Field(default_factory=list, description="Rule tags")


class RuleSignal(BaseModel):
    rule_id: str
    match_summary: str
    conditions_met: list[str] = Field(default_factory=list)
    intensity: str
    shadow: str = ""


class GroupedInsight(BaseModel):
    theme: str = Field(description="Shared thematic label for this group")
    life_areas: list[str] = Field(default_factory=list, description="Unique life areas touched by this group")
    signals: list[RuleSignal] = Field(default_factory=list, description="Individual rule signals in this group")
    combined_trait: str = Field(default="", description="Merged trait summary for LLM consumption")


class LedgerEntry(BaseModel):
    name: str = Field(description="Name of the yoga or life-shaping combination")
    subtitle: str = Field(description="Short living explanation")
    sacred_capacity: str = Field(description="What beautiful power it places in the life")
    distortion: str = Field(description="How it becomes costly or strained")
    purified_expression: str = Field(description="What it becomes when lived truthfully")


class TimingLedgerEntry(BaseModel):
    name: str = Field(description="Timing current or dasha/bhukti name")
    subtitle: str = Field(description="Short living explanation of the chapter")
    chapter_body: str = Field(description="How it shapes the life")
    start: Optional[date] = None
    end: Optional[date] = None


class ContextModifier(BaseModel):
    kind: str = Field(description="Type of modifier: remedy, gemstone, life_stage, maturity, environment, practice, circumstance")
    label: str = Field(description="Short label for the modifier")
    effect: str = Field(description="Internal description of how it may modify expression")
    confidence: Optional[str] = Field(default=None, description="Internal confidence such as low, medium, high")


class PeriodWindow(BaseModel):
    label: str = Field(description="Short name for the window")
    start: date
    end: date
    note: str = Field(description="Internal note about the window's tone or threshold")


class UserProfile(BaseModel):
    name: str
    natal_moon: NatalMoon
    dasha: DashaPeriod
    natal_signature_summary: Optional[str] = Field(default=None, description="Translated internal chart summary for the model only. Human language, not jargon.")
    current_chapter_summary: Optional[str] = Field(default=None, description="Translated summary of the active dasha chapter for the model only.")
    present_center_summary: Optional[str] = Field(default=None, description="Hidden note anchoring the reading in the member's present lived experience.")
    past_pattern_summary: Optional[str] = Field(default=None, description="Hidden note describing how the same chart pattern may have shown up earlier in life.")
    future_arc_summary: Optional[str] = Field(default=None, description="Hidden note describing how the same pattern may mature or unfold later.")
    interpretive_anchors: list[str] = Field(default_factory=list, description="Short translated chart anchors the model should weave into the reading.")
    dominant_themes: list[str] = Field(default_factory=list, description="Top repeated themes in the chart for internal reasoning only.")
    reasoning_hierarchy_summary: Optional[str] = Field(default=None, description="Hidden reasoning note that states natal promise first, dasha activation second, transit trigger third.")
    conflict_resolution_summary: Optional[str] = Field(default=None, description="Hidden note describing mixed signals and how they should be resolved.")
    confidence_summary: Optional[str] = Field(default=None, description="Hidden note describing which claims deserve strong language and which need softer framing.")
    navamsha_summary: Optional[str] = Field(default=None, description="Hidden premium refinement note from Navamsha.")
    panchanga_birth_summary: Optional[str] = Field(default=None, description="Hidden note about birth-day panchanga tone if relevant.")
    rule_interpretations: list[RuleInterpretation] = Field(default_factory=list, description="Structured rule engine interpretations matched from the natal chart and transits.")
    grouped_insights: list[GroupedInsight] = Field(default_factory=list, description="Rule signals grouped by theme, sorted by strength. Use these as primary interpretive anchors.")
    verified_yoga_ledger: list[LedgerEntry] = Field(default_factory=list, description="Source-of-truth ledger of yogas to preserve individually in deep readings.")
    verified_shaping_forces_ledger: list[LedgerEntry] = Field(default_factory=list, description="Source-of-truth ledger of conjunctions, lordship truths, axis burdens, and other shaping forces.")
    verified_timing_ledger: list[TimingLedgerEntry] = Field(default_factory=list, description="Source-of-truth timing ledger of mahadashas and currently relevant sub-periods.")
    absent_or_do_not_claim_ledger: list[str] = Field(default_factory=list, description="Items that should not be claimed in the reading.")
    central_knot_summary: Optional[str] = Field(default=None, description="Hidden note stating the one great knot of the life.")
    entrusted_beauty_summary: Optional[str] = Field(default=None, description="Hidden note naming the sacred beauty and promise of the life.")
    external_modifiers: list[ContextModifier] = Field(default_factory=list, description="Optional real-world or remedial modifiers that affect expression but never override chart truth.")
    lagna: Optional[LagnaInfo] = None
    planets: Optional[list[PlanetPlacement]] = None
    house_lords: Optional[list[HouseLordship]] = None
    yogas: Optional[list[YogaInfo]] = None


class TodayContext(BaseModel):
    date: date
    moon: TransitMoon
    significant_transits: list[TransitPlanet] = Field(default_factory=list)
    today_focus_summary: Optional[str] = Field(default=None, description="Translated summary of today's main experiential focus for the model only.")
    active_life_areas: list[str] = Field(default_factory=list, description="Translated life areas most active now, for the model only.")
    interpretive_anchors: list[str] = Field(default_factory=list, description="Short translated timing anchors the model should weave into the reading.")
    panchanga: Optional[PanchangaContext] = Field(default=None, description="Today's panchanga texture in internal translated form.")
    timing_windows: list[PeriodWindow] = Field(default_factory=list, description="Upcoming threshold windows or weighted dates relevant to this surface.")


class PartnerProfile(BaseModel):
    name: str
    natal_moon: NatalMoon
    dasha: Optional[DashaPeriod] = None
    natal_signature_summary: Optional[str] = Field(default=None, description="Hidden translated summary of the partner chart.")
    current_chapter_summary: Optional[str] = Field(default=None, description="Hidden summary of the partner's current chapter.")
    interpretive_anchors: list[str] = Field(default_factory=list, description="Hidden anchors for the partner chart.")
    dominant_themes: list[str] = Field(default_factory=list, description="Top repeated themes in the partner chart.")
    navamsha_summary: Optional[str] = Field(default=None, description="Hidden premium refinement note from the partner Navamsha.")
    lagna: Optional[LagnaInfo] = None
    planets: Optional[list[PlanetPlacement]] = None


# ── Composite inputs per surface ──────────────────────────────────

class NowInput(BaseModel):
    user: UserProfile
    today: TodayContext


class MandalaInput(BaseModel):
    user: UserProfile
    today: TodayContext


class MandalaDeepReadInput(BaseModel):
    user: UserProfile
    today: TodayContext
    activation: TransitPlanet = Field(description="The specific transit to expand on")


class UnionInput(BaseModel):
    user: UserProfile
    partner: PartnerProfile
    today: TodayContext
    relationship_summary: Optional[str] = Field(default=None, description="Hidden synastry translation describing the bond's central dynamic.")
    shared_growth_edges: list[str] = Field(default_factory=list, description="Hidden relationship tensions or lessons to guide deeper reads.")


class ChartRevealInput(BaseModel):
    user: UserProfile


class BirthChartInput(BaseModel):
    user: UserProfile


class PeriodOverviewInput(BaseModel):
    user: UserProfile
    today: TodayContext
    period: str = Field(description="'weekly' or 'monthly'")
    period_start: date
    period_end: date
    period_focus_summary: Optional[str] = Field(default=None, description="Hidden summary of the broader period arc.")
    key_windows: list[PeriodWindow] = Field(default_factory=list, description="Important windows inside the period.")


# ── Birth Chart Parallel Section Inputs ──────────────────────────

class ChartEssence(BaseModel):
    """Shared global context injected into every parallel section call.

    Contains both tonal anchors AND cross-referencing data so every section
    knows the full landscape of the reading — which yogas exist, which forces,
    what timing chapter is active — and can write coherently without needing
    to see other sections' outputs.
    """
    # Identity
    moon_sign: str
    moon_nakshatra: str
    lagna_sign: str
    mahadasha_lord: str
    antardasha_lord: str

    # Tonal summaries
    natal_signature_summary: str
    current_chapter_summary: str
    central_knot_summary: str
    entrusted_beauty_summary: str
    dominant_themes: list[str] = Field(default_factory=list)
    confidence_summary: str = ""
    reasoning_hierarchy_summary: str = ""
    conflict_resolution_summary: str = ""
    interpretive_anchors: list[str] = Field(default_factory=list)

    # Cross-referencing data (pre-computed from chart, shared across all sections)
    yoga_names: list[str] = Field(default_factory=list, description="Names of all yogas in this chart. Every section can reference these by name.")
    force_names: list[str] = Field(default_factory=list, description="Names of all shaping forces in this chart.")
    current_timing_chapter: str = Field(default="", description="The active mahadasha/antardasha label.")
    recurring_threads: list[str] = Field(default_factory=list, description="Thematic threads that appear across multiple chart factors. All sections should honor these.")


class BirthChartYogasInput(BaseModel):
    chart_essence: ChartEssence
    verified_yoga_ledger: list[LedgerEntry] = Field(default_factory=list)
    absent_or_do_not_claim_ledger: list[str] = Field(default_factory=list)
    grouped_insights: list[GroupedInsight] = Field(default_factory=list, description="Rule engine grouped insights relevant to yogas.")


class BirthChartForcesInput(BaseModel):
    chart_essence: ChartEssence
    verified_shaping_forces_ledger: list[LedgerEntry] = Field(default_factory=list)
    grouped_insights: list[GroupedInsight] = Field(default_factory=list, description="Rule engine grouped insights relevant to forces.")


class BirthChartTimingInput(BaseModel):
    chart_essence: ChartEssence
    verified_timing_ledger: list[TimingLedgerEntry] = Field(default_factory=list)


class SectionDigest(BaseModel):
    """Compact summary of a completed content section for synthesis cross-referencing."""
    yoga_names: list[str] = Field(default_factory=list, description="Names of all yogas that were written, in order.")
    yoga_themes: list[str] = Field(default_factory=list, description="One-line theme per yoga as actually written.")
    force_names: list[str] = Field(default_factory=list, description="Names of all shaping forces that were written.")
    force_themes: list[str] = Field(default_factory=list, description="One-line theme per force as actually written.")
    timing_names: list[str] = Field(default_factory=list, description="Names of all timing currents that were written.")
    current_chapter: Optional[str] = Field(default=None, description="The timing current that is active now.")
    life_phase_titles: list[str] = Field(default_factory=list, description="Titles of all life phases that were written.")
    recurring_threads: list[str] = Field(default_factory=list, description="Themes or tensions that appeared across multiple sections.")


class BirthChartSynthesisInput(BaseModel):
    chart_essence: ChartEssence
    present_center_summary: Optional[str] = None
    past_pattern_summary: Optional[str] = None
    future_arc_summary: Optional[str] = None
    navamsha_summary: Optional[str] = None
    panchanga_birth_summary: Optional[str] = None
    central_knot_summary: Optional[str] = None
    entrusted_beauty_summary: Optional[str] = None
    external_modifiers: list[ContextModifier] = Field(default_factory=list)
    lagna: Optional[LagnaInfo] = None
    planets: Optional[list[PlanetPlacement]] = None
    house_lords: Optional[list[HouseLordship]] = None
    grouped_insights: list[GroupedInsight] = Field(default_factory=list)
    # 3+1: actual prose from completed content sections
    completed_yogas_prose: Optional[str] = Field(default=None, description="Actual prose written by the yogas section. Reference these exact themes in your narrative.")
    completed_forces_prose: Optional[str] = Field(default=None, description="Actual prose written by the forces section. Reference these exact themes in your narrative.")
    completed_timing_prose: Optional[str] = Field(default=None, description="Actual prose written by the timing section. Reference these chapter descriptions in your narrative.")
