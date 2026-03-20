"""Corrections: Delta-T, light-time, aberration, nutation, obliquity.

Reconstructed from PL7.exe:
  FUN_0055d4e0 — Delta-T interpolation from DELTAT.ASC
  FUN_0055d7a4 — Aberration correction
  FUN_00405c56 — Nutation (omega polynomial)
  FUN_00406a09 — Nutation in longitude/obliquity (IAU 1980)
  06_EPHEMERIS_PIPELINE.md — Light-time correction
"""
import math
from ..astro.julian import DEG2RAD

# Light-time constant: converts distance to light-travel-time in Julian Centuries
# Used as: corrected_jd = jd - distance * LIGHT_TIME_CONSTANT
LIGHT_TIME_CONSTANT = 1.0570008340246156e-15

# Delta-T conversions
SECONDS_TO_DAYS = 1.1574074074074073e-05  # 1/86400
SECONDS_TO_CENTURIES = 3.1688087814028947e-10  # 1/(86400*36525)


# IERS/USNO observed Delta-T (TT-UT1) in seconds, January values
# Source: https://maia.usno.navy.mil/ser7/deltat.data
_IERS_DELTAT = [
    (1993.0, 59.12), (1994.0, 59.98), (1995.0, 60.79), (1996.0, 61.63),
    (1997.0, 62.30), (1998.0, 62.97), (1999.0, 63.47), (2000.0, 63.83),
    (2001.0, 64.09), (2002.0, 64.30), (2003.0, 64.47), (2004.0, 64.57),
    (2005.0, 64.69), (2006.0, 64.85), (2007.0, 65.15), (2008.0, 65.46),
    (2009.0, 65.78), (2010.0, 66.07), (2011.0, 66.32), (2012.0, 66.60),
    (2013.0, 66.91), (2014.0, 67.28), (2015.0, 67.64), (2016.0, 68.10),
    (2017.0, 68.59), (2018.0, 68.97), (2019.0, 69.22), (2020.0, 69.36),
    (2021.0, 69.36), (2022.0, 69.29), (2023.0, 69.20), (2024.0, 69.18),
    (2025.0, 69.14), (2026.0, 69.11),
]

# Bias correction: polynomial(2026) = 75.07s but IERS(2026) = 69.11s
# Shift polynomial down by the difference so it's continuous at the boundary
_POLY_BIAS = _IERS_DELTAT[-1][1] - (62.92 + 0.32217 * 26.0 + 0.005589 * 26.0**2)


class DeltaTTable:
    """Delta-T interpolation from DELTAT.ASC (FUN_0055d4e0).

    DELTAT.ASC contains pairs of (year, delta_t_seconds) covering 1800-2000+.
    Linear interpolation between entries.
    """

    def __init__(self, deltat_path):
        self.years = []
        self.values = []
        with open(deltat_path, 'r', errors='replace') as f:
            for line in f:
                # Strip whitespace and control characters
                line = line.strip().rstrip('\x1a')
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        self.years.append(float(parts[0]))
                        self.values.append(float(parts[-1].rstrip('\x1a')))
                    except ValueError:
                        continue

    def interpolate(self, T):
        """Interpolate Delta-T in seconds for Julian Century T.

        Args:
            T: Julian Century from J2000

        Returns:
            Delta-T in seconds (TT - UT)
        """
        # Convert T to decimal year
        year = 2000.0 + T * 100.0

        if year <= self.years[0]:
            # Pre-table: Stephenson & Morrison parabolic approximation
            u = (year - 1820.0) / 100.0
            return -20 + 32 * u * u

        if year >= self.years[-1]:
            return self._extrapolate_post_table(year)

        # Binary search for bracketing interval
        lo, hi = 0, len(self.years) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.years[mid] <= year:
                lo = mid
            else:
                hi = mid

        # Linear interpolation
        frac = (year - self.years[lo]) / (self.years[hi] - self.years[lo])
        return self.values[lo] + frac * (self.values[hi] - self.values[lo])

    def _extrapolate_post_table(self, year):
        """Post-table Delta-T: IERS observed values + polynomial fallback.

        1993-2026: Linear interpolation of IERS/USNO observed data (<0.5s accuracy)
        2026+: Espenak & Meeus polynomial (grows less accurate over time)

        Source: https://maia.usno.navy.mil/ser7/deltat.data
        """
        table = _IERS_DELTAT

        # Within IERS observed range: linear interpolation
        if year <= table[-1][0]:
            # Find bracketing entries
            for i in range(len(table) - 1):
                if table[i][0] <= year < table[i + 1][0]:
                    frac = (year - table[i][0]) / (table[i + 1][0] - table[i][0])
                    return table[i][1] + frac * (table[i + 1][1] - table[i][1])
            return table[-1][1]

        # Beyond IERS range: bias-corrected polynomial extrapolation
        # Shift polynomial to match IERS endpoint, eliminating discontinuity
        if year < 2050:
            t = year - 2000.0
            return 62.92 + 0.32217 * t + 0.005589 * t**2 + _POLY_BIAS
        else:
            # Stephenson & Morrison long-range parabolic
            u = (year - 1820.0) / 100.0
            return -20 + 32 * u * u


def mean_obliquity(T):
    """Mean obliquity of the ecliptic (Algorithm 5).

    Simplified IAU formula: epsilon = 23.439291 - 0.013004 * T
    """
    return 23.439291 - 0.013004 * T


