"""Tests for the dual-engine geometric parity checker.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_verify_parity.py -q

``scripts/qa/verify_parity.py`` is the only script in this suite that is NOT
wired into ``.github/workflows/ci.yml`` — README.md, docs/guides/verification.md
and docs/architecture/dual-engine.md all describe it as the CI parity check,
but no workflow invokes it (ci.yml's ``test-geometric-parity`` job runs
``tests/scripts/geometric_regression.py`` instead). It is nonetheless the
documented definition of what "the two kernels agree" means, so what it treats
as agreement, as disagreement, and as not-applicable is worth pinning.

Three things are separated deliberately:

  - ``classify_mode`` decides which modes are even comparable, and it mirrors
    ``generate_commons_catalog._engine_support``. A CadQuery-only cartridge
    declares ``scad_file`` pointing at its own ``.py`` as a placeholder, so
    handing that path to OpenSCAD asks it to parse Python — which was every
    mode in the commons (1363 of 1363 reported as parity failures, none of them
    a comparable pair). A placeholder is now a SKIP that is counted apart from
    failures, and the tests below assert OpenSCAD is never invoked for one.

  - ``check_mesh_parity`` decides agreement from geometry. Volume is HARD (a
    real shape difference); surface divergence only WARNS — tessellation noise
    between a CSG kernel and a B-Rep kernel is expected and must not fail a
    build. Since the G27 ruling (2026-09-05) the bounding box has BOTH: a delta
    inside the 0.05mm faceting band whose surfaces still agree is a warn, and
    anything larger, or any surface divergence, is still hard.
  - ``verify_project`` decides which modes are even eligible. A mode with no
    ``cq_file`` is SKIPPED (single-kernel modes are legitimate), but a mode
    that names a file which is not on disk is a FAILURE — those two must never
    collapse into each other, or a broken cartridge passes as a skip.

The render backends are stubbed at import: this suite must never shell out to
OpenSCAD or build CadQuery geometry. The geometry cases use real trimesh
primitives, so this module runs in the ``backend`` job, whose
apps/api/requirements.txt carries trimesh and numpy; manifest-validation's
whole-suite step installs neither and skips it, and a suite that skips pins
nothing.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

REPO = Path(__file__).resolve().parents[2]
API = REPO / "apps" / "api"


def _install_engine_stubs() -> None:
    """Put fake render backends where verify_parity's import will find them.

    The real modules pull in the Flask app config, the CadQuery kernel and the
    vendored sandbox — none of which a decision-logic test should need, and
    none of which the lanes that run scripts/tests install. Parent packages
    keep their real ``__path__`` so other suites still import the genuine
    ``services.engine.graph_engine``.
    """
    for name, directory in (("services", API / "services"),
                            ("services.engine", API / "services" / "engine")):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = [str(directory)]
            sys.modules[name] = package

    openscad = types.ModuleType("services.engine.openscad")
    openscad.build_openscad_command = lambda **kwargs: ["openscad", "--stub"]
    openscad.run_render = lambda cmd, scad_path: (True, "")
    sys.modules["services.engine.openscad"] = openscad

    cq_runner = types.ModuleType("services.engine.cq_runner")
    cq_runner.run_cadquery_script = lambda *args: None
    sys.modules["services.engine.cq_runner"] = cq_runner


def _load() -> types.ModuleType:
    _install_engine_stubs()
    spec = importlib.util.spec_from_file_location(
        "verify_parity_under_test", REPO / "scripts" / "qa" / "verify_parity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lane = _load()


# ──────────────────────────────────────────────────────────────────────────────
# fixtures
# ──────────────────────────────────────────────────────────────────────────────

def cartridge(tmp_path, manifest: dict, files=()) -> Path:
    directory = tmp_path / "gears"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in files:
        (directory / name).write_text("// geometry\n", encoding="utf-8")
    return directory


def hyperobject(modes) -> dict:
    return {"project": {"name": "Gears", "hyperobject": {"is_hyperobject": True}},
            "modes": modes}


@pytest.fixture
def renders(monkeypatch):
    """Record what the checker asked the two kernels to do."""
    calls: dict[str, list] = {"scad": [], "cq": [], "parity": []}

    def run_render(cmd, scad_path):
        calls["scad"].append(scad_path)
        return True, ""

    def run_cadquery_script(cq_path, out_path, params_json, fmt):
        calls["cq"].append((cq_path, params_json, fmt))

    def check_mesh_parity_report(a, b, tolerance=0.001):
        calls["parity"].append((a, b, tolerance))
        return True, "identical", {}

    monkeypatch.setattr(lane, "run_render", run_render)
    monkeypatch.setattr(lane, "run_cadquery_script", run_cadquery_script)
    monkeypatch.setattr(lane, "check_mesh_parity_report", check_mesh_parity_report)
    return calls


def stl(tmp_path, name: str, mesh) -> str:
    path = tmp_path / name
    mesh.export(path)
    return str(path)


# ──────────────────────────────────────────────────────────────────────────────
# which cartridges and modes are eligible
# ──────────────────────────────────────────────────────────────────────────────

def test_a_directory_with_no_manifest_is_not_a_project(tmp_path, renders):
    assert lane.verify_project(tmp_path / "empty") is True
    assert renders["scad"] == []


def test_an_unreadable_manifest_fails(tmp_path, renders, caplog):
    directory = tmp_path / "gears"
    directory.mkdir()
    (directory / "project.json").write_text("{not json", encoding="utf-8")
    assert lane.verify_project(directory) is False


def test_a_non_hyperobject_is_skipped_without_rendering(tmp_path, renders):
    directory = cartridge(tmp_path, {"project": {"name": "Plain"}, "modes": [
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]},
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is True
    assert renders["scad"] == []


def test_a_cartridge_declared_only_by_its_cdg_interfaces_is_checked(tmp_path, renders):
    directory = cartridge(tmp_path, {
        "hyperobject": {"cdg_interfaces": [{"id": "bore"}]},
        "modes": [{"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}],
    }, files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is True
    assert len(renders["parity"]) == 1


def test_a_hyperobject_with_no_modes_fails(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([]))
    assert lane.verify_project(directory) is False


def test_a_mode_with_no_cq_file_is_skipped_not_failed(tmp_path, renders):
    """Single-kernel modes inside a hyperobject are legitimate."""
    directory = cartridge(tmp_path, hyperobject([
        {"id": "gauge", "scad_file": "gauge.scad"}]), files=["gauge.scad"])
    assert lane.verify_project(directory) is True
    assert renders["parity"] == []


def test_a_mode_with_no_scad_file_fails(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([{"id": "main", "cq_file": "main.py"}]),
                          files=["main.py"])
    assert lane.verify_project(directory) is False


def test_a_declared_scad_file_that_is_not_on_disk_fails(tmp_path, renders):
    """A missing file must not read as 'nothing to compare' — that is a skip."""
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.py"])
    assert lane.verify_project(directory) is False
    assert renders["parity"] == []


def test_a_declared_cq_file_that_is_not_on_disk_fails(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad"])
    assert lane.verify_project(directory) is False
    assert renders["parity"] == []


# ──────────────────────────────────────────────────────────────────────────────
# the render pass
# ──────────────────────────────────────────────────────────────────────────────

def test_a_matching_pair_renders_both_kernels_and_passes(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is True
    assert renders["scad"] == [str(directory / "main.scad")]
    assert renders["cq"][0][0] == str(directory / "main.py")
    assert (directory / "exports").is_dir()


def test_the_two_renders_go_to_separate_per_kernel_outputs(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    lane.verify_project(directory)
    scad_out, cq_out, _ = renders["parity"][0]
    assert scad_out.endswith("exports/main_scad.stl")
    assert cq_out.endswith("exports/main_cq.stl")


def test_the_cadquery_render_is_asked_for_an_stl_with_default_params(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    lane.verify_project(directory)
    _, params_json, fmt = renders["cq"][0]
    assert json.loads(params_json) == {}
    assert fmt == "STL"


def test_a_failed_openscad_render_fails_and_skips_the_comparison(tmp_path, renders, monkeypatch):
    monkeypatch.setattr(lane, "run_render", lambda cmd, scad_path: (False, "syntax error"))
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is False
    assert renders["cq"] == []
    assert renders["parity"] == []


def test_a_raising_cadquery_build_fails_rather_than_propagating(tmp_path, renders, monkeypatch):
    def boom(*args):
        raise RuntimeError("OCP kernel exploded")

    monkeypatch.setattr(lane, "run_cadquery_script", boom)
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is False
    assert renders["parity"] == []


def test_a_sandbox_rejection_fails_the_cartridge_rather_than_the_run(
        tmp_path, renders, monkeypatch):
    """cq_runner rejects a script with sys.exit, and SystemExit is not an
    Exception — one refused cartridge used to kill the audit mid-sweep."""
    def refuse(*args):
        raise SystemExit(1)

    monkeypatch.setattr(lane, "run_cadquery_script", refuse)
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is False
    assert renders["parity"] == []


def test_a_sandbox_rejection_does_not_stop_the_remaining_cartridges(
        tmp_path, monkeypatch, capsys, renders):
    def refuse(*args):
        raise SystemExit(1)

    monkeypatch.setattr(lane, "run_cadquery_script", refuse)
    commons(tmp_path, "a", hyperobject([
        {"id": "m", "scad_file": "m.scad", "cq_file": "m.py"}]), files=["m.scad", "m.py"])
    commons(tmp_path, "b", hyperobject([
        {"id": "m", "scad_file": "m.scad", "cq_file": "m.py"}]), files=["m.scad", "m.py"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "Failed: 2" in out          # both reached, neither aborted the sweep
    assert "Candidates compared: 2" in out


def test_a_failed_parity_comparison_fails_the_cartridge(tmp_path, renders, monkeypatch):
    monkeypatch.setattr(lane, "check_mesh_parity_report",
                        lambda a, b, t: (False, "Volumes differ by 12.0mm^3", {}))
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is False


def test_one_failing_mode_fails_the_cartridge_even_when_another_passes(
        tmp_path, renders, monkeypatch):
    results = iter([(True, "ok", {}), (False, "Volumes differ", {})])
    monkeypatch.setattr(lane, "check_mesh_parity_report", lambda a, b, t: next(results))
    directory = cartridge(tmp_path, hyperobject([
        {"id": "good", "scad_file": "good.scad", "cq_file": "good.py"},
        {"id": "bad", "scad_file": "bad.scad", "cq_file": "bad.py"},
    ]), files=["good.scad", "good.py", "bad.scad", "bad.py"])
    assert lane.verify_project(directory) is False


def test_the_tolerance_is_passed_through_to_the_comparison(tmp_path, renders):
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    lane.verify_project(directory, tolerance=0.05)
    assert renders["parity"][0][2] == 0.05


# ──────────────────────────────────────────────────────────────────────────────
# what counts as the same geometry
# ──────────────────────────────────────────────────────────────────────────────

def test_identical_meshes_agree(tmp_path):
    box = trimesh.creation.box(extents=(10, 10, 10))
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", box), stl(tmp_path, "b.stl", box))
    assert ok is True
    assert "identical" in reason


def test_a_different_bounding_box_is_a_disagreement(tmp_path):
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 12))))
    assert ok is False
    assert "Bounding boxes differ" in reason


def test_the_same_bounding_box_with_a_different_volume_is_a_disagreement(tmp_path):
    """A cone fills the same 10x10x10 box as a cube and is a different solid."""
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.cone(radius=5, height=10)))
    assert ok is False
    assert "Volumes differ" in reason


def test_a_difference_inside_the_tolerance_is_agreement(tmp_path):
    ok, _ = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.0005))),
        tolerance=0.001)
    assert ok is True


def test_the_same_difference_outside_the_tolerance_now_warns(tmp_path):
    """Changed by the G27 ruling, deliberately.

    Before the warn tier this was a hard failure: 0.0005mm exceeds a 0.0001mm
    tolerance and gate 1 did a bare `return False`. It is now a PASS that says
    so, because the delta is inside the 0.05mm faceting band and the surfaces
    agree to 0.00025mm. The tolerance parameter still decides whether the gate
    is engaged at all — it is what makes this a warn rather than silence — but
    it no longer decides the verdict on its own.
    """
    ok, reason, report = lane.check_mesh_parity_report(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.0005))),
        tolerance=0.0001)
    assert ok is True
    assert report["aabb_warn"] is True
    assert "Bounding boxes differ" in reason


# ──────────────────────────────────────────────────────────────────────────────
# the AABB warn tier (G27, ruled 2026-09-05)
#
# Gate 1 was a bare `return False` on any extents delta over `tolerance`, which
# failed five commons pairs (faircap-filter, gears herringbone, glia-diagnostic
# stethoscope, julia-vase, spiral-planter planter) by 0.012-0.034mm of $fn
# chord error rather than shape. The ruling downgrades that to a WARN, but only
# CONJUNCTIVELY: within a 0.05mm band AND with the Hausdorff proxy passing.
# Both halves are pinned below, because the band alone would let a real 0.04mm
# dimensional error through.
# ──────────────────────────────────────────────────────────────────────────────

def test_an_exact_match_passes_with_no_warning(tmp_path):
    box = trimesh.creation.box(extents=(10, 10, 10))
    ok, reason, report = lane.check_mesh_parity_report(
        stl(tmp_path, "a.stl", box), stl(tmp_path, "b.stl", box))
    assert ok is True
    assert report["aabb_warn"] is False
    assert report["aabb_delta_mm"] == pytest.approx(0.0, abs=1e-9)
    assert "faceting warn" not in reason


def test_an_aabb_delta_inside_the_band_with_agreeing_surfaces_warns(tmp_path):
    """0.03mm of chord error: a pass that says why, not a failure."""
    ok, reason, report = lane.check_mesh_parity_report(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.03))))
    assert ok is True
    assert report["aabb_warn"] is True
    assert report["aabb_delta_mm"] == pytest.approx(0.03, abs=1e-5)
    # The surfaces are half the extents delta apart, well inside the 0.5mm proxy.
    assert report["hausdorff_proxy_mm"] == pytest.approx(0.015, abs=1e-5)
    # The parsed wording survives: the sweep harness and PR bodies read it.
    assert "Bounding boxes differ by 0.030000mm" in reason


def test_the_same_delta_with_diverging_surfaces_still_fails(tmp_path):
    """The band is necessary, not sufficient. A notch moves a surface 2mm."""
    notched = trimesh.boolean.difference([
        trimesh.creation.box(extents=(10, 10, 10.03)),
        trimesh.creation.box(extents=(4, 4, 4), transform=trimesh.transformations
                             .translation_matrix((0, 0, 5)))])
    ok, reason, report = lane.check_mesh_parity_report(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", notched))
    assert ok is False
    assert report["aabb_warn"] is False
    assert report["aabb_delta_mm"] == pytest.approx(0.03, abs=1e-5)
    assert report["hausdorff_proxy_mm"] > 0.5
    assert "Bounding boxes differ by 0.030000mm" in reason


def test_an_aabb_delta_beyond_the_band_fails_whatever_the_surfaces_say(tmp_path):
    """0.6mm is over the 0.05mm band: a hard fail, with no surface query."""
    ok, reason, report = lane.check_mesh_parity_report(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.6))))
    assert ok is False
    assert report["aabb_warn"] is False
    assert report["aabb_delta_mm"] == pytest.approx(0.6, abs=1e-5)
    # Not measured at all: over the band nothing gate 3 could say would help.
    assert report["hausdorff_proxy_mm"] is None
    assert "Bounding boxes differ by 0.600000mm" in reason


def test_the_band_is_not_the_tolerance_parameter(tmp_path):
    """A caller's tighter tolerance still gets the band; the two are separate."""
    paths = (stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
             stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.03))))
    ok, _reason, report = lane.check_mesh_parity_report(*paths, tolerance=0.0001)
    assert ok is True
    assert report["aabb_warn"] is True


