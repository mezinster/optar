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
