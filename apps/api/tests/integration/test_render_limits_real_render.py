"""A real CadQuery render under the default render limits (Linux).

``tests/unit/test_render_limits.py`` proves the limits stop a runaway child,
using small Python snippets. These tests prove the other half: the defaults do
not stop ordinary work. They run a real cartridge to GLB (CadQuery's STEP
export, then cascadio's transcode) through the launch paths the render worker
uses, with nothing overridden.

A render refused by ``RLIMIT_AS`` does not fail politely. The allocation is
refused inside native code (OCP, VTK, OpenBLAS) and the process dies with
SIGSEGV, which the Studio reports as ``Render failed with code -11``. That is
how every free Commons render failed in production on 2026-11-21.

Linux only: macOS does not enforce ``RLIMIT_AS``. In CI a missing kernel fails
the test instead of skipping it — a skipped test is how the defect shipped.
"""
import json
import os
import subprocess
import sys

import pytest

from services.engine import cadquery_engine, render_limits
from services.engine.cq_pool import CadQueryPool

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="RLIMIT_AS is enforced on Linux only"
)

#: A flange: a disc with a bore and a bolt circle. Close to the Commons
#: ``flange-plate`` cartridge the defect was reported on.
SCRIPT = """
import cadquery as cq

result = (
    cq.Workplane("XY")
    .circle(plate_radius).extrude(thickness)
    .faces(">Z").workplane().hole(bore)
    .faces(">Z").workplane()
    .polarArray(bolt_circle, 0, 360, bolts).hole(bolt_d)
    .edges("%CIRCLE").edges(">Z").chamfer(0.4)
)
"""
PARAMS = {"plate_radius": 40, "thickness": 6, "bore": 20, "bolt_circle": 28, "bolts": 6, "bolt_d": 5}

#: The default ceiling must clear the projected peak by this factor.
HEADROOM = 1.5
#: CPUs the per-CPU slope is projected to (production nodes have 12).
PROJECTED_CPUS = 32