def test_a_warn_is_a_pass_for_the_cartridge_and_is_counted_apart(tmp_path, renders,
                                                                 monkeypatch):
    """verify_project must not report a warn run as unqualified agreement."""
    monkeypatch.setattr(lane, "check_mesh_parity_report",
                        lambda a, b, t: (True, "faceting warn", {"aabb_warn": True}))
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    stats: dict = {}
    assert lane.verify_project(directory, stats=stats) is True
    assert stats["mode_passed"] == 1
    assert stats["mode_passed_aabb_warn"] == 1


def test_the_public_two_tuple_contract_is_unchanged(tmp_path):
    """Callers and PR-body parsers unpack exactly two values. They still can."""
    result = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.03))))
    assert len(result) == 2
    ok, reason = result
    assert ok is True
    assert "Bounding boxes differ by 0.030000mm" in reason


def test_an_unloadable_mesh_is_reported_rather_than_raising(tmp_path):
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        str(tmp_path / "does-not-exist.stl"))
    assert ok is False
    assert reason


def test_the_same_solid_tessellated_differently_agrees(tmp_path):
    """A CSG kernel and a B-Rep kernel do not emit the same triangles."""
    box = trimesh.creation.box(extents=(10, 10, 10))
    ok, _ = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", box),
        stl(tmp_path, "b.stl", box.subdivide().subdivide()),
        tolerance=0.001)
    assert ok is True


