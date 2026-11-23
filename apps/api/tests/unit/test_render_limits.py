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
    for name in ("RENDER_RLIMIT_AS_MB", "RENDER_RLIMIT_CPU_S", "MALLOC_ARENA_MAX", *render_limits.THREAD_CAPS):
        monkeypatch.delenv(name, raising=False)


def _render_worker_container():
    """The render-worker container's env and memory limit (MiB) from the manifest."""
    from pathlib import Path

    import yaml

    manifest = Path(__file__).resolve().parents[4] / "k8s/production/yantra4d-backend-deployment.yaml"
    docs = [d for d in yaml.safe_load_all(manifest.read_text()) if d and d.get("kind") == "Deployment"]
    containers = docs[0]["spec"]["template"]["spec"]["containers"]
    worker = next(c for c in containers if c["name"] == "render-worker")
    env = {e["name"]: e.get("value") for e in worker.get("env", []) if "value" in e}
    raw = worker["resources"]["limits"]["memory"]
    units = {"Mi": 1, "Gi": 1024}
    return env, int(raw[:-2]) * units[raw[-2:]]


class TestConfiguration:
    def test_defaults_agree_with_the_render_worker_container(self):
        """The ceiling, the warm-worker count and the container's memory limit
        are one budget, set in two files. The worst case the container must
        hold is the worker process, the idle warm workers, and the one render
        in flight at the point its ceiling refuses it.

        The per-process figures are measurements (2026-11-22): the render
        worker's working set in production, a warm worker idle after importing
        CadQuery, and the address space a CadQuery render maps but never
        touches (VmPeak - VmHWM, 595-620 MiB across seven Commons cartridges).
        """
        worker_mib, warm_idle_mib, never_resident_mib = 812, 640, 590
        env, limit_mib = _render_worker_container()
        assert env["RENDER_RLIMIT_AS_MB"] == str(render_limits.DEFAULT_AS_MB), \
            "set the manifest and the code default together"
        warm_workers = int(env.get("YANTRA4D_CQ_WORKERS", "2"))
        in_flight = render_limits.DEFAULT_AS_MB - never_resident_mib
        worst = worker_mib + warm_workers * warm_idle_mib + in_flight
        assert worst <= limit_mib * 0.9, (
            f"worker {worker_mib} + {warm_workers} warm x {warm_idle_mib} + render {in_flight} "
            f"= {worst} MiB, over 90% of the container's {limit_mib} MiB"
        )
        assert render_limits.address_space_limit_bytes() == render_limits.DEFAULT_AS_MB * 1024 * 1024
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
    def test_caps_set_only_with_the_address_space_limit(self, monkeypatch):
        # One BLAS thread per CPU maps 49 MiB each: uncapped, the address space
        # a render needs depends on the node, which is how the 1536 default
        # passed on 4 CPUs and killed every render on 12.
        assert render_limits.limited_env({"A": "1"}) == {
            "A": "1", "MALLOC_ARENA_MAX": "2", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        }
        kept = render_limits.limited_env({"MALLOC_ARENA_MAX": "4", "OPENBLAS_NUM_THREADS": "3"})
        assert kept["MALLOC_ARENA_MAX"] == "4" and kept["OPENBLAS_NUM_THREADS"] == "3"
        monkeypatch.setenv("RENDER_RLIMIT_AS_MB", "0")
        assert render_limits.limited_env({"A": "1"}) == {"A": "1"}

    @linux_only
    def test_caps_reach_a_child_that_inherits_the_environment(self):
        child = render_limits.limited_env(None)
        assert child is not None and child["OPENBLAS_NUM_THREADS"] == "1"

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

    def test_describe_exit_names_the_cpu_limit_and_stays_quiet_on_a_kill(self):
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
