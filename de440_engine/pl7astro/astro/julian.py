"""Julian Day / Century conversions and angle utilities.

Reconstructed from PL7.exe:
  FUN_004626f5 — JD → Julian Century
  FUN_0055d006 — Julian Century → JD
  FUN_0045b106 — normalize degrees
  FUN_0045b0be — angle difference (forward arc)
  FUN_0045b0da — signed angle difference
"""
import math

J2000 = 2451545.0
JULIAN_CENTURY = 36525.0
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi


def julian_century(jd):
    """Convert Julian Day to Julian Centuries since J2000.0 (Algorithm 1)."""
    return (jd - J2000) / JULIAN_CENTURY


def century_to_jd(T):
    """Convert Julian Century to Julian Day (Algorithm 2)."""
    return T * JULIAN_CENTURY + J2000


def date_to_jd(year, month, day, hour=0.0):
    """Convert calendar date to Julian Day Number (Meeus algorithm)."""
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return (int(365.25 * (year + 4716)) + int(30.6001 * (month + 1))
            + day + hour / 24.0 + B - 1524.5)


def jd_to_date(jd):
    """Convert Julian Day to (year, month, day, hour) tuple."""
    jd = jd + 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - int(alpha / 4)
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    hour = f * 24.0
    return year, month, day, hour


def normalize_degrees(angle):
    """Normalize angle to [0, 360) range (Algorithm 6)."""
    angle = angle % 360.0
    if angle < 0:
        angle += 360.0
    return angle


def angle_diff(angle1, angle2):
    """Forward arc from angle1 to angle2 in [0, 360) (Algorithm 7a)."""
    if angle2 < angle1:
        angle2 += 360.0
    return angle2 - angle1


def signed_angle_diff(angle1, angle2):
    """Signed angular difference in [-180, 180) (Algorithm 7b)."""
    diff = angle_diff(angle1, angle2)
    if diff > 180.0:
        diff -= 360.0
    return diff
