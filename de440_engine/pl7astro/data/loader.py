"""Master data loader.

Loads ephemeris data and creates the pipeline. Defaults to JPL DE440 for
high-accuracy positions; falls back to PL7 Chebyshev if explicitly requested.
"""
import os
from ..config import EPHEMDAT_PATH, APPROX_PATH, DELTAT_PATH, DE440_PATH
from ..astro.corrections import DeltaTTable
from ..astro.pipeline import Pipeline


def create_pipeline(de440_path=None, deltat_path=None,
                    ephemdat_path=None, approx_path=None):
    """Create a fully configured Pipeline.

    By default uses JPL DE440 for high-accuracy positions (< 0.001 deg).
    Pass ephemdat_path explicitly to use the legacy PL7 Chebyshev engine.

    Args:
        de440_path: Path to de440.bsp (default: config.DE440_PATH)
        deltat_path: Path to DELTAT.ASC (default: config.DELTAT_PATH)
        ephemdat_path: Path to ephemdat.bin (forces legacy mode)
        approx_path: Path to APPROX.DAT (legacy mode only)

    Returns:
        Pipeline instance (caller should close ephemeris when done)
    """
    if deltat_path is None:
        deltat_path = DELTAT_PATH

    if ephemdat_path:
        # Legacy: use PL7 Chebyshev
        from ..astro.ephemeris import EphemerisReader
        if approx_path is None:
            approx_path = APPROX_PATH
        eph = EphemerisReader(ephemdat_path, approx_path)
    else:
        # Default: use JPL DE440
        from ..astro.jpl_ephemeris import JPLEphemerisReader
        if de440_path is None:
            de440_path = DE440_PATH
        eph = JPLEphemerisReader(de440_path)

    delta_t = None
    if os.path.exists(deltat_path):
        delta_t = DeltaTTable(deltat_path)

    return Pipeline(eph, delta_t)
