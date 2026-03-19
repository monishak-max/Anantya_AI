"""
Bridge — converts computation engine output into LLM input schemas.

This is the glue between:
  engine/calculator.py (raw astronomical data)
  schemas/inputs.py (what the LLM expects)
"""
from __future__ import annotations

from datetime import date

from llm.engine.calculator import NatalChart, TransitSnapshot, PlanetPosition
from llm.schemas.inputs import (
    UserProfile,
    NatalMoon,
    DashaPeriod as InputDasha,
    TodayContext,
    TransitMoon,
    TransitPlanet,
    PartnerProfile,
    NowInput,
    MandalaInput,
    MandalaDeepReadInput,
    UnionInput,
    ChartRevealInput,
    BirthChartInput,
    PlanetPlacement,
    HouseLordship,
    YogaInfo,
    LagnaInfo,
)


SIGN_THEMES = {
    "Aries": "direct movement, urgency, and a need to act before momentum fades",
    "Taurus": "steadiness, patience, and a preference for building what lasts",
    "Gemini": "quick pattern-recognition, mental range, and constant inner movement",
    "Cancer": "protectiveness, emotional memory, and sensitivity to atmosphere",
    "Leo": "presence, dignity, and a quiet need to create from the heart",
    "Virgo": "discernment, precision, and a restless instinct to refine",
    "Libra": "relational awareness, calibration, and an instinct for balance",
    "Scorpio": "depth, privacy, and a habit of feeling more than is shown",
    "Sagittarius": "meaning-seeking, breadth, and a need for forward motion",
    "Capricorn": "responsibility, restraint, and long-range self-command",
    "Aquarius": "distance, perspective, and a need to think outside inherited patterns",
    "Pisces": "porosity, imagination, and a deep response to subtle emotional currents",
}

PLANET_THEMES = {
    "Sun": "identity, confidence, visibility, and self-definition",
    "Moon": "emotional weather, instinct, and inner steadiness",
    "Mercury": "thought, speech, interpretation, and mental load",
    "Venus": "love, taste, receptivity, and what feels nourishing",
    "Mars": "drive, conflict, appetite, and decisive movement",
    "Jupiter": "growth, wisdom, blessing, and larger faith",
    "Saturn": "discipline, time, responsibility, and pressure that matures",
    "Rahu": "hunger, acceleration, appetite, and unfamiliar territory",
    "Ketu": "release, detachment, completion, and inner severing",
}

HOUSE_AREAS = {
    1: "self-definition and personal direction",
    2: "money, voice, values, and stability",
    3: "communication, courage, and daily initiative",
    4: "home, inner steadiness, and private foundations",
    5: "creativity, pleasure, romance, and self-expression",
    6: "workload, discipline, stress, and maintenance",
    7: "partnership, reflection, and close relational truth",
    8: "the unseen, trust, intimacy, and inner transformation",
    9: "meaning, belief, learning, and long-range direction",
    10: "career, visibility, reputation, and contribution",
    11: "community, future plans, and the wider network",
    12: "rest, release, endings, and the inner retreat",
}


def _unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _planet_theme(planet: str) -> str:
    return PLANET_THEMES.get(planet, planet.lower())


def _house_area(house: int | None) -> str:
    return HOUSE_AREAS.get(house or 1, "life direction and lived priorities")


def _build_natal_signature_summary(chart: NatalChart) -> str:
    sun = chart.planets.get("Sun")
    lagna_theme = SIGN_THEMES.get(chart.lagna_sign, "self-direction and visible style")
    moon_theme = SIGN_THEMES.get(chart.moon_sign, "inner sensitivity and instinct")
    sun_theme = SIGN_THEMES.get(sun.sign, "identity and personal radiance") if sun else "identity and personal radiance"
    return (
        f"Outwardly this chart moves through life with {lagna_theme}. "
        f"Emotionally it carries {moon_theme}. "
        f"At the level of identity, it is shaped by {sun_theme}."
    )


def _build_current_chapter_summary(chart: NatalChart) -> str:
    maha = chart.mahadasha.lord
    antar = chart.antardasha.antardasha_lord
    return (
        f"The current chapter emphasizes {_planet_theme(maha)}, with a sharper sub-theme around "
        f"{_planet_theme(antar)}."
    )


def _build_user_anchors(chart: NatalChart) -> list[str]:
    anchors = [
        f"Public style: {SIGN_THEMES.get(chart.lagna_sign, 'visible self-direction')}",
        f"Emotional style: {SIGN_THEMES.get(chart.moon_sign, 'inner sensitivity')}",
        f"Current dasha lesson: {_planet_theme(chart.mahadasha.lord)}",
        f"Current sub-period tone: {_planet_theme(chart.antardasha.antardasha_lord)}",
    ]

    dominant = [p for p in chart.planets.values() if p.is_exalted or p.is_own_sign]
    for p in dominant[:2]:
        anchors.append(f"Dominant planet theme: {_planet_theme(p.planet)}")

    if chart.yogas:
        anchors.append(f"Important chart promise: {chart.yogas[0].description}")

    return _unique_keep_order(anchors)[:6]


