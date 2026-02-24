import sys
import pytest
from unittest.mock import patch, MagicMock

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