def test_the_reason_reports_the_measured_surface_divergence(tmp_path):
    """Agreement is decided by AABB and volume; divergence is only reported."""
    box = trimesh.creation.box(extents=(10, 10, 10))
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", box), stl(tmp_path, "b.stl", box))
    assert ok is True
    assert "mm tolerance" in reason


# ──────────────────────────────────────────────────────────────────────────────
# candidate selection — mirroring generate_commons_catalog._engine_support
# ──────────────────────────────────────────────────────────────────────────────

def classify(tmp_path, mode, files=()):
    directory = cartridge(tmp_path, hyperobject([mode]), files=files)
    verdict, _scad_path, _cq_path, detail = lane.classify_mode(mode, directory)
    return verdict, detail


def test_a_placeholder_scad_file_is_skipped_not_failed(tmp_path):
    """A CadQuery-only mode names its own .py in scad_file; OpenSCAD cannot parse it."""
    verdict, detail = classify(
        tmp_path, {"id": "main", "scad_file": "main.py", "cq_file": "main.py"},
        files=["main.py"])
    assert verdict == "skip"
    assert "placeholder" in detail


def test_a_placeholder_mode_never_reaches_openscad(tmp_path, renders):
    """The 1363-failure regression, pinned: no render, no failure, still True."""
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.py", "cq_file": "main.py"}]), files=["main.py"])
    assert lane.verify_project(directory) is True
    assert renders["scad"] == []
    assert renders["cq"] == []
    assert renders["parity"] == []


