"""
Context builder — flattens NatalChart + TransitSnapshot into a flat dict for rule evaluation.

Produces ~104 keys covering moon, lagna, 10 planets, dasha, yogas, and optional transits.
"""
from __future__ import annotations

from typing import Optional

from llm.engine.calculator import NatalChart, TransitSnapshot

PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Rahu", "Ketu", "Ascendant",
]


def build_rule_context(
    chart: NatalChart,
    transits: Optional[TransitSnapshot] = None,
) -> dict:
    if not chart.moon_sign:
        raise ValueError("chart.moon_sign is required for rule evaluation")
    if not chart.planets:
        raise ValueError("chart.planets is required for rule evaluation")
    if not chart.mahadasha:
        raise ValueError("chart.mahadasha is required for rule evaluation")

    ctx: dict = {}

    # Moon core
    ctx["moon_sign"] = chart.moon_sign
    ctx["moon_nakshatra"] = chart.moon_nakshatra
    ctx["lagna_sign"] = chart.lagna_sign

    # Per planet
    for planet_name in PLANETS:
        p = chart.planets.get(planet_name)
        if p is None:
            continue
        key = planet_name.lower()
        ctx[f"{key}_sign"] = p.sign
        ctx[f"{key}_nakshatra"] = p.nakshatra
        ctx[f"{key}_house_from_lagna"] = p.house_from_lagna
        ctx[f"{key}_house_from_moon"] = p.house_from_moon
        ctx[f"{key}_retrograde"] = p.retrograde
        ctx[f"{key}_is_exalted"] = p.is_exalted
        ctx[f"{key}_is_debilitated"] = p.is_debilitated
        ctx[f"{key}_is_own_sign"] = p.is_own_sign
        ctx[f"{key}_degree"] = p.degree_in_sign
        ctx[f"{key}_longitude"] = p.longitude

    # Dasha
    ctx["mahadasha_lord"] = chart.mahadasha.lord
    ctx["antardasha_lord"] = chart.antardasha.antardasha_lord

    # Yogas
    ctx["yoga_present"] = [y.name for y in chart.yogas]

    # Transit fields (optional)
    if transits is not None:
        transit_moon = transits.planets.get("Moon")
        if transit_moon:
            ctx["transit_moon_sign"] = transit_moon.sign
            ctx["transit_moon_nakshatra"] = transit_moon.nakshatra
            ctx["transit_moon_house"] = transit_moon.house_from_moon

        for planet_name in PLANETS:
            tp = transits.planets.get(planet_name)
            if tp is None or planet_name == "Moon":
                continue
            key = planet_name.lower()
            ctx[f"transit_{key}_sign"] = tp.sign
            ctx[f"transit_{key}_house"] = tp.house_from_moon
            ctx[f"transit_{key}_retrograde"] = tp.retrograde

    return ctx
