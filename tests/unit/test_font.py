# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import re
from pathlib import Path

import numpy as np

from optar.font import fine_label, glyph_strip, label_text, render_label, render_line
from optar.format import PageFormat, get_layout

F = PageFormat(65, 93)


def test_strip_matches_font_h():
    src = Path(__file__).parents[2].joinpath("lega-c", "font.h").read_text(errors="replace")
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


def test_fine_label_is_the_standard_size_line_across_the_band():
    name = "a-long-file-name-that-the-large-dots-cut-off.pdf"
    layout = get_layout("a4", "large")
    fmt = layout.fmt
    strip = fine_label(layout, 3, 33, name)
    # Large dots are twice the standard size, so the band holds twice the pixels.
    assert strip.shape == (24, fmt.data_width * 2)
    text = f"  {fmt.to_string()} 3/33 {name}"
    assert label_text(fmt, 3, 33, name) != text  # the page's own label cuts it
    assert label_text(fmt, 3, 33, name, strip.shape[1]) == text
    assert np.array_equal(strip, render_line(text, strip.shape[1]))
    # The same glyphs as a page's own label, pixel for pixel.
    own = render_label(fmt, label_text(fmt, 3, 33, name))
    assert np.array_equal(strip[:, : fmt.data_width - 13], own[:, : fmt.data_width - 13])


def test_fine_label_width_is_whole_standard_dots():
    layout = get_layout("a4", "medium")  # 4/3 of the standard size
    strip = fine_label(layout, 1, 1, "x")
    assert strip.shape == (24, layout.fmt.data_width * 4 // 3)


def test_standard_dots_need_no_fine_label():
    assert fine_label(get_layout("a4", "standard"), 1, 1, "x") is None
