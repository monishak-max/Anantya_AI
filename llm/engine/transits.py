"""
Transit Engine -- find exact moments when planets cross boundaries.

Uses half-day scanning + bisection refinement to find precise crossing
times for sign ingresses, nakshatra ingresses, and custom target longitudes.

Ported from the DE440 engine's vedic/transit.py, adapted for Swiss Ephemeris.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from typing import Optional

from llm.engine.constants import RASHIS, NAKSHATRAS, NAKSHATRA_SPAN

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hope_this_is_final"))
from pl7astro.astro.julian import date_to_jd

SIGN_SPAN = 30.0


def _planet_longitude_at(planet_name: str, jd: float) -> float:
    """Get sidereal longitude of a planet at a given Julian Day via DE440."""
    from llm.engine.calculator import _de440_pipe

    body_map = {"Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
                "Jupiter": 5, "Venus": 6, "Saturn": 7, "Rahu": 8}

    if planet_name == "Ketu":
        result = _de440_pipe.calc_all(jd, timezone=0.0, latitude=0.0, longitude=0.0, ayanamsha_system=1)
        return (result.planets[8].sidereal_lon + 180) % 360

    body_id = body_map.get(planet_name)
    if body_id is None:
        return 0.0

    result = _de440_pipe.calc_all(jd, timezone=0.0, latitude=0.0, longitude=0.0, ayanamsha_system=1)
    return result.planets[body_id].sidereal_lon


def _check_crossing(lon1: float, lon2: float, target: float) -> bool:
    """Check if target longitude is between lon1 and lon2 (any direction)."""
    lon1 = lon1 % 360.0
    lon2 = lon2 % 360.0
    target = target % 360.0

    fwd_arc = (lon2 - lon1) % 360.0
    fwd_to_target = (target - lon1) % 360.0

    if fwd_arc <= 180.0:
        return fwd_to_target < fwd_arc and fwd_arc > 0
    else:
        bwd_arc = 360.0 - fwd_arc
        bwd_to_target = (lon1 - target) % 360.0
        return bwd_to_target < bwd_arc and bwd_arc > 0


def find_exact_crossing(
    planet_name: str,
    start_jd: float,
    end_jd: float,
    target_longitude: float,
    precision_days: float = 0.001,
) -> tuple[float, int]:
    """Find exact JD when a planet reaches a target sidereal longitude.

    Uses half-day scanning followed by bisection refinement.

    Args:
        planet_name: Planet name (e.g. "Sun", "Moon", "Mars")
        start_jd: Start of search window (Julian Day UT)
        end_jd: End of search window (Julian Day UT)
        target_longitude: Target sidereal longitude (0-360)
        precision_days: Bisection precision (default ~1.4 minutes)

    Returns:
        (crossing_jd, direction): JD of crossing and +1 (direct) / -1 (retrograde)
        Returns (0.0, 0) if not found
    """
    step = 0.5  # half-day scanning
    prev_jd = start_jd
    prev_lon = _planet_longitude_at(planet_name, prev_jd)

    jd = start_jd + step
    while jd <= end_jd:
        curr_lon = _planet_longitude_at(planet_name, jd)

        if _check_crossing(prev_lon, curr_lon, target_longitude):
            # Bisection refinement
            lo, hi = prev_jd, jd
            lo_lon = prev_lon
            while (hi - lo) > precision_days:
                mid = (lo + hi) / 2.0
                mid_lon = _planet_longitude_at(planet_name, mid)
                if _check_crossing(lo_lon, mid_lon, target_longitude):
                    hi = mid
                else:
                    lo = mid
                    lo_lon = mid_lon

            crossing_jd = (lo + hi) / 2.0

            # Determine direction
            lon_before = _planet_longitude_at(planet_name, crossing_jd - 0.01)
            lon_after = _planet_longitude_at(planet_name, crossing_jd + 0.01)
            diff = lon_after - lon_before
            if diff > 180: diff -= 360
            if diff < -180: diff += 360
            direction = 1 if diff > 0 else -1

            return crossing_jd, direction

        prev_jd = jd
        prev_lon = curr_lon
        jd += step

    return 0.0, 0


def find_all_crossings(
    planet_name: str,
    start_jd: float,
    end_jd: float,
    target_longitude: float,
    precision_days: float = 0.001,
) -> list[tuple[float, int]]:
    """Find ALL crossings of a target longitude in a time range.

    Handles retrograde motion (a planet can cross the same point 3 times).

    Returns:
        list of (crossing_jd, direction) tuples
    """
    results = []
    search_start = start_jd
    while search_start < end_jd:
        jd, direction = find_exact_crossing(
            planet_name, search_start, end_jd, target_longitude, precision_days
        )
        if jd <= 0:
            break
        results.append((jd, direction))
        search_start = jd + 0.5
    return results


def find_sign_ingresses(
    planet_name: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Find all sign ingresses for a planet in a date range.

    Returns:
        list of {"jd": float, "date": str, "sign": str, "sign_index": int, "direction": int}
    """
    start_jd = date_to_jd(start_date.year, start_date.month, start_date.day, 0.0)
    end_jd = date_to_jd(end_date.year, end_date.month, end_date.day, 24.0)

    results = []
    for sign_idx in range(12):
        boundary = sign_idx * SIGN_SPAN
        crossings = find_all_crossings(planet_name, start_jd, end_jd, boundary)
        for jd, direction in crossings:
            from pl7astro.astro.julian import jd_to_date
            y, m, d, h = jd_to_date(jd)
            results.append({
                "jd": jd,
                "date": f"{y}-{m:02d}-{d:02d}",
                "sign": RASHIS[sign_idx],
                "sign_index": sign_idx,
                "direction": direction,
                "type": "direct" if direction > 0 else "retrograde",
            })

    results.sort(key=lambda x: x["jd"])
    return results


