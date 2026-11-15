# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Shared pytest fixtures."""

import shutil

import pytest

from tests import cbuild


@pytest.fixture(scope="session")
def ghostscript():
    """Path to the Ghostscript executable, or skip when it is not installed."""
    gs = shutil.which("gs")
    if gs is None:
        pytest.skip("Ghostscript (gs) not available")
    return gs


@pytest.fixture(scope="session")
def c_build(tmp_path_factory):
    """Factory: c_build(format_overrides=None) -> CBuild, cached per override set."""
    if cbuild.compiler() is None:
        pytest.skip("no C compiler available")
    cache: dict[tuple, cbuild.CBuild] = {}

    def factory(format_overrides: dict[str, int] | None = None) -> cbuild.CBuild:
        key = tuple(sorted((format_overrides or {}).items()))
        if key not in cache:
            dest = tmp_path_factory.mktemp("cbuild")
            cache[key] = cbuild.build_c_tools(dest, format_overrides)
        return cache[key]

    yield factory
    for b in cache.values():
        shutil.rmtree(b.dir, ignore_errors=True)
