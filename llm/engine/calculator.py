"""
Astro Computation Engine -- computes all Jyotish data from birth details.

PRIMARY ENGINE: DE440 (JPL ephemeris via pl7astro pipeline)
BACKUP ENGINE:  Swiss Ephemeris (commented out, kept for reference/validation)

Computes:
  - Lagna (Ascendant) and house cusps
  - All planet positions (sign, degree, nakshatra, pada, retrograde)
  - Moon sign, nakshatra, pada (primary anchor for the app)
  - House positions from both Lagna and Moon (whole sign houses)
  - House lordships
  - Vimshottari Dasha periods (mahadasha + antardasha)
  - Yoga detection (major classical yogas)
  - Current transits
  - Divisional charts (14 vargas: D-1 through D-60)
  - Panchanga (Tithi, Nakshatra, Yoga, Karana, Vara)
  - Transit boundary solver (sign/nakshatra ingress timing)
"""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional

from timezonefinder import TimezoneFinder
import pytz

from llm.engine.constants import (
    RASHIS,
    NAKSHATRAS,
    NAKSHATRA_SPAN,
    PADA_SPAN,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    SIGN_LORDS,
    EXALTATION,
    DEBILITATION,
    OWN_SIGNS,
    KENDRA_HOUSES,
    TRIKONA_HOUSES,
    DUSTHANA_HOUSES,
    NATURAL_BENEFICS,
    NATURAL_MALEFICS,
)

# ═══════════════════════════════════════════════════════════════════
# ENGINE SELECTION: DE440 (primary) or Swiss (backup)
# ═══════════════════════════════════════════════════════════════════

ENGINE = "DE440"  # Change to "SWISS" to switch back

if ENGINE == "DE440":
    # DE440 engine -- JPL ephemeris, full control, no license constraints
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hope_this_is_final"))
    from pl7astro.astro.jpl_ephemeris import JPLEphemerisReader
    from pl7astro.astro.corrections import DeltaTTable
    from pl7astro.astro.pipeline import Pipeline as DE440Pipeline
    from pl7astro.astro.julian import J2000, JULIAN_CENTURY, date_to_jd, normalize_degrees
    from pl7astro.vedic.ayanamsha import calc_ayanamsha

    # Initialize DE440 pipeline (singleton)
    _DE440_BSP = os.path.join(os.path.dirname(__file__), "..", "..", "de440.bsp")
    _DELTAT_ASC = os.path.join(os.path.dirname(__file__), "..", "..", "DELTAT.ASC")
    _de440_eph = JPLEphemerisReader(_DE440_BSP)
    _de440_dt = DeltaTTable(_DELTAT_ASC)
    _de440_pipe = DE440Pipeline(_de440_eph, _de440_dt)

# ── Swiss Ephemeris (commented out -- kept as backup) ──────────────
# To switch back: change ENGINE = "SWISS" above
#
# if ENGINE == "SWISS":
#     import swisseph as swe
#     from llm.engine.constants import PLANET_IDS
#     swe.set_sid_mode(swe.SIDM_LAHIRI)

tf = TimezoneFinder()


# ── Data classes ───────────────────────────────────────────────────

@dataclass
class PlanetPosition:
    planet: str
    longitude: float         # sidereal longitude 0-360
    sign: str                # rashi name
    degree_in_sign: float    # 0-30
    nakshatra: str
    nakshatra_pada: int      # 1-4
    nakshatra_lord: str
    retrograde: bool = False
    house_from_moon: Optional[int] = None   # 1-12, whole sign from Moon
    house_from_lagna: Optional[int] = None  # 1-12, whole sign from Ascendant
    is_exalted: bool = False
    is_debilitated: bool = False
    is_own_sign: bool = False
    navamsha_sign: Optional[str] = None     # D-9 Navamsha sign placement


@dataclass
class HouseLord:
    house: int          # 1-12
    lord: str           # planet name
    placed_in_house: int  # which house the lord sits in (from lagna)
    placed_in_sign: str


