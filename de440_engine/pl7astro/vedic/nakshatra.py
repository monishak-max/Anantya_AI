"""Nakshatra (lunar mansion) calculations.

Reconstructed from FUN_00408452 (Algorithm 8).
"""

NAKSHATRA_SPAN = 13.333333333333334  # 360/27 degrees
PADA_SPAN = 3.333333333333333  # 360/108 degrees

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Nakshatra lords cycle: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
] * 3  # 27 nakshatras, 9 lords cycling


def calc_nakshatra(sidereal_longitude):
    """Determine nakshatra, pada, and lord from sidereal longitude.

    Args:
        sidereal_longitude: Sidereal longitude in degrees [0, 360)

    Returns:
        dict with keys: index (0-26), pada (1-4), name, lord, degree_in_nakshatra
    """
    nak_index = int(sidereal_longitude / NAKSHATRA_SPAN)
    if nak_index >= 27:
        nak_index = 26
    degree_in_nak = sidereal_longitude - nak_index * NAKSHATRA_SPAN
    pada = int(degree_in_nak / (NAKSHATRA_SPAN / 4.0)) + 1
    if pada > 4:
        pada = 4

    return {
        'index': nak_index,
        'pada': pada,
        'name': NAKSHATRA_NAMES[nak_index],
        'lord': NAKSHATRA_LORDS[nak_index],
        'degree_in_nakshatra': degree_in_nak,
    }
