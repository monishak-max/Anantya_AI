"""Ayanamsha calculation — all 7 systems from PL7.

Reconstructed from FUN_0055d3ea (Algorithm 4).
"""


def calc_ayanamsha(jd, system=1):
    """Calculate ayanamsha for given Julian Day.

    Args:
        jd: Julian Day Number (TT)
        system: 1=Lahiri, 2=None(Tropical), 3=Raman, 4=KP,
                5=KP_New, 6=Fagan-Bradley, 7=Yukteshwar, 8=Bhasin

    Returns:
        Ayanamsha in degrees
    """
    # +1.0 converts J2000 centuries to B1900 centuries (~JD 2415020.3).
    # The Lahiri precession polynomial below uses the B1900 epoch as origin.
    T_J2000 = (jd - 2451545.0) / 36525.0 + 1.0

    # Lahiri (Chitrapaksha) — polynomial precession
    lahiri = (5026.87434 + 1.11113 * T_J2000) * T_J2000 / 3600.0 + 22.46045833333

    # T_B1900 = tropical centuries from B1900
    T_B1900 = (jd - 2415020.5) / 36524.2198781

    if system == 2:
        return 0.0  # Tropical (no ayanamsha)
    elif system == 3:
        return 21.015 + 1.5 * T_B1900  # Raman
    elif system == 4:
        return 21.013888889 + 1.398148148 * T_B1900  # Krishnamurti (KP)
    elif system == 5:
        return 21.363888889 + 1.398148148 * T_B1900  # Krishnamurti New
    elif system == 6:
        return 23.348888889 + 1.398148148 * T_B1900  # Fagan-Bradley
    elif system == 7:
        return 22.453973785 + 1.3955235417 * T_B1900  # Yukteshwar
    elif system == 8:
        return lahiri - 0.101388 + 0.0011118 * T_B1900  # Bhasin
    else:
        return lahiri  # Default: Lahiri
