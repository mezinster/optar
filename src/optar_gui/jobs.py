# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""Running work off the interface thread.

A ``JobRunner`` runs functions such as ``optar_gui.work.process_scan`` on a
private ``QThreadPool`` and reports their results on the thread that owns the
runner (the interface thread) through its signals.

Workers never touch the runner. Each one hands its result to a small
lock-guarded channel that emits a signal of a relay object living on the
interface thread; the relay's signal reaches the runner through a queued
connection. When the runner shuts down or is destroyed the channel is closed
under its lock, so no worker can emit afterwards.
"""

from __future__ import annotations

import itertools
import logging
import os
import threading
from collections import deque
from collections.abc import Callable
from functools import partial

from PySide6.QtCore import QEventLoop, QObject, Qt, QThreadPool, QTimer, Signal

from optar.errors import OptarError
from optar_gui.work import Cancelled

__all__ = ["JobRunner", "default_max_workers"]

log = logging.getLogger(__name__)

_FINISHED, _FAILED, _CANCELLED = range(3)


def default_max_workers() -> int:
    """Half the cores, at least 1 and at most 3 (see JobRunner for why 3)."""
    return max(1, min(3, (os.cpu_count() or 2) // 2))


def _one_line(e: BaseException) -> str:
    text = next((line.strip() for line in str(e).splitlines() if line.strip()), "")
    if isinstance(e, OptarError) and text:
        return text
    return f"{type(e).__name__}: {text}" if text else type(e).__name__


class _Job:
    __slots__ = ("serial", "scan_id", "fn", "flag")

    def __init__(self, serial: int, scan_id: int, fn: Callable) -> None:
        self.serial = serial
        self.scan_id = scan_id
        self.fn = fn
        self.flag = threading.Event()


class _Relay(QObject):
    done = Signal(int, int, object)  # job serial, kind, result or message


class _Channel:
    """The workers' only way back: emits on the relay until closed."""

    def __init__(self, relay: _Relay) -> None:
        self.lock = threading.Lock()
        self.relay: _Relay | None = relay
        self.flags: dict[int, threading.Event] = {}  # serial -> flag of every live job

    def deliver(self, serial: int, kind: int, payload: object) -> None:
        with self.lock:
            if self.relay is not None:
                self.relay.done.emit(serial, kind, payload)

    def close(self, *_args) -> None:
        """Cancel every job and stop all delivery. Safe to call more than once."""
        with self.lock:
            self.relay = None
            for flag in self.flags.values():
                flag.set()


def _run(channel: _Channel, job: _Job) -> None:
    """Run one job on a worker thread and hand its outcome to the channel."""
    try:
        payload = job.fn(job.flag.is_set)
        kind = _FINISHED
    except Cancelled:
        payload, kind = None, _CANCELLED
    except BaseException as e:
        log.error("background job for scan %d failed", job.scan_id, exc_info=e)
        payload, kind = _one_line(e), _FAILED
    job.fn = None
    channel.deliver(job.serial, kind, payload)