@dataclass
class Yoga:
    name: str
    category: str       # "raja", "dhana", "pancha_mahapurusha", "lunar", "solar", "combination"
    planets_involved: list[str]
    description: str    # human-readable one-liner for the LLM


@dataclass
class DashaPeriod:
    lord: str
    start: datetime
    end: datetime
    years: float


@dataclass
class AntarDasha:
    mahadasha_lord: str
    antardasha_lord: str
    start: datetime
    end: datetime


@dataclass
class NatalChart:
    """Complete natal chart data -- everything the LLM layer needs."""
    birth_dt: datetime
    latitude: float
    longitude: float
    timezone: str
    julian_day: float

    # Lagna (Ascendant)
    lagna_sign: str
    lagna_degree: float
    lagna_nakshatra: str

    # All planet positions
    planets: dict[str, PlanetPosition]

    # House lordships (from Lagna)
    house_lords: list[HouseLord]

    # Yogas detected
    yogas: list[Yoga]

    # Moon-specific (primary anchor)
    moon_sign: str
    moon_degree: float
    moon_nakshatra: str
    moon_nakshatra_pada: int
    moon_nakshatra_lord: str

    # Dasha
    mahadasha: DashaPeriod
    antardasha: AntarDasha
    all_mahadashas: list[DashaPeriod]

    # Panchanga (optional, computed on demand)
    panchanga: Optional[dict] = None


@dataclass
class TransitSnapshot:
    """Current planetary positions -- computed for a given date."""
    date: date
    planets: dict[str, PlanetPosition]
    moon_sign: str
    moon_nakshatra: str
    moon_house_from_natal: Optional[int] = None


# ── Shared helpers (engine-independent) ───────────────────────────

def _get_timezone(lat: float, lng: float) -> str:
    """Get timezone string from coordinates."""
    tz = tf.timezone_at(lat=lat, lng=lng)
    return tz or "UTC"


def _longitude_to_position(planet_name: str, longitude: float, retrograde: bool = False) -> PlanetPosition:
    """Convert a sidereal longitude to full position data."""
    sign_idx = int(longitude / 30) % 12
    degree_in_sign = longitude % 30

    # Nakshatra
    nak_idx = int(longitude / NAKSHATRA_SPAN) % 27
    nak_data = NAKSHATRAS[nak_idx]
    degree_in_nak = longitude - nak_data["start"]
    pada = min(int(degree_in_nak / PADA_SPAN) + 1, 4)

    return PlanetPosition(
        planet=planet_name,
        longitude=longitude,
        sign=RASHIS[sign_idx],
        degree_in_sign=round(degree_in_sign, 2),
        nakshatra=nak_data["name"],
        nakshatra_pada=pada,
        nakshatra_lord=nak_data["lord"],
        retrograde=retrograde,
    )


def _house_from_moon(planet_sign: str, moon_sign: str) -> int:
    """Calculate house number using whole sign houses from Moon."""
    moon_idx = RASHIS.index(moon_sign)
    planet_idx = RASHIS.index(planet_sign)
    return ((planet_idx - moon_idx) % 12) + 1


def _house_from_lagna(planet_sign: str, lagna_sign: str) -> int:
    """Calculate house number using whole sign houses from Lagna."""
    lagna_idx = RASHIS.index(lagna_sign)
    planet_idx = RASHIS.index(planet_sign)
    return ((planet_idx - lagna_idx) % 12) + 1


# ═══════════════════════════════════════════════════════════════════
# DE440 ENGINE -- Position computation
# ═══════════════════════════════════════════════════════════════════

# DE440 body ID mapping: name -> pl7astro body_id
_DE440_BODY_IDS = {
    "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
    "Jupiter": 5, "Venus": 6, "Saturn": 7,
}


def _de440_to_julian_day(dt: datetime) -> float:
    """Convert datetime to Julian Day."""
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    return date_to_jd(dt.year, dt.month, dt.day, hour)


