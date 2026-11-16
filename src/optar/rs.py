# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Reed-Solomon codes over GF(256) with errors and erasures, vectorised over rows.

Field polynomial 0x11D, primitive element alpha = 2, generator roots
alpha^0 .. alpha^(parity-1). A codeword is 255 bytes: data, then parity.
Byte i of a codeword is the coefficient of x^(254-i).

Every linear map (parity, syndromes, polynomial evaluation at all 255
positions) is a table lookup per input byte, XORed together eight output
bytes at a time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from optar.format import CODEWORD as _N

# exp[k] = alpha^k for 0 <= k < 510; log[0] is a sentinel so that any sum of
# logs involving zero lands in the zero tail of exp.
_ZERO_LOG = 510
_EXP = np.zeros(2 * _ZERO_LOG + 1, dtype=np.uint8)
_LOG = np.zeros(256, dtype=np.int16)


def _build_field() -> None:
    x = 1
    for k in range(255):
        _EXP[k] = x
        _LOG[x] = k
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    _EXP[255:510] = _EXP[:255]
    _LOG[0] = _ZERO_LOG


_build_field()


def _mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return _EXP[_LOG[a] + _LOG[b]]


def _inv(a: np.ndarray) -> np.ndarray:
    """Inverse of nonzero elements; 0 maps to 0."""
    return np.where(a == 0, 0, _EXP[(255 - _LOG[a]) % 255]).astype(np.uint8)


def _alpha_pow(k: np.ndarray) -> np.ndarray:
    return _EXP[np.mod(k, 255)]


def _table(matrix: np.ndarray) -> np.ndarray:
    """Lookup table of a GF-linear map: out = XOR_a matrix[a] * x[a].

    Returns uint64 (n_in, 256, ceil(n_out/8)): row [a, v] is v * matrix[a]
    packed eight bytes per word.
    """
    n_in, n_out = matrix.shape
    pad = -n_out % 8
    out = np.zeros((n_in, 256, n_out + pad), dtype=np.uint8)
    values = np.arange(256)
    for a in range(n_in):
        out[a, :, :n_out] = _mul(values[:, None], matrix[a][None, :])
    return out.view(np.uint64)


def _apply(table: np.ndarray, x: np.ndarray, n_out: int) -> np.ndarray:
    """Apply a table from _table to rows x uint8 (R, n_in) -> uint8 (R, n_out)."""
    acc = np.zeros((x.shape[0], table.shape[2]), dtype=np.uint64)
    for a in range(x.shape[1]):
        acc ^= table[a, x[:, a]]
    return acc.view(np.uint8)[:, :n_out]


def _bytes(x, what: str) -> np.ndarray:
    """x as a uint8 array; any other dtype is refused rather than wrapped."""
    x = np.asarray(x)
    if x.dtype != np.uint8:
        raise ValueError(f"{what} must be a uint8 array, not {x.dtype}")
    return x


@dataclass(frozen=True)
class RSResult:
    words: np.ndarray  # corrected codewords (w, 255); rows that failed are returned as received
    ok: np.ndarray  # bool (w,)
    # int (w,): bytes changed at places not marked erased. A failed row
    # reports 0: its errors are unknown, so 0 does not mean clean.
    errors: np.ndarray
    erasures: np.ndarray  # int (w,): bytes marked erased (whether or not their value changed)


