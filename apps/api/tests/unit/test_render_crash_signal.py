"""An engine process that dies of a crash signal is reported as one.

The fact travels as structure, never as log text (the runner's output echoes
the visitor's parameters): the engine reads the process's exit status, the
render worker puts ``crash_signal`` on the part's error event, and the API
settles a metered render from it (tests/e2e/test_commons_render_quota.py).

The engine tests run a real child that kills itself, through the same launch
paths the worker uses.
"""
import json
import signal
import sys
from pathlib import Path

import pytest

from services.engine import cadquery_engine, render_limits
from services.engine.render_contract import RENDER_FIELD_CRASH_SIGNAL
from services.engine.render_engine import CRASH_SIGNALS, EngineResult, crash_signal_of

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

# Imported after the sys.path line above, which is what makes it importable.
import render_worker

posix_only = pytest.mark.skipif(not render_limits.limits_supported(), reason="POSIX signals")


def _dies_of(name: str) -> list:
    return [sys.executable, "-c", f"import os, signal; os.kill(os.getpid(), signal.{name})"]


EXITS_ONE = [sys.executable, "-c", "print('StdFail_NotDone'); raise SystemExit(1)"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("RENDER_RLIMIT_AS_MB", "RENDER_RLIMIT_CPU_S", "MALLOC_ARENA_MAX"):
        monkeypatch.delenv(name, raising=False)


class TestCrashSignalOf:
    @pytest.mark.parametrize("name", ["SIGSEGV", "SIGBUS", "SIGILL", "SIGFPE", "SIGABRT"])
    def test_crash_signals(self, name):
        number = int(getattr(signal, name))
        assert number in CRASH_SIGNALS
        assert crash_signal_of(-number) == number

    @pytest.mark.parametrize("name", ["SIGKILL", "SIGTERM", "SIGXCPU", "SIGINT"])
    def test_our_own_stops_are_not_crashes(self, name):
        # SIGKILL is our timeout and cancel (and the OOM killer), SIGXCPU the
        # CPU-time limit a visitor's parameters can reach, SIGTERM a shutdown.
        assert crash_signal_of(-int(getattr(signal, name))) is None

    @pytest.mark.parametrize("value", [0, 1, 2, 139, None, True, "-11", -11.0, object()])
    def test_everything_else_is_not_a_crash(self, value):
        assert crash_signal_of(value) is None


class TestEngineResult:
    def test_is_the_two_tuple_callers_already_handle(self):
        result = EngineResult(False, "log", 11)
        success, output = result
        assert (success, output) == (False, "log")
        assert result == (False, "log")
        assert result.crash_signal == 11
        assert EngineResult(True, "ok").crash_signal is None


@posix_only
class TestCadQueryLaunchPathsReportTheCrash:
    def test_cancellable_path(self):
        result = cadquery_engine._run_render(_dies_of("SIGSEGV"), is_cancelled=lambda: False)
        assert result == (False, result[1])
        assert result.crash_signal == signal.SIGSEGV
        assert "Render engine process crashed (SIGSEGV)" in result[1]

    def test_one_shot_path(self):
        result = cadquery_engine._run_render(_dies_of("SIGABRT"))
        assert result[0] is False
        assert result.crash_signal == signal.SIGABRT
        assert "crashed (SIGABRT)" in result[1]

    def test_run_render_keeps_it_through_the_log_sanitizer(self):
        result = cadquery_engine.run_render(_dies_of("SIGSEGV"), is_cancelled=lambda: False)
        assert result[0] is False
        assert result.crash_signal == signal.SIGSEGV

    def test_a_script_error_is_not_a_crash(self):
        result = cadquery_engine.run_render(EXITS_ONE, is_cancelled=lambda: False)
        assert result[0] is False and "StdFail_NotDone" in result[1]
        assert result.crash_signal is None

    def test_a_kill_is_not_a_crash(self):
        result = cadquery_engine._run_render(_dies_of("SIGKILL"), is_cancelled=lambda: False)
        assert result[0] is False
        assert getattr(result, "crash_signal", None) is None

    def test_streamed_path(self):
        events = [json.loads(e) for e in cadquery_engine.stream_render(
            _dies_of("SIGSEGV"), "body", 0, 100, 0, 1, is_cancelled=lambda: False)]
        error = events[-1]
        assert error["event"] == "error"
        assert error[RENDER_FIELD_CRASH_SIGNAL] == signal.SIGSEGV
        assert error["message"].startswith(f"Render failed with code {-signal.SIGSEGV}")
        assert "crashed (SIGSEGV)" in error["message"]

    def test_streamed_script_error_carries_no_crash_signal(self):
        events = [json.loads(e) for e in cadquery_engine.stream_render(
            EXITS_ONE, "body", 0, 100, 0, 1, is_cancelled=lambda: False)]
        assert events[-1] == {"event": "error", "part": "body", "message": "Render failed with code 1"}


class TestDescribeExit:
    def test_names_the_signal(self):
        assert "crashed (SIGSEGV)" in render_limits.describe_exit(-signal.SIGSEGV)

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="RLIMIT_AS enforced on Linux only")
    def test_names_the_ceiling_next_to_it(self, monkeypatch):
        # An allocation refused by RLIMIT_AS in native code ends as a crash,
        # so the ceiling is the first thing an operator needs to see.
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "777")
        assert "777 MiB (RENDER_RLIMIT_AS_MB)" in render_limits.describe_exit(-signal.SIGSEGV)
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "0")
        assert "RENDER_RLIMIT_AS_MB" not in render_limits.describe_exit(-signal.SIGSEGV)


