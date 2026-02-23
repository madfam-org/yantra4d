"""Tests for CadQuery runner sandbox security features."""
import pytest
from unittest.mock import patch, MagicMock

from services.engine.cq_runner import (
    _SAFE_BUILTINS,
    _BLOCKED_MODULES,
    _restricted_import,
    run_cadquery_script,
)


class TestRestrictedImport:
    """Tests for the _restricted_import guard."""

    @pytest.mark.parametrize("module", [
        "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
        "importlib", "ctypes", "signal", "multiprocessing", "threading",
        "pickle", "shelve",
    ])
    def test_blocked_modules_raise(self, module):
        with pytest.raises(ImportError, match=f"'{module}' is not allowed"):
            _restricted_import(module)

    @pytest.mark.parametrize("module", [
        "os.path", "subprocess.run", "http.client", "urllib.parse",
    ])
    def test_blocked_submodules_raise(self, module):
        with pytest.raises(ImportError, match=f"'{module}' is not allowed"):
            _restricted_import(module)

    def test_allowed_module_succeeds(self):
        m = _restricted_import("math")
        assert hasattr(m, "pi")

    def test_allowed_json_succeeds(self):
        m = _restricted_import("json")
        assert hasattr(m, "dumps")


class TestSafeBuiltins:
    """Tests for the restricted builtins allowlist."""

    def test_open_not_in_builtins(self):
        assert "open" not in _SAFE_BUILTINS

    def test_eval_not_in_builtins(self):
        assert "eval" not in _SAFE_BUILTINS

    def test_exec_not_in_builtins(self):
        assert "exec" not in _SAFE_BUILTINS

    def test_compile_not_in_builtins(self):
        assert "compile" not in _SAFE_BUILTINS

    def test___import___not_in_base(self):
        assert "__import__" not in _SAFE_BUILTINS

    def test_getattr_not_in_builtins(self):
        assert "getattr" not in _SAFE_BUILTINS

    def test_safe_builtins_include_basics(self):
        for name in ["int", "float", "str", "list", "dict", "len", "range", "print"]:
            assert name in _SAFE_BUILTINS, f"{name} should be in safe builtins"


class TestBlockedModules:
    """Tests for the blocked modules set."""

    def test_os_blocked(self):
        assert "os" in _BLOCKED_MODULES

    def test_subprocess_blocked(self):
        assert "subprocess" in _BLOCKED_MODULES

    def test_socket_blocked(self):
        assert "socket" in _BLOCKED_MODULES

    def test_pickle_blocked(self):
        assert "pickle" in _BLOCKED_MODULES

    def test_math_not_blocked(self):
        assert "math" not in _BLOCKED_MODULES

    def test_cadquery_not_blocked(self):
        assert "cadquery" not in _BLOCKED_MODULES


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

    with patch.dict("sys.modules", {"cadquery": mock_cq, "cascadio": MagicMock()}):
        yield mock_cq


class TestFileExtensionValidation:
    """Tests for script path validation."""

    def test_rejects_txt_extension(self, mock_cq_env, tmp_path):
        script = tmp_path / "script.txt"
        script.write_text("result = cq.Workplane('XY').box(1,1,1)")

        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert exc.value.code == 1

    def test_rejects_scad_extension(self, mock_cq_env, tmp_path):
        script = tmp_path / "model.scad"
        script.write_text("cube([1,1,1]);")

        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert exc.value.code == 1

    def test_accepts_py_extension(self, mock_cq_env, tmp_path):
        script = tmp_path / "script.py"
        script.write_text("result = cq.Workplane('XY').box(1,1,1)")

        run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert mock_cq_env.exporters.export.called

    def test_accepts_cq_extension(self, mock_cq_env, tmp_path):
        script = tmp_path / "model.cq"
        script.write_text("result = cq.Workplane('XY').box(1,1,1)")

        run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert mock_cq_env.exporters.export.called


class TestSandboxedExecution:
    """Tests that scripts run in a sandboxed environment."""

    def test_script_cannot_use_open(self, mock_cq_env, tmp_path):
        script = tmp_path / "evil.py"
        script.write_text("f = open('/etc/passwd', 'r')")

        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert exc.value.code == 1

    def test_script_cannot_import_os(self, mock_cq_env, tmp_path):
        script = tmp_path / "evil.py"
        script.write_text("import os; os.system('echo pwned')")

        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert exc.value.code == 1

    def test_script_cannot_import_subprocess(self, mock_cq_env, tmp_path):
        script = tmp_path / "evil.py"
        script.write_text("import subprocess; subprocess.run(['ls'])")

        with pytest.raises(SystemExit) as exc:
            run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert exc.value.code == 1

    def test_script_can_use_math(self, mock_cq_env, tmp_path):
        script = tmp_path / "safe.py"
        script.write_text("import math\nresult = cq.Workplane('XY').box(math.pi, 1, 1)")

        run_cadquery_script(str(script), "out.stl", "{}", "STL")
        assert mock_cq_env.exporters.export.called
