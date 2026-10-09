"""The render worker reads a graph task's bindings from the manifest on disk.

A fork's bindings change through the API (PUT .../manifest/bindings), which
invalidates only the API process's manifest cache, while the API keys the
render on the binding map. The worker is another process: it must not render a
graph against bindings it cached before the edit.
"""
import json
import sys
from pathlib import Path

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import render_worker

SLUG = "bound-twin"


def _write(project_dir: Path, binding):
    parameter = {"id": "size", "type": "slider", "default": 10}
    if binding:
        parameter["binding"] = binding
    (project_dir / "project.json").write_text(json.dumps({
        "project": {"slug": SLUG, "name": "Bound", "thumbnail": "t.png", "tags": [], "difficulty": "beginner"},
        "modes": [{"id": "body", "scad_file": "part.graph.json", "parts": ["body"]}],
        "parts": [{"id": "body"}],
        "parameters": [parameter],
    }))


def test_graph_task_rereads_the_manifest(tmp_path):
    project_dir = tmp_path / SLUG
    project_dir.mkdir()
    _write(project_dir, None)
    assert render_worker._task_manifest(SLUG, "graph").parameters[0].get("binding") is None

    _write(project_dir, "body.w")  # the API's bindings write, from another process

    assert render_worker._task_manifest(SLUG, "graph").parameters[0]["binding"] == "body.w"


def test_other_engines_keep_the_cached_manifest(tmp_path):
    project_dir = tmp_path / SLUG
    project_dir.mkdir()
    _write(project_dir, None)
    first = render_worker._task_manifest(SLUG, "cadquery")

    _write(project_dir, "body.w")

    assert render_worker._task_manifest(SLUG, "cadquery") is first