class JobRunner(QObject):
    """Runs ``fn(cancelled)`` for scans in the background, a few at a time.

    Signals, all emitted on the thread that owns the runner: ``started(scan
    id)`` when a job's function is handed to a worker, ``finished(scan id,
    result)`` when it returns, ``failed(scan id, message)`` when it raises
    (a one-line message; the traceback goes to the ``logging`` module), and
    ``idle()`` when no job is waiting or running any more.

    ``cancelled`` is a callable the function polls; once a job is cancelled
    it emits nothing, ever, whatever its function does. A function raising
    ``Cancelled`` is not a failure and emits nothing either.

    Concurrency. At most ``max_workers`` functions run at once (default
    ``default_max_workers()``: half the cores, at most 3). Identifying and
    decoding one 600 dpi A4 scan peaks at about 513 MB, and three at once at
    about 1.33 GB; more would gain little speed for a lot of memory. Three
    1200 dpi scans at once would peak near 4 GB, so ``work`` runs scans above
    ``work.LARGE_SCAN_PIXELS`` one at a time, whatever this limit. A cancelled
    function keeps its slot until it actually returns, so cancelling never
    lets more scans than that be in memory at once. Further jobs wait in the
    order submitted; cancelling a waiting job removes it without running it.

    Call ``shutdown`` before the runner is destroyed (from the window's close
    event). Destroying it with jobs still running is safe as well: every job
    is cancelled and the destruction waits for the running functions to
    return, emitting nothing.
    """

    started = Signal(int)
    finished = Signal(int, object)
    failed = Signal(int, str)
    idle = Signal()

    def __init__(self, parent: QObject | None = None, max_workers: int | None = None) -> None:
        super().__init__(parent)
        self._max_workers = default_max_workers() if max_workers is None else int(max_workers)
        if self._max_workers < 1:
            raise ValueError(f"max_workers must be at least 1, got {max_workers}")
        # The pool is created before the relay, so on destruction it is
        # deleted (waiting for its threads) while the relay still exists.
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(self._max_workers)
        relay = _Relay(self)
        relay.done.connect(self._receive, Qt.ConnectionType.QueuedConnection)
        self._channel = _Channel(relay)
        # Emitted before the children are deleted: cancels and closes first.
        self.destroyed.connect(self._channel.close)
        self._serials = itertools.count(1)
        self._waiting: deque[_Job] = deque()
        self._running: dict[int, _Job] = {}  # serial -> job whose function has not returned
        self._closed = False

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def active(self) -> int:
        """Jobs waiting or running, counting cancelled functions not yet returned."""
        return len(self._waiting) + len(self._running)

    def submit(self, scan_id: int, fn: Callable[[Callable[[], bool]], object]) -> None:
        """Queue ``fn(cancelled)`` to run for ``scan_id``."""
        if self._closed:
            raise RuntimeError("the job runner has been shut down")
        job = _Job(next(self._serials), scan_id, fn)
        with self._channel.lock:
            self._channel.flags[job.serial] = job.flag
        self._waiting.append(job)
        self._dispatch()

    def cancel(self, scan_id: int) -> None:
        """Cancel every job for ``scan_id``: waiting ones never run, running ones emit nothing."""
        self._cancel(lambda job: job.scan_id == scan_id)

    def cancel_all(self) -> None:
        self._cancel(lambda job: True)

    def wait_idle(self, timeout_ms: int) -> bool:
        """Process events until no job is waiting or running; False on timeout."""
        if self.active == 0:
            return True
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        self.idle.connect(loop.quit)
        try:
            timer.start(max(0, int(timeout_ms)))
            if self.active:
                loop.exec()
        finally:
            timer.stop()
            self.idle.disconnect(loop.quit)
        return self.active == 0

    def shutdown(self, timeout_ms: int = 10_000) -> bool:
        """Cancel everything and wait for the running functions to return.

        Nothing is emitted from now on and no job may be submitted. Returns
        False if a function was still running when the timeout expired.
        """
        self._closed = True
        self._channel.close()
        self._waiting.clear()
        done = self._pool.waitForDone(max(0, int(timeout_ms)))
        self._running.clear()
        return done

    # --- internals ---------------------------------------------------------------

    def _cancel(self, chosen: Callable[[_Job], bool]) -> None:
        removed = [job for job in self._waiting if chosen(job)]
        for job in removed:
            self._waiting.remove(job)
            self._forget(job)
        for job in self._running.values():
            if chosen(job):
                job.flag.set()
        if removed and self.active == 0 and not self._closed:
            self.idle.emit()

    def _forget(self, job: _Job) -> None:
        job.flag.set()
        with self._channel.lock:
            self._channel.flags.pop(job.serial, None)

    def _dispatch(self) -> None:
        while not self._closed and self._waiting and len(self._running) < self._max_workers:
            job = self._waiting.popleft()
            self._running[job.serial] = job
            self._pool.start(partial(_run, self._channel, job))
            self.started.emit(job.scan_id)

    def _receive(self, serial: int, kind: int, payload: object) -> None:
        job = self._running.pop(serial, None)
        if job is None or self._closed:
            return
        cancelled = job.flag.is_set()
        with self._channel.lock:
            self._channel.flags.pop(serial, None)
        if not cancelled:
            if kind == _FINISHED:
                self.finished.emit(job.scan_id, payload)
            elif kind == _FAILED:
                self.failed.emit(job.scan_id, payload)
        del payload
        self._dispatch()
        if self.active == 0 and not self._closed:
            self.idle.emit()
