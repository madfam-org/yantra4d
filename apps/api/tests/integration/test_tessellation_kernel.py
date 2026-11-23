"""Tessellation profiles on a real CadQuery kernel (owner rulings M1-M3, 2026-11-22).

What the unit tests cannot show without a kernel:

  - M1: the print STL is byte-identical to what the runner wrote before profiles
    existed, i.e. to ``cq.exporters.export(result, path, "STL")`` for a Workplane and
    ``Assembly.save(path, "STL")`` for an assembly, through every way of asking for it
    (no profile, ``"print"``, the one-shot subprocess and the warm pool);
  - M2: ``preview`` is a coarser, regular mesh bounded in millimetres (0.02 mm chord,
    0.35 rad), and it reaches the runner through both process paths;
  - meshing a preview leaves no triangulation behind on the caller's shape, so a shape
    shared across renders in a warm worker cannot carry one profile's mesh into the
    other's export.

Skipped when cadquery is not importable (the unit suite stands on its own).
"""
import itertools
import json
import math

import pytest

from services.engine import cadquery_engine
from services.engine.cq_runner import _export_stl_with_profile, run_cadquery_script
from services.engine.tessellation import PREVIEW, PRINT, profile

cq = pytest.importorskip("cadquery", reason="CadQuery kernel not installed")
trimesh = pytest.importorskip("trimesh")

HOLE_RADIUS = 5.0

PLATE = f"""
import cadquery as cq
result = cq.Workplane("XY").box(40, 30, 6).faces(">Z").workplane().hole({2 * HOLE_RADIUS})
"""

ASSEMBLY = """
import cadquery as cq
plate = cq.Workplane("XY").box(30, 30, 4).faces(">Z").workplane().hole(6)
boss = cq.Workplane("XY").circle(8).extrude(10).translate((60, 0, 0))
assembly = cq.Assembly().add(plate, name="plate").add(boss, name="boss")
"""


def _write(tmp_path, name, source):
    path = tmp_path / name
    path.write_text(source)
    return str(path)


def _exec(source):
    namespace = {"cq": cq, "math": math}
    exec(source, namespace)  # noqa: S102 - the test's own fixture geometry
    return namespace.get("result") or namespace.get("assembly")


def _hole_segments(stl_path):
    """Segments per turn of the hole, read off the vertices that sit on its circle."""
    mesh = trimesh.load(stl_path, force="mesh", process=False)
    mesh.merge_vertices()
    v = mesh.vertices
    radial = (v[:, 0] ** 2 + v[:, 1] ** 2) ** 0.5
    on_hole = v[abs(radial - HOLE_RADIUS) < 1e-3]
    top = on_hole[abs(on_hole[:, 2] - on_hole[:, 2].max()) < 1e-6]
    angles = sorted({round(math.degrees(math.atan2(y, x)) % 360, 4) for x, y, _ in top})
    gaps = [b - a for a, b in itertools.pairwise(angles)] + [360 - angles[-1] + angles[0]]
    return len(angles), max(gaps)


class TestPrintIsUnchanged:
    """M1: print output must not change in this work."""

    def test_workplane_print_is_byte_identical_to_the_exporter_call(self, tmp_path):
        script = _write(tmp_path, "plate.py", PLATE)
        before = tmp_path / "before.stl"
        cq.exporters.export(_exec(PLATE), str(before), "STL")

        implicit, explicit = tmp_path / "implicit.stl", tmp_path / "explicit.stl"
        run_cadquery_script(script, str(implicit), "{}", "STL")
        run_cadquery_script(script, str(explicit), "{}", "STL", PRINT)

        assert implicit.read_bytes() == before.read_bytes()
        assert explicit.read_bytes() == before.read_bytes()

    def test_assembly_print_is_byte_identical_to_assembly_save(self, tmp_path):
        script = _write(tmp_path, "assy.py", ASSEMBLY)
        before = tmp_path / "before.stl"
        _exec(ASSEMBLY).save(str(before), "STL")

        out = tmp_path / "print.stl"
        run_cadquery_script(script, str(out), "{}", "STL", PRINT)
        assert out.read_bytes() == before.read_bytes()

    def test_print_keeps_cadquerys_126_segment_circles(self, tmp_path):
        """What the audit measured on production output: the angular bound acts."""
        out = tmp_path / "print.stl"
        run_cadquery_script(_write(tmp_path, "plate.py", PLATE), str(out), "{}", "STL")
        segments, _ = _hole_segments(str(out))
        assert segments >= 120


