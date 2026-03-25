"""
Bridge — converts computation engine output into LLM input schemas.

This is the glue between:
  engine/calculator.py (raw astronomical data)
  schemas/inputs.py (what the LLM expects)
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from llm.engine.calculator import NatalChart, TransitSnapshot, PlanetPosition
from llm.engine.panchanga import compute_panchanga
from llm.engine.transits import next_moon_sign_change
from llm.engine.rules.evaluator import ConditionMatch, RuleMatch
from llm.engine.rules.schema import Operator, Rule
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
    PeriodOverviewInput,
    PlanetPlacement,
    HouseLordship,
    YogaInfo,
    LagnaInfo,
    PanchangaContext,
    ContextModifier,
    PeriodWindow,
    RuleInterpretation,
    RuleSignal,
    GroupedInsight,
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


def _planet_strength_label(p: PlanetPosition) -> str:
    if p.is_exalted:
        return "strong"
    if p.is_own_sign:
        return "steady"
    if p.is_debilitated:
        return "mixed"
    if p.retrograde:
        return "revising"
    return "moderate"


def _planet_condition_phrase(p: PlanetPosition) -> str:
    if p.is_exalted:
        return f"{p.planet} is a major strength in this chart"
    if p.is_own_sign:
        return f"{p.planet} is stable and self-possessed in this chart"
    if p.is_debilitated:
        return f"{p.planet} carries extra strain or overcompensation in this chart"
    if p.retrograde:
        return f"{p.planet} tends to work through revision, reflection, and delayed clarity"
    return f"{p.planet} plays a meaningful but not dominant role"


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
        f"The current chapter is led by {_planet_theme(maha)}, with a sharper sub-theme around "
        f"{_planet_theme(antar)}. Read the chart through this chapter before letting current weather speak."
    )


def _build_present_center_summary(chart: NatalChart) -> str:
    dominant = _dominant_planets(chart)
    dominant_names = ", ".join(p.planet for p in dominant[:2]) if dominant else chart.mahadasha.lord
    return (
        f"Begin from the member's life as it is now: the chart currently expresses itself through "
        f"{SIGN_THEMES.get(chart.lagna_sign, 'visible self-direction')}, carries {SIGN_THEMES.get(chart.moon_sign, 'inner sensitivity')} inside, "
        f"and is presently being animated by the {chart.mahadasha.lord}/{chart.antardasha.antardasha_lord} chapter. "
        f"Let {dominant_names} describe the living pattern, not a birth-time label."
    )


def _build_past_pattern_summary(chart: NatalChart) -> str:
    moon_area = _house_area(chart.planets.get('Moon').house_from_lagna) if chart.planets.get('Moon') else 'the inner world'
    saturn = chart.planets.get('Saturn')
    rahu = chart.planets.get('Rahu')
    if saturn and saturn.house_from_moon in {1, 4, 7, 8, 12}:
        tone = 'earlier in life this may have shown up as emotional caution, self-control, or carrying more than was said aloud'
    elif rahu and rahu.house_from_moon in {1, 7, 8, 12}:
        tone = 'earlier in life this may have felt like appetite, intensity, or a restless push toward what was not yet settled'
    else:
        tone = 'earlier in life this pattern may have appeared first as instinct before it became conscious style'
    return f"Use the past only to explain formation: around {moon_area}, {tone}."


def _build_future_arc_summary(chart: NatalChart) -> str:
    maha = chart.mahadasha.lord
    areas = []
    for p in _dominant_planets(chart)[:2]:
        areas.append(_planet_theme(p.planet))
    dominant_future = ', '.join(areas[:2]) if areas else _planet_theme(maha)
    return (
        f"Use the future as arc, not prediction: over time this chart matures through {dominant_future}, "
        f"and the member grows by living the current { _planet_theme(maha) } chapter more consciously."
    )


def _dominant_planets(chart: NatalChart) -> list[PlanetPosition]:
    planets = list(chart.planets.values())
    planets.sort(
        key=lambda p: (
            0 if p.is_exalted else 1,
            0 if p.is_own_sign else 1,
            0 if (p.house_from_lagna in {1, 4, 7, 10}) else 1,
            0 if p.planet in {chart.mahadasha.lord, chart.antardasha.antardasha_lord} else 1,
        )
    )
    return planets[:4]


def _build_dominant_themes(chart: NatalChart) -> list[str]:
    themes = [
        f"Visible style: {SIGN_THEMES.get(chart.lagna_sign, 'self-direction and visible style')}",
        f"Emotional base: {SIGN_THEMES.get(chart.moon_sign, 'inner sensitivity and instinct')}",
        f"Current chapter: {_planet_theme(chart.mahadasha.lord)} shaped by {_planet_theme(chart.antardasha.antardasha_lord)}",
    ]
    for p in _dominant_planets(chart)[:2]:
        themes.append(f"Dominant planetary current: {_planet_theme(p.planet)}")
    for y in chart.yogas[:2]:
        themes.append(f"Important promise: {y.description}")
    return _unique_keep_order(themes)[:6]


def _build_reasoning_hierarchy_summary(chart: NatalChart) -> str:
    dominant = _dominant_planets(chart)
    dominant_names = ", ".join(p.planet for p in dominant[:2]) if dominant else chart.mahadasha.lord
    return (
        f"Start from natal promise: Lagna in {chart.lagna_sign}, Moon in {chart.moon_sign}, and the stronger weight of {dominant_names}. "
        f"Then let the {chart.mahadasha.lord}/{chart.antardasha.antardasha_lord} chapter decide what is active now. "
        f"Use transits only as triggers or weather. Do not let temporary movement override the chart's deeper structure."
    )


def _build_conflict_resolution_summary(chart: NatalChart) -> str:
    moon_saturn = chart.planets.get("Saturn") and chart.planets["Saturn"].house_from_moon in {1, 4, 7, 8, 12}
    moon_rahu = chart.planets.get("Rahu") and chart.planets["Rahu"].house_from_moon in {1, 7, 8, 12}
    if moon_saturn and moon_rahu:
        return "Mixed signals likely come from emotional restraint and appetite pulling in different directions. Name tension honestly, but do not confuse intensity with destiny."
    if moon_saturn:
        return "Where the chart looks composed outside and burdened inside, prioritize the underlying sensitivity over surface restraint."
    if moon_rahu:
        return "Where the chart swings between appetite and uncertainty, frame it as growth pressure, not instability alone."
    return "When signals differ, let repeated natal themes and the active dasha outrank any single temporary trigger."


def _build_confidence_summary(chart: NatalChart) -> str:
    repeated = 0
    for p in chart.planets.values():
        if p.is_exalted or p.is_own_sign:
            repeated += 1
    if chart.yogas:
        repeated += 1
    if repeated >= 3:
        return "Several chart signals repeat the same lesson. Strong claims can be stated clearly, but keep dignity and agency intact."
    if repeated == 2:
        return "There is good corroboration. Speak with confidence, but leave room for the member's lived context."
    return "Signals are more mixed. Lead with pattern and possibility rather than certainty."


def _build_user_anchors(chart: NatalChart) -> list[str]:
    anchors = [
        f"Public style: {SIGN_THEMES.get(chart.lagna_sign, 'visible self-direction')}",
        f"Emotional style: {SIGN_THEMES.get(chart.moon_sign, 'inner sensitivity')}",
        f"Current dasha lesson: {_planet_theme(chart.mahadasha.lord)}",
        f"Current sub-period tone: {_planet_theme(chart.antardasha.antardasha_lord)}",
    ]
    for p in _dominant_planets(chart)[:2]:
        anchors.append(f"Dominant planet theme: {_planet_theme(p.planet)}")
    if chart.yogas:
        anchors.append(f"Important chart promise: {chart.yogas[0].description}")
    return _unique_keep_order(anchors)[:7]


def _build_navamsha_summary(chart: NatalChart) -> str | None:
    moon = chart.planets.get("Moon")
    venus = chart.planets.get("Venus")
    parts = []
    if moon and moon.navamsha_sign:
        parts.append(f"The inner emotional refinement of the chart leans toward {SIGN_THEMES.get(moon.navamsha_sign, moon.navamsha_sign.lower())}")
    if venus and venus.navamsha_sign:
        parts.append(f"Relationship maturity deepens through {SIGN_THEMES.get(venus.navamsha_sign, venus.navamsha_sign.lower())}")
    if not parts:
        return None
    return ". ".join(parts) + "."


def _build_birth_panchanga_summary(chart: NatalChart) -> str | None:
    panch = chart.panchanga or {}
    if not panch:
        return None
    tithi = (panch.get("tithi") or {}).get("name")
    vara = (panch.get("vara") or {}).get("name")
    yoga = (panch.get("yoga") or {}).get("name")
    bits = [bit for bit in [tithi, vara, yoga] if bit]
    if not bits:
        return None
    return f"Birth-day panchanga carries {' / '.join(bits)} energy. Use this as texture, never as the main claim."


def _translate_panchanga(panch: dict | None) -> PanchangaContext | None:
    if not panch:
        return None
    tithi = (panch.get("tithi") or {}).get("name")
    vara = (panch.get("vara") or {}).get("name")
    yoga = (panch.get("yoga") or {}).get("name")
    karana = (panch.get("karana") or {}).get("name")
    nak = (panch.get("nakshatra") or {}).get("name")
    summary_bits = []
    if tithi:
        summary_bits.append(f"the day carries the texture of {tithi}")
    if vara:
        summary_bits.append(f"it moves through a {vara.lower()} rhythm")
    if yoga:
        summary_bits.append(f"and is colored by {yoga.lower()} yoga")
    translated = None
    if summary_bits:
        translated = ", ".join(summary_bits).replace(", and", " and") + "."
    return PanchangaContext(tithi=tithi, vara=vara, yoga=yoga, karana=karana, nakshatra=nak, translated_summary=translated)


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


def _coerce_modifier(item: dict | ContextModifier) -> ContextModifier:
    if isinstance(item, ContextModifier):
        return item
    return ContextModifier(
        kind=str(item.get("kind", "circumstance")),
        label=str(item.get("label", item.get("name", "modifier"))),
        effect=str(item.get("effect", item.get("note", "This may shape expression without overriding chart truth."))),
        confidence=item.get("confidence"),
    )


def _build_modifier_objects(external_modifiers: list[dict] | list[ContextModifier] | None) -> list[ContextModifier]:
    if not external_modifiers:
        return []
    return [_coerce_modifier(item) for item in external_modifiers]


def _yoga_activation_status(chart: NatalChart, planets: list[str]) -> str:
    active_lords = {chart.mahadasha.lord, chart.antardasha.antardasha_lord}
    if active_lords.intersection(planets):
        return "active now"
    if active_lords.intersection({"Rahu", "Ketu"}) and set(planets).intersection({"Rahu", "Ketu"}):
        return "activated through the current karmic chapter"
    return "background promise"


def _yoga_strength(chart: NatalChart, planets: list[str]) -> str:
    score = 0
    for planet_name in planets:
        p = chart.planets.get(planet_name)
        if not p:
            continue
        if p.is_exalted:
            score += 2
        elif p.is_own_sign:
            score += 1
        elif p.is_debilitated:
            score -= 1
    if score >= 2:
        return "strong"
    if score <= -1:
        return "fragile"
    if score == 1:
        return "supportive"
    return "mixed"


def _yoga_relevance(chart: NatalChart, description: str, planets: list[str]) -> str:
    active = chart.mahadasha.lord in planets or chart.antardasha.antardasha_lord in planets
    prefix = "This pattern is especially worth using now" if active else "This pattern belongs more to the chart's background architecture"
    return f"{prefix}: {description}"


_KENDRA_HOUSES = {1, 4, 7, 10}
_TRIKONA_HOUSES = {1, 5, 9}
_DUSTHANA_HOUSES = {6, 8, 12}
_UPACHAYA_HOUSES = {3, 6, 10, 11}

_HOUSE_CLASS = {
    "kendra": (_KENDRA_HOUSES, "Kendra houses amplify planetary visibility and action"),
    "trikona": (_TRIKONA_HOUSES, "Trikona houses support fortune, purpose, and growth"),
    "dusthana": (_DUSTHANA_HOUSES, "Dusthana houses carry challenge, effort, or hidden work"),
    "upachaya": (_UPACHAYA_HOUSES, "Upachaya houses grow stronger with time and effort"),
}

_DIGNITY_HINTS = {
    "exalted": "At peak strength — the planet expresses its highest qualities",
    "own_sign": "In its own domain — comfortable, self-directed, and reliable",
    "debilitated": "At its most challenged — expression requires extra effort or support",
}


def _house_info(house: int) -> tuple[str, str]:
    """Return (class_name, meaning_hint) for a house number."""
    for cls, (houses, hint) in _HOUSE_CLASS.items():
        if house in houses:
            return cls, hint
    return "", ""


def _planet_from_field(field: str) -> str:
    return field.split("_")[0].capitalize()


def _expand_condition(cm: ConditionMatch) -> list[str]:
    """Turn one ConditionMatch into 1-3 grounding statements: fact, classification, meaning."""
    field = cm.condition.field
    op = cm.condition.op
    actual = cm.actual_value
    planet = _planet_from_field(field)
    lines: list[str] = []

    if op == Operator.EQ:
        if "sign" in field:
            lines.append(f"{planet} is in {actual}")
        elif "is_exalted" in field and actual:
            lines.append(f"{planet} is exalted")
            lines.append(_DIGNITY_HINTS["exalted"])
        elif "is_own_sign" in field and actual:
            lines.append(f"{planet} is in its own sign")
            lines.append(_DIGNITY_HINTS["own_sign"])
        elif "is_debilitated" in field and actual:
            lines.append(f"{planet} is debilitated")
            lines.append(_DIGNITY_HINTS["debilitated"])
        elif "nakshatra" in field:
            lines.append(f"{planet}'s nakshatra is {actual}")
        elif "mahadasha" in field or "antardasha" in field:
            lines.append(f"{field.replace('_', ' ').capitalize()} is {actual}")
        else:
            lines.append(f"{field} is {actual}")

    elif op == Operator.IN:
        if "house" in field and isinstance(actual, int):
            lines.append(f"{planet} is in house {actual}")
            cls, hint = _house_info(actual)
            if cls:
                lines.append(f"House {actual} is a {cls} house")
                lines.append(hint)
        else:
            lines.append(f"{planet} is one of {cm.condition.value}")

    elif op == Operator.RANGE:
        lo, hi = cm.condition.value
        if "degree" in field:
            lines.append(f"{planet} is at {actual:.0f}° in its sign")
            lines.append(f"This falls within the {lo}°–{hi}° range")
        else:
            lines.append(f"{field} is {actual} (within {lo}–{hi})")

    elif op == Operator.GT:
        if "degree" in field:
            lines.append(f"{planet} is at {actual:.0f}° in its sign")
            lines.append(f"Past {cm.condition.value}° — late-degree placement, suggesting matured or concentrated energy")
        else:
            lines.append(f"{field} is {actual} (above {cm.condition.value})")

    elif op == Operator.LT:
        if "degree" in field:
            lines.append(f"{planet} is at {actual:.0f}° in its sign")
            lines.append(f"Before {cm.condition.value}° — early-degree placement, suggesting fresh or unrefined energy")
        else:
            lines.append(f"{field} is {actual} (below {cm.condition.value})")

    else:
        lines.append(f"{field} is {actual}")

    return lines


def _build_match_summary(trait: str, conditions: list[str]) -> str:
    """One-line grounding summary from the trait + first condition fact."""
    if not conditions:
        return trait
    # First condition is always the raw fact — use it as grounding
    return f"{conditions[0]}, {trait[0].lower()}{trait[1:]}" if trait else conditions[0]


def _rule_matches_to_interpretations(matches: list[RuleMatch]) -> list[RuleInterpretation]:
    result = []
    for m in matches:
        conditions_met: list[str] = []
        for cm in m.matched_conditions:
            if cm.matched:
                conditions_met.extend(_expand_condition(cm))
        result.append(RuleInterpretation(
            rule_id=m.rule.id,
            theme=m.rule.output.theme,
            life_area=m.rule.output.life_area,
            trait=m.rule.output.trait,
            intensity=m.rule.output.intensity,
            shadow=m.rule.output.shadow,
            priority=m.priority,
            evidence=m.evidence_summary,
            match_summary=_build_match_summary(m.rule.output.trait, conditions_met),
            conditions_met=conditions_met,
            tags=list(m.rule.tags),
        ))
    return result


_INTENSITY_RANK = {"high": 3, "medium": 2, "low": 1}
_MAX_INSIGHTS = 7

# Words that are too generic to count as unique content when merging traits
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "to", "for", "is", "are",
    "that", "this", "with", "from", "by", "as", "on", "at", "be", "may",
})


def _extract_phrases(text: str) -> list[str]:
    """Split a trait into clause-level phrases on '—', ','."""
    parts: list[str] = []
    for chunk in text.replace("—", "|").replace("–", "|").split("|"):
        for sub in chunk.split(", "):
            cleaned = sub.strip().strip(",").strip()
            # Strip leading conjunctions
            for prefix in ("and ", "or ", "but "):
                if cleaned.lower().startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            if cleaned:
                parts.append(cleaned)
    return parts


def _content_words(phrase: str) -> set[str]:
    """Extract meaningful words from a phrase for overlap detection."""
    return {w.lower() for w in phrase.split() if w.lower() not in _STOP_WORDS and len(w) > 2}


def _synthesize_traits(traits: list[str]) -> str:
    """Merge multiple trait strings into one coherent sentence.

    Strategy:
    - 1 trait: return as-is
    - 2+ traits: use first trait as anchor, extract novel phrases from the rest,
      append as 'deepened by ...' or 'reinforced by ...'
    """
    # Deduplicate while preserving order
    unique: list[str] = []
    seen: set[str] = set()
    for t in traits:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)

    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]

    # First trait is the anchor (highest priority rule)
    anchor = unique[0]
    anchor_words = _content_words(anchor)

    # Extract novel phrases from remaining traits
    novel: list[str] = []
    for trait in unique[1:]:
        for phrase in _extract_phrases(trait):
            phrase_words = _content_words(phrase)
            # Keep phrase only if it brings >50% new content words
            if phrase_words and len(phrase_words - anchor_words) > len(phrase_words) * 0.5:
                novel.append(phrase)
                anchor_words |= phrase_words  # absorb to prevent further dupes

    if not novel:
        return anchor

    # Lowercase first char of novel phrases for mid-sentence flow,
    # but preserve proper nouns (planet names, sign names)
    _PROPER = frozenset({
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    })

    def _lc(s: str) -> str:
        if not s:
            return s
        first_word = s.split()[0] if s.split() else ""
        if first_word in _PROPER:
            return s
        return s[0].lower() + s[1:]

    lowered = [_lc(p) for p in novel[:3]]  # cap at 3 novel additions
    if len(lowered) == 1:
        suffix = lowered[0]
    elif len(lowered) == 2:
        suffix = f"{lowered[0]} and {lowered[1]}"
    else:
        suffix = f"{lowered[0]}, {lowered[1]}, and {lowered[2]}"

    if anchor.rstrip().endswith((".", "!", "?")):
        return f"{anchor} Also shaped by {suffix}"
    return f"{anchor} — deepened by {suffix}"


def _group_rule_interpretations(interps: list[RuleInterpretation]) -> tuple[list[str], list[GroupedInsight]]:
    """Sort, cap, group, and merge rule interpretations for LLM consumption.

    Returns (dominant_themes, grouped_insights).
    """
    if not interps:
        return [], []

    # 1. Sort by priority desc, then intensity desc
    scored = sorted(
        interps,
        key=lambda r: (r.priority, _INTENSITY_RANK.get(r.intensity, 0)),
        reverse=True,
    )

    # 2. Cap at top N
    top = scored[:_MAX_INSIGHTS]

    # 3. Group by theme, preserving sort order for first appearance
    groups: dict[str, list[RuleInterpretation]] = {}
    for r in top:
        groups.setdefault(r.theme, []).append(r)

    # 4. Build GroupedInsight objects
    insights: list[GroupedInsight] = []
    for theme, members in groups.items():
        life_areas = _unique_keep_order([m.life_area for m in members])
        signals = [
            RuleSignal(
                rule_id=m.rule_id,
                match_summary=m.match_summary,
                conditions_met=m.conditions_met,
                intensity=m.intensity,
                shadow=m.shadow,
            )
            for m in members
        ]
        combined = _synthesize_traits([m.trait for m in members])

        insights.append(GroupedInsight(
            theme=theme,
            life_areas=life_areas,
            signals=signals,
            combined_trait=combined,
        ))

    # 5. Dominant themes = ordered theme list from grouped insights
    dominant = [g.theme for g in insights]

    return dominant, insights


def _chart_to_base_profile(chart: NatalChart, name: str, external_modifiers: list[dict] | list[ContextModifier] | None = None) -> dict:
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
        "present_center_summary": _build_present_center_summary(chart),
        "past_pattern_summary": _build_past_pattern_summary(chart),
        "future_arc_summary": _build_future_arc_summary(chart),
        "interpretive_anchors": _build_user_anchors(chart),
        "dominant_themes": _build_dominant_themes(chart),
        "reasoning_hierarchy_summary": _build_reasoning_hierarchy_summary(chart),
        "conflict_resolution_summary": _build_conflict_resolution_summary(chart),
        "confidence_summary": _build_confidence_summary(chart),
        "navamsha_summary": _build_navamsha_summary(chart),
        "panchanga_birth_summary": _build_birth_panchanga_summary(chart),
        "external_modifiers": _build_modifier_objects(external_modifiers),
    }


def chart_to_user_profile(
    chart: NatalChart,
    name: str,
    full: bool = False,
    external_modifiers: list[dict] | list[ContextModifier] | None = None,
    rule_matches: list[RuleMatch] | None = None,
) -> UserProfile:
    base = _chart_to_base_profile(chart, name, external_modifiers)

    if rule_matches:
        interps = _rule_matches_to_interpretations(rule_matches)
        base["rule_interpretations"] = interps
        rule_themes, grouped = _group_rule_interpretations(interps)
        base["grouped_insights"] = grouped
        # Merge rule-derived themes into dominant_themes (existing bridge themes take precedence)
        existing = base.get("dominant_themes", [])
        base["dominant_themes"] = _unique_keep_order(existing + rule_themes)

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
                navamsha_sign=p.navamsha_sign,
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
                strength=_yoga_strength(chart, y.planets_involved),
                activation_status=_yoga_activation_status(chart, y.planets_involved),
                relevance=_yoga_relevance(chart, y.description, y.planets_involved),
            )
            for y in chart.yogas
        ]

    return UserProfile(**base)


def chart_to_partner_profile(chart: NatalChart, name: str, full: bool = False) -> PartnerProfile:
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
                navamsha_sign=p.navamsha_sign,
            )
            for p in chart.planets.values()
        ]
    return PartnerProfile(**base)


def _pick_significant_transits(transits: TransitSnapshot) -> list[TransitPlanet]:
    significant = []
    slow_planets = {"Saturn", "Jupiter", "Rahu", "Ketu"}
    key_houses = {1, 4, 5, 7, 8, 10, 12}
    for name, pos in transits.planets.items():
        if name == "Moon":
            continue
        is_slow = name in slow_planets
        is_key_house = pos.house_from_moon in key_houses if pos.house_from_moon else False
        if is_slow or is_key_house:
            significant.append(
                TransitPlanet(
                    planet=name,
                    sign=pos.sign,
                    degree=pos.degree_in_sign,
                    nakshatra=pos.nakshatra,
                    house_from_moon=pos.house_from_moon or 1,
                    retrograde=pos.retrograde,
                )
            )
    house_weight = {1: 10, 7: 9, 10: 8, 4: 7, 8: 6, 5: 5, 12: 4}
    significant.sort(key=lambda t: (0 if t.planet in slow_planets else 1, -house_weight.get(t.house_from_moon, 0)))
    return significant[:6]


def _build_timing_windows(target_date: date, period: str = "daily") -> list[PeriodWindow]:
    windows: list[PeriodWindow] = []
    try:
        moon_change = next_moon_sign_change(target_date)
        moon_date = date.fromisoformat(moon_change["date"])
        windows.append(
            PeriodWindow(
                label=f"Moon shift into {moon_change.get('to_sign', 'a new sign')}",
                start=moon_date,
                end=moon_date,
                note=f"Emotional tone changes as the Moon moves from {moon_change.get('from_sign', 'the current sign')} into {moon_change.get('to_sign', 'a new sign')}."
            )
        )
    except Exception:
        pass

    if period == "weekly":
        start = target_date
        windows.append(PeriodWindow(label="Opening stretch", start=start, end=min(start + timedelta(days=2), start + timedelta(days=6)), note="Use the opening days to notice what is beginning to press for attention."))
        windows.append(PeriodWindow(label="Midweek pivot", start=start + timedelta(days=3), end=start + timedelta(days=4), note="Midweek usually shows what is ripening versus what is merely noisy."))
    elif period == "monthly":
        start = target_date.replace(day=1)
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = start.replace(day=last_day)
        windows.append(PeriodWindow(label="Opening phase", start=start, end=min(start + timedelta(days=9), end), note="The opening of the month reveals the main pressure line."))
        windows.append(PeriodWindow(label="Middle turn", start=min(start + timedelta(days=10), end), end=min(start + timedelta(days=20), end), note="The middle of the month shows what must be adjusted, not just endured."))
        windows.append(PeriodWindow(label="Closing phase", start=min(start + timedelta(days=21), end), end=end, note="The closing days show what settles and what carries forward."))

    return windows[:4]


def transits_to_today_context(transits: TransitSnapshot, natal_moon_sign: str) -> TodayContext:
    moon = transits.planets["Moon"]
    try:
        panch = compute_panchanga(transits.date)
    except Exception:
        panch = None
    return TodayContext(
        date=transits.date,
        moon=TransitMoon(
            sign=moon.sign,
            degree=moon.degree_in_sign,
            nakshatra=moon.nakshatra,
            house_from_natal_moon=moon.house_from_moon or 1,
        ),
        significant_transits=_pick_significant_transits(transits),
        today_focus_summary=_build_today_focus_summary(transits),
        active_life_areas=_build_active_life_areas(transits),
        interpretive_anchors=_build_today_anchors(transits),
        panchanga=_translate_panchanga(panch),
        timing_windows=_build_timing_windows(transits.date),
    )


def _relationship_summary(chart: NatalChart, partner_chart: NatalChart) -> str:
    moon_distance = ((["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"].index(partner_chart.moon_sign) - ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"].index(chart.moon_sign)) % 12) + 1
    if moon_distance in {1, 5, 7, 9, 11}:
        rhythm = "There is a natural emotional recognition between these charts, even when style differs."
    elif moon_distance in {6, 8, 12}:
        rhythm = "This bond can feel karmically charged, where attraction and friction teach each other at the same time."
    else:
        rhythm = "The charts create complementarity more than sameness, which can be stabilizing when handled consciously."
    return (
        f"{rhythm} One chart currently emphasizes {_planet_theme(chart.mahadasha.lord)}, while the other moves through {_planet_theme(partner_chart.mahadasha.lord)}. "
        f"Read the bond through timing and maturity, not chemistry alone."
    )


def _shared_growth_edges(chart: NatalChart, partner_chart: NatalChart) -> list[str]:
    edges = [
        f"One chart is learning {_planet_theme(chart.mahadasha.lord)} while the other is learning {_planet_theme(partner_chart.mahadasha.lord)}.",
        "Do not mistake difference in timing for lack of care.",
    ]
    if chart.planets.get("Saturn") and partner_chart.planets.get("Rahu"):
        edges.append("One partner may move through caution while the other moves through appetite or acceleration.")
    return edges[:3]


def _period_bounds(target_date: date, period: str) -> tuple[date, date]:
    if period == "weekly":
        return target_date, target_date + timedelta(days=6)
    start = target_date.replace(day=1)
    last_day = calendar.monthrange(start.year, start.month)[1]
    return start, start.replace(day=last_day)


def _period_focus_summary(chart: NatalChart, transits: TransitSnapshot, period: str, start: date, end: date) -> str:
    areas = ", ".join(_build_active_life_areas(transits)[:2])
    span = "week" if period == "weekly" else "month"
    return (
        f"Across this {span}, keep natal promise in front, read the {chart.mahadasha.lord}/{chart.antardasha.antardasha_lord} chapter as the active storyline, "
        f"and treat current transits as triggers around {areas}. The useful horizon runs from {start.isoformat()} to {end.isoformat()}."
    )


def build_now_input(chart: NatalChart, transits: TransitSnapshot, name: str, external_modifiers: list[dict] | None = None, rule_matches: list[RuleMatch] | None = None) -> NowInput:
    return NowInput(user=chart_to_user_profile(chart, name, full=False, external_modifiers=external_modifiers, rule_matches=rule_matches), today=transits_to_today_context(transits, chart.moon_sign))


def build_mandala_input(chart: NatalChart, transits: TransitSnapshot, name: str, external_modifiers: list[dict] | None = None, rule_matches: list[RuleMatch] | None = None) -> MandalaInput:
    return MandalaInput(user=chart_to_user_profile(chart, name, full=False, external_modifiers=external_modifiers, rule_matches=rule_matches), today=transits_to_today_context(transits, chart.moon_sign))


def build_union_input(
    chart: NatalChart,
    partner_chart: NatalChart,
    transits: TransitSnapshot,
    name: str,
    partner_name: str,
    deep: bool = False,
    external_modifiers: list[dict] | None = None,
    rule_matches: list[RuleMatch] | None = None,
) -> UnionInput:
    return UnionInput(
        user=chart_to_user_profile(chart, name, full=deep, external_modifiers=external_modifiers, rule_matches=rule_matches),
        partner=chart_to_partner_profile(partner_chart, partner_name, full=deep),
        today=transits_to_today_context(transits, chart.moon_sign),
        relationship_summary=_relationship_summary(chart, partner_chart),
        shared_growth_edges=_shared_growth_edges(chart, partner_chart),
    )


def build_chart_reveal_input(chart: NatalChart, name: str, external_modifiers: list[dict] | None = None, rule_matches: list[RuleMatch] | None = None) -> ChartRevealInput:
    return ChartRevealInput(user=chart_to_user_profile(chart, name, full=True, external_modifiers=external_modifiers, rule_matches=rule_matches))


def build_birth_chart_input(chart: NatalChart, name: str, external_modifiers: list[dict] | None = None, rule_matches: list[RuleMatch] | None = None) -> BirthChartInput:
    return BirthChartInput(user=chart_to_user_profile(chart, name, full=True, external_modifiers=external_modifiers, rule_matches=rule_matches))


def build_mandala_deep_read_input(
    chart: NatalChart,
    transits: TransitSnapshot,
    name: str,
    activation_planet: str = "Saturn",
    external_modifiers: list[dict] | None = None,
    rule_matches: list[RuleMatch] | None = None,
) -> MandalaDeepReadInput:
    today_ctx = transits_to_today_context(transits, chart.moon_sign)
    activation = None
    for t in today_ctx.significant_transits:
        if t.planet == activation_planet:
            activation = t
            break
    if activation is None and today_ctx.significant_transits:
        activation = today_ctx.significant_transits[0]
    if activation is None:
        activation = TransitPlanet(planet="Moon", sign=transits.moon_sign, house_from_moon=transits.moon_house_from_natal or 1, retrograde=False)
    return MandalaDeepReadInput(
        user=chart_to_user_profile(chart, name, full=False, external_modifiers=external_modifiers, rule_matches=rule_matches),
        today=today_ctx,
        activation=activation,
    )


def build_period_overview_input(
    chart: NatalChart,
    transits: TransitSnapshot,
    name: str,
    period: str = "weekly",
    target_date: date | None = None,
    external_modifiers: list[dict] | None = None,
    rule_matches: list[RuleMatch] | None = None,
) -> PeriodOverviewInput:
    target = target_date or transits.date
    start, end = _period_bounds(target, period)
    return PeriodOverviewInput(
        user=chart_to_user_profile(chart, name, full=False, external_modifiers=external_modifiers, rule_matches=rule_matches),
        today=transits_to_today_context(transits, chart.moon_sign),
        period=period,
        period_start=start,
        period_end=end,
        period_focus_summary=_period_focus_summary(chart, transits, period, start, end),
        key_windows=_build_timing_windows(target, period),
    )
