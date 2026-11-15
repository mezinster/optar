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


# Pillow itself warns for images above the cap, before read_scan refuses them.
@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_scan_above_pixel_limit_is_refused(tmp_path, monkeypatch):
    Image.fromarray(gradient()).save(tmp_path / "g.png")
    monkeypatch.setattr(optar.imageio, "MAX_SCAN_PIXELS", 1000)
    limit = Image.MAX_IMAGE_PIXELS
    with pytest.raises(OptarError, match="1,024 pixels.*1,000"):
        read_scan(tmp_path / "g.png")
    assert Image.MAX_IMAGE_PIXELS == limit


def test_read_scan_is_safe_from_many_threads(tmp_path):
    import threading

    arr = np.full((300, 200), 255, np.uint8)
    paths = []
    for i in range(8):
        p = tmp_path / f"s{i}.png"
        Image.fromarray(arr).save(p)
        paths.append(p)
    before = Image.MAX_IMAGE_PIXELS
    seen, errors = [], []

    def worker(p):
        try:
            # Warnings are not checked here (images are tiny); the bomb limit is
            # covered by the deterministic and large-image tests.
            for _ in range(20):
                read_scan(p)
                seen.append(Image.MAX_IMAGE_PIXELS)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=worker, args=(p,)) for p in paths]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errors
    assert len(seen) == 8 * 20
    assert Image.MAX_IMAGE_PIXELS == before


def test_pillow_limit_is_normal_while_pixels_load(tmp_path, monkeypatch):
    import threading

    Image.fromarray(gradient()).save(tmp_path / "g.png")
    normal = Image.MAX_IMAGE_PIXELS
    assert normal is not None
    inside, other_thread = [], []
    entered, release = threading.Event(), threading.Event()
    real = optar.imageio._to_gray8

    def blocked(im):
        inside.append(Image.MAX_IMAGE_PIXELS)
        entered.set()
        assert release.wait(30)
        return real(im)

    monkeypatch.setattr(optar.imageio, "_to_gray8", blocked)
    t = threading.Thread(target=read_scan, args=(tmp_path / "g.png",))
    t.start()
    try:
        assert entered.wait(30)  # reader is now inside pixel loading
        probe = threading.Thread(target=lambda: other_thread.append(Image.MAX_IMAGE_PIXELS))
        probe.start()
        probe.join()
    finally:
        release.set()
        t.join()
    assert inside == [normal] and other_thread == [normal]
    assert Image.MAX_IMAGE_PIXELS == normal


def _save_tiff(path, width, height):
    Image.new("L", (width, height), 200).save(path, compression="tiff_adobe_deflate")


@pytest.mark.slow  # about 100 MB of pixels
def test_large_tiff_reads_without_decompression_bomb_warning(tmp_path):
    _save_tiff(tmp_path / "big.tif", 10000, 10000)  # 100 MP: above the warning threshold
    assert 10000 * 10000 > Image.MAX_IMAGE_PIXELS
    limit = Image.MAX_IMAGE_PIXELS
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = read_scan(tmp_path / "big.tif")
    assert out.shape == (10000, 10000)
    assert Image.MAX_IMAGE_PIXELS == limit


@pytest.mark.slow  # about 200 MB of pixels
def test_tiff_above_pillow_error_threshold_reads(tmp_path):
    _save_tiff(tmp_path / "huge.tif", 14000, 14000)  # 196 MP: Pillow alone would refuse
    assert 14000 * 14000 > 2 * Image.MAX_IMAGE_PIXELS
    limit = Image.MAX_IMAGE_PIXELS
    out = read_scan(tmp_path / "huge.tif")
    assert out.shape == (14000, 14000)
    assert Image.MAX_IMAGE_PIXELS == limit


def test_non_png_load_holds_the_lock_so_other_reads_wait(tmp_path, monkeypatch):
    import threading

    Image.fromarray(gradient()).save(tmp_path / "g.tif")
    Image.fromarray(gradient()).save(tmp_path / "g.png")
    normal = Image.MAX_IMAGE_PIXELS
    entered, release = threading.Event(), threading.Event()
    seen, finished = [], threading.Event()
    real = optar.imageio._to_gray8

    def blocked(im):
        if im.format == "TIFF":
            seen.append(Image.MAX_IMAGE_PIXELS)  # raised to the cap while a TIFF loads
            entered.set()
            assert release.wait(30)
        return real(im)

    monkeypatch.setattr(optar.imageio, "_to_gray8", blocked)
    results = {}

    def read(name):
        results[name] = read_scan(tmp_path / name)

    tiff = threading.Thread(target=read, args=("g.tif",))
    png = threading.Thread(target=lambda: (read("g.png"), finished.set()))
    tiff.start()
    try:
        assert entered.wait(30)
        png.start()
        assert not finished.wait(0.5)  # the PNG read waits for the TIFF
    finally:
        release.set()
        tiff.join(30)
        if png.ident is not None:
            png.join(30)
    assert not tiff.is_alive() and not png.is_alive()
    assert seen == [optar.imageio.MAX_SCAN_PIXELS] and finished.is_set()
    assert np.array_equal(results["g.tif"], results["g.png"])
    assert Image.MAX_IMAGE_PIXELS == normal