def _de440_calc_positions(jd_ut: float) -> dict[str, tuple[float, bool]]:
    """Compute all planet sidereal positions via DE440 pipeline.

    Returns dict of planet_name -> (sidereal_longitude, is_retrograde).
    """
    result = _de440_pipe.calc_all(jd_ut, timezone=0.0, latitude=0.0, longitude=0.0, ayanamsha_system=1)

    positions = {}
    name_map = {1: "Sun", 2: "Moon", 3: "Mars", 4: "Mercury", 5: "Jupiter", 6: "Venus", 7: "Saturn"}

    for body_id, name in name_map.items():
        planet = result.planets[body_id]
        sid_lon = planet.sidereal_lon
        # Compute velocity for retrograde detection
        T = result.T
        try:
            pos1, vel1 = _de440_eph.geocentric_ecliptic_with_velocity(body_id, T)
            daily_speed = vel1[0]  # degrees per day (approximate from km/day)
            is_retro = daily_speed < 0
        except Exception:
            is_retro = False
        positions[name] = (sid_lon, is_retro)

    # Rahu
    rahu_lon = result.planets[8].sidereal_lon
    positions["Rahu"] = (rahu_lon, False)

    return positions


def _de440_calc_lagna(jd_ut: float, lat: float, lng: float) -> tuple[float, str, str]:
    """Calculate sidereal Ascendant via DE440 pipeline.

    The pipeline computes GAST -> LST -> Ascendant internally.
    """
    # Pipeline expects west-positive longitude internally, but we pass through calc_all
    # which handles the sign convention. Use longitude=0 and let the pipeline compute.
    # For accurate lagna, we need the full pipeline with location.

    # Convert east-positive (user) to west-positive (PL7 internal)
    pl7_lng = -lng
    pl7_tz = 0.0  # We pass JD_UT, so timezone offset is 0

    result = _de440_pipe.calc_all(jd_ut, timezone=pl7_tz, latitude=lat, longitude=pl7_lng, ayanamsha_system=1)
    asc_sid = result.ascendant  # Already sidereal

    pos = _longitude_to_position("Lagna", asc_sid)
    return asc_sid, pos.sign, pos.nakshatra


def _de440_calc_planet_at(jd_ut: float, planet_name: str) -> tuple[float, bool]:
    """Get a single planet's sidereal position from DE440."""
    result = _de440_pipe.calc_all(jd_ut, timezone=0.0, latitude=0.0, longitude=0.0, ayanamsha_system=1)

    body_map = {"Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
                "Jupiter": 5, "Venus": 6, "Saturn": 7, "Rahu": 8}

    body_id = body_map.get(planet_name)
    if body_id is None:
        return 0.0, False

    planet = result.planets[body_id]
    return planet.sidereal_lon, False


# ═══════════════════════════════════════════════════════════════════
# SWISS ENGINE -- Position computation (COMMENTED OUT)
# ═══════════════════════════════════════════════════════════════════

# def _swiss_to_julian_day(dt: datetime) -> float:
#     """Convert datetime to Julian Day for Swiss Ephemeris."""
#     hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
#     return swe.julday(dt.year, dt.month, dt.day, hour)
#
#
# def _swiss_calc_planet(jd: float, planet_id: int) -> tuple[float, bool]:
#     """Calculate sidereal longitude and retrograde status via Swiss."""
#     result = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
#     longitude = result[0][0] % 360
#     speed = result[0][3]
#     return longitude, speed < 0
#
#
# def _swiss_calc_lagna(jd: float, lat: float, lng: float) -> tuple[float, str, str]:
#     """Calculate sidereal Ascendant via Swiss Ephemeris."""
#     cusps, ascmc = swe.houses(jd, lat, lng, b'W')
#     tropical_asc = ascmc[0]
#     ayanamsa = swe.get_ayanamsa(jd)
#     sidereal_asc = (tropical_asc - ayanamsa) % 360
#     pos = _longitude_to_position("Lagna", sidereal_asc)
#     return sidereal_asc, pos.sign, pos.nakshatra


# ═══════════════════════════════════════════════════════════════════
# Engine-independent: House lordships, Dignities, Yogas, Dasha
# (These work on sidereal positions regardless of which engine produced them)
# ═══════════════════════════════════════════════════════════════════

