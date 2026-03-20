"""Full planetary position pipeline matching FUN_0055ec16.

Orchestrates: JD conversion → Delta-T → Chebyshev interpolation →
helio-to-geo → light-time → aberration → ecliptic coordinates →
nutation → sidereal time → ayanamsha → sidereal positions.
"""
import math
from ..astro.julian import (
    J2000, JULIAN_CENTURY, DEG2RAD, RAD2DEG,
    julian_century, normalize_degrees,
)
from ..astro.ephemeris import EphemerisReader
from ..astro.coordinates import spherical_to_rect, rect_to_spherical, helio_to_geo_rect
from ..astro.corrections import (
    DeltaTTable, LIGHT_TIME_CONSTANT, SECONDS_TO_DAYS,
    calc_nutation, mean_obliquity, apply_aberration,
)

# Planet names for output
PLANET_NAMES = {
    1: "Sun", 2: "Moon", 3: "Mars", 4: "Mercury",
    5: "Jupiter", 6: "Venus", 7: "Saturn",
    8: "Rahu", 9: "Ketu",
}

# Vedic body order mapping: Vedic ID → ephemeris body ID
# PL7 uses: 1=Sun/Earth, 2=Moon, 3=Mars, 4=Mercury, 5=Jupiter, 6=Venus, 7=Saturn, 8=Rahu
VEDIC_PLANETS = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # includes Ketu
STANDARD_PLANETS = [3, 4, 5, 6, 7]  # planets needing full correction pipeline


class PlanetPosition:
    """Result for one planet."""
    __slots__ = ['tropical_lon', 'tropical_lat', 'distance',
                 'sidereal_lon', 'name']

    def __init__(self, name=""):
        self.tropical_lon = 0.0
        self.tropical_lat = 0.0
        self.distance = 0.0
        self.sidereal_lon = 0.0
        self.name = name

    def __repr__(self):
        return (f"<{self.name}: trop={self.tropical_lon:.4f}° "
                f"sid={self.sidereal_lon:.4f}°>")


class ChartResult:
    """Full chart calculation result."""

    def __init__(self):
        self.planets = {}  # planet_id -> PlanetPosition
        self.ayanamsha = 0.0
        self.sidereal_time = 0.0
        self.ascendant = 0.0  # sidereal ascendant
        self.jd_ut = 0.0
        self.jd_tt = 0.0
        self.T = 0.0
        self.delta_t = 0.0
        self.delta_psi = 0.0
        self.true_obliquity = 0.0


