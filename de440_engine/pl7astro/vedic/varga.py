"""Divisional charts (Vargas) — all 16 from PL7.

Reconstructed from FUN_0057d260 through FUN_0057d86a (Algorithm 13).
Each function takes a sidereal longitude and returns the varga longitude.
"""
import math
from ..astro.julian import normalize_degrees

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _sign_and_degree(longitude):
    """Get 1-based sign number and degree within sign."""
    sign = int(longitude / 30.0) % 12 + 1
    degree = longitude % 30.0
    return sign, degree


def lon_to_sign(longitude):
    """Convert longitude to sign name and degree string."""
    sign, deg = _sign_and_degree(longitude)
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return f"{d:02d}°{m:02d}'{s:02d}\" {SIGN_NAMES[sign - 1]}"


def d1_rashi(longitude):
    """D-1 Rashi chart (identity — sidereal longitude itself)."""
    return normalize_degrees(longitude)


def d2_hora(longitude):
    """D-2 Hora (FUN_0057d260)."""
    sign, degree = _sign_and_degree(longitude)
    frac = math.modf(degree / 15.0)[0]
    is_odd = sign % 2 == 1
    if is_odd:
        offset = sign + 11 if degree >= 15 else sign + 5
    else:
        offset = sign + 5 if degree >= 15 else sign - 1
    return normalize_degrees((offset + frac) * 30.0)


def d3_drekkana(longitude):
    """D-3 Drekkana (FUN_0057d2f3)."""
    sign, degree = _sign_and_degree(longitude)
    part = int(degree / 10.0)
    frac = math.modf(degree / 10.0)[0]
    return normalize_degrees((sign - 1 + part * 4 + frac) * 30.0)


def d4_chaturthamsha(longitude):
    """D-4 Chaturthamsha (FUN_0057d350)."""
    sign, degree = _sign_and_degree(longitude)
    part = int(degree / 7.5)
    frac = math.modf(degree / 7.5)[0]
    return normalize_degrees((part * 3 - 1 + sign + frac) * 30.0)


def d7_saptamsha(longitude):
    """D-7 Saptamsha (FUN_0057d397)."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    seg = int(degree / 6.0)
    frac = math.modf(degree / 6.0)[0]
    offsets_odd = [0, 300, 240, 60, 180]
    offsets_even = [30, 150, 330, 270, 210]
    if seg > 4:
        seg = 4
    offset = offsets_odd[seg] if is_odd else offsets_even[seg]
    return normalize_degrees(frac * 0.2 * 30.0 + offset)


def d9_navamsha(longitude):
    """D-9 Navamsha — most important divisional chart."""
    sign, degree = _sign_and_degree(longitude)
    element = (sign - 1) % 4
    start_signs = [1, 10, 7, 4]  # Aries, Cap, Libra, Cancer
    nav_part = int(degree / (30.0 / 9.0))
    if nav_part > 8:
        nav_part = 8
    nav_sign = ((start_signs[element] - 1 + nav_part) % 12) + 1
    nav_degree = (degree % (30.0 / 9.0)) * 9.0
    return normalize_degrees((nav_sign - 1) * 30.0 + nav_degree)


def d10_dashamsha(longitude):
    """D-10 Dashamsha (FUN_0057d510)."""
    sign, degree = _sign_and_degree(longitude)
    adj = (sign - 1) % 3
    pos = degree * 8.0 / 30.0
    return normalize_degrees((pos + adj * 4) * 30.0)


def d12_dwadashamsha(longitude):
    """D-12 Dwadashamsha (FUN_0057d55c)."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    offset = sign - 1 if is_odd else sign + 7
    return normalize_degrees((offset + degree / 3.0) * 30.0)


def d16_shodashamsha(longitude):
    """D-16 Shodashamsha (FUN_0057d647)."""
    sign, degree = _sign_and_degree(longitude)
    return normalize_degrees((sign - 1 + degree * 12.0 / 30.0) * 30.0)


def d20_vimshamsha(longitude):
    """D-20 Vimshamsha (FUN_0057d675)."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    pos = degree * 24.0 / 30.0
    adj = 4 if is_odd else 3
    return normalize_degrees((pos + adj) * 30.0)


def d27_saptavimshamsha(longitude):
    """D-27 Saptavimshamsha (FUN_0057d6b1) — complex piecewise."""
    sign, degree = _sign_and_degree(longitude)
    is_odd = sign % 2 == 1
    # Unequal segments: 5°, 5°, 8°, 7°, 5° = 30°
    boundaries = [0, 5, 10, 18, 25, 30]
    for i in range(5):
        if degree < boundaries[i + 1]:
            seg = i
            frac = (degree - boundaries[i]) / (boundaries[i + 1] - boundaries[i])
            break
    else:
        seg = 4
        frac = 1.0
    start_odd = [0, 1, 2, 3, 4]
    start_even = [3, 4, 0, 1, 2]
    start = start_odd[seg] if is_odd else start_even[seg]
    return normalize_degrees((sign - 1 + start + frac) * 30.0)


def d40_khavedamsha(longitude):
    """D-40 (FUN_0057d7ea)."""
    sign, degree = _sign_and_degree(longitude)
    is_even = sign % 2 == 0
    pos = degree * 40.0 / 30.0
    if is_even:
        pos += 6
    return normalize_degrees(pos * 30.0)


def d45_akshavedamsha(longitude):
    """D-45 Akshavedamsha (FUN_0057d81e)."""
    sign, degree = _sign_and_degree(longitude)
    adj = (sign - 1) % 3
    pos = degree * 45.0 / 30.0
    return normalize_degrees((pos + adj * 4) * 30.0)


def d60_shashtiamsha(longitude):
    """D-60 Shashtiamsha (FUN_0057d86a)."""
    sign, degree = _sign_and_degree(longitude)
    return normalize_degrees((sign - 1 + degree * 2.0) * 30.0)


# All varga functions indexed by division number
VARGA_FUNCTIONS = {
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


def calc_varga(longitude, division):
    """Calculate varga chart position for any supported division."""
    func = VARGA_FUNCTIONS.get(division)
    if func is None:
        raise ValueError(f"Unsupported varga division: D-{division}")
    return func(longitude)
