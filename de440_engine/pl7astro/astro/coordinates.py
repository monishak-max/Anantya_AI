"""Coordinate transformations: spherical ↔ rectangular, helio → geo.

Reconstructed from PL7.exe:
  FUN_0055da81 — Rectangular to spherical (lon, lat, dist)
  FUN_0055e2ef — Coordinate combination (helio to geo)
  FUN_0055e315 — Earth-Sun distance computation
"""
import math
from ..astro.julian import DEG2RAD, RAD2DEG


def spherical_to_rect(lon_deg, lat_deg, dist):
    """Convert spherical (lon°, lat°, dist) to rectangular (x, y, z)."""
    lon = lon_deg * DEG2RAD
    lat = lat_deg * DEG2RAD
    cos_lat = math.cos(lat)
    return (
        math.cos(lon) * cos_lat * dist,
        math.sin(lon) * cos_lat * dist,
        math.sin(lat) * dist,
    )


def rect_to_spherical(x, y, z):
    """Convert rectangular (x, y, z) to spherical (lon°, lat°, dist).

    Matches FUN_0055da81: atan-based with quadrant correction.
    """
    dist = math.sqrt(x * x + y * y + z * z)
    xy = math.sqrt(x * x + y * y)

    if xy < 1e-30:
        lat = 90.0 if z >= 0 else -90.0
        lon = 0.0
    else:
        lat = math.atan(z / xy) * RAD2DEG
        lon = math.atan(y / x) * RAD2DEG if abs(x) > 1e-30 else (90.0 if y > 0 else 270.0)
        if x < 0:
            lon += 180.0

    if lon < 0:
        lon += 360.0
    if lon >= 360.0:
        lon -= 360.0

    return lon, lat, dist


def helio_to_geo_rect(planet_rect, earth_rect):
    """Convert heliocentric rectangular to geocentric rectangular."""
    return (
        planet_rect[0] - earth_rect[0],
        planet_rect[1] - earth_rect[1],
        planet_rect[2] - earth_rect[2],
    )
