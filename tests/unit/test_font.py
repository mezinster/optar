# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import re
from pathlib import Path

import numpy as np

from optar.font import glyph_strip, label_text, render_label
from optar.format import PageFormat

F = PageFormat(65, 93)


def test_strip_matches_font_h():
    src = Path(__file__).parents[2].joinpath("font.h").read_text(errors="replace")
    cmap_txt = src[src.index("header_data_cmap[256][3]") : src.index("header_data[36000]")]
    cmap = [int(m) for m in re.findall(r"\{\s*(-?\d+),", cmap_txt)]
    cmap += [0] * (256 - len(cmap))
    body = src[src.index("header_data[36000]") :]
    data = np.array([int(m) for m in re.findall(r"-?\d+", body[body.index("{") :])][:36000])
    expect = np.where(np.array(cmap)[data % 256] & 0x80, 255, 0).reshape(24, 1500)
    assert np.array_equal(glyph_strip(), expect)


def test_label_text():
    assert label_text(F, 1, 2, "name") == "  0-65-93-24-3-1-2-24 1/2 name"
    assert len(label_text(F, 1, 2, "x" * 500)) == F.data_width // 13 - 1


def test_render_label_shape_and_odd_characters():
    img = render_label(F, label_text(F, 1, 1, "naïve ☃ ok"))
    assert img.shape == (24, F.data_width) and set(np.unique(img)) <= {0, 255}
    assert np.array_equal(img, render_label(F, label_text(F, 1, 1, "nave  ok")))


def test_logo_then_first_glyph_placement():
    strip = glyph_strip()
    img = render_label(F, "  ")
    assert np.array_equal(img[:, :265], strip[:, 1235:])
    assert np.array_equal(img[:, 265:278], strip[:, :13])
    assert not img[:, 291:].any()
