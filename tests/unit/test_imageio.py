# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import numpy as np
import pytest
from PIL import Image

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