def _build_today_focus_summary(transits: TransitSnapshot) -> str:
    moon = transits.planets["Moon"]
    primary_area = _house_area(moon.house_from_moon)
    top_transit = next((p for name, p in transits.planets.items() if name != "Moon" and p.house_from_moon in HOUSE_AREAS), None)
    if top_transit:
        return (
            f"Today heightens {primary_area} while also stirring "
            f"{_planet_theme(top_transit.planet)} in {_house_area(top_transit.house_from_moon)}."
        )
    return f"Today centers on {primary_area}."


def _build_active_life_areas(transits: TransitSnapshot) -> list[str]:
    items = []
    moon = transits.planets["Moon"]
    items.append(_house_area(moon.house_from_moon))
    for name, pos in transits.planets.items():
        if name == "Moon":
            continue
        if pos.house_from_moon in HOUSE_AREAS:
            items.append(_house_area(pos.house_from_moon))
    return _unique_keep_order(items)[:4]


def _build_today_anchors(transits: TransitSnapshot) -> list[str]:
    moon = transits.planets["Moon"]
    anchors = [
        f"The day's emotional weather leans toward {_house_area(moon.house_from_moon)}",
    ]
    for name, pos in transits.planets.items():
        if name == "Moon":
            continue
        if pos.house_from_moon in HOUSE_AREAS:
            anchors.append(f"{_planet_theme(name).capitalize()} is active around {_house_area(pos.house_from_moon)}")
        if pos.retrograde:
            anchors.append(f"A revisiting tone is present around {_house_area(pos.house_from_moon)}")
    return _unique_keep_order(anchors)[:6]


def _chart_to_base_profile(chart: NatalChart, name: str) -> dict:
    """Shared fields for UserProfile and PartnerProfile."""
    return {
        "name": name,
        "natal_moon": NatalMoon(
            sign=chart.moon_sign,
            degree=chart.moon_degree,
            nakshatra=chart.moon_nakshatra,
            nakshatra_pada=chart.moon_nakshatra_pada,
        ),
        "dasha": InputDasha(
            mahadasha=chart.mahadasha.lord,
            antardasha=chart.antardasha.antardasha_lord,
            period_start=chart.mahadasha.start.date(),
            period_end=chart.mahadasha.end.date(),
        ),
        "natal_signature_summary": _build_natal_signature_summary(chart),
        "current_chapter_summary": _build_current_chapter_summary(chart),
        "interpretive_anchors": _build_user_anchors(chart),
    }


def chart_to_user_profile(chart: NatalChart, name: str, full: bool = False) -> UserProfile:
    """
    Convert a NatalChart into a UserProfile for the LLM.

    Args:
        full: If True, include lagna, all planets, house lords, yogas.
              Used for birth chart premium readings.
              If False, only Moon + dasha (lighter payload for daily surfaces).
    """
    base = _chart_to_base_profile(chart, name)

    if full:
        base["lagna"] = LagnaInfo(
            sign=chart.lagna_sign,
            degree=chart.lagna_degree,
            nakshatra=chart.lagna_nakshatra,
        )
        base["planets"] = [
            PlanetPlacement(
                planet=p.planet,
                sign=p.sign,
                degree=p.degree_in_sign,
                nakshatra=p.nakshatra,
                house_from_lagna=p.house_from_lagna or 1,
                house_from_moon=p.house_from_moon or 1,
                retrograde=p.retrograde,
                is_exalted=p.is_exalted,
                is_debilitated=p.is_debilitated,
                is_own_sign=p.is_own_sign,
            )
            for p in chart.planets.values()
        ]
        base["house_lords"] = [
            HouseLordship(
                house=hl.house,
                lord=hl.lord,
                placed_in_house=hl.placed_in_house,
                placed_in_sign=hl.placed_in_sign,
            )
            for hl in chart.house_lords
        ]
        base["yogas"] = [
            YogaInfo(
                name=y.name,
                category=y.category,
                planets_involved=y.planets_involved,
                description=y.description,
            )
            for y in chart.yogas
        ]

    return UserProfile(**base)


def chart_to_partner_profile(chart: NatalChart, name: str) -> PartnerProfile:
    """Convert a NatalChart into a PartnerProfile for Union readings."""
    base = _chart_to_base_profile(chart, name)
    return PartnerProfile(**base)


