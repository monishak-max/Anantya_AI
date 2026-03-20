"""JPL DE440 ephemeris reader for high-accuracy geocentric ecliptic positions.

Replaces the PL7 Chebyshev ephemeris (ephemdat.bin) with JPL DE440:
- Range: 1550-2650 AD (vs 1801-2049)
- Accuracy: < 0.001 deg (vs ~0.16 deg for fast planets)
- Direct geocentric ecliptic-of-date computation from ICRF equatorial

Pipeline: DE440 ICRF → precession → equatorial of date → ecliptic of date (geometric)
"""
import math
from jplephem.spk import SPK
from ..astro.julian import J2000, JULIAN_CENTURY, DEG2RAD, RAD2DEG, normalize_degrees

# km -> AU
KM_PER_AU = 149597870.7

# Arcseconds to radians
ARCSEC2RAD = DEG2RAD / 3600.0

# pl7astro body_id -> SPK target
BODY_TO_SPK = {
    1: 10,   # Sun
    2: 301,  # Moon
    3: 4,    # Mars
    4: 1,    # Mercury
    5: 5,    # Jupiter
    6: 2,    # Venus
    7: 6,    # Saturn
}

# Bodies that need two-step computation (SSB -> EMB -> body)
TWO_STEP_BODIES = {301, 399}


def _precession_angles(T):
    """IAU 1976 precession angles (Lieske 1979) in radians.

    Args:
        T: Julian centuries from J2000

    Returns:
        (zeta_A, z_A, theta_A) in radians
    """
    T2 = T * T
    T3 = T2 * T
    zeta_A = ((2306.2181 + 1.39656 * T - 0.000139 * T2) * T
              + (0.30188 - 0.000344 * T) * T2
              + 0.017998 * T3) * ARCSEC2RAD
    z_A = ((2306.2181 + 1.39656 * T - 0.000139 * T2) * T
           + (1.09468 + 0.000066 * T) * T2
           + 0.018203 * T3) * ARCSEC2RAD
    theta_A = ((2004.3109 - 0.85330 * T - 0.000217 * T2) * T
               - (0.42665 + 0.000217 * T) * T2
               - 0.041833 * T3) * ARCSEC2RAD
    return zeta_A, z_A, theta_A


def _precess_j2000_to_date(x, y, z, T):
    """Precess equatorial coordinates from J2000 (ICRF) to equatorial of date.

    Uses IAU 1976 precession: R = R_z(-z_A) * R_y(theta_A) * R_z(-zeta_A)
    """
    zeta_A, z_A, theta_A = _precession_angles(T)

    cos_zeta = math.cos(zeta_A)
    sin_zeta = math.sin(zeta_A)
    cos_z = math.cos(z_A)
    sin_z = math.sin(z_A)
    cos_theta = math.cos(theta_A)
    sin_theta = math.sin(theta_A)

    # Combined rotation matrix elements
    # R = R_z(-z_A) * R_y(theta_A) * R_z(-zeta_A)
    r11 = cos_z * cos_theta * cos_zeta - sin_z * sin_zeta
    r12 = -cos_z * cos_theta * sin_zeta - sin_z * cos_zeta
    r13 = -cos_z * sin_theta
    r21 = sin_z * cos_theta * cos_zeta + cos_z * sin_zeta
    r22 = -sin_z * cos_theta * sin_zeta + cos_z * cos_zeta
    r23 = -sin_z * sin_theta
    r31 = sin_theta * cos_zeta
    r32 = -sin_theta * sin_zeta
    r33 = cos_theta

    xp = r11 * x + r12 * y + r13 * z
    yp = r21 * x + r22 * y + r23 * z
    zp = r31 * x + r32 * y + r33 * z

    return xp, yp, zp


def _mean_obliquity_date(T):
    """Mean obliquity of the ecliptic at date T (IAU 1980).

    Returns obliquity in radians.
    """
    eps_arcsec = (84381.448
                  - 46.8150 * T
                  - 0.00059 * T * T
                  + 0.001813 * T * T * T)
    return eps_arcsec * ARCSEC2RAD


