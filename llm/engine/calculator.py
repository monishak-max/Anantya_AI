"""
Astro Computation Engine — computes all Jyotish data from birth details.

Uses Swiss Ephemeris (pyswisseph) with Lahiri ayanamsa and sidereal zodiac.

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
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional

import swisseph as swe
from timezonefinder import TimezoneFinder
import pytz

from llm.engine.constants import (
    RASHIS,
    NAKSHATRAS,
    NAKSHATRA_SPAN,
    PADA_SPAN,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    PLANET_IDS,
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

# Initialize Swiss Ephemeris with Lahiri ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

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
    """Complete natal chart data — everything the LLM layer needs."""
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
    """Current planetary positions — computed for a given date."""
    date: date
    planets: dict[str, PlanetPosition]
    moon_sign: str
    moon_nakshatra: str
    moon_house_from_natal: Optional[int] = None


# ── Core computation functions ─────────────────────────────────────

def _get_timezone(lat: float, lng: float) -> str:
    """Get timezone string from coordinates."""
    tz = tf.timezone_at(lat=lat, lng=lng)
    return tz or "UTC"


def _to_julian_day(dt: datetime) -> float:
    """Convert datetime to Julian Day for Swiss Ephemeris."""
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    return swe.julday(dt.year, dt.month, dt.day, hour)


def _calc_planet(jd: float, planet_id: int) -> tuple[float, bool]:
    """
    Calculate sidereal longitude and retrograde status for a planet.
    Returns (longitude, is_retrograde).
    """
    result = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
    longitude = result[0][0] % 360
    speed = result[0][3]  # daily speed in longitude
    return longitude, speed < 0


def _longitude_to_position(planet_name: str, longitude: float, retrograde: bool = False) -> PlanetPosition:
    """Convert a sidereal longitude to full position data."""
    sign_idx = int(longitude / 30)
    degree_in_sign = longitude % 30

    # Nakshatra
    nak_idx = int(longitude / NAKSHATRA_SPAN)
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
    """
    Calculate house number using whole sign houses from Moon.
    Moon's sign = house 1.
    """
    moon_idx = RASHIS.index(moon_sign)
    planet_idx = RASHIS.index(planet_sign)
    return ((planet_idx - moon_idx) % 12) + 1


# ── Lagna (Ascendant) computation ──────────────────────────────────

def _calc_lagna(jd: float, lat: float, lng: float) -> tuple[float, str, str]:
    """
    Calculate the sidereal Ascendant (Lagna).
    Returns (degree, sign, nakshatra).
    """
    # Get tropical ascendant, then subtract ayanamsa for sidereal
    cusps, ascmc = swe.houses(jd, lat, lng, b'W')  # Whole sign houses
    tropical_asc = ascmc[0]
    ayanamsa = swe.get_ayanamsa(jd)
    sidereal_asc = (tropical_asc - ayanamsa) % 360

    pos = _longitude_to_position("Lagna", sidereal_asc)
    return sidereal_asc, pos.sign, pos.nakshatra


def _house_from_lagna(planet_sign: str, lagna_sign: str) -> int:
    """Calculate house number using whole sign houses from Lagna."""
    lagna_idx = RASHIS.index(lagna_sign)
    planet_idx = RASHIS.index(planet_sign)
    return ((planet_idx - lagna_idx) % 12) + 1


# ── House lordships ────────────────────────────────────────────────

def _calc_house_lords(lagna_sign: str, planets: dict[str, PlanetPosition]) -> list[HouseLord]:
    """
    Calculate house lordships from Lagna.
    Each house is a whole sign; the lord is the ruler of that sign.
    """
    lagna_idx = RASHIS.index(lagna_sign)
    lords = []

    for house_num in range(1, 13):
        sign_idx = (lagna_idx + house_num - 1) % 12
        sign = RASHIS[sign_idx]
        lord_planet = SIGN_LORDS[sign]

        # Where is this lord placed?
        if lord_planet in planets:
            placed_house = planets[lord_planet].house_from_lagna or 1
            placed_sign = planets[lord_planet].sign
        else:
            placed_house = house_num
            placed_sign = sign

        lords.append(HouseLord(
            house=house_num,
            lord=lord_planet,
            placed_in_house=placed_house,
            placed_in_sign=placed_sign,
        ))

    return lords


# ── Dignity check ──────────────────────────────────────────────────

def _set_dignities(planets: dict[str, PlanetPosition]):
    """Set exaltation/debilitation/own-sign flags on planet positions."""
    for name, pos in planets.items():
        if name in EXALTATION and pos.sign == EXALTATION[name][0]:
            pos.is_exalted = True
        if name in DEBILITATION and pos.sign == DEBILITATION[name][0]:
            pos.is_debilitated = True
        if name in OWN_SIGNS and pos.sign in OWN_SIGNS[name]:
            pos.is_own_sign = True


# ── Yoga detection ─────────────────────────────────────────────────

def _detect_yogas(planets: dict[str, PlanetPosition], lagna_sign: str) -> list[Yoga]:
    """
    Detect major classical yogas from the natal chart.
    Returns a list of Yoga objects with human-readable descriptions.
    """
    yogas = []

    # Helper: get house from lagna for a planet
    def h(planet: str) -> int:
        return planets[planet].house_from_lagna or 0

    def sign(planet: str) -> str:
        return planets[planet].sign

    def same_sign(p1: str, p2: str) -> bool:
        return sign(p1) == sign(p2)

    # ── Gaja Kesari Yoga ──────────────────────────────────────
    # Jupiter in kendra from Moon
    moon_sign = planets["Moon"].sign
    jup_house_from_moon = _house_from_moon(sign("Jupiter"), moon_sign)
    if jup_house_from_moon in KENDRA_HOUSES:
        yogas.append(Yoga(
            name="Gaja Kesari Yoga",
            category="lunar",
            planets_involved=["Jupiter", "Moon"],
            description="Jupiter in an angular house from Moon — brings wisdom, reputation, and emotional resilience. The person carries a natural dignity and is respected in their community.",
        ))

    # ── Budhaditya Yoga ───────────────────────────────────────
    # Sun and Mercury in the same sign
    if same_sign("Sun", "Mercury"):
        yogas.append(Yoga(
            name="Budhaditya Yoga",
            category="solar",
            planets_involved=["Sun", "Mercury"],
            description="Sun-Mercury conjunction — sharpens intellect and communication. The person thinks clearly, expresses well, and may excel in fields requiring articulation or analytical skill.",
        ))

    # ── Pancha Mahapurusha Yogas ──────────────────────────────
    # Mars/Mercury/Jupiter/Venus/Saturn in own sign or exalted AND in kendra from lagna
    mahapurusha = {
        "Mars":    ("Ruchaka",    "Ruchaka Yoga — Mars in power. Courage, physical vitality, leadership quality, and a capacity to act decisively. Thrives in competitive or pioneering environments."),
        "Mercury": ("Bhadra",     "Bhadra Yoga — Mercury in power. Exceptional communication, learning ability, business acumen. A sharp, adaptable mind that processes complexity with ease."),
        "Jupiter": ("Hamsa",      "Hamsa Yoga — Jupiter in power. Wisdom, spiritual depth, good fortune, and natural teaching ability. The person radiates ethical clarity and expansive vision."),
        "Venus":   ("Malavya",    "Malavya Yoga — Venus in power. Refined taste, artistic sensibility, relational grace, and material comfort. Life carries a quality of beauty and harmony."),
        "Saturn":  ("Sasha",      "Sasha Yoga — Saturn in power. Discipline, endurance, organizational mastery, and authority earned through effort. A slow but formidable builder."),
    }
    for planet, (yoga_name, yoga_desc) in mahapurusha.items():
        pos = planets[planet]
        in_kendra = pos.house_from_lagna in KENDRA_HOUSES
        in_power = pos.is_exalted or pos.is_own_sign
        if in_kendra and in_power:
            yogas.append(Yoga(
                name=yoga_name,
                category="pancha_mahapurusha",
                planets_involved=[planet],
                description=yoga_desc,
            ))

    # ── Raja Yogas (Kendra-Trikona lord connections) ──────────
    # When a kendra lord and a trikona lord are conjunct or the same planet
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

    # Check for conjunctions between kendra and trikona lords
    raja_found = set()
    for kl, kh in kendra_lords:
        for tl, th in trikona_lords:
            if kl == tl:
                # Same planet rules both kendra and trikona — strong raja yoga
                key = frozenset([kl])
                if key not in raja_found:
                    raja_found.add(key)
                    yogas.append(Yoga(
                        name=f"Raja Yoga ({kl})",
                        category="raja",
                        planets_involved=[kl],
                        description=f"{kl} rules both a kendra (house {kh}) and a trikona (house {th}) — a powerful combination for worldly success, authority, and recognition. Life offers genuine opportunities for rise.",
                    ))
            elif same_sign(kl, tl) if (kl in planets and tl in planets) else False:
                key = frozenset([kl, tl])
                if key not in raja_found:
                    raja_found.add(key)
                    yogas.append(Yoga(
                        name=f"Raja Yoga ({kl}-{tl})",
                        category="raja",
                        planets_involved=[kl, tl],
                        description=f"Kendra lord {kl} (house {kh}) conjunct trikona lord {tl} (house {th}) — creates conditions for meaningful achievement, leadership, or social elevation.",
                    ))

    # ── Dhana Yogas (wealth) ──────────────────────────────────
    # 2nd lord and 11th lord connected (conjunct)
    second_sign = RASHIS[(lagna_idx + 1) % 12]
    eleventh_sign = RASHIS[(lagna_idx + 10) % 12]
    lord_2 = SIGN_LORDS[second_sign]
    lord_11 = SIGN_LORDS[eleventh_sign]
    if lord_2 in planets and lord_11 in planets:
        if same_sign(lord_2, lord_11):
            yogas.append(Yoga(
                name="Dhana Yoga (2nd-11th)",
                category="dhana",
                planets_involved=[lord_2, lord_11],
                description=f"Lords of wealth (2nd house) and gains (11th house) are connected — strong potential for financial growth, resource accumulation, and material stability through effort.",
            ))

    # ── Neecha Bhanga Raja Yoga (cancelled debilitation) ──────
    for planet_name, pos in planets.items():
        if pos.is_debilitated and planet_name in DEBILITATION:
            deb_sign = DEBILITATION[planet_name][0]
            sign_lord = SIGN_LORDS[deb_sign]
            # If the lord of the debilitation sign is in kendra from lagna or Moon
            if sign_lord in planets:
                lord_house_lagna = planets[sign_lord].house_from_lagna or 0
                lord_house_moon = _house_from_moon(planets[sign_lord].sign, planets["Moon"].sign)
                if lord_house_lagna in KENDRA_HOUSES or lord_house_moon in KENDRA_HOUSES:
                    yogas.append(Yoga(
                        name=f"Neecha Bhanga ({planet_name})",
                        category="combination",
                        planets_involved=[planet_name, sign_lord],
                        description=f"{planet_name}'s debilitation is cancelled by {sign_lord}'s strong placement — what appears as a weakness becomes a source of depth. Challenges in this area ultimately lead to mastery.",
                    ))

    # ── Chandra-Mangal Yoga ───────────────────────────────────
    if same_sign("Moon", "Mars"):
        yogas.append(Yoga(
            name="Chandra-Mangal Yoga",
            category="lunar",
            planets_involved=["Moon", "Mars"],
            description="Moon-Mars conjunction — gives financial acumen, emotional courage, and drive. Can bring wealth through effort and a quality of determination in pursuing goals.",
        ))

    # ── Saraswati Yoga ────────────────────────────────────────
    # Jupiter, Venus, Mercury in kendras/trikonas/2nd house
    learning_planets = ["Jupiter", "Venus", "Mercury"]
    good_houses = KENDRA_HOUSES | TRIKONA_HOUSES | {2}
    if all(planets[p].house_from_lagna in good_houses for p in learning_planets if p in planets):
        yogas.append(Yoga(
            name="Saraswati Yoga",
            category="combination",
            planets_involved=learning_planets,
            description="Jupiter, Venus, and Mercury well-placed — blesses with learning, eloquence, artistic talent, and refined intelligence. The person may excel in education, arts, or creative expression.",
        ))

    return yogas


# ── Vimshottari Dasha calculation ──────────────────────────────────

def _calc_vimshottari(moon_longitude: float, birth_dt: datetime) -> list[DashaPeriod]:
    """
    Calculate all Vimshottari Mahadasha periods from birth.

    The dasha sequence starts from the nakshatra lord of the natal Moon.
    The balance of the first dasha depends on how far the Moon has
    traveled through its nakshatra at birth.
    """
    # Find Moon's nakshatra and its lord
    nak_idx = int(moon_longitude / NAKSHATRA_SPAN)
    nak_lord = NAKSHATRAS[nak_idx]["lord"]

    # Find position in the Vimshottari sequence
    lord_names = [d[0] for d in VIMSHOTTARI_SEQUENCE]
    start_idx = lord_names.index(nak_lord)

    # Balance of first dasha: fraction of nakshatra remaining
    degree_in_nak = moon_longitude - NAKSHATRAS[nak_idx]["start"]
    fraction_elapsed = degree_in_nak / NAKSHATRA_SPAN
    fraction_remaining = 1.0 - fraction_elapsed

    periods = []
    current_dt = birth_dt

    for i in range(9):  # 9 dashas in the cycle
        idx = (start_idx + i) % 9
        lord, total_years = VIMSHOTTARI_SEQUENCE[idx]

        if i == 0:
            # First dasha: only the remaining balance
            years = total_years * fraction_remaining
        else:
            years = float(total_years)

        days = years * 365.25
        end_dt = current_dt + timedelta(days=days)

        periods.append(DashaPeriod(
            lord=lord,
            start=current_dt,
            end=end_dt,
            years=round(years, 4),
        ))

        current_dt = end_dt

    return periods


def _find_current_dasha(periods: list[DashaPeriod], target_dt: datetime) -> DashaPeriod:
    """Find which mahadasha is active at a given date."""
    for period in periods:
        if period.start <= target_dt < period.end:
            return period
    # If beyond all periods, return the last one
    return periods[-1]


def _calc_antardasha(mahadasha: DashaPeriod, target_dt: datetime) -> AntarDasha:
    """
    Calculate the antardasha (sub-period) within a mahadasha.
    Antardashas follow the same Vimshottari sequence starting from the mahadasha lord.
    """
    lord_names = [d[0] for d in VIMSHOTTARI_SEQUENCE]
    lord_years = {d[0]: d[1] for d in VIMSHOTTARI_SEQUENCE}
    start_idx = lord_names.index(mahadasha.lord)

    maha_total_days = (mahadasha.end - mahadasha.start).total_seconds() / 86400

    current_dt = mahadasha.start

    for i in range(9):
        idx = (start_idx + i) % 9
        antar_lord = lord_names[idx]

        # Antardasha duration = (mahadasha_years * antardasha_years / 120) scaled to actual maha duration
        proportion = lord_years[antar_lord] / VIMSHOTTARI_TOTAL_YEARS
        antar_days = maha_total_days * proportion
        end_dt = current_dt + timedelta(days=antar_days)

        if current_dt <= target_dt < end_dt:
            return AntarDasha(
                mahadasha_lord=mahadasha.lord,
                antardasha_lord=antar_lord,
                start=current_dt,
                end=end_dt,
            )

        current_dt = end_dt

    # Fallback: return last antardasha
    return AntarDasha(
        mahadasha_lord=mahadasha.lord,
        antardasha_lord=lord_names[(start_idx + 8) % 9],
        start=current_dt,
        end=mahadasha.end,
    )


# ── Public API ─────────────────────────────────────────────────────

def compute_natal_chart(
    birth_date: date,
    birth_time: str,        # "HH:MM" format, or "unknown"
    latitude: float,
    longitude: float,
    as_of: datetime | None = None,
) -> NatalChart:
    """
    Compute full natal chart from birth details.

    Args:
        birth_date: Date of birth
        birth_time: Time of birth as "HH:MM" or "unknown" (defaults to noon)
        latitude: Birth location latitude
        longitude: Birth location longitude
        as_of: Date to calculate current dasha for (defaults to now)

    Returns:
        NatalChart with all planet positions, Moon data, and dasha info
    """
    # Parse birth time
    if birth_time == "unknown":
        hour, minute = 12, 0  # Default to noon
    else:
        parts = birth_time.split(":")
        hour, minute = int(parts[0]), int(parts[1])

    # Get timezone and convert to UTC
    tz_name = _get_timezone(latitude, longitude)
    tz = pytz.timezone(tz_name)
    local_dt = tz.localize(datetime(birth_date.year, birth_date.month, birth_date.day, hour, minute))
    utc_dt = local_dt.astimezone(pytz.UTC)

    # Julian day
    jd = _to_julian_day(utc_dt)

    # Calculate Lagna (Ascendant)
    lagna_deg, lagna_sign, lagna_nak = _calc_lagna(jd, latitude, longitude)

    # Calculate all planet positions
    planets = {}
    for planet_name, planet_id in PLANET_IDS.items():
        lng, retro = _calc_planet(jd, planet_id)
        planets[planet_name] = _longitude_to_position(planet_name, lng, retro)

    # Ketu = Rahu + 180°
    rahu_lng = planets["Rahu"].longitude
    ketu_lng = (rahu_lng + 180) % 360
    planets["Ketu"] = _longitude_to_position("Ketu", ketu_lng, planets["Rahu"].retrograde)

    # Moon data (primary anchor)
    moon = planets["Moon"]

    # Set house positions from both Moon and Lagna
    for p in planets.values():
        p.house_from_moon = _house_from_moon(p.sign, moon.sign)
        p.house_from_lagna = _house_from_lagna(p.sign, lagna_sign)

    # Set dignities (exalted, debilitated, own sign)
    _set_dignities(planets)

    # Navamsha (D-9) for each planet
    from llm.engine.varga import navamsha_sign
    for p in planets.values():
        p.navamsha_sign = navamsha_sign(p.longitude)

    # House lordships (from Lagna)
    house_lords = _calc_house_lords(lagna_sign, planets)

    # Yoga detection
    yogas = _detect_yogas(planets, lagna_sign)

    # Vimshottari Dasha
    all_dashas = _calc_vimshottari(moon.longitude, utc_dt)
    now = as_of or datetime.now(pytz.UTC)
    current_maha = _find_current_dasha(all_dashas, now)
    current_antar = _calc_antardasha(current_maha, now)

    # Panchanga
    from llm.engine.panchanga import compute_panchanga
    panch = compute_panchanga(birth_date, latitude, longitude)

    return NatalChart(
        birth_dt=utc_dt,
        latitude=latitude,
        longitude=longitude,
        timezone=tz_name,
        julian_day=jd,
        lagna_sign=lagna_sign,
        lagna_degree=round(lagna_deg % 30, 2),
        lagna_nakshatra=lagna_nak,
        planets=planets,
        house_lords=house_lords,
        yogas=yogas,
        moon_sign=moon.sign,
        moon_degree=moon.degree_in_sign,
        moon_nakshatra=moon.nakshatra,
        moon_nakshatra_pada=moon.nakshatra_pada,
        moon_nakshatra_lord=moon.nakshatra_lord,
        all_mahadashas=all_dashas,
        mahadasha=current_maha,
        antardasha=current_antar,
        panchanga=panch,
    )


def compute_transits(
    target_date: date,
    natal_moon_sign: str | None = None,
) -> TransitSnapshot:
    """
    Compute current planetary positions for a given date.

    Args:
        target_date: Date to compute transits for
        natal_moon_sign: If provided, calculates house_from_moon for each planet

    Returns:
        TransitSnapshot with all planet positions
    """
    # Use noon UTC for transit calculations
    jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)

    planets = {}
    for planet_name, planet_id in PLANET_IDS.items():
        lng, retro = _calc_planet(jd, planet_id)
        pos = _longitude_to_position(planet_name, lng, retro)
        if natal_moon_sign:
            pos.house_from_moon = _house_from_moon(pos.sign, natal_moon_sign)
        planets[planet_name] = pos

    # Ketu
    rahu_lng = planets["Rahu"].longitude
    ketu_lng = (rahu_lng + 180) % 360
    ketu = _longitude_to_position("Ketu", ketu_lng, planets["Rahu"].retrograde)
    if natal_moon_sign:
        ketu.house_from_moon = _house_from_moon(ketu.sign, natal_moon_sign)
    planets["Ketu"] = ketu

    moon = planets["Moon"]

    return TransitSnapshot(
        date=target_date,
        planets=planets,
        moon_sign=moon.sign,
        moon_nakshatra=moon.nakshatra,
        moon_house_from_natal=moon.house_from_moon,
    )
