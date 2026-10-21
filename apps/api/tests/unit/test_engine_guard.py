"""CadQuery runs on the render worker, never in the API process.

Three layers, cheapest first:

1. **Source**: no API module imports the CadQuery engine or its pool (the
   render worker, ``apps/worker``, is the one place that does).
2. **Import graph**: a freshly created API app has not loaded either module,
   so nothing reachable from a route can call them.
3. **Runtime**: the CadQuery entry points refuse to run inside a Flask
   request context (``services.engine.engine_guard.worker_only``).

Rendering from a route goes through ``services.engine.worker_dispatch`` (or
the ``render_orchestrator`` paths ``/api/render`` uses), which queue the job.
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[2]

#: Modules that execute CadQuery code (or own the processes that do).
ENGINE_MODULES = {
    "services.engine.cadquery_engine",
    "services.engine.cq_pool",
    "services.engine.cq_runner",
}

#: The engine package itself; everything else in the API must not import it.
ENGINE_FILES = {
    API_ROOT / "services" / "engine" / "cadquery_engine.py",
    API_ROOT / "services" / "engine" / "cq_pool.py",
    API_ROOT / "services" / "engine" / "cq_runner.py",
    API_ROOT / "services" / "engine" / "cq_sandbox.py",
    API_ROOT / "services" / "engine" / "engine_guard.py",
}

SKIP_DIRS = {"tests", ".venv", "venv", "__pycache__", "node_modules", "migrations", "static", "data"}


def _api_sources():
    for path in API_ROOT.rglob("*.py"):
        if SKIP_DIRS.intersection(path.relative_to(API_ROOT).parts):
            continue
        if path in ENGINE_FILES:
            continue
        yield path


def _engine_references(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names if alias.name in ENGINE_MODULES]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module in ENGINE_MODULES:
                found.append(node.module)
            elif node.module == "services.engine":
                found += [
                    f"services.engine.{alias.name}" for alias in node.names
                    if f"services.engine.{alias.name}" in ENGINE_MODULES
                ]
        elif isinstance(node, ast.Constant) and node.value in ENGINE_MODULES:
            # importlib.import_module("services.engine.cadquery_engine") and friends
            found.append(node.value)
    return found


def test_no_api_module_imports_the_cadquery_engine():
    offenders = {}
    for path in _api_sources():
        refs = _engine_references(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        if refs:
            offenders[str(path.relative_to(API_ROOT))] = sorted(set(refs))
    assert offenders == {}, (
        "CadQuery runs on the render worker only. Queue the render "
        "(services.engine.worker_dispatch / render_orchestrator) instead of "
        f"importing the engine: {offenders}"
    )


def test_the_scan_sees_a_violation():
    """Guard the guard: the detector must flag every import spelling."""
    sources = [
        "from services.engine.cadquery_engine import run_render",
        "import services.engine.cq_pool",
        "from services.engine import cadquery_engine",
        "def f():\n    from services.engine.cq_pool import cq_pool",
        "import importlib\nimportlib.import_module('services.engine.cadquery_engine')",
    ]
    for source in sources:
        assert _engine_references(ast.parse(source)), source
    assert _engine_references(ast.parse("from services.engine import worker_dispatch")) == []


def test_api_app_never_loads_the_cadquery_engine(tmp_path):
    """Create the whole app (every blueprint) in a clean interpreter and look."""
    probe = (
        "import json, sys\n"
        "from app import create_app\n"
        "create_app()\n"
        f"print(json.dumps(sorted(m for m in {sorted(ENGINE_MODULES)!r} if m in sys.modules)))\n"
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(API_ROOT),
        "ANALYTICS_DB_PATH": str(tmp_path / "analytics.db"),
    }
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=API_ROOT, env=env,
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert loaded == [], f"the API process loaded {loaded}"


class TestWorkerOnly:
    def test_cadquery_entry_points_refuse_inside_a_request(self, app_ctx):
        from services.engine import cadquery_engine
        from services.engine.cq_pool import cq_pool
        from services.engine.engine_guard import EngineInRequestError

        cmd = cadquery_engine.build_cadquery_command("/tmp/out.stl", "/tmp/in.py", {}, "stl")
        with app_ctx.test_request_context("/api/anything"):
            with pytest.raises(EngineInRequestError):
                cadquery_engine.run_render(cmd)
            with pytest.raises(EngineInRequestError):
                cadquery_engine.stream_render(cmd, "body", 0, 100, 0, 1)
            with pytest.raises(EngineInRequestError):
                cq_pool.submit("/tmp/in.py", "/tmp/out.stl", "{}", "stl")

    def test_outside_a_request_the_wrapper_is_transparent(self, app_ctx):
        from services.engine.engine_guard import worker_only

        @worker_only
        def render(a, *, b):
            """docstring"""
            return a + b

        assert render(1, b=2) == 3
        assert render.__name__ == "render" and render.__doc__ == "docstring"
        with app_ctx.test_request_context("/"), pytest.raises(RuntimeError, match="render worker"):
            render(1, b=2)


@pytest.fixture
def app_ctx():
    from flask import Flask
    return Flask("engine-guard-test")