class RSCode:
    """A systematic (255, 255 - parity) Reed-Solomon code."""

    _SYNDROME_CHUNK = 65536
    _SOLVER_CHUNK = 4096

    def __init__(self, parity: int):
        if not 1 <= parity <= _N - 1:
            raise ValueError(f"parity must be 1 to {_N - 1}, not {parity}")
        self.parity = parity
        self.k = _N - parity
        self._encode_table: np.ndarray | None = None
        self._syndrome_table: np.ndarray | None = None
        self._eval_table: np.ndarray | None = None

    # Tables are built on first use.

    def _encoder(self) -> np.ndarray:
        if self._encode_table is None:
            p = self.parity
            # Generator, lowest degree first.
            g = np.zeros(p + 1, dtype=np.uint8)
            g[0] = 1
            for j in range(p):
                root = _EXP[j]
                shifted = np.concatenate([[0], g[:-1]]).astype(np.uint8)
                g = shifted ^ _mul(g, root)
            # rem[m] = x^m mod g as p coefficients, highest degree first.
            rows = np.zeros((_N, p), dtype=np.uint8)
            rem = g[:p][::-1].copy()  # x^p = g_low (characteristic 2)
            rows[p] = rem
            for m in range(p + 1, _N):
                top = rem[0]
                rem = np.concatenate([rem[1:], [0]]).astype(np.uint8)
                rem ^= _mul(top, g[:p][::-1])
                rows[m] = rem
            # Data byte i is the coefficient of x^(254 - i).
            self._encode_table = _table(rows[_N - 1 - np.arange(self.k)])
        return self._encode_table

    def _syndromes(self, words: np.ndarray) -> np.ndarray:
        if self._syndrome_table is None:
            powers = (_N - 1 - np.arange(_N))[:, None] * np.arange(self.parity)[None, :]
            self._syndrome_table = _table(_alpha_pow(powers))
        out = np.empty((words.shape[0], self.parity), dtype=np.uint8)
        for start in range(0, words.shape[0], self._SYNDROME_CHUNK):
            part = words[start : start + self._SYNDROME_CHUNK]
            out[start : start + len(part)] = _apply(self._syndrome_table, part, self.parity)
        return out

    def _evaluate(self, poly: np.ndarray) -> np.ndarray:
        """poly (R, d <= parity+1), lowest degree first -> values at X_i^-1 for all i."""
        if self._eval_table is None:
            powers = -np.arange(self.parity + 1)[:, None] * (_N - 1 - np.arange(_N))[None, :]
            self._eval_table = _table(_alpha_pow(powers))
        return _apply(self._eval_table, poly, _N)

    def encode(self, data: np.ndarray) -> np.ndarray:
        """data uint8 (w, k) -> parity uint8 (w, parity).

        Systematic: the codeword is the data, then the parity.
        """
        data = _bytes(data, "data")
        if data.ndim != 2 or data.shape[1] != self.k:
            raise ValueError(f"data must have shape (w, {self.k}), not {data.shape}")
        return _apply(self._encoder(), data, self.parity).copy()

    def decode(self, words: np.ndarray, erased: np.ndarray | None = None) -> RSResult:
        """words uint8 (w, 255); erased bool (w, 255), True where the byte is known bad."""
        words = _bytes(words, "words")
        if words.ndim != 2 or words.shape[1] != _N:
            raise ValueError(f"words must have shape (w, {_N}), not {words.shape}")
        if erased is None:
            erased = np.zeros(words.shape, dtype=bool)
        else:
            erased = np.asarray(erased, dtype=bool)
            if erased.shape != words.shape:
                raise ValueError("erased must have the same shape as words")
        w = words.shape[0]
        out = words.copy()
        ok = np.ones(w, dtype=bool)
        errors = np.zeros(w, dtype=np.int64)
        erasures = erased.sum(axis=1).astype(np.int64)

        syndromes = self._syndromes(words)
        damaged = np.flatnonzero(syndromes.any(axis=1) | (erasures > 0))
        too_many = erasures[damaged] > self.parity
        ok[damaged[too_many]] = False
        damaged = damaged[~too_many]
        for start in range(0, len(damaged), self._SOLVER_CHUNK):
            rows = damaged[start : start + self._SOLVER_CHUNK]
            fixed, row_ok, row_errors = self._solve(
                words[rows], erased[rows], syndromes[rows], erasures[rows]
            )
            out[rows] = np.where(row_ok[:, None], fixed, words[rows])
            ok[rows] = row_ok
            errors[rows] = np.where(row_ok, row_errors, 0)
        return RSResult(words=out, ok=ok, errors=errors, erasures=erasures)

    def _solve(self, words, erased, s, e):
        """Errors-and-erasures decoding of rows with nonzero syndromes or erasures.

        Berlekamp-Massey started from the erasure locator, Chien search over
        all positions, Forney for the values. Returns (corrected, ok, errors).
        """
        p = self.parity
        r = words.shape[0]
        # Erasure locator Gamma(x) = prod (1 - X x), X = alpha^(254 - position).
        order = np.argsort(~erased, axis=1, kind="stable")[:, :p]
        gamma = np.zeros((r, p + 1), dtype=np.uint8)
        gamma[:, 0] = 1
        for k in range(int(e.max())):
            x = _alpha_pow(_N - 1 - order[:, k])
            step = _mul(x[:, None], gamma[:, :-1])
            step[k >= e] = 0
            gamma[:, 1:] ^= step

        # Berlekamp-Massey (Blahut's form) with erasures: L starts at e and
        # the steps for n < e are skipped.
        lam = gamma.copy()
        b = gamma.copy()
        length = e.copy()
        for n in range(p):
            d = np.bitwise_xor.reduce(_mul(lam[:, : n + 1], s[:, n::-1]), axis=1)
            in_range = n >= e
            active = in_range & (d != 0)
            change = active & (2 * length <= n + e)
            xb = np.zeros_like(b)
            xb[:, 1:] = b[:, :-1]
            new_lam = np.where(active[:, None], lam ^ _mul(d[:, None], xb), lam)
            b = np.where(
                change[:, None],
                _mul(_inv(d)[:, None], lam),
                np.where(in_range[:, None], xb, b),
            )
            length = np.where(change, n + 1 - length + e, length)
            lam = new_lam

        # Chien search: roots of Lambda at X_i^-1.
        roots = self._evaluate(lam) == 0
        consistent = roots.sum(axis=1) == length

        # Omega = S * Lambda mod x^p, and the formal derivative of Lambda.
        omega = np.zeros((r, p), dtype=np.uint8)
        for j in range(int(length.max()) + 1):
            omega[:, j:] ^= _mul(lam[:, j : j + 1], s[:, : p - j])
        deriv = np.zeros((r, p + 1), dtype=np.uint8)
        deriv[:, 0:p:2] = lam[:, 1 : p + 1 : 2]
        omega_full = np.zeros((r, p + 1), dtype=np.uint8)
        omega_full[:, :p] = omega
        num = self._evaluate(omega_full)
        den = self._evaluate(deriv)
        # Forney with first root alpha^0: e = X * Omega(X^-1) / Lambda'(X^-1).
        x_all = _alpha_pow(_N - 1 - np.arange(_N))[None, :]
        values = _mul(x_all, _mul(num, _inv(den)))
        consistent &= ~(roots & (den == 0)).any(axis=1)
        fixed = words ^ np.where(roots, values, 0).astype(np.uint8)

        row_errors = ((fixed != words) & ~erased).sum(axis=1)
        clean = ~self._syndromes(fixed).any(axis=1)
        row_ok = consistent & clean & (2 * row_errors + e <= p)
        return fixed, row_ok, row_errors
