"""Yoga rule engine — Panchanga yogas and chart yogas.

Panchanga Yoga: Based on Sun+Moon sidereal longitude sum.
Chart Yogas: Placeholder for Yogas_1.dat rule database.
"""
from ..astro.julian import normalize_degrees

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]


def calc_panchanga_yoga(sun_sidereal, moon_sidereal):
    """Calculate Panchanga Yoga from Sun and Moon sidereal longitudes.

    yoga_index = floor((sun + moon) / 13.333333)

    Args:
        sun_sidereal: Sun's sidereal longitude in degrees
        moon_sidereal: Moon's sidereal longitude in degrees

    Returns:
        dict with index (0-26), name, and degree within yoga
    """
    total = normalize_degrees(sun_sidereal + moon_sidereal)
    yoga_span = 13.333333333333334  # 360/27
    yoga_index = int(total / yoga_span)
    if yoga_index >= 27:
        yoga_index = 26
    degree_in_yoga = total - yoga_index * yoga_span

    return {
        'index': yoga_index,
        'name': YOGA_NAMES[yoga_index],
        'degree_in_yoga': degree_in_yoga,
    }


# Common BPHS yogas (textbook rules)

def check_gajakesari(moon_sign, jupiter_sign):
    """Gajakesari Yoga: Moon and Jupiter in mutual kendras (1,4,7,10)."""
    diff = (jupiter_sign - moon_sign) % 12
    return diff in (0, 3, 6, 9)


def check_pancha_mahapurusha(planet_sign, planet_id, ascendant_sign):
    """Pancha Mahapurusha Yoga: Mars/Mercury/Jupiter/Venus/Saturn in own/exalted sign in kendra."""
    diff = (planet_sign - ascendant_sign) % 12
    is_kendra = diff in (0, 3, 6, 9)
    if not is_kendra:
        return False, None

    # Own signs and exaltation signs for each planet
    own_exalt = {
        3: ([0, 7], [9]),      # Mars: Aries/Scorpio, exalted Capricorn → Ruchaka
        4: ([2, 5], [5]),      # Mercury: Gemini/Virgo, exalted Virgo → Bhadra
        5: ([8, 11], [3]),     # Jupiter: Sagittarius/Pisces, exalted Cancer → Hamsa
        6: ([1, 6], [11]),     # Venus: Taurus/Libra, exalted Pisces → Malavya
        7: ([9, 10], [6]),     # Saturn: Capricorn/Aquarius, exalted Libra → Shasha
    }

    yoga_names = {3: "Ruchaka", 4: "Bhadra", 5: "Hamsa", 6: "Malavya", 7: "Shasha"}

    if planet_id not in own_exalt:
        return False, None

    own_signs, exalt_signs = own_exalt[planet_id]
    if planet_sign in own_signs or planet_sign in exalt_signs:
        return True, yoga_names[planet_id]

    return False, None


def detect_yogas(chart_result):
    """Detect common yogas from a ChartResult.

    Args:
        chart_result: ChartResult from Pipeline.calc_all()

    Returns:
        list of detected yoga descriptions
    """
    yogas = []

    # Panchanga Yoga
    sun_sid = chart_result.planets[1].sidereal_lon
    moon_sid = chart_result.planets[2].sidereal_lon
    py = calc_panchanga_yoga(sun_sid, moon_sid)
    yogas.append(f"Panchanga Yoga: {py['name']} ({py['index'] + 1}/27)")

    # Gajakesari
    moon_sign = int(moon_sid / 30)
    jup_sign = int(chart_result.planets[5].sidereal_lon / 30)
    if check_gajakesari(moon_sign, jup_sign):
        yogas.append("Gajakesari Yoga (Moon-Jupiter in mutual kendras)")

    # Pancha Mahapurusha
    asc_sign = int(chart_result.ascendant / 30)
    for pid in [3, 4, 5, 6, 7]:
        p_sign = int(chart_result.planets[pid].sidereal_lon / 30)
        found, name = check_pancha_mahapurusha(p_sign, pid, asc_sign)
        if found:
            yogas.append(f"{name} Yoga ({chart_result.planets[pid].name} in kendra in own/exalted sign)")

    return yogas
