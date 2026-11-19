# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Reading and writing page and scan images."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

import numpy as np
from PIL import Image, UnidentifiedImageError

from .errors import Alternatives, Grouped, OptarError, error
from .format import PIXELS_PER_INCH

DEFAULT_FILE_GAMMA = 0.454545
# Largest scan read_scan accepts: a 2400 dpi A4 or Letter scan is about 560
# megapixels. Pillow's own decompression-bomb limit (about 179 megapixels,
# warning above 89) would refuse or warn about ordinary 1200 dpi scans.
MAX_SCAN_PIXELS = 600_000_000
# Image.MAX_IMAGE_PIXELS is process-wide; it is lifted only while Image.open runs.
_OPEN_LOCK = threading.Lock()
# Formats read_scan opens (PPM covers PGM and PBM). JPEG is lossy, a poor choice
# for scans, but users will try it.
SCAN_FORMATS = ("PNG", "TIFF", "BMP", "PPM", "JPEG")
_GRAY_WEIGHTS = (0.212671, 0.715160, 0.072169)


def pgm_bytes(pixels: np.ndarray) -> bytes:
    """Binary PGM (P5) encoding of an 8-bit page, as dump_ary in optar.c."""
    height, width = pixels.shape
    header = b"P5\n%d %d\n255\n" % (width, height)
    return header + np.ascontiguousarray(pixels, dtype=np.uint8).tobytes()


def write_pgm(path, pixels: np.ndarray) -> None:
    with open(path, "wb") as f:
        f.write(pgm_bytes(pixels))


def write_png(path, pixels: np.ndarray, pixels_per_inch=PIXELS_PER_INCH) -> None:
    """Write a page (values 0 and 255 only) as a lossless 1-bit PNG."""
    im = Image.fromarray(np.ascontiguousarray(pixels, dtype=np.uint8) != 0)
    im = im.convert("1")
    dpi = (float(pixels_per_inch), float(pixels_per_inch))
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


def _accepted_formats() -> Alternatives:
    return Alternatives({"PPM": "PGM/PPM"}.get(f, f) for f in SCAN_FORMATS)


@contextmanager
def scan_pixel_limit() -> Iterator[None]:
    """Lets Pillow open images of up to MAX_SCAN_PIXELS while the block runs.

    For code that opens scans with Pillow itself (to show one, say). The limit is
    process-wide, so the block holds the lock read_scan takes: reads in other
    threads wait meanwhile and never see the raised limit. Keep the block short:
    open the image (and, for formats other than PNG, load it) inside it. The lock
    is not reentrant: calling read_scan (or entering this block again) inside the
    block deadlocks.
    """
    with _OPEN_LOCK:
        pillow_limit = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_SCAN_PIXELS
        try:
            yield
        finally:
            Image.MAX_IMAGE_PIXELS = pillow_limit


def read_scan(path) -> np.ndarray:
    """Load a scan as 8-bit gray in linear light, like read_png in unoptar.c."""
    # Pillow's size check runs inside Image.open for PNG, but other plugins
    # (TIFF, ...) repeat it while loading. So PNG releases the lock right after
    # open; every other format keeps the limit set to the cap and the lock held
    # until its pixels are loaded and converted.
    held = True
    _OPEN_LOCK.acquire()
    pillow_limit = Image.MAX_IMAGE_PIXELS
    # Never None: our own check refuses above the cap from the header size, and
    # Pillow's check (warning above the cap, error above twice it) stays as a
    # backstop for images that grow while loading.
    Image.MAX_IMAGE_PIXELS = MAX_SCAN_PIXELS

    def release() -> None:
        nonlocal held
        if held:
            held = False
            Image.MAX_IMAGE_PIXELS = pillow_limit
            _OPEN_LOCK.release()

    try:
        with Image.open(path, formats=SCAN_FORMATS) as im:
            if im.format == "PNG":
                release()
            pixels = im.width * im.height
            if pixels > MAX_SCAN_PIXELS:
                raise error(
                    OptarError, "err.image_too_large",
                    "cannot read image {path}: {pixels} pixels is more than the {limit} a "
                    "scan may have",
                    path=path, pixels=Grouped(pixels), limit=Grouped(MAX_SCAN_PIXELS),
                )
            checked_pixels = pixels
            im.load()
            if im.width * im.height > MAX_SCAN_PIXELS:
                raise error(
                    OptarError, "err.image_too_large",
                    "cannot read image {path}: {pixels} pixels is more than the {limit} a "
                    "scan may have",
                    path=path, pixels=Grouped(im.width * im.height),
                    limit=Grouped(MAX_SCAN_PIXELS),
                )
            if im.width * im.height != checked_pixels:  # a transpose keeps the count
                raise error(
                    OptarError, "err.image_size_changed",
                    "cannot read image {path}: image size changed while loading", path=path,
                )
            file_gamma = im.info.get("gamma") or DEFAULT_FILE_GAMMA
            data, is_colour = _to_gray8(im)
    except UnidentifiedImageError as e:
        raise error(
            OptarError, "err.not_an_image", "cannot read image {path}: not a {formats} image",
            path=path, formats=_accepted_formats(),
        ) from e
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        raise error(
            OptarError, "err.image_unreadable", "cannot read image {path}: {reason}",
            path=path, reason=str(e),
        ) from e
    finally:
        release()
    table = _gamma_table(float(file_gamma))
    lin = table[data]
    if not is_colour:
        return lin
    r, g, b = _GRAY_WEIGHTS
    gray = lin[..., 0] * np.float32(r)
    gray += lin[..., 1] * np.float32(g)
    gray += lin[..., 2] * np.float32(b)
    return np.floor(gray + np.float32(0.5)).astype(np.uint8)
