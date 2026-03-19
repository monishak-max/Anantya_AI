"""
Jyotish constants — signs, nakshatras, planets, and their attributes.
"""
from __future__ import annotations

# ── 12 Rashis (Sidereal signs) ─────────────────────────────────────
RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# ── 27 Nakshatras ──────────────────────────────────────────────────
# Each spans 13°20' (13.3333°). Total = 360°.
NAKSHATRAS = [
    {"name": "Ashwini",            "lord": "Ketu",    "start": 0.0000,  "deity": "Ashwini Kumaras"},
    {"name": "Bharani",            "lord": "Venus",   "start": 13.3333, "deity": "Yama"},
    {"name": "Krittika",           "lord": "Sun",     "start": 26.6667, "deity": "Agni"},
    {"name": "Rohini",             "lord": "Moon",    "start": 40.0000, "deity": "Brahma"},
    {"name": "Mrigashira",         "lord": "Mars",    "start": 53.3333, "deity": "Soma"},
    {"name": "Ardra",              "lord": "Rahu",    "start": 66.6667, "deity": "Rudra"},
    {"name": "Punarvasu",          "lord": "Jupiter", "start": 80.0000, "deity": "Aditi"},
    {"name": "Pushya",             "lord": "Saturn",  "start": 93.3333, "deity": "Brihaspati"},
    {"name": "Ashlesha",           "lord": "Mercury", "start": 106.6667, "deity": "Sarpa"},
    {"name": "Magha",              "lord": "Ketu",    "start": 120.0000, "deity": "Pitrs"},
    {"name": "Purva Phalguni",     "lord": "Venus",   "start": 133.3333, "deity": "Bhaga"},
    {"name": "Uttara Phalguni",    "lord": "Sun",     "start": 146.6667, "deity": "Aryaman"},
    {"name": "Hasta",              "lord": "Moon",    "start": 160.0000, "deity": "Savitar"},
    {"name": "Chitra",             "lord": "Mars",    "start": 173.3333, "deity": "Tvashtar"},
    {"name": "Swati",              "lord": "Rahu",    "start": 186.6667, "deity": "Vayu"},
    {"name": "Vishakha",           "lord": "Jupiter", "start": 200.0000, "deity": "Indra-Agni"},
    {"name": "Anuradha",           "lord": "Saturn",  "start": 213.3333, "deity": "Mitra"},
    {"name": "Jyeshtha",           "lord": "Mercury", "start": 226.6667, "deity": "Indra"},
    {"name": "Mula",               "lord": "Ketu",    "start": 240.0000, "deity": "Nirriti"},
    {"name": "Purva Ashadha",      "lord": "Venus",   "start": 253.3333, "deity": "Apas"},
    {"name": "Uttara Ashadha",     "lord": "Sun",     "start": 266.6667, "deity": "Vishvedevas"},
    {"name": "Shravana",           "lord": "Moon",    "start": 280.0000, "deity": "Vishnu"},
    {"name": "Dhanishta",          "lord": "Mars",    "start": 293.3333, "deity": "Vasus"},
    {"name": "Shatabhisha",        "lord": "Rahu",    "start": 306.6667, "deity": "Varuna"},
    {"name": "Purva Bhadrapada",   "lord": "Jupiter", "start": 320.0000, "deity": "Aja Ekapada"},
    {"name": "Uttara Bhadrapada",  "lord": "Saturn",  "start": 333.3333, "deity": "Ahir Budhnya"},
    {"name": "Revati",             "lord": "Mercury", "start": 346.6667, "deity": "Pushan"},
]

NAKSHATRA_SPAN = 13.333333333  # 13°20' in decimal degrees
PADA_SPAN = 3.333333333        # 3°20' in decimal degrees

# ── Vimshottari Dasha sequence & years ─────────────────────────────
# The dasha cycle starts from the nakshatra lord of the natal Moon.
# Total cycle = 120 years.
VIMSHOTTARI_SEQUENCE = [
    ("Ketu",    7),
    ("Venus",   20),
    ("Sun",     6),
    ("Moon",    10),
    ("Mars",    7),
    ("Rahu",    18),
    ("Jupiter", 16),
    ("Saturn",  19),
    ("Mercury", 17),
]

VIMSHOTTARI_TOTAL_YEARS = 120  # sum of all periods

# ── Planet IDs ────────────────────────────────────────────────────
# DE440 engine uses pl7astro body IDs (1-8)
PLANET_IDS_DE440 = {
    "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
    "Jupiter": 5, "Venus": 6, "Saturn": 7, "Rahu": 8,
}

# Swiss Ephemeris IDs (commented out -- kept for backup)
# import swisseph as swe
# PLANET_IDS_SWISS = {
#     "Sun":     swe.SUN,
#     "Moon":    swe.MOON,
#     "Mars":    swe.MARS,
#     "Mercury": swe.MERCURY,
#     "Jupiter": swe.JUPITER,
#     "Venus":   swe.VENUS,
#     "Saturn":  swe.SATURN,
#     "Rahu":    swe.MEAN_NODE,
# }

PLANET_IDS = PLANET_IDS_DE440

# Ketu is always 180 degrees from Rahu
PLANETS_COMPUTED = list(PLANET_IDS.keys()) + ["Ketu"]


# ── Sign lordships (ruler of each rashi) ───────────────────────────
SIGN_LORDS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


# ── Exaltation / Debilitation ──────────────────────────────────────
# (sign, degree of exact exaltation)
EXALTATION = {
    "Sun":     ("Aries", 10),
    "Moon":    ("Taurus", 3),
    "Mars":    ("Capricorn", 28),
    "Mercury": ("Virgo", 15),
    "Jupiter": ("Cancer", 5),
    "Venus":   ("Pisces", 27),
    "Saturn":  ("Libra", 20),
    "Rahu":    ("Taurus", 20),
    "Ketu":    ("Scorpio", 20),
}

DEBILITATION = {
    "Sun":     ("Libra", 10),
    "Moon":    ("Scorpio", 3),
    "Mars":    ("Cancer", 28),
    "Mercury": ("Pisces", 15),
    "Jupiter": ("Capricorn", 5),
    "Venus":   ("Virgo", 27),
    "Saturn":  ("Aries", 20),
    "Rahu":    ("Scorpio", 20),
    "Ketu":    ("Taurus", 20),
}

# Own sign (Moolatrikona simplified — planet in own sign)
OWN_SIGNS = {
    "Sun":     ["Leo"],
    "Moon":    ["Cancer"],
    "Mars":    ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus":   ["Taurus", "Libra"],
    "Saturn":  ["Capricorn", "Aquarius"],
}


# ── Kendra (angular) and Trikona (trinal) houses ──────────────────
KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
UPACHAYA_HOUSES = {3, 6, 10, 11}


# ── Natural benefics and malefics ──────────────────────────────────
NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
