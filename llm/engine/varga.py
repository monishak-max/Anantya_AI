"""
Divisional Charts (Vargas) -- 14 standard divisions from D-1 to D-60.

Each function takes a sidereal longitude and returns the varga chart position.
Used for premium features: Navamsha (D-9) for relationships, Dashamsha (D-10)
for career, etc.

Ported from the DE440 engine's vedic/varga.py.
"""
from __future__ import annotations

import math

from llm.engine.constants import RASHIS

SIGN_NAMES = RASHIS


def _normalize(lon: float) -> float:
    """Normalize longitude to [0, 360)."""
    return lon % 360.0


def _sign_and_degree(longitude: float) -> tuple[int, float]:
    """Get 1-based sign number and degree within sign."""
    sign = int(longitude / 30.0) % 12 + 1
    degree = longitude % 30.0
    return sign, degree


# ── Individual varga functions ────────────────────────────────────

def d1_rashi(longitude: float) -> float:
    """D-1 Rashi chart (identity)."""
    return _normalize(longitude)


def d2_hora(longitude: float) -> float:
    """D-2 Hora -- wealth and resources."""
    sign, degree = _sign_and_degree(longitude)
    frac = math.modf(degree / 15.0)[0]
    is_odd = sign % 2 == 1
    if is_odd:
        offset = sign + 11 if degree >= 15 else sign + 5
    else:
        offset = sign + 5 if degree >= 15 else sign - 1
    return _normalize((offset + frac) * 30.0)


def d3_drekkana(longitude: float) -> float:
    """D-3 Drekkana -- siblings, courage, initiative."""
    sign, degree = _sign_and_degree(longitude)
    part = int(degree / 10.0)
    frac = math.modf(degree / 10.0)[0]
    return _normalize((sign - 1 + part * 4 + frac) * 30.0)


def d4_chaturthamsha(longitude: float) -> float:
    """D-4 Chaturthamsha -- home, property, fixed assets."""
    sign, degree = _sign_and_degree(longitude)
    part = int(degree / 7.5)
    frac = math.modf(degree / 7.5)[0]
    return _normalize((part * 3 - 1 + sign + frac) * 30.0)


def d7_saptamsha(longitude: float) -> float:
    """D-7 Saptamsha -- children and progeny."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    seg = min(int(degree / 6.0), 4)
    frac = math.modf(degree / 6.0)[0]
    offsets_odd = [0, 300, 240, 60, 180]
    offsets_even = [30, 150, 330, 270, 210]
    offset = offsets_odd[seg] if is_odd else offsets_even[seg]
    return _normalize(frac * 0.2 * 30.0 + offset)


def d9_navamsha(longitude: float) -> float:
    """D-9 Navamsha -- most important divisional chart (dharma, spouse, inner self)."""
    sign, degree = _sign_and_degree(longitude)
    element = (sign - 1) % 4
    start_signs = [1, 10, 7, 4]  # Aries, Capricorn, Libra, Cancer
    nav_part = min(int(degree / (30.0 / 9.0)), 8)
    nav_sign = ((start_signs[element] - 1 + nav_part) % 12) + 1
    nav_degree = (degree % (30.0 / 9.0)) * 9.0
    return _normalize((nav_sign - 1) * 30.0 + nav_degree)


def d10_dashamsha(longitude: float) -> float:
    """D-10 Dashamsha -- career, public life, profession."""
    sign, degree = _sign_and_degree(longitude)
    adj = (sign - 1) % 3
    pos = degree * 8.0 / 30.0
    return _normalize((pos + adj * 4) * 30.0)


def d12_dwadashamsha(longitude: float) -> float:
    """D-12 Dwadashamsha -- parents, lineage."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    offset = sign - 1 if is_odd else sign + 7
    return _normalize((offset + degree / 3.0) * 30.0)


def d16_shodashamsha(longitude: float) -> float:
    """D-16 Shodashamsha -- vehicles, comforts, luxuries."""
    sign, degree = _sign_and_degree(longitude)
    return _normalize((sign - 1 + degree * 12.0 / 30.0) * 30.0)


def d20_vimshamsha(longitude: float) -> float:
    """D-20 Vimshamsha -- spiritual life, upasana."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    pos = degree * 24.0 / 30.0
    adj = 4 if is_odd else 3
    return _normalize((pos + adj) * 30.0)


def d27_saptavimshamsha(longitude: float) -> float:
    """D-27 Saptavimshamsha -- strength, stamina."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    boundaries = [0, 5, 10, 18, 25, 30]
    seg = 4
    frac = 1.0
    for i in range(5):
        if degree < boundaries[i + 1]:
            seg = i
            frac = (degree - boundaries[i]) / (boundaries[i + 1] - boundaries[i])
            break
    start_odd = [0, 1, 2, 3, 4]
    start_even = [3, 4, 0, 1, 2]
    start = start_odd[seg] if is_odd else start_even[seg]
    return _normalize((sign - 1 + start + frac) * 30.0)


def d40_khavedamsha(longitude: float) -> float:
    """D-40 Khavedamsha -- auspicious/inauspicious effects."""
    sign, degree = _sign_and_degree(longitude)
    is_even = sign % 2 == 0
    pos = degree * 40.0 / 30.0
    if is_even:
        pos += 6
    return _normalize(pos * 30.0)


def d45_akshavedamsha(longitude: float) -> float:
    """D-45 Akshavedamsha -- general well-being."""
    sign, degree = _sign_and_degree(longitude)
    adj = (sign - 1) % 3
    pos = degree * 45.0 / 30.0
    return _normalize((pos + adj * 4) * 30.0)


def d60_shashtiamsha(longitude: float) -> float:
    """D-60 Shashtiamsha -- past life karma, finest division."""
    sign, degree = _sign_and_degree(longitude)
    return _normalize((sign - 1 + degree * 2.0) * 30.0)


# ── Lookup table ──────────────────────────────────────────────────

VARGA_FUNCTIONS: dict[int, callable] = {
    1: d1_rashi,
    2: d2_hora,
    3: d3_drekkana,
    4: d4_chaturthamsha,
    7: d7_saptamsha,
    9: d9_navamsha,
    10: d10_dashamsha,
    12: d12_dwadashamsha,
    16: d16_shodashamsha,
    20: d20_vimshamsha,
    27: d27_saptavimshamsha,
    40: d40_khavedamsha,
    45: d45_akshavedamsha,
    60: d60_shashtiamsha,
}


def calc_varga(longitude: float, division: int) -> float:
    """Calculate varga chart position for any supported division.

    Args:
        longitude: Sidereal longitude (0-360)
        division: Varga division (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 27, 40, 45, 60)

    Returns:
        Varga longitude (0-360)
    """
    func = VARGA_FUNCTIONS.get(division)
    if func is None:
        raise ValueError(f"Unsupported varga division: D-{division}")
    return func(longitude)


def calc_all_vargas(longitude: float) -> dict[int, dict]:
    """Calculate all standard varga positions for a longitude.

    Returns dict of {division: {"longitude": float, "sign": str, "degree": float}}
    """
    results = {}
    for div in VARGA_FUNCTIONS:
        varga_lon = calc_varga(longitude, div)
        sign_idx = int(varga_lon / 30) % 12
        results[div] = {
            "longitude": round(varga_lon, 4),
            "sign": RASHIS[sign_idx],
            "degree": round(varga_lon % 30, 2),
        }
    return results


def navamsha_sign(longitude: float) -> str:
    """Quick helper: get Navamsha sign name for a longitude."""
    nav_lon = d9_navamsha(longitude)
    return RASHIS[int(nav_lon / 30) % 12]