def test_a_placeholder_is_counted_apart_from_failures(tmp_path, renders):
    stats: dict = {}
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.py", "cq_file": "main.py"}]), files=["main.py"])
    lane.verify_project(directory, stats=stats)
    assert stats.get("mode_skipped_placeholder") == 1
    assert stats.get("mode_failed") is None
    assert stats.get("mode_candidate") is None


def test_a_real_pair_is_still_a_candidate(tmp_path, renders):
    stats: dict = {}
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory, stats=stats) is True
    assert stats["mode_candidate"] == 1
    assert stats["mode_passed"] == 1
    assert len(renders["parity"]) == 1


def test_a_placeholder_mode_does_not_suppress_a_real_pair_beside_it(tmp_path, renders):
    stats: dict = {}
    directory = cartridge(tmp_path, hyperobject([
        {"id": "cq_only", "scad_file": "cq_only.py", "cq_file": "cq_only.py"},
        {"id": "dual", "scad_file": "dual.scad", "cq_file": "dual.py"},
    ]), files=["cq_only.py", "dual.scad", "dual.py"])
    assert lane.verify_project(directory, stats=stats) is True
    assert stats["mode_skipped_placeholder"] == 1
    assert stats["mode_candidate"] == 1
    assert renders["scad"] == [str(directory / "dual.scad")]


