# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Safe writing of output files: a failed write never damages an existing file."""

from __future__ import annotations

import contextlib
import errno
import os
import stat
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

from .errors import OptarError, error


def io_error(verb: str, path: str | os.PathLike, e: OSError) -> OptarError:
    """``cannot read PATH: REASON`` (or write); the verb chooses the message key."""
    reason = str(e.strerror or e)
    if verb == "read":
        return error(OptarError, "err.cannot_read", "cannot read {path}: {reason}",
                     path=path, reason=reason)  # fmt: skip
    if verb == "write":
        return error(OptarError, "err.cannot_write", "cannot write {path}: {reason}",
                     path=path, reason=reason)  # fmt: skip
    return OptarError(f"cannot {verb} {path}: {reason}")


# The umask can only be read by setting it; the lock keeps two threads from
# interleaving the pair and leaving it set to 0.
_UMASK_LOCK = threading.Lock()


def _new_file_mode() -> int:
    with _UMASK_LOCK:
        umask = os.umask(0)
        os.umask(umask)
    return 0o666 & ~umask


@contextlib.contextmanager
def replacing(path: str | os.PathLike) -> Iterator[str]:
    """Yield a temporary path next to `path`; move it onto `path` only on success.

    An existing file at `path` is left untouched unless the block completes,
    and on any failure only the temporary file is removed. A read-only
    existing file is refused, as opening it for writing would be.

    An existing target that is neither a regular file nor a directory (a
    device such as /dev/null, a pipe, a socket) is written directly: no
    temporary file, and nothing is removed if writing fails.
    """
    target = Path(path)
    try:
        st = os.stat(target)
    except OSError:
        st = None
    if st is not None and not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
        try:
            yield os.fspath(path)
        except OSError as e:
            raise io_error("write", path, e) from e
        return
    try:
        if target.exists() and not os.access(target, os.W_OK):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), os.fspath(path))
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else _new_file_mode()
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False
        ) as tmp:
            temp = tmp.name
    except OSError as e:
        raise io_error("write", path, e) from e
    try:
        yield temp
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException as e:
        with contextlib.suppress(OSError):
            os.unlink(temp)
        if isinstance(e, OSError):
            raise io_error("write", path, e) from e
        raise
