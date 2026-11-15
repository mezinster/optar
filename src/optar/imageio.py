# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Reading and writing page and scan images."""

import numpy as np
from PIL import Image

from .errors import OptarError
from .format import PIXELS_PER_INCH

DEFAULT_FILE_GAMMA = 0.454545
_GRAY_WEIGHTS = (0.212671, 0.715160, 0.072169)


def pgm_bytes(pixels: np.ndarray) -> bytes:
    """Binary PGM (P5) encoding of an 8-bit page, as dump_ary in optar.c."""
    height, width = pixels.shape
    header = b"P5\n%d %d\n255\n" % (width, height)
    return header + np.ascontiguousarray(pixels, dtype=np.uint8).tobytes()


def write_pgm(path, pixels: np.ndarray) -> None:
    with open(path, "wb") as f:
        f.write(pgm_bytes(pixels))


def write_png(path, pixels: np.ndarray) -> None:
    """Write a page (values 0 and 255 only) as a lossless 1-bit PNG."""
    im = Image.fromarray(np.ascontiguousarray(pixels, dtype=np.uint8) != 0)
    im = im.convert("1")
    dpi = (PIXELS_PER_INCH, PIXELS_PER_INCH)
    im.save(path, format="PNG", dpi=dpi)


def _gamma_table(file_gamma: float) -> np.ndarray:
    v = np.arange(256, dtype=np.float64)
    exponent = 1.0 / file_gamma
    return np.floor(255.0 * (v / 255.0) ** exponent + 0.5).astype(np.uint8)


def _to_gray8(im: Image.Image) -> tuple[np.ndarray, bool]:
    """Return (array, is_colour): 8-bit gray (H, W) or RGB (H, W, 3)."""
    mode = im.mode
    if mode in ("1", "L"):
        return np.asarray(im.convert("L")), False  # 1-bit expands to 0/255
    if mode in ("I;16", "I;16L", "I;16B", "I;16N", "I"):
        a = np.asarray(im)
        if mode == "I":  # Pillow reads 16-bit gray PNG as "I"
            a = np.clip(a, 0, 65535)
        return (a.astype(np.uint32) >> 8).astype(np.uint8), False
    if mode in ("LA", "La"):
        return np.asarray(im.convert("L")), False
    if mode == "PA":
        im = im.convert("RGBA")
    return np.asarray(im.convert("RGB")), True


def read_scan(path) -> np.ndarray:
    """Load a scan as 8-bit gray in linear light, like read_png in unoptar.c."""
    try:
        with Image.open(path) as im:
            im.load()
            file_gamma = im.info.get("gamma") or DEFAULT_FILE_GAMMA
            data, is_colour = _to_gray8(im)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        raise OptarError(f"cannot read image {path}: {e}") from e
    table = _gamma_table(float(file_gamma))
    lin = table[data]
    if not is_colour:
        return lin
    r, g, b = _GRAY_WEIGHTS
    gray = lin[..., 0] * np.float32(r)
    gray += lin[..., 1] * np.float32(g)
    gray += lin[..., 2] * np.float32(b)
    return np.floor(gray + np.float32(0.5)).astype(np.uint8)
