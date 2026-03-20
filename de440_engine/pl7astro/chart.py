"""High-level Chart API — clean interface over the pl7astro pipeline.

Usage:
    from pl7astro import Chart

    chart = Chart(date="1946-08-19 08:51", lat=33.6669, lon=-93.5914, tz=-6)
    chart.planets()       # all planet positions
    chart.houses()        # house cusps
    chart.nakshatras()    # nakshatra for each planet
    chart.dasha()         # Vimshottari dasha timeline
    chart.yogas()         # detected yogas
    chart.to_json()       # full structured output for LLM consumption
"""
import hashlib
import json
import math
from datetime import datetime

from .astro.julian import date_to_jd, jd_to_date, normalize_degrees
from .astro.pipeline import PLANET_NAMES
from .data.loader import create_pipeline
from .vedic.nakshatra import calc_nakshatra, NAKSHATRA_NAMES
from .vedic.dasha import build_vimshottari_timeline
from .vedic.yoga import calc_panchanga_yoga, detect_yogas
from .vedic.houses import equal_house_cusps
from .vedic.varga import calc_varga, lon_to_sign, VARGA_FUNCTIONS
from .vedic.ayanamsha import calc_ayanamsha

# Signs
SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Module-level shared pipeline (lazy init)
_shared_pipeline = None


def _get_pipeline():
    global _shared_pipeline
    if _shared_pipeline is None:
        _shared_pipeline = create_pipeline()
    return _shared_pipeline


def _parse_datetime(date_str):
    """Parse date string into (year, month, day, hour_decimal).

    Accepts: "YYYY-MM-DD HH:MM", "YYYY-MM-DD HH:MM:SS", "YYYY-MM-DD"
    """
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            return dt.year, dt.month, dt.day, hour
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str!r}. Use 'YYYY-MM-DD HH:MM' format.")


def _lon_to_dms(lon):
    """Convert longitude to sign, degrees, minutes, seconds."""
    sign_idx = int(lon / 30.0) % 12
    deg_in_sign = lon % 30.0
    d = int(deg_in_sign)
    m = int((deg_in_sign - d) * 60)
    s = round(((deg_in_sign - d) * 60 - m) * 60, 1)
    return {
        "sign": SIGN_NAMES[sign_idx],
        "sign_index": sign_idx,
        "degrees": d,
        "minutes": m,
        "seconds": s,
        "total_degrees": round(lon, 6),
    }


def _jd_to_iso(jd):
    """Convert JD to ISO date string."""
    y, m, d, h = jd_to_date(jd)
    hour = int(h)
    minute = int((h - hour) * 60)
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}T{hour:02d}:{minute:02d}"


