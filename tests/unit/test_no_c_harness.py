# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The tests need no C compiler: nothing in them reaches the C build harness."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"

# Files that may name lega-c: this test, the vector notes (which say how the vectors
# were recorded) and the font test, which reads lega-c/font.h as data (no compiler).
MAY_NAME_LEGA_C = {
    TESTS / "unit" / "test_no_c_harness.py",
    TESTS / "vectors" / "README.md",
    TESTS / "unit" / "test_font.py",
}
# Files that may name cbuild: this test and the vector notes.
MAY_NAME_CBUILD = {TESTS / "unit" / "test_no_c_harness.py", TESTS / "vectors" / "README.md"}


def _files():
    for path in sorted(TESTS.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".png":
            yield path, path.read_text(encoding="utf-8", errors="replace")


def test_no_test_imports_the_c_harness():
    for path, text in _files():
        rel = path.relative_to(ROOT)
        if path not in MAY_NAME_CBUILD:
            assert "cbuild" not in text, rel
        if path not in MAY_NAME_LEGA_C:
            assert "lega-c" not in text, rel

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"oracle' not in pyproject
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "libpng" not in ci
    assert "oracle" not in ci
