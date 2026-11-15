# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Cross synchronisation: sync_crosses and its helpers (unoptar.c).

Ports get_pixel_interp, load_search_area, integrate_search_area,
cross_correl_search, cross_correl, resync_cross, cross_stats and
sync_crosses. Float widths follow C: pixel interpolation, the search area,
the correlation sums and the per-cross cut levels are 32-bit floats; the
cross coordinates and the pitch vectors are doubles.

The crosses are visited one by one (each estimate comes from an already
resynced neighbour); the work inside one cross is vectorised.
"""

from __future__ import annotations

import math

import numpy as np

from optar.decoder.geometry import Geometry
from optar.decoder.levels import Levels
from optar.decoder.options import DecodeOptions
from optar.format import PageFormat

FINESTEP = 0.25  # fine cross search step, in input pixels
HALFRANGE = int(0.5 / FINESTEP)  # fine search covers -0.5..0.5 input pixel

_f32 = np.float32


def interp(img: np.ndarray, x, y) -> np.ndarray:
    """get_pixel_interp for arrays of coordinates (integers at pixel centres).

    A negative coordinate has integer part 0 and is extrapolated; neighbours
    outside the image read as 255. Returns float32 of the coordinates' shape.
    """
    h, w = img.shape
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    xf = np.where(x < 0, 0.0, np.floor(x))
    yf = np.where(y < 0, 0.0, np.floor(y))
    hpar = (x - xf).astype(_f32)
    vpar = (y - yf).astype(_f32)
    # Indices at or past the edge all read as white; clamp before casting.
    xi = np.minimum(xf, w).astype(np.intp)
    yi = np.minimum(yf, h).astype(np.intp)
    xi1 = xi + 1
    yi1 = yi + 1

    def pix(xs, ys):
        inside = (xs < w) & (ys < h)
        v = img[np.minimum(ys, h - 1), np.minimum(xs, w - 1)]
        return np.where(inside, v, 255).astype(_f32)

    ul, ur, ll, lr = pix(xi, yi), pix(xi1, yi), pix(xi, yi1), pix(xi1, yi1)
    one = _f32(1)
    u = ur * hpar + ul * (one - hpar)
    lo = lr * hpar + ll * (one - hpar)
    return (lo * vpar + u * (one - vpar)).astype(_f32, copy=False)


def _first_max(values: np.ndarray, start: int) -> int:
    """Index C's `if (result > max)` scan ends on, preloaded with values[start]."""
    best = int(np.argmax(values))
    return best if values[best] > values[start] else start


