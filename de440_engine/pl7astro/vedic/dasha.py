"""Vimshottari Dasha system — period calculation and timeline builder.

Reconstructed from:
  FUN_004603ec — Dasha period builder
  FUN_0045dc1a — Dasha constants
  FUN_00460018 — Timeline computation
  FUN_00566a75 — Nakshatra-to-lord mapping
"""
from ..astro.julian import jd_to_date

# Dasha-internal planet indices
PLANET_NAMES = {
    0: "Ketu", 1: "Sun", 2: "Moon", 3: "Mars", 4: "Mercury",
    5: "Jupiter", 6: "Venus", 7: "Saturn", 8: "Rahu", 9: "Ketu",
}

# Vimshottari periods in years
VIMSHOTTARI_DURATIONS = {
    0: 7, 1: 6, 2: 10, 3: 7, 4: 17,
    5: 16, 6: 20, 7: 19, 8: 18, 9: 7,
}

VIMSHOTTARI_TOTAL = 120  # total years

# Next-planet cycle: Ketu→Venus→Sun→Moon→Mars→Rahu→Jupiter→Saturn→Mercury→Ketu
VIMSHOTTARI_NEXT = {
    0: 6, 1: 2, 2: 3, 3: 8, 4: 9,
    5: 7, 6: 1, 7: 4, 8: 5, 9: 6,
}

# Nakshatra → lord mapping (dasha-internal indices)
NAKSHATRA_TO_LORD_CYCLE = [0, 6, 1, 2, 3, 8, 5, 7, 4]

# Year factor options (from FUN_00464743)
# tropical: standard solar year (365.2422 days) — default for Vimshottari
# savana: 360 tithis = 360 days (BPHS definition of savana year)
# nakshatra: sidereal lunar year ≈ 12 × 27.3217 ≈ 327.86 days
YEAR_FACTORS = {
    'tropical': 365.2421875,
    'savana': 360.0,
    'nakshatra': 327.85,
}


def get_nakshatra_lord(nak_index):
    """Get Vimshottari dasha lord index for a nakshatra (0-26)."""
    return NAKSHATRA_TO_LORD_CYCLE[nak_index % 9]


def build_vimshottari_timeline(moon_sidereal_lon, birth_jd, max_level=2,
                                year_type='tropical'):
    """Build complete Vimshottari Dasha timeline.

    Args:
        moon_sidereal_lon: Moon's sidereal longitude in degrees [0, 360)
        birth_jd: Birth Julian Day number
        max_level: 1=Maha only, 2=+Antar, 3=+Pratyantar
        year_type: 'tropical', 'savana', or 'nakshatra'

    Returns:
        dict with nakshatra info and list of mahadasha periods
    """
    year_factor = YEAR_FACTORS[year_type]
    nak_span = 13.333333333333

    nak_index = int(moon_sidereal_lon / nak_span)
    if nak_index >= 27:
        nak_index = 26
    fraction_elapsed = (moon_sidereal_lon - nak_index * nak_span) / nak_span

    initial_lord = get_nakshatra_lord(nak_index)
    first_duration = VIMSHOTTARI_DURATIONS[initial_lord]
    elapsed_years = first_duration * fraction_elapsed
    dasha_start_jd = birth_jd - elapsed_years * year_factor

    planet = initial_lord
    current_jd = dasha_start_jd
    mahadashas = []

    for _ in range(9):
        years = VIMSHOTTARI_DURATIONS[planet]
        end_jd = current_jd + years * year_factor

        maha = {
            'planet': planet,
            'planet_name': PLANET_NAMES[planet],
            'start_jd': current_jd,
            'end_jd': end_jd,
            'years': years,
        }

        if max_level >= 2:
            maha['antardashas'] = _build_sub_periods(
                planet, current_jd, end_jd, years, year_factor, max_level, 2
            )

        mahadashas.append(maha)
        current_jd = end_jd
        planet = VIMSHOTTARI_NEXT[planet]

    from ..vedic.nakshatra import NAKSHATRA_NAMES
    return {
        'nakshatra_index': nak_index,
        'nakshatra_name': NAKSHATRA_NAMES[nak_index],
        'fraction_elapsed': fraction_elapsed,
        'initial_lord': initial_lord,
        'initial_lord_name': PLANET_NAMES[initial_lord],
        'dasha_start_jd': dasha_start_jd,
        'year_factor': year_factor,
        'mahadashas': mahadashas,
    }


def _build_sub_periods(parent_planet, parent_start, parent_end, parent_years,
                        year_factor, max_level, level):
    """Build sub-period hierarchy using proportional subdivision."""
    sub_periods = []
    planet = parent_planet
    current_jd = parent_start

    for _ in range(9):
        planet_duration = VIMSHOTTARI_DURATIONS[planet]
        sub_years = parent_years * (planet_duration / VIMSHOTTARI_TOTAL)
        end_jd = current_jd + sub_years * year_factor

        entry = {
            'planet': planet,
            'planet_name': PLANET_NAMES[planet],
            'start_jd': current_jd,
            'end_jd': end_jd,
            'years': sub_years,
        }

        if level < max_level:
            entry['sub_periods'] = _build_sub_periods(
                planet, current_jd, end_jd, sub_years, year_factor, max_level, level + 1
            )

        sub_periods.append(entry)
        current_jd = end_jd
        planet = VIMSHOTTARI_NEXT[planet]

    return sub_periods
