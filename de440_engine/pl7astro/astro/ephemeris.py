"""Ephemeris reader with Chebyshev interpolation and APPROX.DAT corrections.

Reconstructed from PL7.exe:
  FUN_0055d55b — Chebyshev polynomial evaluator (position + velocity)
  FUN_0055de40 — Chebyshev interpolation engine
  FUN_0055db28 — Main planet segment reader
  FUN_0055dbc1 — Moon segment reader
  FUN_0055f58f — Planet perturbation corrections (APPROX.DAT)
  FUN_0055f843 — Moon perturbation corrections
  FUN_0055fa13 — Rahu correction
"""
import struct
import math
from ..astro.julian import DEG2RAD

# Ephemeris constants
T_START = -1.9960164271  # Julian Century of ephemeris epoch start
JULIAN_CENTURY = 36525.0
J2000 = 2451545.0
UNIT_TO_DEG = 5.729577951307856e-07  # RAD2DEG * 1e-6

# Body layout parameters: coeff counts and segment sizes for bodies 1-12
COEFF_COUNTS = [10, 10, 8, 16, 3, 8, 3, 11, 11, 3, 3, 3]
SEG_SIZES = [0xa0, 8, 0xa0, 0x28, 0xa0, 0x50, 0xa0, 0x10, 0x10, 0xa0, 0xa0, 0xa0]
EPHEMDAT_MAIN_OFFSET = 0x28
EPHEMDAT_MOON_OFFSET = 0xD249D


class BodyParams:
    """Parameters for one body in the ephemeris."""
    __slots__ = ['coeff_count', 'stride', 'seg_size', 'is_moon_type',
                 'sub_segments', 'dimensions', 'total', 'uses_moon_reader', 'offset']


def compute_body_layout():
    """Compute per-body parameters and file offsets."""
    bodies = {}
    for i in range(12):
        b = i + 1
        bp = BodyParams()
        bp.coeff_count = COEFF_COUNTS[i]
        bp.stride = COEFF_COUNTS[i] + 1
        bp.seg_size = SEG_SIZES[i]
        bp.is_moon_type = (b == 2) or (7 < b < 10)
        if bp.is_moon_type:
            bp.sub_segments = 0x10 // bp.seg_size
            bp.dimensions = 1
        else:
            bp.sub_segments = 0xa0 // bp.seg_size
            bp.dimensions = 3
        bp.total = bp.stride * bp.dimensions * bp.sub_segments
        bp.uses_moon_reader = (b == 2 or b == 8)
        bodies[b] = bp

    main_off = 0
    for b in [1, 3, 4, 5, 6, 7, 10, 11, 12]:
        bodies[b].offset = main_off
        main_off += bodies[b].total
    moon_off = 0
    for b in [2, 8]:
        bodies[b].offset = moon_off
        moon_off += bodies[b].total

    return bodies, main_off, moon_off


BODIES, MAIN_SEG_SIZE, MOON_SEG_SIZE = compute_body_layout()


def chebyshev_eval(coeffs, t_norm, n):
    """Evaluate Chebyshev polynomial using float32 accumulation (matching PL7).

    Returns: position value
    """
    if n == 0:
        return 0.0
    T_prev = 1.0
    T_curr = t_norm
    result = float(coeffs[0])
    if n > 1:
        result = float(float(coeffs[0]) + float(coeffs[1]) * float(t_norm))
    for i in range(2, n):
        T_next = 2.0 * t_norm * T_curr - T_prev
        result = float(float(result) + float(coeffs[i]) * float(T_next))
        T_prev = T_curr
        T_curr = T_next
    return result


def chebyshev_eval_with_velocity(coeffs, t_norm, n, scale):
    """Evaluate Chebyshev polynomial returning (position, velocity).

    Algorithm 11 from ALGORITHM_ANALYSIS.md — includes derivative recurrence.

    Args:
        coeffs: Chebyshev coefficients
        t_norm: Normalized time in [-1, 1]
        n: Number of coefficients
        scale: Velocity scale factor = (2 * sub_segments / seg_span) * 36525.0

    Returns:
        (position, velocity)
    """
    if n == 0:
        return 0.0, 0.0

    # Position polynomials
    T = [0.0] * n
    T[0] = 1.0
    if n > 1:
        T[1] = t_norm

    # Derivative polynomials
    dT = [0.0] * n
    dT[0] = 0.0
    if n > 1:
        dT[1] = scale

    for i in range(2, n):
        T[i] = 2.0 * t_norm * T[i - 1] - T[i - 2]
        dT[i] = 2.0 * (t_norm * dT[i - 1] + T[i - 1]) - dT[i - 2]

    position = 0.0
    velocity = 0.0
    for i in range(n):
        c = float(coeffs[i])
        position += c * T[i]
        velocity += c * dT[i]

    return position, velocity


