"""Exercise the installed CAD kernel and converters, without mocked exports."""
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("file_format", ["STL", "STEP", "GLB"])
def test_boolean_geometry_survives_runner_export(tmp_path, file_format):
    # An overlapping subtraction distinguishes real boolean geometry from a
    # successful import or a placeholder box. The remaining solid is 5x10x10.
    script = tmp_path / "boolean.py"
    script.write_text(
        'result = cq.Workplane("XY").box(10, 10, 10).cut('
        'cq.Workplane("XY").box(5, 10, 10).translate((2.5, 0, 0)))\n'
    )
    output = tmp_path / f"boolean.{file_format.lower()}"
    runner = Path(__file__).resolve().parents[2] / "services/engine/cq_runner.py"
    completed = subprocess.run(
        [sys.executable, str(runner), str(script), str(output), "{}", file_format],
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output.stat().st_size > 0

    if file_format == "STEP":
        import cadquery as cq

        solid = cq.importers.importStep(str(output)).val()
        assert solid.isValid()
        assert solid.Volume() == pytest.approx(500)
        bounds = solid.BoundingBox()
        assert (bounds.xlen, bounds.ylen, bounds.zlen) == pytest.approx((5, 10, 10))
    else:
        import trimesh

        mesh = trimesh.load(output, force="mesh")
        # glTF uses meters; the CAD and STL paths use millimeters. Vertex
        # seams in the GLB encode face normals, so weld them before topology QA.
        scale = 0.001 if file_format == "GLB" else 1
        mesh.merge_vertices()
        assert mesh.is_watertight
        assert mesh.extents == pytest.approx([5 * scale, 10 * scale, 10 * scale])
        assert mesh.volume == pytest.approx(500 * scale**3, rel=1e-5)