def test_pillow_limit_is_never_none_during_non_png_read(tmp_path, monkeypatch):
    Image.fromarray(gradient()).save(tmp_path / "g.tif")
    normal = Image.MAX_IMAGE_PIXELS
    seen = []
    real = optar.imageio._to_gray8

    def spy(im):
        seen.append(Image.MAX_IMAGE_PIXELS)
        return real(im)

    monkeypatch.setattr(optar.imageio, "_to_gray8", spy)
    read_scan(tmp_path / "g.tif")
    assert seen == [optar.imageio.MAX_SCAN_PIXELS]
    assert Image.MAX_IMAGE_PIXELS == normal


@pytest.mark.parametrize("ext", ["ico", "gif"])
def test_formats_a_scan_cannot_be_are_refused(tmp_path, ext):
    path = tmp_path / f"x.{ext}"
    Image.fromarray(gradient()).save(path)
    limit = Image.MAX_IMAGE_PIXELS
    with pytest.raises(OptarError, match="not a PNG, TIFF, BMP, PGM/PPM or JPEG image"):
        read_scan(path)
    assert Image.MAX_IMAGE_PIXELS == limit


def test_size_change_while_loading_is_refused(tmp_path, monkeypatch):
    Image.fromarray(gradient()).save(tmp_path / "g.tif")
    real_load = Image.Image.load

    def growing_load(self):
        result = real_load(self)
        self._size = (self.width + 1, self.height)  # the pixel count changes
        return result

    monkeypatch.setattr(Image.Image, "load", growing_load)
    limit = Image.MAX_IMAGE_PIXELS
    with pytest.raises(OptarError, match="size changed while loading"):
        read_scan(tmp_path / "g.tif")
    assert Image.MAX_IMAGE_PIXELS == limit


def test_size_above_cap_after_loading_is_refused(tmp_path, monkeypatch):
    Image.fromarray(gradient()).save(tmp_path / "g.tif")  # 1,024 pixels
    real_load = Image.Image.load
    cap = 2000

    def growing_load(self):
        result = real_load(self)
        self._size = (self.width * 3, self.height)  # 27,648 pixels
        return result

    monkeypatch.setattr(optar.imageio, "MAX_SCAN_PIXELS", cap)
    monkeypatch.setattr(Image.Image, "load", growing_load)
    with pytest.raises(OptarError, match="27,648 pixels.*2,000"):
        read_scan(tmp_path / "g.tif")


@pytest.mark.parametrize("fmt", ["BMP", "PPM", "TIFF", "JPEG"])
def test_other_scan_formats_read(tmp_path, fmt):
    path = tmp_path / "g.img"
    Image.fromarray(gradient()).save(path, format=fmt)
    out = read_scan(path)
    expected = read_scan_png_reference(tmp_path)
    assert out.shape == expected.shape
    if fmt == "JPEG":
        assert np.abs(out.astype(int) - expected.astype(int)).max() <= 12
    else:
        assert np.array_equal(out, expected)


def read_scan_png_reference(tmp_path):
    Image.fromarray(gradient()).save(tmp_path / "ref.png")
    return read_scan(tmp_path / "ref.png")


@pytest.mark.parametrize("orientation", [6, 8])
def test_orientation_tagged_tiff_reads_transposed(tmp_path, orientation):
    arr = np.tile(np.arange(40, dtype=np.uint8), (20, 1))  # 40 wide, 20 high
    path = tmp_path / "o.tif"
    Image.fromarray(arr).save(path, tiffinfo={274: orientation})
    with Image.open(path) as im:
        header_size = im.size
        im.load()
        loaded_size = im.size
    assert loaded_size == header_size[::-1]  # the tag took effect: Pillow swapped the size
    out = read_scan(path)
    assert out.shape == (loaded_size[1], loaded_size[0])  # what Pillow gives, not the header
    assert Image.MAX_IMAGE_PIXELS is not None


def test_unidentified_file_names_accepted_formats(tmp_path):
    (tmp_path / "t.txt").write_text("hello")
    with pytest.raises(OptarError, match=r"t\.txt: not a PNG, TIFF, BMP, PGM/PPM or JPEG image"):
        read_scan(tmp_path / "t.txt")