def find_nakshatra_ingresses(
    planet_name: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Find all nakshatra ingresses for a planet in a date range.

    Returns:
        list of {"jd": float, "date": str, "nakshatra": str, "index": int, "direction": int}
    """
    start_jd = date_to_jd(start_date.year, start_date.month, start_date.day, 0.0)
    end_jd = date_to_jd(end_date.year, end_date.month, end_date.day, 24.0)

    results = []
    for nak_idx in range(27):
        boundary = nak_idx * NAKSHATRA_SPAN
        crossings = find_all_crossings(planet_name, start_jd, end_jd, boundary)
        for jd, direction in crossings:
            from pl7astro.astro.julian import jd_to_date
            y, m, d, h = jd_to_date(jd)
            results.append({
                "jd": jd,
                "date": f"{y}-{m:02d}-{d:02d}",
                "nakshatra": NAKSHATRAS[nak_idx]["name"],
                "index": nak_idx,
                "direction": direction,
            })

    results.sort(key=lambda x: x["jd"])
    return results


def next_moon_sign_change(from_date: date) -> dict:
    """Find the next time Moon changes sign from a given date.

    Returns:
        {"jd": float, "date": str, "from_sign": str, "to_sign": str}
    """
    start_jd = date_to_jd(from_date.year, from_date.month, from_date.day, 0.0)
    current_lon = _planet_longitude_at("Moon", start_jd)
    current_sign_idx = int(current_lon / 30) % 12
    next_sign_idx = (current_sign_idx + 1) % 12
    boundary = next_sign_idx * 30.0

    end_jd = start_jd + 3.0  # Moon changes sign every ~2.5 days
    jd, direction = find_exact_crossing("Moon", start_jd, end_jd, boundary, 0.0001)

    if jd > 0:
        from pl7astro.astro.julian import jd_to_date
        y, m, d, h = jd_to_date(jd)
        return {
            "jd": jd,
            "date": f"{y}-{m:02d}-{d:02d}",
            "hour": round(h, 2),
            "from_sign": RASHIS[current_sign_idx],
            "to_sign": RASHIS[next_sign_idx],
        }

    return {"jd": 0, "date": str(from_date), "from_sign": RASHIS[current_sign_idx], "to_sign": "unknown"}
