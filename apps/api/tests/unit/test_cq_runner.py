import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_cq_env():
    class Workplane: 
        def __init__(self, *args, **kwargs): pass
        def box(self, *args): return self
    class Assembly:
        pass

    class Shape:
        pass
    
    mock_cq = MagicMock()
    mock_cq.Workplane = Workplane
    mock_cq.Assembly = Assembly
    mock_cq.Shape = Shape
    mock_cq.exporters = MagicMock()
    
    with patch.dict('sys.modules', {
        'cadquery': mock_cq,
        'cascadio': MagicMock()
    }):
        yield mock_cq

def test_cq_runner_missing_cadquery(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == 'cadquery':
            raise ImportError("No module named cadquery")
        return real_import(name, *args, **kwargs)
    
    monkeypatch.setattr(builtins, '__import__', fake_import)
    from services.engine.cq_runner import run_cadquery_script
    
    with pytest.raises(SystemExit) as e:
        run_cadquery_script("script.py", "out.stl", "{}", "STL")
    assert e.value.code == 1

def test_cq_runner_success(mock_cq_env, tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("result = cq.Workplane('XY').box(1, 1, 1)")
    
    from services.engine.cq_runner import run_cadquery_script
    
    run_cadquery_script(str(script_path), "out.stl", "{}", "STL")
    assert mock_cq_env.exporters.export.called

def test_cq_runner_missing_result(mock_cq_env, tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("a = 1 + 1")
    
    from services.engine.cq_runner import run_cadquery_script
    
    with pytest.raises(SystemExit) as e:
        run_cadquery_script(str(script_path), "out.stl", "{}", "STL")
    assert e.value.code == 1

def test_cq_runner_gltf_export(mock_cq_env, tmp_path):
    script_path = tmp_path / "script.py"
    script_path.write_text("result = cq.Workplane('XY').box(1, 1, 1)")
    
    from services.engine.cq_runner import run_cadquery_script
    
    run_cadquery_script(str(script_path), "out.glb", "{}", "GLTF")
    
    # We didn't explicitly capture the mock for cascadio so let's check sys.modules
    assert sys.modules["cascadio"].step_to_glb.called


# ── Scripts that export themselves (the legacy satellite pattern) ──────────────
#
# 21 commons cartridges (motor-mount, spiral-planter, din-rail-clip, fasteners,
# gears, julia-vase, maze, …) end with
#
#     if __name__ == "__main__":
#         args = parse(--params, --out)
#         cq.exporters.export(res, args.out)
#
# The runner mocks that argv, so for a `.glb` request the script used to call
# exporters.export on a `.glb` path — an extension CadQuery cannot infer — and
# die inside exec before the runner's STEP→cascadio transcode ran. The runner
# now hands such scripts its STEP intermediate as `--out` and transcodes what
# they wrote. Caught by the first prerender-commons run (2026-09-19).

LEGACY_SELF_EXPORTING_SCRIPT = '''
import cadquery as cq
import json
import argparse

def build(params):
    size = float(params.get("size", 10))
    return cq.Workplane("XY").box(size, size, size / 2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", default="{}")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    res = build(json.loads(args.params))
    cq.exporters.export(res, args.out)
'''


def test_self_exporting_script_gets_a_step_path_for_glb(mock_cq_env, tmp_path, monkeypatch):
    """The `--out` a self-exporting script sees must be a STEP path when GLB is asked."""
    script_path = tmp_path / "legacy.py"
    script_path.write_text(LEGACY_SELF_EXPORTING_SCRIPT)
    seen = {}

    def fake_export(res, out, *args, **kwargs):
        seen["out"] = out
        # Behave like CadQuery: an unknown extension is an error, a STEP is written.
        if not str(out).lower().endswith((".step", ".stp", ".stl")):
            raise ValueError("Unknown extensions, specify export type explicitly")
        with open(out, "wb") as fh:
            fh.write(b"ISO-10303-21;")

    mock_cq_env.exporters.export.side_effect = fake_export
    # argparse in the script must see the runner's argv, not pytest's.
    from services.engine.cq_runner import run_cadquery_script

    run_cadquery_script(str(script_path), str(tmp_path / "out.glb"), '{"size": 4}', "glb")

    assert seen["out"].lower().endswith(".step"), seen
    assert sys.modules["cascadio"].step_to_glb.called
    (step_arg, glb_arg), _ = sys.modules["cascadio"].step_to_glb.call_args
    assert step_arg == seen["out"]
    assert glb_arg == str(tmp_path / "out.glb")


def test_self_exporting_script_still_gets_the_real_path_for_stl(mock_cq_env, tmp_path):
    script_path = tmp_path / "legacy.py"
    script_path.write_text(LEGACY_SELF_EXPORTING_SCRIPT)
    seen = []
    mock_cq_env.exporters.export.side_effect = lambda res, out, *a, **k: seen.append(out)
    from services.engine.cq_runner import run_cadquery_script

    run_cadquery_script(str(script_path), str(tmp_path / "out.stl"), "{}", "stl")

    # The script exported to the real path, then the runner exported `result` there too.
    assert seen and all(str(o) == str(tmp_path / "out.stl") for o in seen)


def test_self_exporting_script_produces_a_real_glb():
    """End to end with the real kernel: the legacy pattern yields a valid binary glTF."""
    pytest.importorskip("cadquery")
    pytest.importorskip("cascadio")
    import tempfile
    from pathlib import Path

    from services.engine.cq_runner import run_cadquery_script

    with tempfile.TemporaryDirectory() as d:
        script = Path(d) / "legacy.py"
        script.write_text(LEGACY_SELF_EXPORTING_SCRIPT)
        out = Path(d) / "part.glb"
        run_cadquery_script(str(script), str(out), '{"size": 6}', "glb")
        data = out.read_bytes()
        assert data[:4] == b"glTF", data[:16]
        assert len(data) > 200