def _equatorial_to_ecliptic_of_date(x, y, z, T):
    """Rotate equatorial-of-date to ecliptic-of-date using mean obliquity."""
    eps = _mean_obliquity_date(T)
    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)
    x_ecl = x
    y_ecl = y * cos_eps + z * sin_eps
    z_ecl = -y * sin_eps + z * cos_eps
    return x_ecl, y_ecl, z_ecl


# Speed of light in km/day
C_KM_DAY = 299792.458 * 86400.0


class JPLEphemerisReader:
    """JPL DE440 ephemeris reader with the same interface as EphemerisReader.

    Computes apparent geocentric ecliptic-of-date coordinates from DE440 ICRF positions.
    Pipeline: ICRF → light-time → aberration → precession to date → ecliptic of date → spherical.
    """

    def __init__(self, spk_path):
        self.kernel = SPK.open(spk_path)
        self._segments = {}
        for seg in self.kernel.segments:
            self._segments[(seg.center, seg.target)] = seg

    def close(self):
        self.kernel.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _compute_position(self, spk_target, jd):
        """Compute SSB position in km for an SPK target at Julian Day."""
        if spk_target in TWO_STEP_BODIES:
            emb = self._segments[(0, 3)].compute(jd)
            body_from_emb = self._segments[(3, spk_target)].compute(jd)
            return emb + body_from_emb
        else:
            return self._segments[(0, spk_target)].compute(jd)

    def _compute_position_and_velocity(self, spk_target, jd):
        """Compute SSB position (km) and velocity (km/day) for an SPK target."""
        if spk_target in TWO_STEP_BODIES:
            emb_pos, emb_vel = self._segments[(0, 3)].compute_and_differentiate(jd)
            body_pos, body_vel = self._segments[(3, spk_target)].compute_and_differentiate(jd)
            return emb_pos + body_pos, emb_vel + body_vel
        else:
            return self._segments[(0, spk_target)].compute_and_differentiate(jd)

    def _earth_ssb(self, jd):
        """Earth position from SSB in km."""
        return self._compute_position(399, jd)

    def _earth_ssb_with_velocity(self, jd):
        """Earth position and velocity from SSB."""
        return self._compute_position_and_velocity(399, jd)

    def _geo_to_ecliptic_of_date(self, geo_x, geo_y, geo_z, T):
        """Convert geocentric ICRF to ecliptic-of-date spherical coordinates.

        Steps: ICRF → precess to date → ecliptic of date → spherical
        """
        # Precess from J2000 (ICRF) to equatorial of date
        xp, yp, zp = _precess_j2000_to_date(geo_x, geo_y, geo_z, T)

        # Rotate equatorial-of-date to ecliptic-of-date
        x_ecl, y_ecl, z_ecl = _equatorial_to_ecliptic_of_date(xp, yp, zp, T)

        # Spherical coordinates
        dist_km = math.sqrt(geo_x * geo_x + geo_y * geo_y + geo_z * geo_z)
        lon = math.atan2(y_ecl, x_ecl) * RAD2DEG % 360.0
        lat = math.atan2(z_ecl, math.sqrt(x_ecl * x_ecl + y_ecl * y_ecl)) * RAD2DEG
        dist_au = dist_km / KM_PER_AU

        return lon, lat, dist_au

    @staticmethod
    def _apply_aberration(geo_x, geo_y, geo_z, earth_vel):
        """Apply annual aberration to geocentric ICRF position.

        First-order aberration: shifts apparent direction by v_earth/c
        perpendicular to the line of sight.

        Args:
            geo_x, geo_y, geo_z: geocentric ICRF position (km)
            earth_vel: Earth velocity from SSB (km/day), 3-element array

        Returns:
            (geo_x_ab, geo_y_ab, geo_z_ab) aberration-corrected position (km)
        """
        r = math.sqrt(geo_x * geo_x + geo_y * geo_y + geo_z * geo_z)
        if r < 1e-30:
            return geo_x, geo_y, geo_z

        # Unit direction vector
        nx = geo_x / r
        ny = geo_y / r
        nz = geo_z / r

        # Earth velocity / c (dimensionless)
        bx = earth_vel[0] / C_KM_DAY
        by = earth_vel[1] / C_KM_DAY
        bz = earth_vel[2] / C_KM_DAY

        # n dot beta
        n_dot_b = nx * bx + ny * by + nz * bz

        # Aberration correction: delta_n = beta - n*(n.beta)
        # (component of beta perpendicular to line of sight)
        # Applied to position: G' = G + r * (beta - n * n_dot_beta)
        geo_x_ab = geo_x + r * (bx - nx * n_dot_b)
        geo_y_ab = geo_y + r * (by - ny * n_dot_b)
        geo_z_ab = geo_z + r * (bz - nz * n_dot_b)

        return geo_x_ab, geo_y_ab, geo_z_ab

    def geocentric_ecliptic(self, body_id, T):
        """Compute apparent geocentric ecliptic-of-date (lon, lat, dist) for a body.

        Computes apparent position via:
        1. Light-time correction: body at retarded time (t - tau)
        2. Annual aberration: shift due to Earth's orbital velocity

        Args:
            body_id: pl7astro body ID (1=Sun, 2=Moon, 3=Mars, etc.)
            T: Julian Century from J2000

        Returns:
            (lon_deg, lat_deg, dist_AU) in geocentric ecliptic-of-date coordinates
        """
        jd = T * JULIAN_CENTURY + J2000
        earth_pos, earth_vel = self._earth_ssb_with_velocity(jd)

        spk_target = BODY_TO_SPK[body_id]

        # First pass: geometric position to get distance
        planet = self._compute_position(spk_target, jd)
        geo_x = planet[0] - earth_pos[0]
        geo_y = planet[1] - earth_pos[1]
        geo_z = planet[2] - earth_pos[2]
        dist_km = math.sqrt(geo_x**2 + geo_y**2 + geo_z**2)

        # Light-time correction: recompute body at retarded time
        tau_days = dist_km / C_KM_DAY
        jd_ret = jd - tau_days
        planet_ret = self._compute_position(spk_target, jd_ret)

        # Light-time corrected geocentric = body(t-tau) - earth(t)
        geo_x = planet_ret[0] - earth_pos[0]
        geo_y = planet_ret[1] - earth_pos[1]
        geo_z = planet_ret[2] - earth_pos[2]

        # Annual aberration correction
        geo_x, geo_y, geo_z = self._apply_aberration(geo_x, geo_y, geo_z, earth_vel)

        lon, lat, dist = self._geo_to_ecliptic_of_date(geo_x, geo_y, geo_z, T)
        # Return geometric ecliptic longitude (no nutation).
        # Nutation is only used for sidereal time (GAST), not sidereal positions.
        return lon, lat, dist

    def geocentric_ecliptic_with_velocity(self, body_id, T):
        """Compute apparent geocentric ecliptic-of-date position and velocity.

        Uses planetary aberration (light-time corrected body position).

        Returns:
            ((lon, lat, dist), (dlon_deg_per_day, dlat, ddist))
        """
        jd = T * JULIAN_CENTURY + J2000
        earth_pos, earth_vel = self._earth_ssb_with_velocity(jd)

        spk_target = BODY_TO_SPK[body_id]

        # First pass: geometric position to get distance for light-time
        planet_pos0 = self._compute_position(spk_target, jd)
        geo_x0 = planet_pos0[0] - earth_pos[0]
        geo_y0 = planet_pos0[1] - earth_pos[1]
        geo_z0 = planet_pos0[2] - earth_pos[2]
        dist_km = math.sqrt(geo_x0**2 + geo_y0**2 + geo_z0**2)

        # Light-time correction: body at retarded time
        tau_days = dist_km / (299792.458 * 86400.0)
        jd_ret = jd - tau_days
        planet_pos, planet_vel = self._compute_position_and_velocity(spk_target, jd_ret)

        # Light-time corrected geocentric = body(t-tau) - earth(t)
        geo_x = planet_pos[0] - earth_pos[0]
        geo_y = planet_pos[1] - earth_pos[1]
        geo_z = planet_pos[2] - earth_pos[2]

        # Annual aberration correction
        geo_x, geo_y, geo_z = self._apply_aberration(geo_x, geo_y, geo_z, earth_vel)

        geo_vx = planet_vel[0] - earth_vel[0]
        geo_vy = planet_vel[1] - earth_vel[1]
        geo_vz = planet_vel[2] - earth_vel[2]

        lon, lat, dist = self._geo_to_ecliptic_of_date(geo_x, geo_y, geo_z, T)
        # Geometric ecliptic longitude (no nutation for sidereal positions)
        pos = (lon, lat, dist)

        # Precess velocity too
        xp, yp, zp = _precess_j2000_to_date(geo_x, geo_y, geo_z, T)
        vxp, vyp, vzp = _precess_j2000_to_date(geo_vx, geo_vy, geo_vz, T)

        x_ecl, y_ecl, z_ecl = _equatorial_to_ecliptic_of_date(xp, yp, zp, T)
        vx_ecl, vy_ecl, vz_ecl = _equatorial_to_ecliptic_of_date(vxp, vyp, vzp, T)

        r_xy = math.sqrt(x_ecl * x_ecl + y_ecl * y_ecl)
        if r_xy > 1e-30:
            dlon = (x_ecl * vy_ecl - y_ecl * vx_ecl) / (r_xy * r_xy) * RAD2DEG
        else:
            dlon = 0.0

        r = math.sqrt(geo_x * geo_x + geo_y * geo_y + geo_z * geo_z)
        if r > 1e-30 and r_xy > 1e-30:
            dlat = (vz_ecl * r_xy - z_ecl * (x_ecl * vx_ecl + y_ecl * vy_ecl) / r_xy) / (r * r) * RAD2DEG
            ddist = (geo_x * geo_vx + geo_y * geo_vy + geo_z * geo_vz) / (r * KM_PER_AU)
        else:
            dlat = 0.0
            ddist = 0.0

        return pos, (dlon, dlat, ddist)

    # --- EphemerisReader-compatible interface ---

    def helio_position(self, body_id, T):
        """Returns geocentric ecliptic (lon, lat, dist) — named for interface compat."""
        return self.geocentric_ecliptic(body_id, T)

    def helio_position_with_velocity(self, body_id, T):
        """Returns geocentric ecliptic position and velocity — interface compat."""
        pos, vel = self.geocentric_ecliptic_with_velocity(body_id, T)
        return list(pos), list(vel)

    def moon_longitude(self, T):
        """Return 0.0 — Moon position comes entirely from geocentric_ecliptic."""
        return 0.0

    def rahu_longitude(self, T):
        """True lunar node longitude from osculating orbital elements (DE440).

        Uses cross-product method on Moon position/velocity vectors.
        Falls back to Meeus analytical approximation if orbit is degenerate.
        """
        return self.true_node_longitude(T)

    def true_node_longitude(self, T):
        """Osculating true lunar node from Moon's geocentric r x v.

        Computes the longitude of the ascending node of the Moon's
        osculating orbit using the angular momentum vector h = r x v
        in ecliptic-of-date coordinates.

        Uses the same apparent-position pipeline as planets (light-time +
        aberration) for frame consistency across all bodies.

        Returns:
            Ascending node longitude in degrees [0, 360)
        """
        jd = T * JULIAN_CENTURY + J2000
        earth_pos, earth_vel = self._earth_ssb_with_velocity(jd)

        # Moon at retarded time (light-time correction for consistency)
        moon_pos0 = self._compute_position(301, jd)
        geo_x0 = moon_pos0[0] - earth_pos[0]
        geo_y0 = moon_pos0[1] - earth_pos[1]
        geo_z0 = moon_pos0[2] - earth_pos[2]
        dist_km = math.sqrt(geo_x0**2 + geo_y0**2 + geo_z0**2)

        tau_days = dist_km / C_KM_DAY
        jd_ret = jd - tau_days
        moon_pos, moon_vel = self._compute_position_and_velocity(301, jd_ret)

        # Geocentric position and velocity (ICRF)
        rx = moon_pos[0] - earth_pos[0]
        ry = moon_pos[1] - earth_pos[1]
        rz = moon_pos[2] - earth_pos[2]

        vx = moon_vel[0] - earth_vel[0]
        vy = moon_vel[1] - earth_vel[1]
        vz = moon_vel[2] - earth_vel[2]

        # NO aberration for node computation — aberration is an apparent-direction
        # effect for observation, not a physical orbital property. Applying it to
        # r before r×v corrupts the orbital plane (amplified by Moon's low 5.1° inclination).

        # Precess position and velocity: ICRF → equatorial-of-date
        rx_d, ry_d, rz_d = _precess_j2000_to_date(rx, ry, rz, T)
        vx_d, vy_d, vz_d = _precess_j2000_to_date(vx, vy, vz, T)

        # Rotate to ecliptic-of-date
        rx_e, ry_e, rz_e = _equatorial_to_ecliptic_of_date(rx_d, ry_d, rz_d, T)
        vx_e, vy_e, vz_e = _equatorial_to_ecliptic_of_date(vx_d, vy_d, vz_d, T)

        # Angular momentum h = r x v (ecliptic-of-date)
        hx = ry_e * vz_e - rz_e * vy_e
        hy = rz_e * vx_e - rx_e * vz_e

        # Ascending node: n = k x h = (-hy, hx, 0)
        nx = -hy
        ny = hx

        # Degenerate orbit guard (Moon inclination is ~5.1°, never triggers)
        if abs(nx) + abs(ny) < 1e-12:
            return self._meeus_rahu_longitude(T)

        node_lon = math.atan2(ny, nx) * RAD2DEG % 360.0
        # Return geometric node longitude (no nutation — Rahu is orbital geometry, not apparent)
        return node_lon

    def _meeus_rahu_longitude(self, T):
        """Meeus True Lunar Node (Astronomical Algorithms, Ch. 47).

        Mean node + periodic corrections from Sun/Moon arguments.
        Accuracy: ~0.01 deg vs full numerical integration.
        """
        # Mean node (longitude of ascending node)
        omega = (125.0445479
                 - 1934.1362891 * T
                 + 0.0020754 * T * T
                 + T * T * T / 467441.0
                 - T * T * T * T / 60616000.0)

        # Fundamental arguments for periodic corrections
        # D = Moon's mean elongation
        D = (297.8501921
             + 445267.1114034 * T
             - 0.0018819 * T * T
             + T * T * T / 545868.0
             - T * T * T * T / 113065000.0) * DEG2RAD

        # M = Sun's mean anomaly
        M = (357.5291092
             + 35999.0502909 * T
             - 0.0001536 * T * T
             + T * T * T / 24490000.0) * DEG2RAD

        # M' = Moon's mean anomaly
        Mp = (134.9633964
              + 477198.8675055 * T
              + 0.0087414 * T * T
              + T * T * T / 69699.0
              - T * T * T * T / 14712000.0) * DEG2RAD

        # F = Moon's argument of latitude
        F = (93.2720950
             + 483202.0175233 * T
             - 0.0036539 * T * T
             - T * T * T / 3526000.0
             + T * T * T * T / 863310000.0) * DEG2RAD

        # Periodic corrections (degrees) — main terms from Meeus Table 47.A
        corr = (-1.4979 * math.sin(2.0 * (D - F))
                - 0.1500 * math.sin(M)
                - 0.1226 * math.sin(2.0 * D)
                + 0.1176 * math.sin(2.0 * F)
                - 0.0801 * math.sin(2.0 * (Mp - F)))

        return (omega + corr) % 360.0

    def interpolate(self, body_id, T):
        """Interface compat: Moon returns full geocentric lon, Rahu returns 0."""
        if body_id == 2:
            lon, lat, dist = self.geocentric_ecliptic(2, T)
            return [lon]
        elif body_id == 8:
            return [0.0]
        else:
            lon, lat, dist = self.geocentric_ecliptic(body_id, T)
            return [lon, lat, dist]

    def interpolate_with_velocity(self, body_id, T):
        """Interface compat with velocity."""
        pos, vel = self.geocentric_ecliptic_with_velocity(body_id, T)
        return list(pos), list(vel)