class Chart:
    """A birth chart (Kundali) with lazy computation and caching.

    Args:
        date: Birth date/time string "YYYY-MM-DD HH:MM" (local time)
        lat: Latitude in degrees (north positive)
        lon: Longitude in degrees (east positive, standard convention)
             Note: internally converted to PL7's west-positive convention
        tz: Timezone offset from UTC in hours (e.g., -6 for CST, +5.5 for IST)
            Positive = east of Greenwich (standard convention)
        ayanamsha: 1=Lahiri(default), 2=Tropical, 3=Raman, 4=KP, etc.
        pipeline: Optional Pipeline instance (uses shared singleton if None)
    """

    def __init__(self, date, lat, lon, tz=0.0, ayanamsha=1, pipeline=None):
        # Parse date
        if isinstance(date, str):
            y, m, d, h = _parse_datetime(date)
        elif isinstance(date, (list, tuple)) and len(date) >= 3:
            y, m, d = date[0], date[1], date[2]
            h = date[3] if len(date) > 3 else 0.0
        else:
            raise ValueError("date must be a string 'YYYY-MM-DD HH:MM' or (y,m,d,h) tuple")

        self._year = y
        self._month = m
        self._day = d
        self._hour = h
        self._lat = lat
        self._lon = lon
        self._tz = tz
        self._ayanamsha_system = ayanamsha

        # Convert to PL7 internal conventions
        # PL7: timezone = hours WEST of Greenwich (CST=6.0), longitude = west positive
        self._pl7_timezone = -tz  # standard east-positive → PL7 west-positive
        self._pl7_longitude = -lon  # standard east-positive → PL7 west-positive

        # Compute local JD (as PL7 stores it)
        self._jd_local = date_to_jd(y, m, d, h)

        # Pipeline
        self._pipeline = pipeline or _get_pipeline()

        # Lazy cache
        self._result = None
        self._dasha_cache = None
        self._yoga_cache = None

    def _compute(self):
        """Run the pipeline (lazy, cached)."""
        if self._result is None:
            self._result = self._pipeline.calc_all(
                jd_local=self._jd_local,
                timezone=self._pl7_timezone,
                latitude=self._lat,
                longitude=self._pl7_longitude,
                ayanamsha_system=self._ayanamsha_system,
            )
        return self._result

    @property
    def cache_key(self):
        """Deterministic cache key for this chart's input parameters."""
        raw = f"{self._jd_local:.10f}|{self._pl7_timezone:.4f}|{self._lat:.6f}|{self._pl7_longitude:.6f}|{self._ayanamsha_system}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ── Planet positions ──

    def planets(self):
        """All planet positions (sidereal).

        Returns:
            list of dicts with planet name, sidereal position (sign/degree/DMS),
            tropical position, and nakshatra.
        """
        r = self._compute()
        out = []
        for pid in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            p = r.planets[pid]
            nak = calc_nakshatra(p.sidereal_lon)
            out.append({
                "id": pid,
                "name": p.name,
                "sidereal": _lon_to_dms(p.sidereal_lon),
                "tropical_lon": round(p.tropical_lon, 6),
                "nakshatra": nak["name"],
                "nakshatra_pada": nak["pada"],
                "nakshatra_lord": nak["lord"],
                "retrograde": False,  # TODO: detect from velocity when available
            })
        return out

    # ── Houses ──

    def houses(self):
        """Equal house cusps (sidereal).

        Returns:
            list of 12 dicts with house number and cusp position.
        """
        r = self._compute()
        cusps = equal_house_cusps(r.ascendant)
        return [
            {
                "house": i + 1,
                "cusp": _lon_to_dms(cusps[i]),
                "sign": SIGN_NAMES[int(cusps[i] / 30.0) % 12],
            }
            for i in range(12)
        ]

    # ── Ascendant ──

    def ascendant(self):
        """Sidereal ascendant (Lagna)."""
        r = self._compute()
        return _lon_to_dms(r.ascendant)

    # ── Nakshatras for all planets ──

    def nakshatras(self):
        """Nakshatra placement for each planet.

        Returns:
            list of dicts with planet name, nakshatra, pada, lord.
        """
        r = self._compute()
        out = []
        for pid in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            p = r.planets[pid]
            nak = calc_nakshatra(p.sidereal_lon)
            out.append({
                "planet": p.name,
                "nakshatra": nak["name"],
                "pada": nak["pada"],
                "lord": nak["lord"],
                "degree_in_nakshatra": round(nak["degree_in_nakshatra"], 4),
            })
        return out

    # ── Dasha ──

    def dasha(self, max_level=2):
        """Vimshottari dasha timeline.

        Args:
            max_level: 1=Maha only, 2=+Antar(default), 3=+Pratyantar

        Returns:
            dict with nakshatra info and mahadasha periods with dates.
        """
        if self._dasha_cache is not None and self._dasha_cache[0] == max_level:
            return self._dasha_cache[1]

        r = self._compute()
        moon_sid = r.planets[2].sidereal_lon
        timeline = build_vimshottari_timeline(moon_sid, self._jd_local, max_level)

        # Convert JDs to readable dates
        result = {
            "moon_nakshatra": timeline["nakshatra_name"],
            "starting_dasha": timeline["initial_lord_name"],
            "balance_at_birth": round(
                (1.0 - timeline["fraction_elapsed"]) * timeline["mahadashas"][0]["years"],
                2
            ),
            "periods": [],
        }

        for maha in timeline["mahadashas"]:
            period = {
                "planet": maha["planet_name"],
                "years": maha["years"],
                "start": _jd_to_iso(maha["start_jd"]),
                "end": _jd_to_iso(maha["end_jd"]),
            }
            if "antardashas" in maha:
                period["sub_periods"] = [
                    {
                        "planet": ad["planet_name"],
                        "start": _jd_to_iso(ad["start_jd"]),
                        "end": _jd_to_iso(ad["end_jd"]),
                    }
                    for ad in maha["antardashas"]
                ]
            result["periods"].append(period)

        self._dasha_cache = (max_level, result)
        return result

    # ── Yogas ──

    def yogas(self):
        """Detected yogas in the chart.

        Returns:
            list of yoga description strings.
        """
        if self._yoga_cache is not None:
            return self._yoga_cache

        r = self._compute()
        self._yoga_cache = detect_yogas(r)
        return self._yoga_cache

    # ── Vargas (divisional charts) ──

    def varga(self, division=9):
        """Compute a divisional chart.

        Args:
            division: Varga number (1,2,3,4,7,9,10,12,16,20,27,40,45,60)

        Returns:
            list of dicts with planet name and varga position.
        """
        r = self._compute()
        out = []
        for pid in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            p = r.planets[pid]
            varga_lon = calc_varga(p.sidereal_lon, division)
            out.append({
                "planet": p.name,
                "position": _lon_to_dms(varga_lon),
            })
        return out

    # ── Panchanga ──

    def panchanga(self):
        """Panchanga elements for the chart moment.

        Returns:
            dict with tithi, nakshatra (Moon), yoga, karana, vara (weekday).
        """
        r = self._compute()
        sun_sid = r.planets[1].sidereal_lon
        moon_sid = r.planets[2].sidereal_lon

        # Tithi: based on Moon-Sun elongation
        elongation = normalize_degrees(moon_sid - sun_sid)
        tithi_index = int(elongation / 12.0)
        tithi_names = [
            "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
            "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
            "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya",
        ]
        paksha = "Shukla" if tithi_index < 15 else "Krishna"
        tithi_in_paksha = (tithi_index % 15) + 1

        # Yoga
        yoga = calc_panchanga_yoga(sun_sid, moon_sid)

        # Nakshatra (Moon)
        moon_nak = calc_nakshatra(moon_sid)

        # Karana (half-tithi)
        karana_index = int(elongation / 6.0) % 60

        # Vara (weekday from JD)
        vara_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                      "Friday", "Saturday", "Sunday"]
        vara_index = int(self._result.jd_ut + 0.5) % 7
        vara = vara_names[vara_index]

        return {
            "tithi": {
                "index": tithi_index + 1,
                "paksha": paksha,
                "tithi_in_paksha": tithi_in_paksha,
                "name": tithi_names[tithi_index % 15],
            },
            "nakshatra": {
                "name": moon_nak["name"],
                "pada": moon_nak["pada"],
                "lord": moon_nak["lord"],
            },
            "yoga": {
                "name": yoga["name"],
                "index": yoga["index"] + 1,
            },
            "karana_index": karana_index + 1,
            "vara": vara,
        }

    # ── Summary / metadata ──

    def summary(self):
        """Chart metadata and key indicators."""
        r = self._compute()
        moon_nak = calc_nakshatra(r.planets[2].sidereal_lon)
        return {
            "date": f"{self._year:04d}-{self._month:02d}-{self._day:02d}",
            "time": f"{int(self._hour):02d}:{int((self._hour % 1) * 60):02d}",
            "location": {"lat": self._lat, "lon": self._lon, "tz": self._tz},
            "ayanamsha": round(r.ayanamsha, 6),
            "ayanamsha_system": self._ayanamsha_system,
            "ascendant": _lon_to_dms(r.ascendant),
            "moon_nakshatra": moon_nak["name"],
            "moon_pada": moon_nak["pada"],
            "jd_ut": round(r.jd_ut, 8),
            "delta_t": round(r.delta_t, 2),
        }

    # ── Full structured output ──

    def to_dict(self):
        """Complete chart data as a dictionary (for JSON serialization).

        This is the primary output format for LLM consumption.
        """
        return {
            "chart": self.summary(),
            "planets": self.planets(),
            "houses": self.houses(),
            "nakshatras": self.nakshatras(),
            "panchanga": self.panchanga(),
            "dasha": self.dasha(),
            "yogas": self.yogas(),
        }

    def to_json(self, indent=2):
        """Complete chart data as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def __repr__(self):
        r = self._compute()
        asc = _lon_to_dms(r.ascendant)
        return (f"<Chart {self._year:04d}-{self._month:02d}-{self._day:02d} "
                f"{int(self._hour):02d}:{int((self._hour % 1) * 60):02d} "
                f"Asc={asc['sign']} {asc['degrees']}°{asc['minutes']}'>")