def _pick_significant_transits(
    transits: TransitSnapshot,
    natal_moon_sign: str,
) -> list[TransitPlanet]:
    """
    Select the most astrologically significant transits for the reading.

    Significance rules:
    - Slow planets (Saturn, Jupiter, Rahu, Ketu) are always significant
    - Planets in key houses from Moon (1, 4, 7, 8, 10, 12) get priority
    - Retrograde planets are flagged
    """
    significant = []
    slow_planets = {"Saturn", "Jupiter", "Rahu", "Ketu"}
    key_houses = {1, 4, 5, 7, 8, 10, 12}

    for name, pos in transits.planets.items():
        if name == "Moon":
            continue  # Moon is handled separately

        is_slow = name in slow_planets
        is_key_house = pos.house_from_moon in key_houses if pos.house_from_moon else False

        if is_slow or is_key_house:
            significant.append(TransitPlanet(
                planet=name,
                sign=pos.sign,
                degree=pos.degree_in_sign,
                nakshatra=pos.nakshatra,
                house_from_moon=pos.house_from_moon or 1,
                retrograde=pos.retrograde,
            ))

    # Sort by significance: slow planets first, then by house importance
    house_weight = {1: 10, 7: 9, 10: 8, 4: 7, 8: 6, 5: 5, 12: 4}
    significant.sort(key=lambda t: (
        0 if t.planet in slow_planets else 1,
        -house_weight.get(t.house_from_moon, 0),
    ))

    return significant[:6]  # Cap at 6 to keep context manageable


def transits_to_today_context(
    transits: TransitSnapshot,
    natal_moon_sign: str,
) -> TodayContext:
    """Convert a TransitSnapshot into a TodayContext for the LLM."""
    moon = transits.planets["Moon"]

    return TodayContext(
        date=transits.date,
        moon=TransitMoon(
            sign=moon.sign,
            degree=moon.degree_in_sign,
            nakshatra=moon.nakshatra,
            house_from_natal_moon=moon.house_from_moon or 1,
        ),
        significant_transits=_pick_significant_transits(transits, natal_moon_sign),
        today_focus_summary=_build_today_focus_summary(transits),
        active_life_areas=_build_active_life_areas(transits),
        interpretive_anchors=_build_today_anchors(transits),
    )


# ── Convenience builders for each surface ──────────────────────────

def build_now_input(chart: NatalChart, transits: TransitSnapshot, name: str) -> NowInput:
    return NowInput(
        user=chart_to_user_profile(chart, name, full=False),
        today=transits_to_today_context(transits, chart.moon_sign),
    )


def build_mandala_input(chart: NatalChart, transits: TransitSnapshot, name: str) -> MandalaInput:
    return MandalaInput(
        user=chart_to_user_profile(chart, name, full=False),
        today=transits_to_today_context(transits, chart.moon_sign),
    )


def build_union_input(
    chart: NatalChart,
    partner_chart: NatalChart,
    transits: TransitSnapshot,
    name: str,
    partner_name: str,
) -> UnionInput:
    return UnionInput(
        user=chart_to_user_profile(chart, name, full=False),
        partner=chart_to_partner_profile(partner_chart, partner_name),
        today=transits_to_today_context(transits, chart.moon_sign),
    )


def build_chart_reveal_input(chart: NatalChart, name: str) -> ChartRevealInput:
    """Chart reveal gets the FULL profile — needs lagna, planets, yogas for specificity."""
    return ChartRevealInput(
        user=chart_to_user_profile(chart, name, full=True),
    )


def build_birth_chart_input(chart: NatalChart, name: str) -> BirthChartInput:
    """Birth chart gets the FULL profile — lagna, all planets, house lords, yogas."""
    return BirthChartInput(
        user=chart_to_user_profile(chart, name, full=True),
    )


def build_mandala_deep_read_input(
    chart: NatalChart, transits: TransitSnapshot, name: str, activation_planet: str = "Saturn"
) -> MandalaDeepReadInput:
    """Mandala deep read zooms into one specific transit activation."""
    today_ctx = transits_to_today_context(transits, chart.moon_sign)
    # Find the matching transit or use the first significant one
    activation = None
    for t in today_ctx.significant_transits:
        if t.planet == activation_planet:
            activation = t
            break
    if activation is None and today_ctx.significant_transits:
        activation = today_ctx.significant_transits[0]
    if activation is None:
        # Fallback: create a minimal transit from Moon
        activation = TransitPlanet(
            planet="Moon", sign=transits.moon_sign,
            house_from_moon=transits.moon_house_from_natal or 1,
            retrograde=False,
        )
    return MandalaDeepReadInput(
        user=chart_to_user_profile(chart, name, full=False),
        today=today_ctx,
        activation=activation,
    )


def build_period_overview_input(
    chart: NatalChart, transits: TransitSnapshot, name: str, period: str = "weekly"
) -> "PeriodOverviewInput":
    """Build input for weekly or monthly overview."""
    from llm.schemas.inputs import PeriodOverviewInput
    from datetime import date as _date
    return PeriodOverviewInput(
        user=chart_to_user_profile(chart, name, full=False),
        today=transits_to_today_context(transits, chart.moon_sign),
        period=period,
        period_start=_date.today(),
    )
