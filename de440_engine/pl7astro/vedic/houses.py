"""Sidereal time, RAMC, ascendant, and house cusps.

Reconstructed from:
  FUN_00406a09 — Sidereal time / RAMC / house cusps (Algorithm 9)
  FUN_004060a5 — Ascendant calculation (Algorithm 10)
"""
import math
from ..astro.julian import J2000, DEG2RAD, RAD2DEG, normalize_degrees, julian_century
from ..astro.corrections import calc_nutation, mean_obliquity


def calc_sidereal_time(jd_ut, longitude, T_ut=None):
    """Calculate Local Apparent Sidereal Time in degrees.

    Args:
        jd_ut: Julian Day in UT
        longitude: Geographic longitude (west positive, as PL7 stores)
        T_ut: Julian centuries UT (computed if not given)

    Returns:
        Local Apparent Sidereal Time in degrees [0, 360)
    """
    if T_ut is None:
        T_ut = julian_century(jd_ut)

    D = jd_ut - J2000

    # GMST (IAU 1982, Meeus Ch.12) in degrees
    gmst = (280.46061837
            + 360.98564736629 * D
            + 0.000387933 * T_ut * T_ut
            - T_ut ** 3 / 38710000.0)

    # Nutation correction
    delta_psi, delta_eps = calc_nutation(T_ut)
    eps = mean_obliquity(T_ut) + delta_eps

    # Apparent sidereal time
    gast = gmst + delta_psi * math.cos(eps * DEG2RAD)

    # Local sidereal time (west longitude positive)
    lst = gast - longitude

    return normalize_degrees(lst)


def calc_ascendant(ramc_deg, obliquity_deg, latitude_deg):
    """Calculate Ascendant (Lagna) in degrees (Algorithm 10).

    Standard formula:
    Asc = atan2(cos(RAMC), -(sin(ε)*tan(φ) + cos(ε)*sin(RAMC)))
    """
    ramc = ramc_deg * DEG2RAD
    eps = obliquity_deg * DEG2RAD
    phi = latitude_deg * DEG2RAD

    y = math.cos(ramc)
    x = -(math.sin(eps) * math.tan(phi) + math.cos(eps) * math.sin(ramc))

    asc = math.atan2(y, x) * RAD2DEG
    return normalize_degrees(asc)


def equal_house_cusps(ascendant_deg, num_houses=12):
    """Compute Equal House system cusps.

    In Vedic astrology, each house = Ascendant + (n-1) * 30°.

    Returns:
        List of 12 house cusp longitudes (sidereal degrees)
    """
    return [normalize_degrees(ascendant_deg + i * 30.0) for i in range(num_houses)]
