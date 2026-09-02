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

Two things are separated deliberately:

  - ``check_mesh_parity`` decides agreement from geometry. Bounding box and
    volume are HARD (a real shape difference), while surface divergence only
    WARNS — tessellation noise between a CSG kernel and a B-Rep kernel is
    expected and must not fail a build.
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

    def check_mesh_parity(a, b, tolerance=0.001):
        calls["parity"].append((a, b, tolerance))
        return True, "identical"

    monkeypatch.setattr(lane, "run_render", run_render)
    monkeypatch.setattr(lane, "run_cadquery_script", run_cadquery_script)
    monkeypatch.setattr(lane, "check_mesh_parity", check_mesh_parity)
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


def test_a_failed_parity_comparison_fails_the_cartridge(tmp_path, renders, monkeypatch):
    monkeypatch.setattr(lane, "check_mesh_parity",
                        lambda a, b, t: (False, "Volumes differ by 12.0mm^3"))
    directory = cartridge(tmp_path, hyperobject([
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}]),
        files=["main.scad", "main.py"])
    assert lane.verify_project(directory) is False


def test_one_failing_mode_fails_the_cartridge_even_when_another_passes(
        tmp_path, renders, monkeypatch):
    results = iter([(True, "ok"), (False, "Volumes differ")])
    monkeypatch.setattr(lane, "check_mesh_parity", lambda a, b, t: next(results))
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


def test_the_same_difference_outside_the_tolerance_is_not(tmp_path):
    ok, reason = lane.check_mesh_parity(
        stl(tmp_path, "a.stl", trimesh.creation.box(extents=(10, 10, 10))),
        stl(tmp_path, "b.stl", trimesh.creation.box(extents=(10, 10, 10.0005))),
        tolerance=0.0001)
    assert ok is False
    assert "Bounding boxes differ" in reason


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
