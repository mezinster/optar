# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import os
import stat
import threading

import pytest

from optar.errors import OptarError
from optar.fileio import io_error, replacing

posix = pytest.mark.skipif(os.name == "nt", reason="uses POSIX permissions or special files")
posix_user = pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="needs POSIX permissions as a non-root user"
)


def _no_temp_files(directory):
    return not list(directory.glob("*.tmp"))


def test_io_error_names_verb_path_and_reason():
    err = io_error("write", "/x/y", OSError(28, "No space left on device"))
    assert isinstance(err, OptarError)
    assert str(err) == "cannot write /x/y: No space left on device"


def test_missing_target_is_created_via_temp_file(tmp_path):
    target = tmp_path / "out.bin"
    with replacing(target) as temp:
        assert temp != str(target) and os.path.dirname(temp) == str(tmp_path)
        assert not target.exists()
        with open(temp, "wb") as f:
            f.write(b"new")
    assert target.read_bytes() == b"new"
    assert _no_temp_files(tmp_path)


def test_accepts_str_and_pathlike(tmp_path):
    with replacing(str(tmp_path / "a")) as temp:
        open(temp, "wb").close()
    with replacing(tmp_path / "b") as temp:
        open(temp, "wb").close()
    assert (tmp_path / "a").exists() and (tmp_path / "b").exists()


def test_existing_regular_file_is_replaced(tmp_path):
    target = tmp_path / "out.bin"
    target.write_bytes(b"old")
    with replacing(target) as temp:
        assert target.read_bytes() == b"old"  # untouched until the block completes
        with open(temp, "wb") as f:
            f.write(b"new")
    assert target.read_bytes() == b"new"
    assert _no_temp_files(tmp_path)


@posix
def test_new_file_gets_mode_from_umask(tmp_path):
    umask = os.umask(0o027)
    try:
        with replacing(tmp_path / "n") as temp:
            open(temp, "wb").close()
    finally:
        os.umask(umask)
    assert stat.S_IMODE((tmp_path / "n").stat().st_mode) == 0o666 & ~0o027


@posix
def test_existing_file_keeps_its_mode(tmp_path):
    target = tmp_path / "x"
    target.write_bytes(b"old")
    target.chmod(0o640)
    with replacing(target) as temp:
        with open(temp, "wb") as f:
            f.write(b"new")
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert target.read_bytes() == b"new"


@posix_user
def test_existing_read_only_file_is_refused(tmp_path):
    target = tmp_path / "ro"
    target.write_bytes(b"precious")
    target.chmod(0o444)
    with pytest.raises(OptarError, match="cannot write"), replacing(target):
        pytest.fail("block must not run")
    assert target.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)


def test_directory_target_gives_clean_error(tmp_path):
    target = tmp_path / "d"
    target.mkdir()
    with pytest.raises(OptarError, match="cannot write"), replacing(target) as temp:
        open(temp, "wb").close()
    assert target.is_dir()
    assert _no_temp_files(tmp_path)


def test_missing_directory_gives_clean_error(tmp_path):
    target = tmp_path / "nodir" / "x"
    with pytest.raises(OptarError, match="cannot write.*nodir"), replacing(target):
        pytest.fail("block must not run")


def test_failure_keeps_existing_file_and_removes_only_temp(tmp_path):
    target = tmp_path / "x"
    target.write_bytes(b"precious")
    other = tmp_path / "other.tmp"
    other.write_bytes(b"not ours")
    with pytest.raises(RuntimeError, match="boom"), replacing(target) as temp:
        with open(temp, "wb") as f:
            f.write(b"partial")
        raise RuntimeError("boom")
    assert target.read_bytes() == b"precious"
    assert [p.name for p in tmp_path.glob("*.tmp")] == ["other.tmp"]
    assert other.read_bytes() == b"not ours"


def test_oserror_in_block_becomes_optar_error_and_removes_temp(tmp_path):
    target = tmp_path / "x"
    with pytest.raises(OptarError, match="cannot write.*No space"), replacing(target):
        raise OSError(28, "No space left on device")
    assert not target.exists()
    assert _no_temp_files(tmp_path)


def test_failed_replace_keeps_existing_file(tmp_path, monkeypatch):
    target = tmp_path / "x"
    target.write_bytes(b"precious")

    def failing_replace(src, dst):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OptarError, match="Permission denied"), replacing(target) as temp:
        open(temp, "wb").close()
    assert target.read_bytes() == b"precious"
    assert _no_temp_files(tmp_path)


@posix
def test_dev_null_is_written_directly(tmp_path):
    with replacing(os.devnull) as path:
        assert path == os.devnull
        with open(path, "wb") as f:
            f.write(b"x")
    assert stat.S_ISCHR(os.stat(os.devnull).st_mode)
    assert _no_temp_files(tmp_path)


@posix
def test_dev_null_failure_unlinks_nothing(tmp_path):
    with pytest.raises(OptarError, match="cannot write"), replacing(os.devnull):
        raise OSError(5, "Input/output error")
    assert stat.S_ISCHR(os.stat(os.devnull).st_mode)


@posix
def test_fifo_is_written_directly_and_kept(tmp_path):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    received = []

    def reader():
        fd = os.open(fifo, os.O_RDONLY)
        with os.fdopen(fd, "rb") as f:
            received.append(f.read())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    with replacing(fifo) as path:
        assert path == str(fifo)
        with open(path, "wb") as f:
            f.write(b"hello")
    thread.join(timeout=30)
    assert not thread.is_alive() and received == [b"hello"]
    assert stat.S_ISFIFO(os.stat(fifo).st_mode)
    assert _no_temp_files(tmp_path)


@posix
def test_fifo_failure_does_not_unlink_it(tmp_path):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(OptarError, match="cannot write"), replacing(fifo):
        raise OSError(32, "Broken pipe")
    assert stat.S_ISFIFO(os.stat(fifo).st_mode)


@posix
def test_socket_is_written_directly_and_kept(tmp_path, monkeypatch):
    import socket

    # Bound by a relative name: tmp_path on macOS is longer than a socket path may be.
    monkeypatch.chdir(tmp_path)
    path = str(tmp_path / "s")
    with socket.socket(socket.AF_UNIX) as srv:
        srv.bind("s")
        with pytest.raises(OptarError, match="cannot write"), replacing(path) as p:
            assert p == path
            raise OSError(111, "Connection refused")
        assert stat.S_ISSOCK(os.stat(path).st_mode)
    assert _no_temp_files(tmp_path)


@posix
def test_concurrent_writers_never_leave_the_umask_changed():
    import sys

    import optar.fileio as fileio

    original = os.umask(0o022)
    os.umask(original)
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)  # switch threads as often as possible
    seen = []
    try:
        def many():
            for _ in range(3000):
                seen.append(fileio._new_file_mode())

        threads = [threading.Thread(target=many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)
        left = os.umask(original)
    assert left == original
    assert set(seen) == {0o666 & ~original}