def _calc_house_lords(lagna_sign: str, planets: dict[str, PlanetPosition]) -> list[HouseLord]:
    """Calculate house lordships from Lagna."""
    lagna_idx = RASHIS.index(lagna_sign)
    lords = []
    for house_num in range(1, 13):
        sign_idx = (lagna_idx + house_num - 1) % 12
        sign = RASHIS[sign_idx]
        lord_planet = SIGN_LORDS[sign]
        if lord_planet in planets:
            placed_house = planets[lord_planet].house_from_lagna or 1
            placed_sign = planets[lord_planet].sign
        else:
            placed_house = house_num
            placed_sign = sign
        lords.append(HouseLord(house=house_num, lord=lord_planet,
                               placed_in_house=placed_house, placed_in_sign=placed_sign))
    return lords


def _set_dignities(planets: dict[str, PlanetPosition]):
    """Set exaltation/debilitation/own-sign flags on planet positions."""
    for name, pos in planets.items():
        if name in EXALTATION and pos.sign == EXALTATION[name][0]:
            pos.is_exalted = True
        if name in DEBILITATION and pos.sign == DEBILITATION[name][0]:
            pos.is_debilitated = True
        if name in OWN_SIGNS and pos.sign in OWN_SIGNS[name]:
            pos.is_own_sign = True


