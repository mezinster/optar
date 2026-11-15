# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Sampling every channel bit: bit_coord and pixel_correct_sample (unoptar.c).

Float widths follow C: cross positions and the sampling coordinates are
doubles, the interpolated cut level and pixel values are 32-bit floats, the
unsharp-mask product is computed in double and stored to float.
"""

from __future__ import annotations

import numpy as np

from optar.decoder.crosses import interp
from optar.decoder.geometry import Geometry
from optar.decoder.options import DecodeOptions
from optar.format import PageFormat
from optar.layout import channel_xy

CHUNK = 250_000  # positions sampled at once; bounds the temporaries

_f32 = np.float32


def _bilinear(ul, ur, ll, lr, hpar, vpar):
    """C bilinear() (double) or bilinearf() (float32), by the argument dtype."""
    one = hpar.dtype.type(1)
    u = ur * hpar + ul * (one - hpar)
    lo = lr * hpar + ll * (one - hpar)
    return lo * vpar + u * (one - vpar)


def _bit_coord(x, y, positions, cutlevels, fmt: PageFormat):
    """Sampling centre (integers at pixel centres) and local cut level for x, y."""
    c, p = fmt.chalf, fmt.cpitch
    cx = np.minimum(np.where(x < c, 0, (x - c) // p), fmt.xcrosses - 2)
    cy = np.minimum(np.where(y < c, 0, (y - c) // p), fmt.ycrosses - 2)
    xrem = ((x - (cx * p + c)) + 0.5) / p  # remainders may be < 0 or > 1
    yrem = ((y - (cy * p + c)) + 0.5) / p
    corners = (positions[cx, cy], positions[cx + 1, cy], positions[cx, cy + 1],
               positions[cx + 1, cy + 1])  # fmt: skip
    xd = _bilinear(*(q[:, 0] for q in corners), xrem, yrem)
    yd = _bilinear(*(q[:, 1] for q in corners), xrem, yrem)
    cut = _bilinear(
        cutlevels[cx, cy], cutlevels[cx + 1, cy], cutlevels[cx, cy + 1], cutlevels[cx + 1, cy + 1],
        xrem.astype(_f32), yrem.astype(_f32),
    )  # fmt: skip
    return xd - 0.5, yd - 0.5, cut


def _correct_sample(img, x, y, geom: Geometry, opts: DecodeOptions):
    """pixel_correct_sample: unsharp mask against four neighbours, float32."""
    phx, phy = geom.ph
    pvx, pvy = geom.pv
    hdist = geom.hpixel * opts.unsharp_dist
    vdist = geom.vpixel * opts.unsharp_dist
    avg = None
    for dx, dy in ((-hdist, 0.0), (hdist, 0.0), (0.0, vdist), (0.0, -vdist)):
        v = interp(img, (x + dx * phx) + dy * pvx, (y + dx * phy) + dy * pvy)
        avg = v if avg is None else avg + v
    avg = avg / _f32(4)
    val = interp(img, x, y)
    diff = (val - avg).astype(np.float64)
    return (val.astype(np.float64) + opts.unsharp_mask * diff).astype(_f32)


def sample_bits(
    img: np.ndarray,
    positions: np.ndarray,
    cutlevels: np.ndarray,
    geom: Geometry,
    fmt: PageFormat,
    opts: DecodeOptions,
) -> np.ndarray:
    """Raw channel bits (uint8 0/1, 1 = dark) for every position in channel_xy order."""
    xs, ys = channel_xy(fmt)
    cutlevels = np.asarray(cutlevels, _f32)
    bits = np.empty(xs.size, np.uint8)
    for start in range(0, xs.size, CHUNK):
        x = xs[start : start + CHUNK].astype(np.int64)
        y = ys[start : start + CHUNK].astype(np.int64)
        xd, yd, cut = _bit_coord(x, y, positions, cutlevels, fmt)
        val = _correct_sample(img, xd, yd, geom, opts)
        bits[start : start + CHUNK] = val < cut
    return bits
