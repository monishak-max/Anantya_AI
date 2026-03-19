"""
Panchanga -- the five limbs of Vedic time-keeping.

Computes:
  1. Tithi (lunar day) -- phase of Moon relative to Sun
  2. Nakshatra (lunar mansion) -- Moon's nakshatra at the moment
  3. Yoga (Sun+Moon combination) -- one of 27 luni-solar yogas
  4. Karana (half-tithi) -- one of 11 karanas
  5. Vara (weekday) -- day of the week

Uses Swiss Ephemeris for Sun/Moon positions.
Ported from the DE440 engine's vedic/yoga.py panchanga logic.
"""
from __future__ import annotations

import os
import sys
from datetime import date

from llm.engine.constants import RASHIS, NAKSHATRAS, NAKSHATRA_SPAN

# Use DE440 pipeline for Sun/Moon positions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "de440_engine"))
from pl7astro.astro.julian import date_to_jd

# ── Yoga names (27 luni-solar yogas) ─────────────────────────────

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

# ── Tithi names (30 tithis across Shukla and Krishna paksha) ─────

TITHI_NAMES = [
    "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya",
    "Shukla Chaturthi", "Shukla Panchami", "Shukla Shashthi",
    "Shukla Saptami", "Shukla Ashtami", "Shukla Navami",
    "Shukla Dashami", "Shukla Ekadashi", "Shukla Dwadashi",
    "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
    "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya",
    "Krishna Chaturthi", "Krishna Panchami", "Krishna Shashthi",
    "Krishna Saptami", "Krishna Ashtami", "Krishna Navami",
    "Krishna Dashami", "Krishna Ekadashi", "Krishna Dwadashi",
    "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
]

# ── Karana names (11 karanas, 60 half-tithis per lunar month) ────

KARANA_NAMES_CYCLE = [
    "Bava", "Balava", "Kaulava", "Taitila",
    "Garija", "Vanija", "Vishti",
]
KARANA_FIXED = ["Shakuni", "Chatushpada", "Naga", "Kimstughna"]

# ── Vara (weekday) ───────────────────────────────────────────────

VARA_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

VARA_SANSKRIT = [
    "Somavara", "Mangalavara", "Budhavara", "Guruvara",
    "Shukravara", "Shanivara", "Ravivara",
]


# ── Core computation ─────────────────────────────────────────────

def compute_panchanga(target_date: date, latitude: float = 0.0, longitude: float = 0.0) -> dict:
    """
    Compute all 5 panchanga elements for a given date.

    Args:
        target_date: Date to compute panchanga for
        latitude: Observer latitude (for vara precision)
        longitude: Observer longitude

    Returns:
        dict with tithi, nakshatra, yoga, karana, vara and their details
    """
    jd = date_to_jd(target_date.year, target_date.month, target_date.day, 12.0)

    # Get sidereal Sun and Moon positions via DE440 pipeline
    from llm.engine.calculator import _de440_pipe
    result = _de440_pipe.calc_all(jd, timezone=0.0, latitude=0.0, longitude=0.0, ayanamsha_system=1)
    sun_lon = result.planets[1].sidereal_lon
    moon_lon = result.planets[2].sidereal_lon

    # 1. TITHI -- based on Moon-Sun angular distance
    tithi_data = _calc_tithi(moon_lon, sun_lon)

    # 2. NAKSHATRA -- Moon's current nakshatra
    nak_data = _calc_nakshatra(moon_lon)

    # 3. YOGA -- Sun+Moon combined longitude
    yoga_data = _calc_yoga(sun_lon, moon_lon)

    # 4. KARANA -- half of tithi
    karana_data = _calc_karana(tithi_data["index"])

    # 5. VARA -- weekday
    vara_data = _calc_vara(jd)

    return {
        "date": str(target_date),
        "tithi": tithi_data,
        "nakshatra": nak_data,
        "yoga": yoga_data,
        "karana": karana_data,
        "vara": vara_data,
        "sun_sidereal": round(sun_lon, 4),
        "moon_sidereal": round(moon_lon, 4),
    }


def _calc_tithi(moon_lon: float, sun_lon: float) -> dict:
    """Calculate tithi from Moon-Sun angular distance."""
    diff = (moon_lon - sun_lon) % 360
    tithi_idx = int(diff / 12.0)
    if tithi_idx >= 30:
        tithi_idx = 29
    degree_in_tithi = diff - tithi_idx * 12.0

    paksha = "Shukla" if tithi_idx < 15 else "Krishna"

    return {
        "index": tithi_idx,
        "number": (tithi_idx % 15) + 1,
        "name": TITHI_NAMES[tithi_idx],
        "paksha": paksha,
        "degree_remaining": round(12.0 - degree_in_tithi, 2),
    }


def _calc_nakshatra(moon_lon: float) -> dict:
    """Calculate Moon's nakshatra."""
    nak_idx = int(moon_lon / NAKSHATRA_SPAN)
    if nak_idx >= 27:
        nak_idx = 26
    nak = NAKSHATRAS[nak_idx]
    degree_in_nak = moon_lon - nak["start"]
    pada = min(int(degree_in_nak / 3.333333333) + 1, 4)

    return {
        "index": nak_idx,
        "name": nak["name"],
        "lord": nak["lord"],
        "pada": pada,
        "degree_in_nakshatra": round(degree_in_nak, 2),
    }


def _calc_yoga(sun_lon: float, moon_lon: float) -> dict:
    """Calculate panchanga yoga from Sun+Moon longitude sum."""
    total = (sun_lon + moon_lon) % 360
    yoga_span = 360.0 / 27.0
    yoga_idx = int(total / yoga_span)
    if yoga_idx >= 27:
        yoga_idx = 26
    degree_in_yoga = total - yoga_idx * yoga_span

    return {
        "index": yoga_idx,
        "name": YOGA_NAMES[yoga_idx],
        "degree_in_yoga": round(degree_in_yoga, 2),
    }


def _calc_karana(tithi_index: int) -> dict:
    """Calculate karana (half-tithi).

    There are 60 karanas in a lunar month (2 per tithi).
    First karana of Shukla Pratipada is always Kimstughna (fixed).
    Last karana of Amavasya is always Naga (fixed).
    The 56 middle karanas cycle through the 7 repeating karanas (8 times).
    """
    karana_index = tithi_index * 2  # First half of current tithi

    if karana_index == 0:
        name = "Kimstughna"
    elif karana_index == 59:
        name = "Naga"
    elif karana_index == 58:
        name = "Chatushpada"
    elif karana_index == 57:
        name = "Shakuni"
    else:
        cycle_idx = (karana_index - 1) % 7
        name = KARANA_NAMES_CYCLE[cycle_idx]

    return {
        "index": karana_index,
        "name": name,
    }


def _calc_vara(jd: float) -> dict:
    """Calculate weekday (vara) from Julian Day."""
    # JD 0 = Monday (Julian Day number mod 7)
    day_idx = int(jd + 0.5) % 7

    return {
        "index": day_idx,
        "name": VARA_NAMES[day_idx],
        "sanskrit": VARA_SANSKRIT[day_idx],
    }
