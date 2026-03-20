"""Transit engine and boundary crossing solver.

Reconstructed from:
  FUN_00465ad2 — find_exact_crossing (1621 bytes)
  FUN_00466127 — find_interval_crossing (475 bytes)
  FUN_00466302 — find_sign_crossing_with_opposition (575 bytes)
  FUN_00466541 — find_boundary_simple (459 bytes)
  FUN_004667af — find_dasha_boundary (2513 bytes, master dispatcher)
"""
import math
from ..astro.julian import normalize_degrees

SIGN_SPAN = 30.0
NAKSHATRA_SPAN = 13.333333333333334
PADA_SPAN = 3.333333333333333

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


class TransitEngine:
    """Transit/boundary crossing solver using the corrected pipeline."""

    def __init__(self, pipeline):
        """
        Args:
            pipeline: Pipeline instance for computing positions at arbitrary JDs
        """
        self.pipeline = pipeline

    def planet_longitude_at(self, planet_id, jd_local, timezone=0.0):
        """Get sidereal longitude of a planet at a given JD.

        This is the core evaluation used by all solvers.
        """
        result = self.pipeline.calc_all(jd_local, timezone)
        if planet_id in result.planets:
            return result.planets[planet_id].sidereal_lon
        return 0.0

    def find_exact_crossing(self, start_jd, end_jd, target_longitude,
                            planet_id, timezone=0.0, precision_days=0.001):
        """Find exact JD when a planet reaches a target sidereal longitude.

        Uses half-day scanning followed by bisection refinement.
        Matches FUN_00465ad2 algorithm.

        Args:
            start_jd: Start of search window (local JD)
            end_jd: End of search window (local JD)
            target_longitude: Target sidereal longitude (degrees, 0-360)
            planet_id: Planet identifier (1-9)
            timezone: Timezone offset
            precision_days: Bisection stops when interval < this

        Returns:
            (crossing_jd, direction): JD of crossing and +1/-1 direction
            Returns (0.0, 0) if not found
        """
        if start_jd < 10000.0:
            return 0.0, 0

        # Handle Ketu: add 180° to target and search for Rahu
        if planet_id == 9:
            target_longitude = normalize_degrees(target_longitude + 180.0)
            planet_id = 8

        # Step size: 0.5 days for scanning
        step = 0.5
        prev_jd = start_jd
        prev_lon = self.planet_longitude_at(planet_id, prev_jd, timezone)

        jd = start_jd + step
        while jd <= end_jd:
            curr_lon = self.planet_longitude_at(planet_id, jd, timezone)

            # Check if target is between prev_lon and curr_lon
            # Handle wraparound at 0/360
            crossed = self._check_crossing(prev_lon, curr_lon, target_longitude)

            if crossed:
                # Bisection refinement
                lo, hi = prev_jd, jd
                while (hi - lo) > precision_days:
                    mid = (lo + hi) / 2.0
                    mid_lon = self.planet_longitude_at(planet_id, mid, timezone)
                    if self._check_crossing(prev_lon, mid_lon, target_longitude):
                        hi = mid
                    else:
                        lo = mid
                        prev_lon = mid_lon

                crossing_jd = (lo + hi) / 2.0

                # Determine direction
                lon_before = self.planet_longitude_at(planet_id, crossing_jd - 0.01, timezone)
                lon_after = self.planet_longitude_at(planet_id, crossing_jd + 0.01, timezone)
                diff = lon_after - lon_before
                if diff > 180:
                    diff -= 360
                if diff < -180:
                    diff += 360
                direction = 1 if diff > 0 else -1

                return crossing_jd, direction

            prev_jd = jd
            prev_lon = curr_lon
            jd += step

        return 0.0, 0

    def find_all_crossings(self, start_jd, end_jd, target_longitude,
                           planet_id, timezone=0.0, precision_days=0.001):
        """Find ALL crossings of a target longitude in a time range.

        Handles retrograde motion by continuing to scan after each crossing found.

        Returns:
            list of (crossing_jd, direction) tuples
        """
        results = []
        search_start = start_jd
        while search_start < end_jd:
            jd, direction = self.find_exact_crossing(
                search_start, end_jd, target_longitude, planet_id,
                timezone, precision_days)
            if jd <= 0:
                break
            results.append((jd, direction))
            search_start = jd + 0.5  # skip past this crossing
        return results

    def find_sign_ingress(self, planet_id, start_jd, end_jd, timezone=0.0):
        """Find all sign ingresses for a planet in a time range.

        Finds multiple crossings per boundary (retrograde planets can cross 3 times).

        Returns:
            list of (jd, sign_index, direction) tuples
        """
        results = []
        for sign_idx in range(12):
            boundary = sign_idx * SIGN_SPAN
            crossings = self.find_all_crossings(
                start_jd, end_jd, boundary, planet_id, timezone
            )
            for jd, direction in crossings:
                results.append((jd, sign_idx, direction))

        results.sort(key=lambda x: x[0])
        return results

    def find_nakshatra_ingress(self, planet_id, start_jd, end_jd, timezone=0.0):
        """Find all nakshatra ingresses for a planet in a time range.

        Finds multiple crossings per boundary (retrograde planets can cross 3 times).

        Returns:
            list of (jd, nakshatra_index, direction) tuples
        """
        results = []
        for nak_idx in range(27):
            boundary = nak_idx * NAKSHATRA_SPAN
            crossings = self.find_all_crossings(
                start_jd, end_jd, boundary, planet_id, timezone
            )
            for jd, direction in crossings:
                results.append((jd, nak_idx, direction))

        results.sort(key=lambda x: x[0])
        return results

    def _check_crossing(self, lon1, lon2, target):
        """Check if target longitude is between lon1 and lon2 (any direction).

        Handles both direct (forward) and retrograde (backward) motion.
        """
        lon1 = lon1 % 360.0
        lon2 = lon2 % 360.0
        target = target % 360.0

        # Forward arc from lon1 to lon2
        fwd_arc = (lon2 - lon1) % 360.0
        fwd_to_target = (target - lon1) % 360.0

        if fwd_arc <= 180.0:
            # Direct motion: target must be within the forward arc
            return fwd_to_target < fwd_arc and fwd_arc > 0
        else:
            # Retrograde motion: target must be within the backward arc
            bwd_arc = 360.0 - fwd_arc
            bwd_to_target = (lon1 - target) % 360.0
            return bwd_to_target < bwd_arc and bwd_arc > 0
