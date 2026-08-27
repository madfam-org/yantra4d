"""Integration tests for the warm CadQuery pool against a real cadquery kernel.

The unit tests fake the workers; these drive actual ``cq_runner.py --serve``
subprocesses so the JSON-lines protocol, the sandbox path, and the warm-reuse
claim are exercised end to end. Skipped when cadquery is not importable, which
is why the unit suite must stand on its own.
"""
import json
import time

import pytest

from services.engine import cadquery_engine
from services.engine.cq_pool import CadQueryPool

cadquery = pytest.importorskip("cadquery", reason="CadQuery kernel not installed")

SCRIPT = """
import cadquery as cq
result = cq.Workplane("XY").box(size, size, size)
"""


@pytest.fixture
def cartridge(tmp_path):
    path = tmp_path / "box.py"
    path.write_text(SCRIPT)
    return path


@pytest.fixture
def pool():
    p = CadQueryPool()
    yield p
    p.shutdown()


class TestRealWarmWorker:
    def test_renders_through_a_warm_worker(self, pool, cartridge, tmp_path):
        out = tmp_path / "box.stl"
        result = pool.submit(
            str(cartridge), str(out), json.dumps({"size": 10}), "stl"
        )
        assert result is not None, "pool declined the job"
        success, output = result
        assert success is True, output
        assert out.is_file() and out.stat().st_size > 0

    def test_output_is_watertight(self, pool, cartridge, tmp_path):
        """mesh_integrity is the repo's own verdict on rendered geometry."""
        trimesh = pytest.importorskip("trimesh")
        from services.engine.mesh_integrity import assess

        out = tmp_path / "box.stl"
        success, output = pool.submit(
            str(cartridge), str(out), json.dumps({"size": 12}), "stl"
        )
        assert success is True, output
        verdict = assess(trimesh.load(str(out)))
        assert verdict.watertight is True, verdict.summary

    def test_second_render_reuses_the_warm_kernel(self, pool, cartridge, tmp_path):
        """The whole point: the OCCT import is paid once, not per render."""
        first_out = tmp_path / "a.stl"
        t0 = time.monotonic()
        pool.submit(str(cartridge), str(first_out), json.dumps({"size": 8}), "stl")
        cold = time.monotonic() - t0

        second_out = tmp_path / "b.stl"
        t1 = time.monotonic()
        pool.submit(str(cartridge), str(second_out), json.dumps({"size": 9}), "stl")
        warm = time.monotonic() - t1

        assert second_out.is_file()
        # The first call includes worker startup + import; the second must not.
        assert warm < cold, f"warm {warm:.2f}s not faster than cold {cold:.2f}s"
        assert pool.stats()["live"] == 1

    def test_bad_cartridge_fails_without_killing_the_worker(self, pool, tmp_path):
        broken = tmp_path / "broken.py"
        broken.write_text("raise ValueError('cartridge is wrong')\n")
        out = tmp_path / "nope.stl"

        success, output = pool.submit(
            str(broken), str(out), json.dumps({}), "stl"
        )
        assert success is False
        assert "cartridge is wrong" in output
        # The worker survived a bad cartridge and still serves the next job.
        assert pool.stats()["idle"] == 1

    def test_sandbox_rejects_a_disallowed_extension(self, pool, tmp_path):
        """commons_sandbox validation runs identically in serve mode."""
        bad = tmp_path / "script.txt"
        bad.write_text("result = None\n")
        success, output = pool.submit(
            str(bad), str(tmp_path / "o.stl"), json.dumps({}), "stl"
        )
        assert success is False
        assert "Error" in output


class TestEngineEndToEnd:
    def test_run_render_produces_geometry_through_the_engine_api(
        self, cartridge, tmp_path, monkeypatch
    ):
        """The public engine entrypoint, unchanged contract, warm underneath."""
        monkeypatch.setenv("YANTRA4D_CQ_WORKERS", "1")
        out = tmp_path / "engine.stl"
        cmd = cadquery_engine.build_cadquery_command(
            str(out), str(cartridge), {"size": 6}, "stl"
        )
        try:
            success, output = cadquery_engine.run_render(cmd)
            assert success is True, output
            assert out.is_file() and out.stat().st_size > 0
        finally:
            cadquery_engine.cq_pool.reset()