class TestPreview:
    def test_preview_is_coarser_and_bounded_in_millimetres(self, tmp_path):
        script = _write(tmp_path, "plate.py", PLATE)
        printed, preview = tmp_path / "print.stl", tmp_path / "preview.stl"
        run_cadquery_script(script, str(printed), "{}", "STL")
        run_cadquery_script(script, str(preview), "{}", "STL", PREVIEW)

        print_tris = len(trimesh.load(str(printed), force="mesh").faces)
        preview_tris = len(trimesh.load(str(preview), force="mesh").faces)
        assert preview_tris < print_tris

        segments, widest_gap_deg = _hole_segments(str(preview))
        chord = HOLE_RADIUS * (1 - math.cos(math.radians(widest_gap_deg) / 2))
        tess = profile(PREVIEW)
        assert chord <= tess.linear * 1.05  # 0.02 mm, absolute
        assert math.radians(widest_gap_deg) <= tess.angular + 1e-6
        assert segments < 126

        mesh = trimesh.load(str(preview), force="mesh", process=False)
        mesh.merge_vertices()
        assert mesh.is_watertight

    def test_preview_leaves_no_triangulation_on_the_callers_shape(self, tmp_path):
        from OCP.BRep import BRep_Tool
        from OCP.TopLoc import TopLoc_Location

        shape = _exec(PLATE)
        _export_stl_with_profile(cq, shape, str(tmp_path / "p.stl"), profile(PREVIEW))
        faces = shape.val().Faces()
        assert faces
        assert all(BRep_Tool.Triangulation_s(f.wrapped, TopLoc_Location()) is None for f in faces)

    def test_preview_of_an_assembly_is_one_mesh(self, tmp_path):
        out = tmp_path / "assy.stl"
        run_cadquery_script(_write(tmp_path, "assy.py", ASSEMBLY), str(out), "{}", "STL", PREVIEW)
        mesh = trimesh.load(str(out), force="mesh")
        assert len(mesh.faces) > 0

    @pytest.mark.parametrize("fmt", ["STEP", "3MF", "GLB"])
    def test_runner_refuses_preview_for_anything_but_stl(self, tmp_path, fmt, capsys):
        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(_write(tmp_path, "plate.py", PLATE), str(tmp_path / f"o.{fmt.lower()}"),
                                "{}", fmt, PREVIEW)
        assert exc.value.code == 1
        assert "only offered for STL" in capsys.readouterr().out

    def test_runner_refuses_an_unknown_profile(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            run_cadquery_script(_write(tmp_path, "plate.py", PLATE), str(tmp_path / "o.stl"), "{}", "STL", "draft")
        assert "unknown tessellation profile" in capsys.readouterr().out


class TestBothProcessPaths:
    """The profile survives the argv contract and the warm pool's JSON lines."""

    @pytest.mark.parametrize("pooled", [False, True], ids=["subprocess", "warm-pool"])
    def test_profile_reaches_the_runner(self, tmp_path, monkeypatch, pooled):
        monkeypatch.setenv("YANTRA4D_CQ_POOL_ENABLED", "1" if pooled else "0")
        script = _write(tmp_path, "plate.py", PLATE)
        reference = {}
        for name in (PRINT, PREVIEW):
            ref = tmp_path / f"ref-{name}.stl"
            run_cadquery_script(script, str(ref), "{}", "STL", name)
            reference[name] = ref.read_bytes()

        try:
            for name in (PRINT, PREVIEW):
                out = tmp_path / f"out-{name}.stl"
                cmd = cadquery_engine.build_cadquery_command(str(out), script, {}, "stl", name)
                success, output = cadquery_engine.run_render(cmd)
                assert success, output
                assert out.read_bytes() == reference[name], json.dumps({"profile": name, "log": output[-400:]})
        finally:
            cadquery_engine.cq_pool.reset()