class Pipeline:
    """Full PL7 planetary calculation pipeline.

    Matches the correction order from FUN_0055ec16:
    1. local JD → UT (subtract timezone)
    2. UT → TT (add Delta-T)
    3. T = (TT - J2000) / 36525
    4. Compute ayanamsha
    5. Earth heliocentric (Chebyshev + velocity)
    6. Sun: light-time → re-interpolate → geocentric
    7. Standard planets: Chebyshev → aberration → helio-to-geo →
       distance → light-time → re-interpolate → aberration → ecliptic
    8. Moon: interpolate at light-time corrected JD
    9. Rahu: interpolate, no corrections; Ketu = Rahu + 180
    10. Nutation → sidereal time + ascendant
    11. Subtract ayanamsha → sidereal positions
    """

    def __init__(self, ephemeris, delta_t_table=None, ayanamsha_func=None):
        """
        Args:
            ephemeris: EphemerisReader or JPLEphemerisReader instance
            delta_t_table: DeltaTTable instance (optional, enables Delta-T correction)
            ayanamsha_func: callable(jd) -> ayanamsha_degrees (defaults to Lahiri)
        """
        self.eph = ephemeris
        self.delta_t = delta_t_table
        self.ayanamsha_func = ayanamsha_func
        self._use_jpl = hasattr(ephemeris, 'geocentric_ecliptic')

    def calc_all(self, jd_local, timezone=0.0, latitude=0.0, longitude=0.0,
                 ayanamsha_system=1):
        """Calculate all planet positions for a given moment.

        Args:
            jd_local: Julian Day in LOCAL time (as PL7 stores it)
            timezone: Hours west of Greenwich (positive = west, e.g. CST = 6.0)
            latitude: Geographic latitude in degrees (north positive)
            longitude: Geographic longitude in degrees (west positive, as PL7 stores)
            ayanamsha_system: 1=Lahiri, 2=None, 3=Raman, etc.

        Returns:
            ChartResult with all computed positions
        """
        result = ChartResult()

        # Step 1: Local → UT
        # PL7 stores timezone as hours BEHIND UT (e.g. CST=6.0 means UTC-6)
        # So UT = local + timezone (CST 8:51 AM + 6h = 14:51 UT)
        jd_ut = jd_local + timezone / 24.0
        result.jd_ut = jd_ut

        # Step 2: UT → TT (Terrestrial Time) via Delta-T
        T_ut = julian_century(jd_ut)
        if self.delta_t:
            delta_t_sec = self.delta_t.interpolate(T_ut)
            result.delta_t = delta_t_sec
            jd_tt = jd_ut + delta_t_sec * SECONDS_TO_DAYS
        else:
            jd_tt = jd_ut
            result.delta_t = 0.0
        result.jd_tt = jd_tt

        # Step 3: Julian Century from TT
        T = julian_century(jd_tt)
        result.T = T

        # Step 4: Ayanamsha
        from ..vedic.ayanamsha import calc_ayanamsha
        if self.ayanamsha_func:
            ayanamsha = self.ayanamsha_func(jd_tt)
        else:
            ayanamsha = calc_ayanamsha(jd_tt, ayanamsha_system)
        result.ayanamsha = ayanamsha

        if self._use_jpl:
            # JPL DE440 path: direct geocentric ecliptic, no helio->geo needed
            self._calc_all_jpl(T, ayanamsha, result)
        else:
            # Legacy PL7 Chebyshev path
            self._calc_all_legacy(T, ayanamsha, result)

        # Step 10: Nutation → sidereal time → ascendant
        delta_psi, delta_eps = calc_nutation(T)
        result.delta_psi = delta_psi
        eps = mean_obliquity(T) + delta_eps
        result.true_obliquity = eps

        # Sidereal time
        D = jd_ut - J2000  # Use UT for sidereal time
        T_ut_for_gst = T_ut  # Julian centuries UT
        gmst = (280.46061837
                + 360.98564736629 * D
                + 0.000387933 * T_ut_for_gst * T_ut_for_gst
                - T_ut_for_gst ** 3 / 38710000.0)

        # Apparent sidereal time = GMST + nutation in longitude * cos(obliquity)
        gast = gmst + delta_psi * math.cos(eps * DEG2RAD)

        # Local sidereal time (west longitude positive in PL7)
        lst = gast - longitude
        result.sidereal_time = normalize_degrees(lst)

        # Step 11: Ascendant
        ramc = result.sidereal_time
        asc_tropical = self._calc_ascendant(ramc, eps, latitude)
        result.ascendant = normalize_degrees(asc_tropical - ayanamsha)

        return result

    def _calc_all_jpl(self, T, ayanamsha, result):
        """Compute all planets using JPL DE440 direct geocentric path."""
        # Sun
        sun = PlanetPosition("Sun")
        lon, lat, dist = self.eph.geocentric_ecliptic(1, T)
        sun.tropical_lon = lon
        sun.tropical_lat = lat
        sun.distance = dist
        sun.sidereal_lon = normalize_degrees(lon - ayanamsha)
        result.planets[1] = sun

        # Standard planets
        for body_id in STANDARD_PLANETS:
            name = PLANET_NAMES.get(body_id, f"Body{body_id}")
            planet = PlanetPosition(name)
            lon, lat, dist = self.eph.geocentric_ecliptic(body_id, T)
            planet.tropical_lon = lon
            planet.tropical_lat = lat
            planet.distance = dist
            planet.sidereal_lon = normalize_degrees(lon - ayanamsha)
            result.planets[body_id] = planet

        # Moon
        moon = PlanetPosition("Moon")
        lon, lat, dist = self.eph.geocentric_ecliptic(2, T)
        moon.tropical_lon = lon
        moon.tropical_lat = lat
        moon.distance = dist
        moon.sidereal_lon = normalize_degrees(lon - ayanamsha)
        result.planets[2] = moon

        # Rahu & Ketu
        rahu = PlanetPosition("Rahu")
        rahu_lon = normalize_degrees(self.eph.rahu_longitude(T))
        rahu.tropical_lon = rahu_lon
        rahu.tropical_lat = 0.0
        rahu.distance = 0.0
        rahu.sidereal_lon = normalize_degrees(rahu_lon - ayanamsha)
        result.planets[8] = rahu

        ketu = PlanetPosition("Ketu")
        ketu.tropical_lon = normalize_degrees(rahu.tropical_lon + 180.0)
        ketu.tropical_lat = 0.0
        ketu.sidereal_lon = normalize_degrees(rahu.sidereal_lon + 180.0)
        result.planets[9] = ketu

    def _calc_all_legacy(self, T, ayanamsha, result):
        """Compute all planets using legacy PL7 Chebyshev ephemeris."""
        # Step 5: Earth heliocentric position + velocity
        earth_pos, earth_vel = self.eph.helio_position_with_velocity(1, T)
        earth_lon, earth_lat, earth_dist = earth_pos[0], earth_pos[1], earth_pos[2]
        earth_rect = spherical_to_rect(earth_lon, earth_lat, earth_dist)

        # Compute Earth velocity in rectangular coords (for aberration)
        earth_vel_rect = self._spherical_vel_to_rect(
            earth_lon, earth_lat, earth_dist, earth_vel
        )

        # Step 6: SUN (= Earth + 180, with light-time correction)
        sun = PlanetPosition("Sun")
        sun_dist = earth_dist
        lt_T = T - sun_dist * LIGHT_TIME_CONSTANT
        earth_lt_pos = self.eph.helio_position(1, lt_T)
        earth_lt_lon = earth_lt_pos[0]
        sun.tropical_lon = normalize_degrees(earth_lt_lon + 180.0)
        sun.tropical_lat = -earth_lt_pos[1]
        sun.distance = sun_dist
        sun.sidereal_lon = normalize_degrees(sun.tropical_lon - ayanamsha)
        result.planets[1] = sun

        # Step 7: Standard planets
        for body_id in STANDARD_PLANETS:
            planet = self._calc_standard_planet(
                body_id, T, earth_rect, earth_vel_rect, ayanamsha
            )
            result.planets[body_id] = planet

        # Step 8: Moon
        moon = self._calc_moon(T, earth_dist, ayanamsha)
        result.planets[2] = moon

        # Step 9: Rahu & Ketu
        rahu = self._calc_rahu(T, ayanamsha)
        result.planets[8] = rahu

        ketu = PlanetPosition("Ketu")
        ketu.tropical_lon = normalize_degrees(rahu.tropical_lon + 180.0)
        ketu.tropical_lat = -rahu.tropical_lat
        ketu.sidereal_lon = normalize_degrees(rahu.sidereal_lon + 180.0)
        result.planets[9] = ketu

    def _calc_standard_planet(self, body_id, T, earth_rect, earth_vel_rect, ayanamsha):
        """Calculate a standard planet with full correction pipeline.

        Follows PL7's FUN_0055ec16 correction order:
        1. Heliocentric position via Chebyshev
        2. Aberration on heliocentric coords
        3. Helio → Geo conversion
        4. Compute geocentric distance
        5. Light-time correction (re-interpolate)
        6. Second light-time iteration (re-compute distance, re-interpolate)
        7. Aberration on corrected coords
        8. Final geo conversion → ecliptic coordinates
        """
        name = PLANET_NAMES.get(body_id, f"Body{body_id}")
        planet = PlanetPosition(name)

        # --- Pass 1: Initial heliocentric + aberration ---
        helio_pos, helio_vel = self.eph.helio_position_with_velocity(body_id, T)
        h_lon, h_lat, h_dist = helio_pos
        h_rect = list(spherical_to_rect(h_lon, h_lat, h_dist))
        h_vel_rect = self._spherical_vel_to_rect(h_lon, h_lat, h_dist, helio_vel)

        h_dist_rect = math.sqrt(h_rect[0]**2 + h_rect[1]**2 + h_rect[2]**2)
        apply_aberration(h_rect, h_vel_rect, h_dist_rect)

        # Helio → Geo
        geo_rect = list(helio_to_geo_rect(h_rect, earth_rect))
        geo_dist = math.sqrt(geo_rect[0]**2 + geo_rect[1]**2 + geo_rect[2]**2)

        # --- Pass 2: First light-time iteration ---
        lt_T = T - geo_dist * LIGHT_TIME_CONSTANT
        lt_pos, lt_vel = self.eph.helio_position_with_velocity(body_id, lt_T)
        lt_lon, lt_lat, lt_dist = lt_pos
        lt_rect = list(spherical_to_rect(lt_lon, lt_lat, lt_dist))

        # Recompute geocentric distance from light-time corrected position
        geo_rect2 = list(helio_to_geo_rect(lt_rect, earth_rect))
        geo_dist2 = math.sqrt(geo_rect2[0]**2 + geo_rect2[1]**2 + geo_rect2[2]**2)

        # --- Pass 3: Second light-time iteration ---
        lt_T2 = T - geo_dist2 * LIGHT_TIME_CONSTANT
        lt_pos2, lt_vel2 = self.eph.helio_position_with_velocity(body_id, lt_T2)
        lt_lon2, lt_lat2, lt_dist2 = lt_pos2
        lt_rect2 = list(spherical_to_rect(lt_lon2, lt_lat2, lt_dist2))
        lt_vel_rect2 = self._spherical_vel_to_rect(lt_lon2, lt_lat2, lt_dist2, lt_vel2)

        # Aberration on final light-time corrected position
        lt_d2 = math.sqrt(lt_rect2[0]**2 + lt_rect2[1]**2 + lt_rect2[2]**2)
        apply_aberration(lt_rect2, lt_vel_rect2, lt_d2)

        # Final geocentric from light-time corrected heliocentric
        geo_rect = list(helio_to_geo_rect(lt_rect2, earth_rect))

        # Convert to ecliptic longitude/latitude
        geo_lon, geo_lat, geo_d = rect_to_spherical(geo_rect[0], geo_rect[1], geo_rect[2])

        planet.tropical_lon = normalize_degrees(geo_lon)
        planet.tropical_lat = geo_lat
        planet.distance = geo_d
        planet.sidereal_lon = normalize_degrees(geo_lon - ayanamsha)

        return planet

    def _calc_moon(self, T, earth_dist, ayanamsha):
        """Calculate Moon position.

        Moon light travel time is ~1.3 seconds (negligible), so no light-time
        correction is applied. The pipeline doc's use of earth_dist for Moon
        light-time was a misinterpretation — verified by testing: no LT gives
        0.7" error vs 295" with Earth-Sun distance LT.
        """
        moon = PlanetPosition("Moon")

        # Moon longitude: mean orbit (FUN_0055f843) + Chebyshev residual
        moon_mean = self.eph.moon_longitude(T)
        moon_cheb = self.eph.interpolate(2, T)
        moon_lon = normalize_degrees(moon_mean + moon_cheb[0])

        moon.tropical_lon = moon_lon
        moon.tropical_lat = 0.0  # Moon body only returns 1 dimension (lon)
        moon.distance = 385000.529  # Mean Moon distance in km (from FUN_0055f843 dim=2)
        moon.sidereal_lon = normalize_degrees(moon_lon - ayanamsha)

        return moon

    def _calc_rahu(self, T, ayanamsha):
        """Calculate Rahu (True Lunar Node) — no corrections applied."""
        rahu = PlanetPosition("Rahu")

        rahu_mean = self.eph.rahu_longitude(T)
        rahu_cheb = self.eph.interpolate(8, T)
        rahu_lon = normalize_degrees(rahu_mean + rahu_cheb[0])

        rahu.tropical_lon = rahu_lon
        rahu.tropical_lat = 0.0
        rahu.distance = 0.0
        rahu.sidereal_lon = normalize_degrees(rahu_lon - ayanamsha)

        return rahu

    def _calc_ascendant(self, ramc_deg, obliquity_deg, latitude_deg):
        """Calculate Ascendant (Algorithm 10).

        Asc = atan2(cos(RAMC), -(sin(ε)*tan(φ) + cos(ε)*sin(RAMC)))
        """
        ramc = ramc_deg * DEG2RAD
        eps = obliquity_deg * DEG2RAD
        phi = latitude_deg * DEG2RAD

        y = math.cos(ramc)
        x = -(math.sin(eps) * math.tan(phi) + math.cos(eps) * math.sin(ramc))

        asc = math.atan2(y, x) * RAD2DEG
        return normalize_degrees(asc)

    def _spherical_vel_to_rect(self, lon_deg, lat_deg, dist, vel_sph):
        """Convert spherical velocity to rectangular velocity.

        This is an approximation using the Jacobian of the spherical→rect transform.
        vel_sph = [d_lon/dT (deg/century), d_lat/dT, d_dist/dT]
        """
        lon = lon_deg * DEG2RAD
        lat = lat_deg * DEG2RAD
        dlon = vel_sph[0] * DEG2RAD  # rad/century
        dlat = vel_sph[1] * DEG2RAD
        ddist = vel_sph[2]

        cos_lon = math.cos(lon)
        sin_lon = math.sin(lon)
        cos_lat = math.cos(lat)
        sin_lat = math.sin(lat)

        # dx/dt = ∂x/∂lon * dlon + ∂x/∂lat * dlat + ∂x/∂r * dr
        vx = (-sin_lon * cos_lat * dist * dlon
              - cos_lon * sin_lat * dist * dlat
              + cos_lon * cos_lat * ddist)
        vy = (cos_lon * cos_lat * dist * dlon
              - sin_lon * sin_lat * dist * dlat
              + sin_lon * cos_lat * ddist)
        vz = (cos_lat * dist * dlat
              + sin_lat * ddist)

        return [vx, vy, vz]
