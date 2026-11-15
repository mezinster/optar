# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import struct
import warnings

import numpy as np
import pytest
from PIL import Image, PngImagePlugin

import optar.imageio
from optar.errors import OptarError
from optar.imageio import pgm_bytes, read_scan, write_pgm, write_png


def gradient():
    return np.tile(np.arange(256, dtype=np.uint8), (4, 1))


def test_pgm_bytes():
    px = np.array([[0, 255, 7], [1, 2, 3]], dtype=np.uint8)
    assert pgm_bytes(px) == b"P5\n3 2\n255\n" + bytes([0, 255, 7, 1, 2, 3])


def test_write_pgm(tmp_path):
    px = np.array([[0, 255, 7], [1, 2, 3]], dtype=np.uint8)
    write_pgm(tmp_path / "a.pgm", px)
    assert (tmp_path / "a.pgm").read_bytes() == pgm_bytes(px)


def test_png_is_one_bit_at_200_ppi(tmp_path):
    px = (np.indices((5, 9)).sum(0) % 2 * 255).astype(np.uint8)
    write_png(tmp_path / "p.png", px)
    im = Image.open(tmp_path / "p.png")
    assert im.mode == "1" and [round(v) for v in im.info["dpi"]] == [200, 200]
    assert np.array_equal(np.array(im.convert("L")), px)


def test_read_scan_linearises_with_default_gamma(tmp_path):
    Image.fromarray(gradient()).save(tmp_path / "g.png")
    out = read_scan(tmp_path / "g.png")
    v = np.arange(256)
    assert out.dtype == np.uint8 and out.shape == (4, 256)
    assert np.array_equal(
        out[0], np.floor(255 * (v / 255) ** (1 / 0.454545) + 0.5).astype(np.uint8)
    )
    assert out[0, 0] == 0 and out[0, 255] == 255


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "I;16", "P"])
def test_colour_and_deep_scans_match_gray(tmp_path, mode):
    g = Image.fromarray(gradient())
    g.save(tmp_path / "g.png")
    if mode == "I;16":
        im = Image.fromarray(gradient().astype(np.uint16) * 257)
    else:
        im = g.convert(mode)
    im.save(tmp_path / "c.png")
    a = read_scan(tmp_path / "g.png").astype(int)
    b = read_scan(tmp_path / "c.png").astype(int)
    assert np.abs(a - b).max() <= 1


def test_unreadable_file(tmp_path):
    from optar.errors import OptarError

    (tmp_path / "x.png").write_bytes(b"not an image")
    with pytest.raises(OptarError):
        read_scan(tmp_path / "x.png")


def test_colour_pixels_use_libpng_weights_after_linearisation(tmp_path):
    rgb = np.array([[[255, 0, 0], [0, 255, 0], [192, 0, 0], [255, 255, 255]]], np.uint8)
    Image.fromarray(rgb).save(tmp_path / "c.png")
    # Linearised 255 stays 255 and 192 becomes 137 (255 * (192/255)**2.2 + 0.5,
    # floored); then 255 * 0.212671 = 54.2, 255 * 0.715160 = 182.4,
    # 137 * 0.212671 = 29.1, each rounded half up.
    assert read_scan(tmp_path / "c.png").tolist() == [[54, 182, 29, 255]]


def test_sixteen_bit_scan_uses_high_byte(tmp_path):
    # 0xC0F0: high byte 192 (linear 137); rounding the 16-bit value to 8 bits
    # would give 193 (linear 138) instead.
    Image.fromarray(np.array([[0xC0F0, 0xFFFF]], np.uint16)).save(tmp_path / "d.png")
    assert read_scan(tmp_path / "d.png").tolist() == [[137, 255]]


def test_gamma_one_png_is_unchanged(tmp_path):
    info = PngImagePlugin.PngInfo()
    info.add(b"gAMA", struct.pack(">I", 100000))  # file gamma 1.0
    Image.fromarray(gradient()).save(tmp_path / "g.png", pnginfo=info)
    with Image.open(tmp_path / "g.png") as im:
        assert im.info["gamma"] == 1.0
    assert np.array_equal(read_scan(tmp_path / "g.png"), gradient())


@pytest.mark.slow  # about 350 MB peak
def test_large_scan_reads_without_decompression_bomb_warning(tmp_path):
    # 95 megapixels: above Pillow's default warning threshold (about 89.5).
    height, width = 10000, 9500
    assert height * width > Image.MAX_IMAGE_PIXELS
    Image.new("1", (width, height), 1).save(tmp_path / "big.png")
    limit = Image.MAX_IMAGE_PIXELS
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = read_scan(tmp_path / "big.png")
    assert out.shape == (height, width) and out[0, 0] == 255
    assert Image.MAX_IMAGE_PIXELS == limit  # global Pillow state restored


def test_scan_above_pixel_limit_is_refused(tmp_path, monkeypatch):
    Image.fromarray(gradient()).save(tmp_path / "g.png")
    monkeypatch.setattr(optar.imageio, "MAX_SCAN_PIXELS", 1000)
    limit = Image.MAX_IMAGE_PIXELS
    with pytest.raises(OptarError, match="1,024 pixels.*1,000"):
        read_scan(tmp_path / "g.png")
    assert Image.MAX_IMAGE_PIXELS == limit