class EphemerisReader:
    """Reads planetary positions from ephemdat.bin using Chebyshev interpolation."""

    def __init__(self, ephemdat_path, approx_path=None):
        self._file = open(ephemdat_path, 'rb')
        self._approx_buf = None
        if approx_path:
            with open(approx_path, 'rb') as af:
                data = af.read()
            self._approx_buf = list(struct.unpack(f'<{len(data) // 8}d', data))
        self._cache_main = {}
        self._cache_moon = {}

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _read_segment(self, body_id, T):
        """Read and cache the raw Chebyshev coefficients for a segment."""
        bp = BODIES[body_id]
        days = (T - T_START) * JULIAN_CENTURY

        if bp.uses_moon_reader:
            seg_span = 16.0
            file_seg = int(days / seg_span)
            time_in = days - file_seg * seg_span
            cache_key = file_seg
            if cache_key not in self._cache_moon:
                offset = file_seg * MOON_SEG_SIZE * 4 + EPHEMDAT_MOON_OFFSET
                self._file.seek(offset)
                data = self._file.read(MOON_SEG_SIZE * 4)
                self._cache_moon[cache_key] = struct.unpack(f'<{MOON_SEG_SIZE}f', data)
            buf = self._cache_moon[cache_key]
        else:
            seg_span = 160.0
            file_seg = int(days / seg_span)
            time_in = days - file_seg * seg_span
            cache_key = file_seg
            if cache_key not in self._cache_main:
                offset = MAIN_SEG_SIZE * file_seg * 4 + EPHEMDAT_MAIN_OFFSET
                self._file.seek(offset)
                data = self._file.read(MAIN_SEG_SIZE * 4)
                self._cache_main[cache_key] = struct.unpack(f'<{MAIN_SEG_SIZE}f', data)
            buf = self._cache_main[cache_key]

        return bp, buf, seg_span, time_in

    def interpolate(self, body_id, T):
        """Interpolate Chebyshev coefficients for body at Julian Century T.

        Returns: list of position values per dimension (1 for Moon/Rahu, 3 for planets)
        """
        bp, buf, seg_span, time_in = self._read_segment(body_id, T)

        inner_span = seg_span / bp.sub_segments
        sub_seg = min(int(time_in / inner_span), bp.sub_segments - 1)
        sub_start = sub_seg * inner_span
        t_norm = 2.0 * (time_in - sub_start) / inner_span - 1.0

        base = bp.offset + bp.stride * bp.dimensions * sub_seg
        results = []
        for dim in range(bp.dimensions):
            start = base + dim * bp.stride
            coeffs = buf[start:start + bp.stride]
            val = chebyshev_eval(coeffs, t_norm, bp.stride)
            results.append(val)
        return results

    def interpolate_with_velocity(self, body_id, T):
        """Interpolate returning (positions[], velocities[]) per dimension.

        Used for aberration correction which needs velocity vectors.
        """
        bp, buf, seg_span, time_in = self._read_segment(body_id, T)

        inner_span = seg_span / bp.sub_segments
        sub_seg = min(int(time_in / inner_span), bp.sub_segments - 1)
        sub_start = sub_seg * inner_span
        t_norm = 2.0 * (time_in - sub_start) / inner_span - 1.0

        # Velocity scale: (2 * sub_segments / seg_span) * 36525.0
        vel_scale = (2.0 * bp.sub_segments / seg_span) * JULIAN_CENTURY

        base = bp.offset + bp.stride * bp.dimensions * sub_seg
        positions = []
        velocities = []
        for dim in range(bp.dimensions):
            start = base + dim * bp.stride
            coeffs = buf[start:start + bp.stride]
            pos, vel = chebyshev_eval_with_velocity(coeffs, t_norm, bp.stride, vel_scale)
            positions.append(pos)
            velocities.append(vel)
        return positions, velocities

    def approx_lon(self, body_id, T):
        """APPROX.DAT longitude correction (FUN_0055f58f, dim=0)."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = (body_id - 1) * 5
        L0, rate, amp, phase, freq = self._approx_buf[base:base + 5]
        return (L0 + rate * t + amp * math.cos(t * freq + phase)) * UNIT_TO_DEG

    def approx_lat(self, body_id, T):
        """APPROX.DAT latitude correction (FUN_0055f58f, dim=1)."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = body_id * 3 + 105
        amp, phase, freq = self._approx_buf[base:base + 3]
        result = math.cos(t * freq + phase) * amp * UNIT_TO_DEG
        if body_id == 12:
            result -= 3.908202
        return result

    def approx_dist(self, body_id, T):
        """APPROX.DAT distance correction (FUN_0055f58f, dim=2)."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = (body_id + 14) * 4
        mean_d, amp, phase, freq = self._approx_buf[base:base + 4]
        return (mean_d + amp * math.cos(t * freq + phase)) * 1.4959787066

    def approx_lon_velocity(self, body_id, T):
        """APPROX.DAT longitude velocity (derivative of approx_lon)."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = (body_id - 1) * 5
        L0, rate, amp, phase, freq = self._approx_buf[base:base + 5]
        sinval = math.sin(t * freq + phase)
        return (rate - sinval * freq * amp) * UNIT_TO_DEG * 0.1

    def approx_lat_velocity(self, body_id, T):
        """APPROX.DAT latitude velocity."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = body_id * 3 + 105
        amp, phase, freq = self._approx_buf[base:base + 3]
        sinval = math.sin(t * freq + phase)
        return -(sinval * freq * amp) * UNIT_TO_DEG * 0.1

    def approx_dist_velocity(self, body_id, T):
        """APPROX.DAT distance velocity."""
        if self._approx_buf is None:
            return 0.0
        t = T * 0.1
        base = (body_id + 14) * 4
        mean_d, amp, phase, freq = self._approx_buf[base:base + 4]
        sinval = math.sin(t * freq + phase)
        return (-sinval * freq * amp) * 1.4959787066 * 0.1

    def helio_position(self, body_id, T):
        """Get heliocentric (lon, lat, dist) for a standard body."""
        cheb = self.interpolate(body_id, T)
        lon = self.approx_lon(body_id, T) + cheb[0]
        lat = self.approx_lat(body_id, T) + cheb[1]
        dist = self.approx_dist(body_id, T) + cheb[2]
        return lon % 360.0 if lon >= 0 else (lon % 360.0 + 360.0), lat, dist

    def helio_position_with_velocity(self, body_id, T):
        """Get heliocentric (pos[3], vel[3]) for a standard body."""
        cheb_pos, cheb_vel = self.interpolate_with_velocity(body_id, T)
        pos = [
            self.approx_lon(body_id, T) + cheb_pos[0],
            self.approx_lat(body_id, T) + cheb_pos[1],
            self.approx_dist(body_id, T) + cheb_pos[2],
        ]
        vel = [
            self.approx_lon_velocity(body_id, T) + cheb_vel[0],
            self.approx_lat_velocity(body_id, T) + cheb_vel[1],
            self.approx_dist_velocity(body_id, T) + cheb_vel[2],
        ]
        return pos, vel

    def moon_longitude(self, T):
        """Moon ecliptic longitude matching FUN_0055f843 (dim=0).

        PL7's actual formula (from decompiled code):
            M' = 134.9634114 + 477198.8676313 * T
            L  = 218.3164591 + 481267.88134236 * T + 6.288774 * sin(M')

        The Chebyshev residuals in ephemdat.bin are calibrated against this
        specific simple formula, so we MUST use it (not the full Meeus series).
        """
        M_prime = 134.9634114 + 477198.8676313 * T
        sin_M = math.sin(M_prime * DEG2RAD)
        return 218.3164591 + 481267.88134236 * T + 6.288774 * sin_M

    def rahu_longitude(self, T):
        """Rahu (True Node) mean longitude (FUN_0055fa13)."""
        return 125.044555 - T * 1934.1361849