#: Runs ``cq_runner.py`` in this process and reports the process's own peaks
#: from ``/proc/self/status`` on the way out (they are gone once it exits).
MEASURE = r"""
import json, os, runpy, sys
keep = os.environ.get("Y4D_MEASURE_CPUS")
if keep:
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[: int(keep)]))
runner = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(runner))
code = 0
try:
    runpy.run_path(runner, run_name="__main__")
except SystemExit as exc:
    code = exc.code or 0
fields = {}
with open("/proc/self/status") as fh:
    for line in fh:
        name, _, rest = line.partition(":")
        if name in ("VmPeak", "VmHWM", "VmData"):
            fields[name] = int(rest.split()[0]) // 1024
        elif name == "Threads":
            fields[name] = int(rest)
fields.update(exit=code, cpus=os.cpu_count(), affinity=len(os.sched_getaffinity(0)))
print("Y4D_MEASURE " + json.dumps(fields))
"""


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """The point is the defaults: nothing in the environment may override them."""
    for name in ("RENDER_RLIMIT_AS_MB", "RENDER_RLIMIT_CPU_S", "MALLOC_ARENA_MAX"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _kernel_present():
    try:
        import cadquery  # noqa: F401
        import cascadio  # noqa: F401
    except ImportError as exc:
        if os.environ.get("CI"):
            pytest.fail(f"CI must run these with the render kernel installed: {exc}")
        pytest.skip(f"CadQuery kernel not installed: {exc}")


@pytest.fixture
def cartridge(tmp_path):
    path = tmp_path / "flange.py"
    path.write_text(SCRIPT)
    return path


def _command(cartridge, out, export_format="glb"):
    return cadquery_engine.build_cadquery_command(str(out), str(cartridge), PARAMS, export_format)


def _drain(generator):
    """Run a ``stream_render`` generator; return (its return value, its events)."""
    events = []
    while True:
        try:
            events.append(json.loads(next(generator)))
        except StopIteration as stop:
            return stop.value, events


class TestDefaultLimitsLetARealRenderFinish:
    def test_streamed_render(self, cartridge, tmp_path):
        """``/api/render-stream``: the path every Studio "Generate" takes."""
        out = tmp_path / "flange.glb"
        ok, events = _drain(cadquery_engine.stream_render(
            _command(cartridge, out), "flange", 0, 100, 0, 1, is_cancelled=lambda: False,
        ))
        errors = [e for e in events if e.get("event") == "error"]
        assert ok is True and not errors, events[-6:]
        assert out.stat().st_size > 0

    def test_one_shot_render(self, cartridge, tmp_path, monkeypatch):
        """``/api/render`` when the warm pool declines the job."""
        monkeypatch.setenv("YANTRA4D_CQ_POOL_ENABLED", "0")
        out = tmp_path / "flange.glb"
        ok, output = cadquery_engine._run_render(_command(cartridge, out), is_cancelled=lambda: False)
        assert ok is True, output[-2000:]
        assert out.stat().st_size > 0

    def test_warm_pool_render(self, cartridge, tmp_path):
        """A warm worker carries the same address-space ceiling for its whole life."""
        pool = CadQueryPool()
        try:
            outputs = []
            for name in ("a.glb", "b.glb"):
                out = tmp_path / name
                result = pool.submit(str(cartridge), str(out), json.dumps(PARAMS), "glb",
                                     env=cadquery_engine._cadquery_env())
                assert result is not None, "the pool declined the job"
                assert result[0] is True, result[1][-2000:]
                outputs.append(out.stat().st_size)
            assert all(size > 0 for size in outputs)
        finally:
            pool.shutdown()


def _measure(cartridge, out, cpus=None):
    env = dict(cadquery_engine._cadquery_env())
    env["MALLOC_ARENA_MAX"] = render_limits.MALLOC_ARENA_MAX
    if cpus:
        env["Y4D_MEASURE_CPUS"] = str(cpus)
    cmd = _command(cartridge, out)
    proc = subprocess.run(
        [cmd[0], "-c", MEASURE, *cmd[1:]], capture_output=True, text=True, timeout=300, check=False, env=env,
    )
    lines = [line for line in proc.stdout.splitlines() if line.startswith("Y4D_MEASURE ")]
    assert lines, (proc.returncode, proc.stdout[-1500:], proc.stderr[-1500:])
    measured = json.loads(lines[-1].removeprefix("Y4D_MEASURE "))
    assert measured["exit"] == 0, proc.stdout[-1500:]
    return measured


class TestDefaultCeilingIsSizedFromAMeasurement:
    def test_default_leaves_headroom_over_a_real_render(self, cartridge, tmp_path, capsys):
        """The ceiling must clear what an ordinary render maps, with room to spare.

        Measured unlimited, in the same minimal environment, on this machine's
        CPUs and again pinned to one: thread pools (OpenBLAS, OCCT, VTK) size
        themselves from the CPU count and every thread maps a stack, so the
        peak grows with cores. The per-CPU slope is projected to
        ``PROJECTED_CPUS`` so a node larger than the CI runner is covered.
        """
        here = _measure(cartridge, tmp_path / "all.glb")
        one = _measure(cartridge, tmp_path / "one.glb", cpus=1)
        spread = max(here["affinity"] - one["affinity"], 1)
        per_cpu = max(here["VmPeak"] - one["VmPeak"], 0) / spread
        projected = one["VmPeak"] + per_cpu * (PROJECTED_CPUS - 1)
        default = render_limits.DEFAULT_AS_MB
        report = (f"real GLB render, unlimited: VmPeak {here['VmPeak']} MiB on {here['affinity']} CPUs "
                  f"({here['Threads']} threads at exit, VmHWM {here['VmHWM']} MiB, VmData {here['VmData']} MiB), "
                  f"{one['VmPeak']} MiB on 1 CPU; {per_cpu:.0f} MiB per CPU, "
                  f"{projected:.0f} MiB projected at {PROJECTED_CPUS} CPUs; default ceiling {default} MiB")
        with capsys.disabled():
            print(f"\n::notice title=Render address space::{report}")
        assert projected * HEADROOM <= default, report



class TestDiagnoseCpuScaling:
    """TEMPORARY: one CI run to find what makes the address space grow per CPU."""

    def test_report(self, cartridge, tmp_path, capsys, monkeypatch):
        def say(row):
            with capsys.disabled():
                print(f"\n::notice title=Render diagnose::{row}", flush=True)

        for label, extra, cpus in (
            ("all cpus", {}, None),
            ("1 cpu", {}, 1),
            ("2 cpus", {}, 2),
            ("all cpus OPENBLAS=1", {"OPENBLAS_NUM_THREADS": "1"}, None),
            ("all cpus OPENBLAS=1 OMP=1", {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}, None),
            ("all cpus OPENBLAS=12", {"OPENBLAS_NUM_THREADS": "12"}, None),
            ("all cpus OPENBLAS=32", {"OPENBLAS_NUM_THREADS": "32"}, None),
        ):
            env = dict(cadquery_engine._cadquery_env())
            env["MALLOC_ARENA_MAX"] = render_limits.MALLOC_ARENA_MAX
            env.update(extra)
            if cpus:
                env["Y4D_MEASURE_CPUS"] = str(cpus)
            cmd = _command(cartridge, tmp_path / "m.glb")
            try:
                proc = subprocess.run([cmd[0], "-c", MEASURE, *cmd[1:]], capture_output=True, text=True,
                                      timeout=120, check=False, env=env)
                line = [ln for ln in proc.stdout.splitlines() if ln.startswith("Y4D_MEASURE ")]
                say(f"{label}: {line[-1][12:] if line else (proc.returncode, proc.stderr[-200:])}")
            except subprocess.TimeoutExpired:
                say(f"{label}: TIMEOUT 120s")
        for label, as_mb, extra in (
            ("limit 1536 default", 1536, {}),
            ("limit 1536 OPENBLAS=12", 1536, {"OPENBLAS_NUM_THREADS": "12"}),
            ("limit 1536 OPENBLAS=32", 1536, {"OPENBLAS_NUM_THREADS": "32"}),
            ("limit 1300 default", 1300, {}),
            ("limit 1024 default", 1024, {}),
            ("limit 2560 OPENBLAS=12", 2560, {"OPENBLAS_NUM_THREADS": "12"}),
        ):
            monkeypatch.setenv("RENDER_RLIMIT_AS_MB", str(as_mb))
            env = dict(render_limits.limited_env(cadquery_engine._cadquery_env()))
            env.update(extra)
            try:
                proc = subprocess.run(
                    _command(cartridge, tmp_path / "l.glb"), capture_output=True, text=True, timeout=90,
                    check=False, env=env, preexec_fn=render_limits.render_preexec_fn(),
                )
                tail = (proc.stdout + proc.stderr).strip().splitlines()[-2:]
                say(f"{label}: rc={proc.returncode} tail={' | '.join(ln[:160] for ln in tail)}")
            except subprocess.TimeoutExpired as exc:
                out = ((exc.stdout or b"") + (exc.stderr or b""))
                out = out.decode(errors="replace") if isinstance(out, bytes) else out
                say(f"{label}: HUNG 90s tail={' | '.join(ln[:160] for ln in out.strip().splitlines()[-2:])}")
