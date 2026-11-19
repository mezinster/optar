# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Shared pytest fixtures."""

import shutil

import pytest


@pytest.fixture(scope="session")
def ghostscript():
    """Path to the Ghostscript executable, or skip when it is not installed."""
    gs = shutil.which("gs")
    if gs is None:
        pytest.skip("Ghostscript (gs) not available")
    return gs


class _Catalogues:
    def __init__(self):
        from optar import i18n

        self._i18n = i18n
        self._real = i18n._read
        self._stubs: dict[str, dict] = {}
        self._visible: set[str] | None = None
        i18n._read = self._read

    def _read(self, code):
        if code in self._stubs:
            return self._stubs[code]
        if self._visible is not None and code not in self._visible:
            return None
        return self._real(code)

    def only(self, *codes):
        """Hide every real catalogue except these; stubs added stay visible."""
        self._visible = set(codes)
        self._i18n._cache.clear()

    def restore(self):
        self._i18n._read = self._real
        self._i18n._cache.clear()

    def add(self, code, data):
        """Make a stub language from a nested dict; "en" merges over English."""
        if code == "en":
            data = _merge(self._real("en") or {}, data)
        self._stubs[code] = data
        self._i18n._cache.clear()


def _merge(base, extra):
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


@pytest.fixture
def catalogues():
    """Stub languages: catalogues.add(code, nested_dict). Restores everything after."""
    from optar import i18n

    cat = _Catalogues()
    i18n._cache.clear()
    try:
        yield cat
    finally:
        cat.restore()
    i18n.set_language("en")