# ──────────────────────────────────────────────
# The render worker puts it on the part's error event
# ──────────────────────────────────────────────

def _task(tmp_path, engine="cadquery"):
    return {
        "job_id": "job-1", "engine": engine, "part": "body",
        "scad_path": "/projects/flange-plate/main.py",
        "output_path": str(tmp_path / "flange_body.glb"), "export_format": "glb",
        "part_index": 0, "num_parts": 1, "part_base": 0, "part_weight": 100,
        "payload": {"project_slug": "flange-plate", "params": {"plate_radius": 40}, "mode_map": {"body": 0},
                    "stl_prefix": "flange_", "scad_filename": "main.py", "scad_content_hash": "abc"},
    }


@pytest.fixture
def events(monkeypatch):
    published = []
    monkeypatch.setattr(render_worker, "_publish_job_event",
                        lambda job_id, payload, emit_final=False: published.append((payload, emit_final)))
    monkeypatch.setattr(render_worker, "_set_active_job", lambda *a, **k: None)
    monkeypatch.setattr(render_worker, "_clear_active_job", lambda *a: None)
    monkeypatch.setattr(render_worker, "_is_cancelled", lambda job_id: False)
    monkeypatch.setattr(render_worker, "get_manifest", lambda slug: object())
    monkeypatch.setattr(render_worker, "invalidate_cache", lambda slug: None)
    monkeypatch.setattr(render_worker, "prepare_graph_script", lambda scad, manifest: scad)
    monkeypatch.setattr(render_worker, "build_cadquery_command", lambda *a, **k: ["cq"])
    return published


def _final_error(published):
    finals = [payload for payload, emit_final in published if emit_final]
    assert len(finals) == 1 and finals[0]["event"] == "error", published
    return finals[0]


class TestWorkerErrorEvent:
    @pytest.mark.parametrize("engine", ["cadquery", "graph"])
    def test_sync_crash(self, events, monkeypatch, tmp_path, engine):
        monkeypatch.setattr(render_worker, "run_cadquery_render",
                            lambda *a, **k: EngineResult(False, "died", 11))
        render_worker.process_sync_task(_task(tmp_path, engine))
        assert _final_error(events)[RENDER_FIELD_CRASH_SIGNAL] == 11

    def test_sync_script_error(self, events, monkeypatch, tmp_path):
        # A plain tuple is what the warm pool and every older caller returns.
        monkeypatch.setattr(render_worker, "run_cadquery_render", lambda *a, **k: (False, "StdFail_NotDone"))
        render_worker.process_sync_task(_task(tmp_path))
        assert RENDER_FIELD_CRASH_SIGNAL not in _final_error(events)

    @pytest.mark.parametrize("engine", ["cadquery", "graph"])
    def test_streamed_crash(self, events, monkeypatch, tmp_path, engine):
        def crashed(*_a, **_k):
            yield json.dumps({"event": "error", "part": "body", "message": "Render failed with code -11",
                              RENDER_FIELD_CRASH_SIGNAL: 11})
        monkeypatch.setattr(render_worker, "stream_cadquery_render", crashed)
        render_worker.process_stream_task(_task(tmp_path, engine))
        assert _final_error(events)[RENDER_FIELD_CRASH_SIGNAL] == 11

    def test_streamed_script_error(self, events, monkeypatch, tmp_path):
        def failed(*_a, **_k):
            yield json.dumps({"event": "error", "part": "body", "message": "Render failed with code 1"})
        monkeypatch.setattr(render_worker, "stream_cadquery_render", failed)
        render_worker.process_stream_task(_task(tmp_path))
        assert RENDER_FIELD_CRASH_SIGNAL not in _final_error(events)

    @pytest.mark.parametrize("value", [None, True, "11", 0, -11, 11.0])
    def test_only_a_signal_number_is_reported(self, value):
        assert render_worker._crash_fields(value) == {}