class _CrossSync:
    """Per-page constants and the per-cross search (resync_cross, cross_stats)."""

    def __init__(self, img, geom: Geometry, fmt: PageFormat, levels: Levels, opts):
        self.img = img
        self.cut = levels.cut
        self.cut32 = _f32(levels.cut)
        phx, phy = geom.ph
        pvx, pvy = geom.pv
        c = geom.chalf
        self.chalf = c

        # load_search_area: rows yoff, columns xoff, -2c..2c-1 (plus a zero
        # row and column in front). PSHIFT(x, xoff, yoff) = x + xoff*ph + yoff*pv.
        offs = np.arange(-2 * c, 2 * c, dtype=np.float64)
        yo, xo = np.meshgrid(offs, offs, indexing="ij")
        self.area_hx, self.area_vx = xo * phx, yo * pvx
        self.area_hy, self.area_vy = xo * phy, yo * pvy
        self.area = np.zeros((4 * c + 1, 4 * c + 1), _f32)

        # cross_correl_search: offsets -c..c, x outer, y inner.
        co = np.arange(-c, c + 1)
        cxo, cyo = (a.ravel() for a in np.meshgrid(co, co, indexing="ij"))
        self.coarse_x = cxo.astype(np.float64)
        self.coarse_y = cyo.astype(np.float64)
        self.coarse_start = int(np.flatnonzero((cxo == 0) & (cyo == 0))[0])
        self.coarse_ix = cxo + 2 * c  # array columns
        self.coarse_iy = cyo + 2 * c  # array rows

        # Fine search: offsets -HALFRANGE..HALFRANGE steps of FINESTEP.
        fo = np.arange(-HALFRANGE, HALFRANGE + 1)
        fxo, fyo = (a.ravel() * FINESTEP for a in np.meshgrid(fo, fo, indexing="ij"))
        self.fine_hx, self.fine_vx = fxo * phx, fyo * pvx
        self.fine_hy, self.fine_vy = fxo * phy, fyo * pvy
        self.fine_xo, self.fine_yo = fxo, fyo
        self.fine_start = int(np.flatnonzero((fxo == 0) & (fyo == 0))[0])

        # cross_correl: dx outer, dy inner, then the four terms in C order.
        cf = max(geom.chalf_fine, 0)
        d = np.arange(cf, dtype=np.float64)
        self.corr_dx = d[None, :, None]
        self.corr_dy = d[None, None, :]
        self.corr_n = 4 * cf * cf
        self.corr_sign = np.array([-1, -1, 1, 1], _f32)

        # cross_stats: xoff outer, yoff inner, integer offsets.
        hh = math.floor(geom.hpixel * (fmt.chalf - opts.cross_trim))
        vh = math.floor(geom.vpixel * (fmt.chalf - opts.cross_trim))
        sxo, syo = np.meshgrid(
            np.arange(-hh, hh + 1, dtype=np.float64),
            np.arange(-vh, vh + 1, dtype=np.float64),
            indexing="ij",
        )
        sxo, syo = sxo.ravel(), syo.ravel()
        self.stats_hx, self.stats_vx = sxo * phx, syo * pvx
        self.stats_hy, self.stats_vy = sxo * phy, syo * pvy
        self.white_cut = _f32(opts.white_cut)
        self.black_cut = _f32(_f32(1) - self.white_cut)
        self.ph, self.pv = (phx, phy), (pvx, pvy)

    def _diffpix(self, x, y):
        return interp(self.img, x, y) - self.cut32

    def _coarse(self, x: float, y: float) -> int:
        """load_search_area, integrate_search_area and the 1-pixel search."""
        c = self.chalf
        a = self.area
        a[1:, 1:] = self._diffpix(
            (x + self.area_hx) + self.area_vx, (y + self.area_hy) + self.area_vy
        )
        s = np.cumsum(np.cumsum(a, axis=1, dtype=_f32), axis=0, dtype=_f32)
        ix, iy = self.coarse_ix, self.coarse_iy
        two = _f32(2)
        total = _f32(-4) * s[iy, ix]
        sides = ((s[iy, ix - c] + s[iy, ix + c]) + s[iy - c, ix]) + s[iy + c, ix]
        total = total + two * sides
        corners = ((s[iy - c, ix - c] + s[iy + c, ix - c]) + s[iy - c, ix + c]) + s[iy + c, ix + c]
        total = total - corners
        return _first_max(total, self.coarse_start)

    def _fine_sums(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """cross_correl at each of the (n,) centres, summed in C's order in float32."""
        n = x.size
        if self.corr_n == 0:
            return np.zeros(n, _f32)
        xa = x[:, None, None] + self.corr_dx
        xb = (x[:, None, None] - 1) - self.corr_dx
        ya = y[:, None, None] + self.corr_dy
        yb = (y[:, None, None] - 1) - self.corr_dy
        shape = np.broadcast_shapes(xa.shape, ya.shape)
        xs = np.stack([np.broadcast_to(v, shape) for v in (xa, xb, xa, xb)], axis=-1)
        ys = np.stack([np.broadcast_to(v, shape) for v in (ya, yb, yb, ya)], axis=-1)
        terms = self._diffpix(xs, ys) * self.corr_sign
        return np.cumsum(terms.reshape(n, self.corr_n), axis=1, dtype=_f32)[:, -1]

    def resync(self, x: float, y: float) -> tuple[float, float]:
        phx, phy = self.ph
        pvx, pvy = self.pv
        k = self._coarse(x, y)
        xo, yo = self.coarse_x[k], self.coarse_y[k]
        xmax = x + xo * phx + yo * pvx
        ymax = y + xo * phy + yo * pvy

        sums = self._fine_sums(
            (xmax + self.fine_hx) + self.fine_vx, (ymax + self.fine_hy) + self.fine_vy
        )
        k = _first_max(sums, self.fine_start)
        xo, yo = self.fine_xo[k], self.fine_yo[k]
        return xmax + xo * phx + yo * pvx, ymax + xo * phy + yo * pvy

    def stats(self, x: float, y: float) -> np.float32:
        """cross_stats: this cross's cut level."""
        vals = interp(
            self.img, (x + self.stats_hx) + self.stats_vx, (y + self.stats_hy) + self.stats_vy
        ).astype(np.int64)  # C assigns the float to a long: truncation
        d = vals - self.cut
        sq = (d * d).astype(_f32)
        white, black = d > 0, d < 0
        nwhite, nblack = int(white.sum()), int(black.sum())
        if not (nwhite and nblack):
            return self.cut32
        zero = _f32(0)
        white_rms = np.cumsum(np.where(white, sq, zero), dtype=_f32)[-1]
        black_rms = np.cumsum(np.where(black, sq, zero), dtype=_f32)[-1]
        white_rms = _f32(math.sqrt(float(_f32(white_rms / _f32(nwhite)))))
        black_rms = _f32(math.sqrt(float(_f32(black_rms / _f32(nblack)))))
        white_level = _f32(self.cut32 + white_rms)
        black_level = _f32(self.cut32 - black_rms)
        return _f32(_f32(white_level * self.white_cut) + _f32(black_level * self.black_cut))


def _bilinear(ul: float, ur: float, ll: float, lr: float, hpar: float, vpar: float) -> float:
    u = ur * hpar + ul * (1 - hpar)
    lo = lr * hpar + ll * (1 - hpar)
    return lo * vpar + u * (1 - vpar)


def sync_crosses(
    img: np.ndarray, geom: Geometry, fmt: PageFormat, levels: Levels, opts: DecodeOptions
) -> tuple[np.ndarray, np.ndarray]:
    """Cross centres (xcrosses, ycrosses, 2) float64, integers at pixel corners,
    and per-cross cut levels (xcrosses, ycrosses) float32."""
    c = [(float(x), float(y)) for x, y in geom.corners]
    rightx = (c[1][0] + c[3][0] - c[0][0] - c[2][0]) / 2 * fmt.cpitch / fmt.width
    righty = (c[1][1] + c[3][1] - c[0][1] - c[2][1]) / 2 * fmt.cpitch / fmt.width
    downx = (c[2][0] + c[3][0] - c[0][0] - c[1][0]) / 2 * fmt.cpitch / fmt.height
    downy = (c[2][1] + c[3][1] - c[0][1] - c[1][1]) / 2 * fmt.cpitch / fmt.height
    hpar = (fmt.border + fmt.chalf) / fmt.width
    vpar = (fmt.border + fmt.chalf) / fmt.height

    sync = _CrossSync(img, geom, fmt, levels, opts)
    positions = np.zeros((fmt.xcrosses, fmt.ycrosses, 2), np.float64)
    cutlevels = np.zeros((fmt.xcrosses, fmt.ycrosses), np.float32)
    x = _bilinear(c[0][0], c[1][0], c[2][0], c[3][0], hpar, vpar)
    y = _bilinear(c[0][1], c[1][1], c[2][1], c[3][1], hpar, vpar)
    for cy in range(fmt.ycrosses):
        for cx in range(fmt.xcrosses):
            if cx > 0:
                x, y = positions[cx - 1, cy]
                x, y = x + rightx, y + righty
            elif cy > 0:
                x, y = positions[cx, cy - 1]
                x, y = x + downx, y + downy
            x, y = sync.resync(float(x), float(y))
            positions[cx, cy] = x, y
            cutlevels[cx, cy] = sync.stats(x, y)
    return positions, cutlevels
