"""Moon accuracy: DE440 vs Swiss Ephemeris direct comparison.

Compares our DE440 pipeline Moon sidereal longitude against Swiss Ephemeris
(pyswisseph, JPL DE431) across 10,000 random dates and a dense daily sweep.
Reports statistics, sign flips, and nakshatra flips.

Run via: python -m pl7astro.tests.test_moon_accuracy
"""
import sys
import os
import math
import random
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import swisseph as swe
from ..astro.julian import date_to_jd
from ..data.loader import create_pipeline

# ── Constants ────────────────────────────────────────────────────────────────

SIGN_SPAN = 30.0
NAKSHATRA_SPAN = 360.0 / 27.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _angle_diff(a, b):
    """Wrap-safe angular difference in degrees. Returns value in [-180, 180)."""
    return ((a - b + 180.0) % 360.0) - 180.0


def _percentile(sorted_vals, p):
    """Simple percentile from pre-sorted list."""
    n = len(sorted_vals)
    k = (p / 100.0) * (n - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def _swiss_moon_sid(jd_ut):
    """Get sidereal Moon longitude from Swiss Ephemeris."""
    result = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SIDEREAL)
    return result[0][0] % 360.0


def _de440_moon_sid(pipeline, jd_ut):
    """Get sidereal Moon longitude from DE440 pipeline."""
    result = pipeline.calc_all(jd_ut, timezone=0, latitude=0, longitude=0,
                               ayanamsha_system=1)
    return result.planets[2].sidereal_lon


def _generate_random_jds(n, year_start, year_end, seed=42):
    """Generate n random JDs uniformly distributed between year_start and year_end."""
    rng = random.Random(seed)
    jd_start = date_to_jd(year_start, 1, 1)
    jd_end = date_to_jd(year_end, 12, 31)
    return [rng.uniform(jd_start, jd_end) for _ in range(n)]


def _print_stats(errors_arcsec, label=""):
    """Print error statistics from a list of absolute errors in arcseconds."""
    n = len(errors_arcsec)
    sorted_errs = sorted(errors_arcsec)
    mean_err = sum(sorted_errs) / n
    max_err = sorted_errs[-1]
    p95 = _percentile(sorted_errs, 95)
    p99 = _percentile(sorted_errs, 99)
    std_dev = math.sqrt(sum((e - mean_err) ** 2 for e in sorted_errs) / n)

    print(f"  Mean error:  {mean_err:.2f}\"")
    print(f"  Max error:   {max_err:.2f}\"")
    print(f"  P95:         {p95:.2f}\"")
    print(f"  P99:         {p99:.2f}\"")
    print(f"  Std dev:     {std_dev:.2f}\"")

    return {"mean": mean_err, "max": max_err, "p95": p95, "p99": p99, "std": std_dev}


# ── Tests ────────────────────────────────────────────────────────────────────

def test_random_dates(pipeline, n=10000):
    """Test 1: 10,000 random dates (1920-2030), DE440 vs Swiss, Moon sidereal.

    Reports error statistics plus sign and nakshatra boundary flips.
    Pass criteria: mean < 5", max < 20", 0 sign flips, 0 nakshatra flips.
    """
    print(f"Test 1: {n:,} Random Dates (1920-2030)")
    print("-" * 50)

    jds = _generate_random_jds(n, 1920, 2030)
    errors_arcsec = []
    sign_flips = 0
    nak_flips = 0
    worst_jd = None
    worst_err = 0.0

    t0 = time.time()
    for jd in jds:
        swe_lon = _swiss_moon_sid(jd)
        de440_lon = _de440_moon_sid(pipeline, jd)

        diff_deg = abs(_angle_diff(de440_lon, swe_lon))
        err_arcsec = diff_deg * 3600.0
        errors_arcsec.append(err_arcsec)

        if err_arcsec > worst_err:
            worst_err = err_arcsec
            worst_jd = jd

        # Sign comparison
        sign_swe = int(swe_lon / SIGN_SPAN) % 12
        sign_de440 = int(de440_lon / SIGN_SPAN) % 12
        if sign_swe != sign_de440:
            sign_flips += 1

        # Nakshatra comparison
        nak_swe = int(swe_lon / NAKSHATRA_SPAN) % 27
        nak_de440 = int(de440_lon / NAKSHATRA_SPAN) % 27
        if nak_swe != nak_de440:
            nak_flips += 1

    elapsed = time.time() - t0

    stats = _print_stats(errors_arcsec)
    print(f"  Sign flips:  {sign_flips} / {n:,}")
    print(f"  Nak flips:   {nak_flips} / {n:,}")
    print(f"  Time:        {elapsed:.1f}s")
    if worst_jd:
        print(f"  Worst at JD: {worst_jd:.6f} ({worst_err:.2f}\")")

    # Pass criteria
    passed = (stats["mean"] < 5.0 and stats["max"] < 20.0
              and sign_flips == 0 and nak_flips == 0)
    print(f"  {'PASSED' if passed else 'FAILED'}")
    print()
    return passed, stats


def test_dense_sweep(pipeline):
    """Test 2: Dense sweep (daily, 1920-2030), Moon only.

    ~40,177 daily dates. Uses 1920-2030 range where Delta-T is well-constrained
    by IERS observations (avoids extrapolation divergence at edges).
    Pass criteria: mean < 5", max < 20".
    """
    jd_start = date_to_jd(1920, 1, 1)
    jd_end = date_to_jd(2030, 12, 31)
    n_days = int(jd_end - jd_start) + 1

    print(f"Test 2: Dense Sweep ({n_days:,} days, 1920-2030)")
    print("-" * 50)

    errors_arcsec = []
    worst_jd = None
    worst_err = 0.0

    t0 = time.time()
    jd = jd_start
    while jd <= jd_end:
        swe_lon = _swiss_moon_sid(jd)
        de440_lon = _de440_moon_sid(pipeline, jd)

        diff_deg = abs(_angle_diff(de440_lon, swe_lon))
        err_arcsec = diff_deg * 3600.0
        errors_arcsec.append(err_arcsec)

        if err_arcsec > worst_err:
            worst_err = err_arcsec
            worst_jd = jd

        jd += 1.0

    elapsed = time.time() - t0

    stats = _print_stats(errors_arcsec)
    print(f"  Days tested: {len(errors_arcsec):,}")
    print(f"  Time:        {elapsed:.1f}s")
    if worst_jd:
        print(f"  Worst at JD: {worst_jd:.6f} ({worst_err:.2f}\")")

    passed = stats["mean"] < 5.0 and stats["max"] < 20.0
    print(f"  {'PASSED' if passed else 'FAILED'}")
    print()
    return passed, stats


# ── Main ─────────────────────────────────────────────────────────────────────

def run_all():
    print()
    print("Moon Accuracy: DE440 vs Swiss Ephemeris")
    print("=" * 50)
    print()

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    pipeline = create_pipeline()

    results = []
    results.append(test_random_dates(pipeline))
    results.append(test_dense_sweep(pipeline))

    pipeline.eph.close()
    swe.close()

    # Summary
    n_passed = sum(1 for passed, _ in results if passed)
    n_total = len(results)
    print("=" * 50)
    print(f"Summary: {n_passed}/{n_total} PASSED")
    print()

    sys.exit(0 if n_passed == n_total else 1)


if __name__ == "__main__":
    run_all()