def nutation_omega(T):
    """Mean longitude of Moon's ascending node (Algorithm 3).

    Full polynomial from FUN_00405c56.
    """
    T2 = T * T
    T3 = T2 * T
    T4 = T3 * T
    return (125.044555
            - 1934.1361849 * T
            + 0.0020762 * T2
            + 2.1394493e-06 * T3
            - 1.6497294e-08 * T4)


def calc_nutation(T):
    """Calculate nutation in longitude and obliquity (IAU 1980, 13 terms).

    Uses the 13 largest terms from the IAU 1980 nutation series
    (Seidelmann 1982). Accuracy: <0.05" in delta_psi, <0.02" in delta_eps.

    Fundamental arguments from Meeus, Astronomical Algorithms, Ch. 22.

    Returns:
        (delta_psi, delta_epsilon) in degrees
        delta_psi = nutation in longitude
        delta_epsilon = nutation in obliquity
    """
    T2 = T * T
    T3 = T2 * T

    # Fundamental arguments (degrees)
    # D = Mean elongation of the Moon
    D = 297.85036 + 445267.111480 * T - 0.0019142 * T2 + T3 / 189474.0
    # M = Sun's mean anomaly
    M = 357.52772 + 35999.050340 * T - 0.0001603 * T2 - T3 / 300000.0
    # Mp = Moon's mean anomaly
    Mp = 134.96298 + 477198.867398 * T + 0.0086972 * T2 + T3 / 56250.0
    # F = Moon's argument of latitude
    F = 93.27191 + 483202.017538 * T - 0.0036825 * T2 + T3 / 327270.0
    # Omega = Longitude of Moon's ascending node
    Om = nutation_omega(T)

    # Convert to radians
    D = D * DEG2RAD
    M = M * DEG2RAD
    Mp = Mp * DEG2RAD
    F = F * DEG2RAD
    Om = Om * DEG2RAD

    # IAU 1980 nutation series — 13 largest terms
    # Each row: (D_mult, M_mult, Mp_mult, F_mult, Om_mult,
    #            psi_sin, psi_sin_T, eps_cos, eps_cos_T) in 0.0001"
    _NUTATION_TABLE = [
        ( 0,  0,  0,  0,  1, -171996, -1742, 92025,  89),
        (-2,  0,  0,  2,  2,  -13187,   -16,  5736, -31),
        ( 0,  0,  0,  2,  2,   -2274,    -2,   977,  -5),
        ( 0,  0,  0,  0,  2,    2062,     2,  -895,   5),
        ( 0,  1,  0,  0,  0,    1426,   -34,    54,  -1),
        ( 0,  0,  1,  0,  0,     712,     1,    -7,   0),
        (-2,  1,  0,  2,  2,    -517,    12,   224,  -6),
        ( 0,  0,  0,  2,  1,    -386,    -4,   200,   0),
        ( 0,  0,  1,  2,  2,    -301,     0,   129,  -1),
        (-2, -1,  0,  2,  2,     217,    -5,   -95,   3),
        (-2,  0,  1,  0,  0,    -158,     0,     0,   0),
        (-2,  0,  0,  2,  1,     129,     1,   -70,   0),
        ( 0,  0, -1,  2,  2,     123,     0,   -53,   0),
    ]

    delta_psi = 0.0
    delta_eps = 0.0
    for row in _NUTATION_TABLE:
        arg = row[0] * D + row[1] * M + row[2] * Mp + row[3] * F + row[4] * Om
        sin_arg = math.sin(arg)
        cos_arg = math.cos(arg)
        delta_psi += (row[5] + row[6] * T) * sin_arg
        delta_eps += (row[7] + row[8] * T) * cos_arg

    # Convert from 0.0001 arcseconds to degrees
    delta_psi = delta_psi * 1e-4 / 3600.0
    delta_eps = delta_eps * 1e-4 / 3600.0

    return delta_psi, delta_eps


def true_obliquity(T):
    """True obliquity = mean obliquity + nutation in obliquity."""
    _, delta_eps = calc_nutation(T)
    return mean_obliquity(T) + delta_eps


def apply_aberration(pos, vel, dist):
    """Apply relativistic aberration correction to rectangular coordinates.

    From FUN_0055d7a4 / 06_EPHEMERIS_PIPELINE.md lines 241-251.

    Modifies pos in-place:
        dot = pos·vel
        pos[i] *= (1.0 - dot * LIGHT_TIME_CONSTANT / dist)

    Args:
        pos: [x, y, z] rectangular position (modified in-place)
        vel: [vx, vy, vz] velocity
        dist: distance scalar
    """
    if dist < 1e-30:
        return
    dot = pos[0] * vel[0] + pos[1] * vel[1] + pos[2] * vel[2]
    factor = 1.0 - dot * LIGHT_TIME_CONSTANT / dist
    pos[0] *= factor
    pos[1] *= factor
    pos[2] *= factor


def light_time_correction(jd_T, distance):
    """Compute light-time corrected Julian Century.

    Args:
        jd_T: Julian Century (not JD!) — will be corrected
        distance: geocentric distance in internal units

    Returns:
        Corrected Julian Century
    """
    return jd_T - distance * LIGHT_TIME_CONSTANT