def test_a_cq_file_that_is_not_python_is_skipped(tmp_path):
    verdict, detail = classify(
        tmp_path, {"id": "main", "scad_file": "main.scad", "cq_file": "main.json"},
        files=["main.scad", "main.json"])
    assert verdict == "skip"
    assert "not a CadQuery source" in detail


# --- inference is a guess; a declaration is a promise ----------------------

def test_an_inferred_sibling_that_exists_makes_the_mode_a_candidate(tmp_path):
    """_engine_support infers <name>.py from <name>.scad; so does this."""
    verdict, _ = classify(tmp_path, {"id": "main", "scad_file": "main.scad"},
                          files=["main.scad", "main.py"])
    assert verdict == "candidate"


def test_an_inferred_sibling_that_is_absent_is_an_openscad_only_mode(tmp_path):
    verdict, detail = classify(tmp_path, {"id": "gauge", "scad_file": "gauge.scad"},
                               files=["gauge.scad"])
    assert verdict == "skip"
    assert "OpenSCAD-only" in detail


def test_a_declared_cq_file_that_is_absent_is_still_a_failure(tmp_path):
    """The manifest promised a file it does not ship — not the same as absence."""
    verdict, detail = classify(
        tmp_path, {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"},
        files=["main.scad"])
    assert verdict == "fail"
    assert "CadQuery file missing" in detail


def test_a_declared_scad_that_is_absent_is_a_failure_not_a_placeholder(tmp_path):
    verdict, detail = classify(
        tmp_path, {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"},
        files=["main.py"])
    assert verdict == "fail"
    assert "SCAD file missing" in detail


def test_a_mode_naming_no_scad_file_at_all_is_a_failure(tmp_path):
    verdict, detail = classify(tmp_path, {"id": "main", "cq_file": "main.py"},
                               files=["main.py"])
    assert verdict == "fail"
    assert "Missing scad_file" in detail


def test_modes_given_as_a_mapping_are_read(tmp_path, renders):
    """Some manifests key modes by id; iterating that yields strings."""
    directory = cartridge(tmp_path, {
        "project": {"name": "Gears", "hyperobject": {"is_hyperobject": True}},
        "modes": {"main": {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}},
    }, files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is True
    assert len(renders["parity"]) == 1


# ──────────────────────────────────────────────────────────────────────────────
# the audit's own arithmetic
# ──────────────────────────────────────────────────────────────────────────────

def run_audit(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify_parity.py"])
    with pytest.raises(SystemExit) as exit_code:
        lane.main()
    return exit_code.value.code, capsys.readouterr().out


def commons(tmp_path, slug, manifest, files=()):
    directory = tmp_path / "projects" / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in files:
        (directory / name).write_text("// geometry\n", encoding="utf-8")
    return directory


def test_an_all_placeholder_commons_reports_nothing_compared_and_exits_zero(
        tmp_path, monkeypatch, capsys, renders):
    commons(tmp_path, "a", hyperobject([
        {"id": "m", "scad_file": "m.py", "cq_file": "m.py"}]), files=["m.py"])
    commons(tmp_path, "b", hyperobject([
        {"id": "m", "scad_file": "m.py", "cq_file": "m.py"}]), files=["m.py"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "Candidates compared: 0" in out
    assert "Skipped, CadQuery-only placeholder scad_file: 2" in out


def test_a_cartridge_with_nothing_to_compare_is_not_reported_as_passed(
        tmp_path, monkeypatch, capsys, renders):
    """Counting an unmeasured cartridge as passed would claim agreement."""
    commons(tmp_path, "a", hyperobject([
        {"id": "m", "scad_file": "m.py", "cq_file": "m.py"}]), files=["m.py"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "Passed: 0" in out
    assert "No comparable pair: 1" in out


def test_a_real_pair_is_counted_as_compared(tmp_path, monkeypatch, capsys, renders):
    commons(tmp_path, "dual", hyperobject([
        {"id": "m", "scad_file": "m.scad", "cq_file": "m.py"}]), files=["m.scad", "m.py"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "Candidates compared: 1" in out
    assert "Passed: 1" in out


def test_a_failing_real_pair_still_exits_non_zero(
        tmp_path, monkeypatch, capsys, renders):
    monkeypatch.setattr(lane, "check_mesh_parity_report",
                        lambda a, b, t: (False, "Volumes differ", {}))
    commons(tmp_path, "dual", hyperobject([
        {"id": "m", "scad_file": "m.scad", "cq_file": "m.py"}]), files=["m.scad", "m.py"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "Failed: 1" in out


def test_non_hyperobjects_are_counted_apart_from_everything_else(
        tmp_path, monkeypatch, capsys, renders):
    commons(tmp_path, "plain", {"project": {"name": "Plain"}, "modes": [
        {"id": "m", "scad_file": "m.scad"}]}, files=["m.scad"])
    code, out = run_audit(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "Not hyperobjects: 1" in out
    assert "Hyperobjects Tested: 0" in out