def _detect_yogas(planets: dict[str, PlanetPosition], lagna_sign: str) -> list[Yoga]:
    """Detect major classical yogas from the natal chart."""
    yogas = []

    def h(planet: str) -> int:
        return planets[planet].house_from_lagna or 0

    def sign(planet: str) -> str:
        return planets[planet].sign

    def same_sign(p1: str, p2: str) -> bool:
        return sign(p1) == sign(p2)

    # Gaja Kesari Yoga
    moon_sign = planets["Moon"].sign
    jup_house_from_moon = _house_from_moon(sign("Jupiter"), moon_sign)
    if jup_house_from_moon in KENDRA_HOUSES:
        yogas.append(Yoga(name="Gaja Kesari Yoga", category="lunar",
            planets_involved=["Jupiter", "Moon"],
            description="Jupiter in an angular house from Moon -- brings wisdom, reputation, and emotional resilience. The person carries a natural dignity and is respected in their community."))

    # Budhaditya Yoga
    if same_sign("Sun", "Mercury"):
        yogas.append(Yoga(name="Budhaditya Yoga", category="solar",
            planets_involved=["Sun", "Mercury"],
            description="Sun-Mercury conjunction -- sharpens intellect and communication. The person thinks clearly, expresses well, and may excel in fields requiring articulation or analytical skill."))

    # Pancha Mahapurusha Yogas
    mahapurusha = {
        "Mars":    ("Ruchaka",  "Ruchaka Yoga -- Mars in power. Courage, physical vitality, leadership quality, and a capacity to act decisively."),
        "Mercury": ("Bhadra",   "Bhadra Yoga -- Mercury in power. Exceptional communication, learning ability, business acumen."),
        "Jupiter": ("Hamsa",    "Hamsa Yoga -- Jupiter in power. Wisdom, spiritual depth, good fortune, and natural teaching ability."),
        "Venus":   ("Malavya",  "Malavya Yoga -- Venus in power. Refined taste, artistic sensibility, relational grace, and material comfort."),
        "Saturn":  ("Sasha",    "Sasha Yoga -- Saturn in power. Discipline, endurance, organizational mastery, and authority earned through effort."),
    }
    for planet, (yoga_name, yoga_desc) in mahapurusha.items():
        pos = planets[planet]
        in_kendra = pos.house_from_lagna in KENDRA_HOUSES
        in_power = pos.is_exalted or pos.is_own_sign
        if in_kendra and in_power:
            yogas.append(Yoga(name=yoga_name, category="pancha_mahapurusha",
                planets_involved=[planet], description=yoga_desc))

    # Raja Yogas
    lagna_idx = RASHIS.index(lagna_sign)
    kendra_lords = set()
    trikona_lords = set()
    for house_num in range(1, 13):
        sign_idx = (lagna_idx + house_num - 1) % 12
        lord = SIGN_LORDS[RASHIS[sign_idx]]
        if house_num in KENDRA_HOUSES:
            kendra_lords.add((lord, house_num))
        if house_num in TRIKONA_HOUSES:
            trikona_lords.add((lord, house_num))

    raja_found = set()
    for kl, kh in kendra_lords:
        for tl, th in trikona_lords:
            if kl == tl:
                key = frozenset([kl])
                if key not in raja_found:
                    raja_found.add(key)
                    yogas.append(Yoga(name=f"Raja Yoga ({kl})", category="raja",
                        planets_involved=[kl],
                        description=f"{kl} rules both a kendra (house {kh}) and a trikona (house {th}) -- a powerful combination for worldly success, authority, and recognition."))
            elif same_sign(kl, tl) if (kl in planets and tl in planets) else False:
                key = frozenset([kl, tl])
                if key not in raja_found:
                    raja_found.add(key)
                    yogas.append(Yoga(name=f"Raja Yoga ({kl}-{tl})", category="raja",
                        planets_involved=[kl, tl],
                        description=f"Kendra lord {kl} (house {kh}) conjunct trikona lord {tl} (house {th}) -- creates conditions for meaningful achievement, leadership, or social elevation."))

    # Dhana Yoga
    second_sign = RASHIS[(lagna_idx + 1) % 12]
    eleventh_sign = RASHIS[(lagna_idx + 10) % 12]
    lord_2 = SIGN_LORDS[second_sign]
    lord_11 = SIGN_LORDS[eleventh_sign]
    if lord_2 in planets and lord_11 in planets:
        if same_sign(lord_2, lord_11):
            yogas.append(Yoga(name="Dhana Yoga (2nd-11th)", category="dhana",
                planets_involved=[lord_2, lord_11],
                description="Lords of wealth (2nd house) and gains (11th house) are connected -- strong potential for financial growth and material stability."))

    # Neecha Bhanga Raja Yoga
    for planet_name, pos in planets.items():
        if pos.is_debilitated and planet_name in DEBILITATION:
            deb_sign = DEBILITATION[planet_name][0]
            sign_lord = SIGN_LORDS[deb_sign]
            if sign_lord in planets:
                lord_house_lagna = planets[sign_lord].house_from_lagna or 0
                lord_house_moon = _house_from_moon(planets[sign_lord].sign, planets["Moon"].sign)
                if lord_house_lagna in KENDRA_HOUSES or lord_house_moon in KENDRA_HOUSES:
                    yogas.append(Yoga(name=f"Neecha Bhanga ({planet_name})", category="combination",
                        planets_involved=[planet_name, sign_lord],
                        description=f"{planet_name}'s debilitation is cancelled by {sign_lord}'s strong placement -- challenges in this area ultimately lead to mastery."))

    # Chandra-Mangal Yoga
    if same_sign("Moon", "Mars"):
        yogas.append(Yoga(name="Chandra-Mangal Yoga", category="lunar",
            planets_involved=["Moon", "Mars"],
            description="Moon-Mars conjunction -- gives financial acumen, emotional courage, and drive."))

    # Saraswati Yoga
    learning_planets = ["Jupiter", "Venus", "Mercury"]
    good_houses = KENDRA_HOUSES | TRIKONA_HOUSES | {2}
    if all(planets[p].house_from_lagna in good_houses for p in learning_planets if p in planets):
        yogas.append(Yoga(name="Saraswati Yoga", category="combination",
            planets_involved=learning_planets,
            description="Jupiter, Venus, and Mercury well-placed -- blesses with learning, eloquence, artistic talent, and refined intelligence."))

    return yogas


# ── Vimshottari Dasha calculation ────────────────────────────────

