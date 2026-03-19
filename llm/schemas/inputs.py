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


class LagnaInfo(BaseModel):
    sign: str
    degree: float
    nakshatra: str


class UserProfile(BaseModel):
    name: str
    natal_moon: NatalMoon
    dasha: DashaPeriod
    natal_signature_summary: Optional[str] = Field(default=None, description="Translated internal chart summary for the model only. Human language, not jargon.")
    current_chapter_summary: Optional[str] = Field(default=None, description="Translated summary of the active dasha chapter for the model only.")
    interpretive_anchors: list[str] = Field(default_factory=list, description="Short translated chart anchors the model should weave into the reading.")
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


class PartnerProfile(BaseModel):
    name: str
    natal_moon: NatalMoon
    dasha: Optional[DashaPeriod] = None


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
