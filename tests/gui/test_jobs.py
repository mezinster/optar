# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
"""JobRunner: background jobs reporting on the interface thread."""

import logging
import threading
import time
from collections import Counter
from functools import partial

import pytest
import shiboken6
from PySide6.QtCore import QObject

from optar.errors import OptarError
from optar_gui.jobs import JobRunner, default_max_workers
from optar_gui.work import Cancelled, ScanWork, process_scan

TIMEOUT = 10_000  # ms; generous for a loaded machine


class Recorder:
    """Everything a runner emits, with the thread it arrived on."""

    def __init__(self, runner):
        self.events = []
        self.threads = set()
        runner.started.connect(lambda i: self._add("started", i))
        runner.finished.connect(lambda i, r: self._add("finished", i, r))
        runner.failed.connect(lambda i, m: self._add("failed", i, m))
        runner.idle.connect(lambda: self._add("idle"))

    def _add(self, *event):
        self.threads.add(threading.get_ident())
        self.events.append(event)

    def of(self, kind):
        return [e[1:] for e in self.events if e[0] == kind]


@pytest.fixture
def make_runner(qtbot):
    runners = []

    def make(**kw):
        runner = JobRunner(**kw)
        runners.append((runner, Recorder(runner)))
        return runners[-1]

    yield make
    for runner, _ in runners:
        runner.shutdown(TIMEOUT)


def blocker():
    """A job function that waits for the returned event (ignoring cancellation)."""
    release = threading.Event()

    def fn(cancelled):
        assert release.wait(TIMEOUT / 1000)
        return "released"

    return fn, release


def until_cancelled(seen=None):
    def fn(cancelled):
        deadline = time.monotonic() + TIMEOUT / 1000
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(0.005)
        if seen is not None:
            seen.append(cancelled())
        return "returned anyway"

    return fn


def test_default_max_workers():
    assert 1 <= default_max_workers() <= 3
    assert JobRunner().max_workers == default_max_workers()
    with pytest.raises(ValueError):
        JobRunner(max_workers=0)


def test_results_arrive_on_the_interface_thread(make_runner):
    runner, rec = make_runner(max_workers=2)
    for scan_id in (1, 2, 3):
        runner.submit(scan_id, lambda cancelled, s=scan_id: (s, threading.get_ident()))
    assert runner.active == 3
    assert runner.wait_idle(TIMEOUT)
    main = threading.get_ident()
    assert rec.threads == {main}
    finished = sorted(rec.of("finished"))
    assert [(i, r[0]) for i, r in finished] == [(1, 1), (2, 2), (3, 3)]
    assert all(r[1] != main for _, r in finished)
    assert sorted(rec.of("started")) == [(1,), (2,), (3,)]
    assert rec.events[-1] == ("idle",) and runner.active == 0


def test_at_most_max_workers_run_at_once(make_runner):
    runner, rec = make_runner(max_workers=2)
    lock = threading.Lock()
    running, peak = [0], [0]

    def fn(cancelled):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.1)
        with lock:
            running[0] -= 1
        return "ok"

    for scan_id in range(6):
        runner.submit(scan_id, fn)
    assert runner.active == 6
    assert runner.wait_idle(TIMEOUT)
    assert peak[0] == 2
    assert sorted(i for i, _ in rec.of("finished")) == list(range(6))


def test_cancel_all_emits_nothing_and_goes_idle(make_runner):
    runner, rec = make_runner(max_workers=2)
    seen = []
    for scan_id in range(4):
        runner.submit(scan_id, until_cancelled(seen))
    assert rec.of("started") == [(0,), (1,)]
    runner.cancel_all()
    assert runner.wait_idle(TIMEOUT)
    assert seen == [True, True]  # the two waiting jobs never ran
    assert rec.of("finished") == [] and rec.of("failed") == []
    assert rec.of("started") == [(0,), (1,)]
    assert rec.events[-1] == ("idle",) and runner.active == 0


def test_cancelled_function_raising_cancelled_is_not_a_failure(make_runner):
    runner, rec = make_runner(max_workers=1)

    def fn(cancelled):
        while not cancelled():
            time.sleep(0.005)
        raise Cancelled()

    runner.submit(7, fn)
    runner.submit(8, lambda cancelled: (_ for _ in ()).throw(Cancelled()))
    runner.cancel(7)
    assert runner.wait_idle(TIMEOUT)
    assert rec.of("finished") == [] and rec.of("failed") == []


def test_job_exception_emits_failed(make_runner, caplog):
    runner, rec = make_runner(max_workers=2)

    def broken(cancelled):
        raise ValueError("bad value\nsecond line")

    def refused(cancelled):
        raise OptarError("cannot read image x.png: not a PNG image")

    with caplog.at_level(logging.ERROR, logger="optar_gui.jobs"):
        runner.submit(1, broken)
        runner.submit(2, refused)
        assert runner.wait_idle(TIMEOUT)
    assert sorted(rec.of("failed")) == [
        (1, "ValueError: bad value"),
        (2, "cannot read image x.png: not a PNG image"),
    ]
    assert rec.of("finished") == []
    errors = [r for r in caplog.records if r.name == "optar_gui.jobs"]
    assert len(errors) == 2 and all(r.exc_info for r in errors)
    assert "ValueError: bad value" in caplog.text and "Traceback" in caplog.text