def _calc_vimshottari(moon_longitude: float, birth_dt: datetime) -> list[DashaPeriod]:
    """Calculate all Vimshottari Mahadasha periods from birth."""
    nak_idx = int(moon_longitude / NAKSHATRA_SPAN)
    nak_lord = NAKSHATRAS[nak_idx]["lord"]
    lord_names = [d[0] for d in VIMSHOTTARI_SEQUENCE]
    start_idx = lord_names.index(nak_lord)
    degree_in_nak = moon_longitude - NAKSHATRAS[nak_idx]["start"]
    fraction_remaining = 1.0 - (degree_in_nak / NAKSHATRA_SPAN)

    periods = []
    current_dt = birth_dt
    for i in range(9):
        idx = (start_idx + i) % 9
        lord, total_years = VIMSHOTTARI_SEQUENCE[idx]
        years = total_years * fraction_remaining if i == 0 else float(total_years)
        days = years * 365.25
        end_dt = current_dt + timedelta(days=days)
        periods.append(DashaPeriod(lord=lord, start=current_dt, end=end_dt, years=round(years, 4)))
        current_dt = end_dt
    return periods


def _find_current_dasha(periods: list[DashaPeriod], target_dt: datetime) -> DashaPeriod:
    """Find which mahadasha is active at a given date."""
    for period in periods:
        if period.start <= target_dt < period.end:
            return period
    return periods[-1]


def _calc_antardasha(mahadasha: DashaPeriod, target_dt: datetime) -> AntarDasha:
    """Calculate the antardasha within a mahadasha."""
    lord_names = [d[0] for d in VIMSHOTTARI_SEQUENCE]
    lord_years = {d[0]: d[1] for d in VIMSHOTTARI_SEQUENCE}
    start_idx = lord_names.index(mahadasha.lord)
    maha_total_days = (mahadasha.end - mahadasha.start).total_seconds() / 86400
    current_dt = mahadasha.start
    for i in range(9):
        idx = (start_idx + i) % 9
        antar_lord = lord_names[idx]
        proportion = lord_years[antar_lord] / VIMSHOTTARI_TOTAL_YEARS
        antar_days = maha_total_days * proportion
        end_dt = current_dt + timedelta(days=antar_days)
        if current_dt <= target_dt < end_dt:
            return AntarDasha(mahadasha_lord=mahadasha.lord, antardasha_lord=antar_lord,
                              start=current_dt, end=end_dt)
        current_dt = end_dt
    return AntarDasha(mahadasha_lord=mahadasha.lord,
                      antardasha_lord=lord_names[(start_idx + 8) % 9],
                      start=current_dt, end=mahadasha.end)


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def compute_natal_chart(
    birth_date: date,
    birth_time: str,
    latitude: float,
    longitude: float,
    as_of: datetime | None = None,
) -> NatalChart:
    """Compute full natal chart from birth details.

    Uses DE440 as primary engine. All Vedic layers (dasha, yoga, houses,
    dignities, navamsha, panchanga) are engine-independent.
    """
    # Parse birth time
    if birth_time == "unknown":
        hour, minute = 12, 0
    else:
        parts = birth_time.split(":")
        hour, minute = int(parts[0]), int(parts[1])

    # Get timezone and convert to UTC
    tz_name = _get_timezone(latitude, longitude)
    tz = pytz.timezone(tz_name)
    local_dt = tz.localize(datetime(birth_date.year, birth_date.month, birth_date.day, hour, minute))
    utc_dt = local_dt.astimezone(pytz.UTC)

    # Julian day
    jd = _de440_to_julian_day(utc_dt)

    # ── Position computation (DE440) ──
    all_positions = _de440_calc_positions(jd)
    lagna_deg, lagna_sign, lagna_nak = _de440_calc_lagna(jd, latitude, longitude)

    # ── Swiss backup (commented out) ──
    # jd = _swiss_to_julian_day(utc_dt)
    # planets = {}
    # for planet_name, planet_id in PLANET_IDS.items():
    #     lng, retro = _swiss_calc_planet(jd, planet_id)
    #     planets[planet_name] = _longitude_to_position(planet_name, lng, retro)
    # lagna_deg, lagna_sign, lagna_nak = _swiss_calc_lagna(jd, latitude, longitude)

    # Build planet positions from DE440 output
    planets = {}
    for planet_name, (sid_lon, retro) in all_positions.items():
        planets[planet_name] = _longitude_to_position(planet_name, sid_lon, retro)

    # Ketu = Rahu + 180
    rahu_lng = planets["Rahu"].longitude
    ketu_lng = (rahu_lng + 180) % 360
    planets["Ketu"] = _longitude_to_position("Ketu", ketu_lng, False)

    # Moon data (primary anchor)
    moon = planets["Moon"]

    # ── Engine-independent Vedic layers ──

    # House positions
    for p in planets.values():
        p.house_from_moon = _house_from_moon(p.sign, moon.sign)
        p.house_from_lagna = _house_from_lagna(p.sign, lagna_sign)

    # Dignities
    _set_dignities(planets)

    # Navamsha
    from llm.engine.varga import navamsha_sign
    for p in planets.values():
        p.navamsha_sign = navamsha_sign(p.longitude)

    # House lordships
    house_lords = _calc_house_lords(lagna_sign, planets)

    # Yogas
    yogas = _detect_yogas(planets, lagna_sign)

    # Dasha
    all_dashas = _calc_vimshottari(moon.longitude, utc_dt)
    now = as_of or datetime.now(pytz.UTC)
    current_maha = _find_current_dasha(all_dashas, now)
    current_antar = _calc_antardasha(current_maha, now)

    # Panchanga
    from llm.engine.panchanga import compute_panchanga
    panch = compute_panchanga(birth_date, latitude, longitude)

    return NatalChart(
        birth_dt=utc_dt, latitude=latitude, longitude=longitude,
        timezone=tz_name, julian_day=jd,
        lagna_sign=lagna_sign, lagna_degree=round(lagna_deg % 30, 2), lagna_nakshatra=lagna_nak,
        planets=planets, house_lords=house_lords, yogas=yogas,
        moon_sign=moon.sign, moon_degree=moon.degree_in_sign,
        moon_nakshatra=moon.nakshatra, moon_nakshatra_pada=moon.nakshatra_pada,
        moon_nakshatra_lord=moon.nakshatra_lord,
        all_mahadashas=all_dashas, mahadasha=current_maha, antardasha=current_antar,
        panchanga=panch,
    )


