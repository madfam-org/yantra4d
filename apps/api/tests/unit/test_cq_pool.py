"""Tests for the warm CadQuery worker pool.

The pool's job is to remove the per-render OCCT import cost without changing the
render contract. These tests pin the properties that make that safe: a wedged or
crashed worker never poisons the pool, workers recycle, and a pool that cannot
start degrades to the historical per-render subprocess spawn rather than failing
a render closed.

Workers are faked here — real CadQuery workers are exercised by the integration
test in tests/integration/test_cq_pool_warm.py, which skips when cadquery is absent.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from services.engine import cadquery_engine, cq_pool
from services.engine.cq_pool import CadQueryPool, CancelledRender, _readline_with_timeout


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "YANTRA4D_CQ_WORKERS",
        "YANTRA4D_CQ_WORKER_MAX_JOBS",
        "YANTRA4D_CQ_POOL_ENABLED",
        "YANTRA4D_CQ_WORKER_START_TIMEOUT_S",
    ):
        monkeypatch.delenv(var, raising=False)


class FakeWorker:
    """Stands in for a persistent cq_runner subprocess."""

    def __init__(self, results=None, alive=True):
        self.jobs_served = 0
        self.results = list(results or [(True, "Rendering complete.")])
        self.killed = False
        self._alive = alive
        self.requests = []

    def await_ready(self, timeout):
        """A fake is warm by construction; the real one blocks on the import."""
        return

    def run(self, request, timeout, is_cancelled=None):
        self.requests.append(request)
        outcome = self.results.pop(0) if self.results else (True, "ok")
        if isinstance(outcome, Exception):
            raise outcome
        self.jobs_served += 1
        return outcome

    def alive(self):
        return self._alive and not self.killed

    def kill(self):
        self.killed = True


def _pool_with(workers):
    """A pool whose worker construction yields *workers* in order."""
    pool = CadQueryPool()
    made = iter(workers)

    def _make(env=None):
        return next(made)

    patcher = patch.object(cq_pool, "_Worker", side_effect=_make)
    patcher.start()
    # await_ready is a method on the real _Worker; fakes are already ready.
    return pool, patcher


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class TestConfiguration:
    def test_default_pool_size_is_two(self):
        assert cq_pool.pool_size() == 2

    def test_pool_size_from_env(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "5")
        assert cq_pool.pool_size() == 5

    def test_zero_disables_the_pool(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "0")
        assert cq_pool.pool_size() == 0
        assert CadQueryPool().submit("s.py", "o.stl", "{}", "stl") is None

    def test_garbage_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "many")
        assert cq_pool.pool_size() == 2

    def test_negative_clamped_to_minimum(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "-3")
        assert cq_pool.pool_size() == 0


# ---------------------------------------------------------------------------
# Happy path and warm reuse
# ---------------------------------------------------------------------------
class TestWarmReuse:
    def test_submit_returns_worker_result(self):
        worker = FakeWorker([(True, "Rendering complete.")])
        pool, patcher = _pool_with([worker])
        try:
            assert pool.submit("s.py", "o.stl", '{"a":1}', "stl") == (
                True, "Rendering complete."
            )
            assert worker.requests[0]["params_json"] == '{"a":1}'
        finally:
            patcher.stop()

    def test_second_job_reuses_the_same_warm_worker(self):
        worker = FakeWorker([(True, "one"), (True, "two")])
        pool, patcher = _pool_with([worker])
        try:
            pool.submit("s.py", "o.stl", "{}", "stl")
            pool.submit("s.py", "o.stl", "{}", "stl")
            # One process served both jobs — that IS the lever.
            assert worker.jobs_served == 2
            assert pool.stats()["live"] == 1
        finally:
            patcher.stop()

    def test_failed_render_is_reported_not_swallowed(self):
        worker = FakeWorker([(False, "Error executing CadQuery script: boom")])
        pool, patcher = _pool_with([worker])
        try:
            success, output = pool.submit("s.py", "o.stl", "{}", "stl")
            assert success is False
            assert "boom" in output
            # A script error is the cartridge's fault, not the worker's;
            # the warm worker stays in the pool.
            assert worker.killed is False
        finally:
            patcher.stop()


# ---------------------------------------------------------------------------
# A wedged or crashed worker must not poison the pool
# ---------------------------------------------------------------------------
class TestPoisonResistance:
    def test_timeout_kills_the_worker_and_reports_failure(self):
        worker = FakeWorker([TimeoutError("Render timed out after 300 seconds")])
        pool, patcher = _pool_with([worker])
        try:
            success, output = pool.submit("s.py", "o.stl", "{}", "stl")
            assert success is False
            assert "timed out" in output
            assert worker.killed is True          # never reused
            assert pool.stats()["live"] == 0      # slot freed
        finally:
            patcher.stop()

    def test_crash_mid_job_yields_none_so_caller_falls_back(self):
        worker = FakeWorker([BrokenPipeError("worker died")])
        pool, patcher = _pool_with([worker])
        try:
            # None means "unproven, retry via subprocess", not "render failed".
            assert pool.submit("s.py", "o.stl", "{}", "stl") is None
            assert worker.killed is True
        finally:
            patcher.stop()

    def test_cancellation_kills_worker_and_matches_subprocess_wording(self):
        worker = FakeWorker([CancelledRender("Render cancelled by user request")])
        pool, patcher = _pool_with([worker])
        try:
            success, output = pool.submit(
                "s.py", "o.stl", "{}", "stl", is_cancelled=lambda: True
            )
            assert success is False
            assert output == "Render cancelled by user request"
            assert worker.killed is True
        finally:
            patcher.stop()

    def test_worker_that_died_while_idle_is_replaced(self):
        dead = FakeWorker([(True, "a")])
        fresh = FakeWorker([(True, "b")])
        pool, patcher = _pool_with([dead, fresh])
        try:
            pool.submit("s.py", "o.stl", "{}", "stl")
            dead._alive = False  # died between jobs
            assert pool.submit("s.py", "o.stl", "{}", "stl") == (True, "b")
            assert dead.killed is True
        finally:
            patcher.stop()


# ---------------------------------------------------------------------------
# Recycling
# ---------------------------------------------------------------------------
class TestRecycling:
    def test_worker_recycled_after_max_jobs(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKER_MAX_JOBS", "2")
        first = FakeWorker([(True, "1"), (True, "2")])
        second = FakeWorker([(True, "3")])
        pool, patcher = _pool_with([first, second])
        try:
            pool.submit("s.py", "o.stl", "{}", "stl")
            pool.submit("s.py", "o.stl", "{}", "stl")
            assert first.killed is True   # spent, retired after 2 jobs
            assert pool.submit("s.py", "o.stl", "{}", "stl") == (True, "3")
            assert second.jobs_served == 1
        finally:
            patcher.stop()

    def test_zero_max_jobs_means_never_recycle(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKER_MAX_JOBS", "0")
        worker = FakeWorker([(True, "1"), (True, "2"), (True, "3")])
        pool, patcher = _pool_with([worker])
        try:
            for _ in range(3):
                pool.submit("s.py", "o.stl", "{}", "stl")
            assert worker.killed is False
            assert worker.jobs_served == 3
        finally:
            patcher.stop()


# ---------------------------------------------------------------------------
# Graceful fallback — never fail closed on the pool
# ---------------------------------------------------------------------------
class TestGracefulFallback:
    def test_worker_that_cannot_start_disables_pool_and_returns_none(self):
        pool = CadQueryPool()
        with patch.object(cq_pool, "_Worker", side_effect=RuntimeError("no cadquery")):
            assert pool.submit("s.py", "o.stl", "{}", "stl") is None
        stats = pool.stats()
        assert stats["disabled"] is True
        assert "no cadquery" in stats["disabled_reason"]
        assert stats["live"] == 0

    def test_disabled_pool_stops_retrying(self):
        pool = CadQueryPool()
        with patch.object(cq_pool, "_Worker", side_effect=RuntimeError("nope")) as made:
            pool.submit("s.py", "o.stl", "{}", "stl")
            pool.submit("s.py", "o.stl", "{}", "stl")
            pool.submit("s.py", "o.stl", "{}", "stl")
            # Spawning a doomed process per render would be worse than no pool.
            assert made.call_count == 1

    def test_saturated_pool_declines_rather_than_queueing(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "1")
        held = FakeWorker([(True, "held")])
        pool, patcher = _pool_with([held])
        try:
            worker = pool._acquire(env=None)   # occupy the only slot
            assert worker is not None
            assert pool.submit("s.py", "o.stl", "{}", "stl") is None
        finally:
            patcher.stop()


# ---------------------------------------------------------------------------
# readline helper
# ---------------------------------------------------------------------------
class TestReadlineWithTimeout:
    def test_returns_stripped_line(self):
        stream = MagicMock()
        stream.readline.return_value = '{"ok": true}\n'
        assert _readline_with_timeout(stream, 5) == '{"ok": true}'

    def test_returns_none_on_timeout(self):
        import threading
        blocked = threading.Event()
        stream = MagicMock()
        stream.readline.side_effect = lambda: blocked.wait(10) or ""
        try:
            assert _readline_with_timeout(stream, 0.2) is None
        finally:
            blocked.set()

    def test_returns_cancelled_sentinel_when_cancel_fires(self):
        import threading
        blocked = threading.Event()
        stream = MagicMock()
        stream.readline.side_effect = lambda: blocked.wait(10) or ""
        try:
            result = _readline_with_timeout(stream, 5, is_cancelled=lambda: True)
            assert result is cq_pool._CANCELLED
        finally:
            blocked.set()


# ---------------------------------------------------------------------------
# Engine integration: dispatch and fallback
# ---------------------------------------------------------------------------
class TestEngineDispatch:
    def test_runner_shaped_command_is_destructured(self):
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {"a": 1}, "stl")
        job = cadquery_engine._job_from_cmd(cmd)
        assert job == {
            "script_path": "s.py",
            "output_path": "o.stl",
            "params_json": json.dumps({"a": 1}),
            "export_format": "stl",
        }

    def test_foreign_command_is_not_pooled(self):
        # Anything not built by build_cadquery_command runs the historical path.
        assert cadquery_engine._job_from_cmd(["python", "-c", "print(1)"]) is None
        assert cadquery_engine._job_from_cmd(["cmd"]) is None

    def test_run_render_uses_pool_when_it_accepts(self):
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {}, "stl")
        with patch.object(
            cadquery_engine.cq_pool, "submit", return_value=(True, "warm")
        ) as submit, patch.object(cadquery_engine.subprocess, "run") as spawn:
            assert cadquery_engine.run_render(cmd) == (True, "warm")
            assert submit.called
            assert not spawn.called  # no cold subprocess

    def test_run_render_falls_back_when_pool_declines(self):
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {}, "stl")
        with patch.object(
            cadquery_engine.cq_pool, "submit", return_value=None
        ), patch.object(cadquery_engine.subprocess, "run") as spawn:
            spawn.return_value = MagicMock(stdout="cold", stderr="")
            assert cadquery_engine.run_render(cmd) == (True, "cold")
            assert spawn.called

    def test_run_render_falls_back_when_pool_raises(self):
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {}, "stl")
        with patch.object(
            cadquery_engine.cq_pool, "submit", side_effect=RuntimeError("pool bug")
        ), patch.object(cadquery_engine.subprocess, "run") as spawn:
            spawn.return_value = MagicMock(stdout="cold", stderr="")
            # A bug in the pool must not become a render failure.
            assert cadquery_engine.run_render(cmd) == (True, "cold")

    def test_pool_can_be_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_CQ_POOL_ENABLED", "0")
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {}, "stl")
        with patch.object(cadquery_engine.cq_pool, "submit") as submit, patch.object(
            cadquery_engine.subprocess, "run"
        ) as spawn:
            spawn.return_value = MagicMock(stdout="cold", stderr="")
            cadquery_engine.run_render(cmd)
            assert not submit.called

    def test_cancellation_is_forwarded_to_the_pool(self):
        cmd = cadquery_engine.build_cadquery_command("o.stl", "s.py", {}, "stl")
        def flag():
            return False

        with patch.object(
            cadquery_engine.cq_pool, "submit", return_value=(True, "warm")
        ) as submit:
            cadquery_engine.run_render(cmd, is_cancelled=flag)
        # The render worker ALWAYS passes is_cancelled; if the pool ignored it
        # this lever would be dead code in production.
        assert submit.call_args.kwargs["is_cancelled"] is flag
