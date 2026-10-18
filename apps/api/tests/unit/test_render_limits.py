"""Per-process rlimits on render subprocesses (A1 D-7).

A render that runs away must fail as that render's error — not grow until the
container is OOM-killed with every other render in it, and not spin forever.
The real-subprocess tests launch a misbehaving child through the same
OpenSCAD / CadQuery launch paths the worker uses.
"""
import signal
import sys

import pytest

from services.engine import render_limits

posix_only = pytest.mark.skipif(not render_limits.limits_supported(), reason="no resource module")
# RLIMIT_AS is not enforced by macOS; the memory tests are Linux-only (CI runs them).
linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="RLIMIT_AS enforced on Linux only")

HOG_MEMORY = "x = bytearray(1024 * 1024 * 1024); print('allocated', len(x))"
HOG_CPU = "while True: pass"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("RENDER_RLIMIT_AS_MB", "RENDER_RLIMIT_CPU_S", "MALLOC_ARENA_MAX"):
        monkeypatch.delenv(name, raising=False)


class TestConfiguration:
    def test_defaults_fit_inside_the_pod_limit(self):
        # The worker container is limited to 2Gi; one render must stay below it.
        assert 0 < render_limits.address_space_limit_bytes() < 2 * 1024 ** 3
        assert render_limits.cpu_limit_seconds() > render_limits.RENDER_TIMEOUT_S

    @pytest.mark.parametrize("raw", ["abc", "-5", " "])
    def test_bad_values_fall_back_to_defaults(self, monkeypatch, raw):
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", raw)
        monkeypatch.setenv("RENDER_RLIMIT_CPU_S", raw)
        assert render_limits.address_space_limit_bytes() == render_limits.DEFAULT_AS_MB * 1024 * 1024
        assert render_limits.cpu_limit_seconds() == render_limits.DEFAULT_CPU_S

    def test_zero_disables_both(self, monkeypatch):
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "0")
        monkeypatch.setenv("RENDER_RLIMIT_CPU_S", "0")
        assert render_limits.render_preexec_fn() is None
        assert render_limits.limited_env({"A": "1"}) == {"A": "1"}

    def test_platform_without_resource_runs_unlimited(self, monkeypatch):
        monkeypatch.setattr(render_limits, "resource", None)
        assert render_limits.render_preexec_fn() is None
        assert render_limits.limited_env(None) is None
        assert render_limits.describe_exit(-9) is None

    @linux_only
    def test_arena_cap_set_only_with_the_address_space_limit(self, monkeypatch):
        assert render_limits.limited_env({"A": "1"}) == {"A": "1", "MALLOC_ARENA_MAX": "2"}
        assert render_limits.limited_env({"MALLOC_ARENA_MAX": "4"})["MALLOC_ARENA_MAX"] == "4"
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "0")
        assert "MALLOC_ARENA_MAX" not in render_limits.limited_env({"A": "1"})

    def test_pool_worker_cpu_budget_spans_its_jobs(self, monkeypatch):
        from services.engine import cq_pool
        monkeypatch.setenv("RENDER_RLIMIT_CPU_S", "100")
        monkeypatch.setenv("YANTRA4D_CQ_WORKER_MAX_JOBS", "5")
        assert cq_pool.pool_worker_cpu_budget() == 500
        monkeypatch.setenv("YANTRA4D_CQ_WORKER_MAX_JOBS", "0")  # never recycles
        assert cq_pool.pool_worker_cpu_budget() == 0


@posix_only
class TestCpuLimitThroughLaunchPaths:
    def test_default_limits_spawn_on_this_platform(self):
        """The defaults never make the spawn itself fail (macOS rejects RLIMIT_AS)."""
        import subprocess
        proc = subprocess.run([sys.executable, "-c", "print('ok')"], capture_output=True, text=True, check=False,
                              timeout=60, env=render_limits.limited_env(None),
                              preexec_fn=render_limits.render_preexec_fn())
        assert proc.returncode == 0 and "ok" in proc.stdout


    def test_openscad_path_stops_a_spinning_render(self, monkeypatch):
        from services.engine import openscad
        monkeypatch.setenv("RENDER_RLIMIT_CPU_S", "1")
        result = openscad.run_render([sys.executable, "-c", HOG_CPU], is_cancelled=lambda: False)
        assert result.success is False
        assert "CPU-time limit" in result.stderr

    def test_cadquery_path_stops_a_spinning_render(self, monkeypatch):
        from services.engine import cadquery_engine
        monkeypatch.setenv("RENDER_RLIMIT_CPU_S", "1")
        ok, output = cadquery_engine._run_render([sys.executable, "-c", HOG_CPU], is_cancelled=lambda: False)
        assert ok is False
        assert "CPU-time limit" in output

    def test_describe_exit_names_sigxcpu_only(self):
        assert "CPU-time limit" in render_limits.describe_exit(-signal.SIGXCPU)
        assert render_limits.describe_exit(-signal.SIGKILL) is None  # cancel / wall timeout
        assert render_limits.describe_exit(1) is None


@linux_only
class TestMemoryLimitThroughLaunchPaths:
    def test_openscad_path_fails_an_oversized_render_cleanly(self, monkeypatch):
        from services.engine import openscad
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "256")
        result = openscad.run_render([sys.executable, "-c", HOG_MEMORY], is_cancelled=lambda: False)
        assert result.success is False
        assert "MemoryError" in result.stderr

    def test_cadquery_path_fails_an_oversized_render_cleanly(self, monkeypatch):
        from services.engine import cadquery_engine
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "256")
        ok, output = cadquery_engine._run_render([sys.executable, "-c", HOG_MEMORY], is_cancelled=lambda: False)
        assert ok is False
        assert "MemoryError" in output
        assert "allocated" not in output

    def test_sync_cadquery_path_is_limited_too(self, monkeypatch):
        from services.engine import cadquery_engine
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "256")
        ok, output = cadquery_engine._run_render([sys.executable, "-c", HOG_MEMORY])
        assert ok is False
        assert "MemoryError" in output

    def test_a_real_cadquery_export_fits_the_default_ceiling(self, tmp_path):
        """The default must not refuse ordinary CadQuery work (OCP + VTK map a lot of address space)."""
        pytest.importorskip("cadquery")
        import subprocess
        out = tmp_path / "box.stl"
        code = ("import sys, cadquery as cq; "
                "cq.exporters.export(cq.Workplane().box(10, 10, 10).fillet(1), sys.argv[1])")
        proc = subprocess.run(
            [sys.executable, "-c", code, str(out)], capture_output=True, text=True, timeout=240, check=False,
            env=render_limits.limited_env(None), preexec_fn=render_limits.render_preexec_fn(),
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert out.stat().st_size > 0
