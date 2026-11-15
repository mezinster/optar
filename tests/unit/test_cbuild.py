# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""The C build harness reports a failed build instead of erroring."""

import os
import shutil

import pytest

from tests import cbuild

posix_only = pytest.mark.skipif(os.name == "nt", reason="uses a shell script as the compiler")


def _fake_cc(tmp_path, body):
    script = tmp_path / "fakecc"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(0o755)
    return str(script)


@posix_only
def test_failed_compile_raises_cbuild_error_with_compiler_message(tmp_path, monkeypatch):
    monkeypatch.setenv("CC", _fake_cc(tmp_path, 'echo "fake compiler says no" >&2; exit 1'))
    with pytest.raises(cbuild.CBuildError, match="fake compiler says no"):
        cbuild.build_c_tools(tmp_path / "build")


@posix_only
def test_relative_dest_builds_with_absolute_paths(tmp_path, monkeypatch):
    # Every command is logged; the build fails at the first compile, after the
    # png.h probe, so no real compiler is needed.
    log = tmp_path / "log"
    monkeypatch.setenv("CC", _fake_cc(tmp_path, f'echo "$@" >> {log}; exit 1'))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(cbuild.CBuildError):
        cbuild.build_c_tools(cbuild.Path("rel"))
    probe = log.read_text().splitlines()[0]
    assert str(tmp_path / "rel" / "pngcheck.c") in probe


@pytest.mark.oracle
@posix_only
def test_failed_unoptar_link_leaves_unoptar_none(tmp_path, monkeypatch):
    cc = cbuild.compiler()
    if cc is None:
        pytest.skip("no C compiler available")
    if not cbuild._has_png_h(cc, cbuild._png_flags(), tmp_path):
        pytest.skip("png.h not available")
    # A compiler that fails only when linking against libpng.
    body = f'for a in "$@"; do [ "$a" = -lpng ] && exit 1; done; exec {cc} "$@"'
    monkeypatch.setenv("CC", _fake_cc(tmp_path, body))
    build = cbuild.build_c_tools(tmp_path / "build")
    assert build.optar.is_file() and build.unoptar is None
    shutil.rmtree(build.dir)