def test_result_queued_before_cancel_is_dropped(make_runner):
    runner, rec = make_runner(max_workers=1)
    runner.submit(5, lambda cancelled: "done")
    # Without processing events, let the function return and its result be
    # queued for the interface thread.
    assert runner._pool.waitForDone(TIMEOUT)
    runner.cancel(5)
    assert runner.wait_idle(TIMEOUT)
    assert rec.of("finished") == [] and rec.of("failed") == []


def test_waiting_jobs_run_in_fifo_order(make_runner):
    runner, rec = make_runner(max_workers=1)
    first, release = blocker()
    order = []
    runner.submit(0, first)
    for scan_id in range(1, 6):
        runner.submit(scan_id, lambda cancelled, s=scan_id: order.append(s) or s)
    assert rec.of("started") == [(0,)]
    release.set()
    assert runner.wait_idle(TIMEOUT)
    assert order == [1, 2, 3, 4, 5]
    assert rec.of("started") == [(i,) for i in range(6)]
    assert [i for i, _ in rec.of("finished")] == list(range(6))


def test_cancel_a_waiting_job(make_runner):
    runner, rec = make_runner(max_workers=1)
    first, release = blocker()
    ran = []
    runner.submit(1, first)
    runner.submit(2, lambda cancelled: ran.append(2))
    runner.submit(3, lambda cancelled: ran.append(3))
    assert runner.active == 3
    runner.cancel(2)
    assert runner.active == 2
    release.set()
    assert runner.wait_idle(TIMEOUT)
    assert ran == [3]
    assert [i for i, _ in rec.of("finished")] == [1, 3]
    assert rec.of("started") == [(1,), (3,)]


def test_cancelled_job_keeps_its_slot_until_it_returns(make_runner):
    runner, rec = make_runner(max_workers=1)
    first, release = blocker()
    runner.submit(1, first)
    runner.submit(2, lambda cancelled: "second")
    runner.cancel(1)
    assert not runner.wait_idle(200)  # the first function ignores its flag
    assert rec.of("started") == [(1,)] and runner.active == 2
    release.set()
    assert runner.wait_idle(TIMEOUT)
    assert rec.of("finished") == [(2, "second")]


def test_shutdown_waits_and_emits_nothing_afterwards(make_runner, qtbot):
    runner, rec = make_runner(max_workers=2)
    fn, release = blocker()
    runner.submit(1, fn)
    runner.submit(2, until_cancelled())
    runner.submit(3, lambda cancelled: "never runs")
    before = list(rec.events)
    timer = threading.Timer(0.3, release.set)  # released once shutdown is waiting
    timer.start()
    start = time.monotonic()
    assert runner.shutdown(timeout_ms=TIMEOUT)
    elapsed = time.monotonic() - start
    timer.join()
    assert 0.2 < elapsed < TIMEOUT / 1000
    qtbot.wait(200)
    assert rec.events == before == [("started", 1), ("started", 2)]
    assert runner.active == 0
    with pytest.raises(RuntimeError):
        runner.submit(4, lambda cancelled: None)


def test_shutdown_times_out_on_a_stuck_function(make_runner, qtbot):
    runner, rec = make_runner(max_workers=1)
    fn, release = blocker()
    runner.submit(1, fn)
    assert not runner.shutdown(timeout_ms=100)
    release.set()
    assert runner._pool.waitForDone(TIMEOUT)
    qtbot.wait(100)
    assert rec.events == [("started", 1)]


def test_destroying_the_parent_while_jobs_run(qtbot):
    parent = QObject()
    runner = JobRunner(parent, max_workers=2)
    rec = Recorder(runner)
    seen = []
    runner.submit(1, until_cancelled(seen))
    runner.submit(2, until_cancelled(seen))
    runner.submit(3, until_cancelled(seen))
    shiboken6.delete(parent)  # waits for the running functions, which see the flag
    assert seen == [True, True]
    qtbot.wait(100)
    assert rec.events == [("started", 1), ("started", 2)]


def test_fifty_quick_jobs_deliver_exactly_once(make_runner):
    runner, rec = make_runner(max_workers=3)
    for scan_id in range(50):
        runner.submit(scan_id, lambda cancelled, s=scan_id: s * 2)
    assert runner.wait_idle(TIMEOUT)
    finished = rec.of("finished")
    assert Counter(i for i, _ in finished) == Counter(range(50))
    assert all(r == i * 2 for i, r in finished)
    assert Counter(i for (i,) in rec.of("started")) == Counter(range(50))


def test_no_qt_warnings(make_runner, qtlog):
    runner, rec = make_runner(max_workers=2)
    for scan_id in range(5):
        runner.submit(scan_id, until_cancelled() if scan_id % 2 else (lambda c: "ok"))
    runner.cancel_all()
    assert runner.wait_idle(TIMEOUT)
    runner.shutdown(TIMEOUT)
    assert qtlog.records == []


def test_process_scan_through_the_runner(make_runner, scan_files):
    data, paths = scan_files()
    assert len(paths) == 2
    runner, rec = make_runner(max_workers=2)
    for scan_id, path in enumerate(paths, start=1):
        runner.submit(scan_id, partial(process_scan, path))
    assert runner.wait_idle(120_000)
    assert rec.of("failed") == []
    finished = dict(rec.of("finished"))
    assert sorted(finished) == [1, 2]
    for scan_id, w in finished.items():
        assert isinstance(w, ScanWork) and w.reason == ""
        assert w.info.page == scan_id and w.info.total == 2 and w.info.name == "doc.tar"
        assert w.outcome.lost == 0
    assert finished[1].outcome.data + finished[2].outcome.data[: len(data) - 199773] == data