def compute_transits(
    target_date: date,
    natal_moon_sign: str | None = None,
) -> TransitSnapshot:
    """Compute current planetary positions for a given date.

    Uses DE440 as primary engine.
    """
    jd = date_to_jd(target_date.year, target_date.month, target_date.day, 12.0)

    # ── DE440 positions ──
    all_positions = _de440_calc_positions(jd)

    # ── Swiss backup (commented out) ──
    # jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
    # planets = {}
    # for planet_name, planet_id in PLANET_IDS.items():
    #     lng, retro = _swiss_calc_planet(jd, planet_id)
    #     pos = _longitude_to_position(planet_name, lng, retro)
    #     if natal_moon_sign:
    #         pos.house_from_moon = _house_from_moon(pos.sign, natal_moon_sign)
    #     planets[planet_name] = pos

    planets = {}
    for planet_name, (sid_lon, retro) in all_positions.items():
        pos = _longitude_to_position(planet_name, sid_lon, retro)
        if natal_moon_sign:
            pos.house_from_moon = _house_from_moon(pos.sign, natal_moon_sign)
        planets[planet_name] = pos

    # Ketu
    rahu_lng = planets["Rahu"].longitude
    ketu_lng = (rahu_lng + 180) % 360
    ketu = _longitude_to_position("Ketu", ketu_lng, False)
    if natal_moon_sign:
        ketu.house_from_moon = _house_from_moon(ketu.sign, natal_moon_sign)
    planets["Ketu"] = ketu

    moon = planets["Moon"]

    return TransitSnapshot(
        date=target_date, planets=planets,
        moon_sign=moon.sign, moon_nakshatra=moon.nakshatra,
        moon_house_from_natal=moon.house_from_moon,
    )
