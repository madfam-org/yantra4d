"""
Regression tests for the render worker heartbeat.

The heartbeat used to be published at the top of the blpop loop, which meant it
stopped for the entire duration of a render. A render legitimately runs to
RENDER_TIMEOUT_S (300s) against a 60s TTL, and the API treats a heartbeat older
than TTL*2 as a dead worker — so a long render made a perfectly healthy worker
look dead: the API refused new renders and, with RENDER_WORKER_REQUIRED=true,
/api/health/ready returned 503 and the kubelet restarted the API pod while the
render that caused it was still running.

It now beats from a daemon thread, so the beat is independent of job duration.

The worker lives outside the api package, so it is imported by path.
"""
import importlib.util
import itertools
import json
import pathlib
import sys
import threading
import time

import pytest

WORKER_PATH = (
    pathlib.Path(__file__).resolve().parents[3] / "worker" / "render_worker.py"
)


@pytest.fixture
def worker():
    """Import render_worker.py fresh, so module-level state is per-test."""
    if not WORKER_PATH.is_file():
        pytest.skip(f"render worker not present at {WORKER_PATH}")
    spec = importlib.util.spec_from_file_location(
        f"_render_worker_under_test_{len(sys.modules)}", WORKER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        yield module
    finally:
        module._stop_beating.set()


class _RecordingRedis:
    """Records heartbeat writes; hands out a fixed set of tasks once."""

    def __init__(self, tasks=()):
        self._tasks = list(tasks)
        self.beats = []
        self._lock = threading.Lock()

    def set(self, key, value, ex=None):
        with self._lock:
            self.beats.append((time.monotonic(), key, value, ex))

    def beat_count(self):
        with self._lock:
            return len(self.beats)

    def beat_times(self):
        with self._lock:
            return [t for t, *_ in self.beats]

    def blpop(self, _queue, timeout=5):
        if self._tasks:
            return ("q", self._tasks.pop(0))
        # Mirror a real blpop timeout: returns None, which the worker loop
        # unpacks into a TypeError and treats as "no work".
        time.sleep(0.01)
        return None


def test_heartbeat_continues_while_a_render_is_in_progress(worker):
    """The bug, directly: a render in flight must not stop the beat.

    Under the old loop-top heartbeat this recorded exactly zero beats for the
    whole duration of the render.
    """
    worker.HEARTBEAT_INTERVAL_SECONDS = 0.02
    fake = _RecordingRedis(tasks=[json.dumps({"job_id": "j1"})])
    worker.r = fake

    render_started = threading.Event()
    release_render = threading.Event()

    def slow_render(_task):
        render_started.set()
        release_render.wait(10)

    worker.process_sync_task = slow_render

    threading.Thread(target=worker.run_worker, daemon=True).start()
    try:
        assert render_started.wait(10), "worker never picked up the task"
        beats_before = fake.beat_count()

        # Hold the render open for ~15 beat intervals.
        time.sleep(0.3)

        beats_during_render = fake.beat_count() - beats_before
        assert beats_during_render >= 5, (
            f"heartbeat stalled during the render: {beats_during_render} beats "
            "while a job was being processed"
        )
    finally:
        release_render.set()
        worker._stop_beating.set()


def test_heartbeat_gap_never_approaches_the_ttl_during_a_render(worker):
    """Beats keep arriving at the interval, and the interval is safely inside
    the TTL — together, the API can never see a stale heartbeat mid-render."""
    worker.HEARTBEAT_INTERVAL_SECONDS = 0.02
    fake = _RecordingRedis(tasks=[json.dumps({"job_id": "j1"})])
    worker.r = fake

    render_started = threading.Event()
    release_render = threading.Event()

    def slow_render(_task):
        render_started.set()
        release_render.wait(10)

    worker.process_sync_task = slow_render

    threading.Thread(target=worker.run_worker, daemon=True).start()
    try:
        assert render_started.wait(10)
        time.sleep(0.3)
        times = fake.beat_times()
    finally:
        release_render.set()
        worker._stop_beating.set()

    assert len(times) >= 5
    gaps = [b - a for a, b in itertools.pairwise(times)]
    # Generous against scheduler jitter; the point is that gaps track the
    # interval rather than the render duration.
    assert max(gaps) < 0.2, f"largest gap between beats was {max(gaps):.3f}s"


def test_beat_interval_leaves_room_for_a_missed_tick(worker):
    """The design guarantee behind the test above: two consecutive misses still
    do not expire the key."""
    assert worker.HEARTBEAT_INTERVAL_SECONDS > 0
    assert (
        worker.HEARTBEAT_INTERVAL_SECONDS * 2
        < worker.RENDER_WORKER_HEARTBEAT_TTL_SECONDS
    )


def test_worker_publishes_a_beat_before_consuming_anything(worker):
    """The API should see a new worker as soon as it is up, not one interval
    later."""
    worker.HEARTBEAT_INTERVAL_SECONDS = 30  # long enough that no timed beat lands
    fake = _RecordingRedis()
    worker.r = fake

    threading.Thread(target=worker.run_worker, daemon=True).start()
    try:
        deadline = time.monotonic() + 5
        while fake.beat_count() < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert fake.beat_count() >= 1, "no heartbeat published at startup"
    finally:
        worker._stop_beating.set()


def test_heartbeat_writes_the_expected_key_with_a_ttl(worker):
    """Unchanged contract: one global key, bare timestamp, carrying the TTL."""
    fake = _RecordingRedis()
    worker.r = fake

    worker._publish_heartbeat()

    assert fake.beat_count() == 1
    _, key, value, ex = fake.beats[0]
    assert key == worker.RENDER_WORKER_HEARTBEAT_KEY
    assert ex == worker.RENDER_WORKER_HEARTBEAT_TTL_SECONDS
    assert abs(int(value) - int(time.time())) < 5


def test_heartbeat_loop_stops_when_asked(worker):
    """The loop is a daemon thread but still exits cleanly on the event."""
    worker.HEARTBEAT_INTERVAL_SECONDS = 0.01
    fake = _RecordingRedis()
    worker.r = fake

    thread = threading.Thread(target=worker._heartbeat_loop, daemon=True)
    thread.start()
    time.sleep(0.05)
    worker._stop_beating.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    settled = fake.beat_count()
    time.sleep(0.05)
    assert fake.beat_count() == settled, "kept beating after being stopped"
