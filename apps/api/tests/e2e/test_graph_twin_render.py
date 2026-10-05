"""User cartridges render their declared graph; curated cartridges render their script.

A graph-twin cartridge declares both a script (``scad_file``/``cq_file``) and a
node graph (``graph_file``) for a mode. In a user cartridge (a fork or a GitHub
import) the graph is the render source: it is what the Studio graph editor
saves, and in a fork it is the only editable source. The commons keeps
rendering the script (services/engine/render_source.py).

These tests drive the real ``/api/render`` route, the real render worker
(inline, through tests/inline_render_worker.py — only the Redis hop is in
memory) and the real CadQuery kernel, then measure the STL that comes back.

``TestTwinFixture`` uses a small twin defined here and always runs.
``TestCommonsTwinAcceptance`` uses the commons' own bed-extrusion-mount twin;
it runs wherever that cartridge carries its graph (the commons submodule at a
pin that includes it, or ``Y4D_TWIN_COMMONS_DIR`` pointing at a commons
checkout) and skips elsewhere.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

trimesh = pytest.importorskip("trimesh")
pytest.importorskip("cadquery")

REPO_ROOT = Path(__file__).resolve().parents[4]

SLUG = "twin-plate"
FORK = "my-twin-plate"
GRAPH = "plate.graph.json"

TWIN_SCRIPT = '''\
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


width = float(PARAM(lambda: width, 30.0))
result = cq.Workplane("XY").box(width, 20.0, 5.0)
'''


def _graph(depth: float) -> dict:
    return {
        "version": "1.1.0",
        "units": "mm",
        "parameters": {"width": {"default": 30.0}},
        "nodes": [{
            "id": "plate", "type": "box",
            "params": {"w": {"expr": "width"}, "d": depth, "h": 5.0},
        }],
        "outputs": {"plate": "plate"},
    }


TWIN_MANIFEST = {
    "project": {
        "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
        "name": "Twin Plate", "slug": SLUG, "version": "1.0.0", "engine": "cadquery",
    },
    "modes": [{
        "id": "plate", "label": {"en": "Plate"},
        "scad_file": "main.py", "cq_file": "main.py", "graph_file": GRAPH,
        "parts": ["plate"], "estimate": {"base_units": 1, "formula": "constant"},
    }],
    "parts": [{"id": "plate", "render_mode": 0, "label": {"en": "Plate"}, "default_color": "#ffffff"}],
    "parameters": [{
        "id": "width", "type": "slider", "default": 30, "min": 10, "max": 80, "label": {"en": "Width"},
    }],
    "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class _ThreadedWorker:
    """``render_worker`` with each task run on a fresh thread (no request context)."""

    def __init__(self, worker):
        self._worker = worker

    def _run(self, fn, task):
        failure = []

        def target():
            try:
                fn(task)
            except BaseException as exc:  # surfaced on the test thread below
                failure.append(exc)

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=300)
        assert not thread.is_alive(), "render task did not finish"
        if failure:
            raise failure[0]

    def process_sync_task(self, task):
        self._run(self._worker.process_sync_task, task)

    def process_stream_task(self, task):
        self._run(self._worker.process_stream_task, task)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Real route, inline worker, real CadQuery; renders land in a scratch store."""
    import render_worker
    from inline_render_worker import install

    from services.engine import render_orchestrator
    from services.engine.render_cache import RenderCache
    from services.storage import FilesystemArtifactStore

    static = tmp_path / "static"
    queue = install(monkeypatch, static)
    # The inline Redis hands a pushed task to the worker on the request's own
    # thread. The real worker is a separate process with no Flask request
    # context, and the CadQuery entry points refuse to run inside one
    # (services/engine/engine_guard.py) — so each task runs on its own thread
    # here, which is what lets the real kernel run.
    queue.worker = _ThreadedWorker(render_worker)
    store = FilesystemArtifactStore(static)
    cache = RenderCache(store=store)
    monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
    monkeypatch.setattr(render_worker, "render_cache", cache)
    monkeypatch.setattr(render_orchestrator, "render_cache", cache)
    # The viewer GLB is not under test; the STL is what gets measured.
    monkeypatch.setattr(render_worker, "stl_to_glb", lambda src, dst: False)
    # One subprocess per part keeps the run independent of a warm pool.
    monkeypatch.setenv("YANTRA4D_CQ_POOL_ENABLED", "0")
    # CadQuery and graph renders are pro features; auth is off in tests.
    from config import Config
    monkeypatch.setattr(Config, "HARNESS_TIER", "pro")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    # Local development mode (auth off + debugger on): the write guard lets any
    # caller write forks, so this exercises the render source, not identity.
    # Who may write a fork is covered in test_cartridge_ownership_api.py.
    flask_app.debug = True
    return flask_app.test_client(), queue, static


def _render(client, project, mode="plate", **parameters):
    res = client.post("/api/render", json={
        "project": project, "mode": mode, "parameters": parameters, "export_format": "stl",
    })
    assert res.status_code == 200, res.get_json()
    return res


def _extents(static: Path, res) -> list[float]:
    (part,) = res.get_json()["parts"]
    mesh = trimesh.load(static / part["url"].removeprefix("/static/"), force="mesh")
    return [round(float(v), 3) for v in mesh.extents]


@pytest.fixture
def twin(tmp_path):
    """The twin fixture as a commons cartridge."""
    cart = tmp_path / SLUG
    cart.mkdir()
    (cart / "project.json").write_text(json.dumps(TWIN_MANIFEST))
    (cart / "main.py").write_text(TWIN_SCRIPT)
    (cart / GRAPH).write_text(json.dumps(_graph(20.0), indent=2))
    return cart


def _fork(client, source: str, new_slug: str) -> Path:
    res = client.post(f"/api/projects/{source}/fork", json={"new_slug": new_slug})
    assert res.status_code == 200, res.get_json()
    from config import Config
    return Path(Config.USER_PROJECTS_DIR) / new_slug


class TestTwinFixture:
    def test_commons_twin_renders_its_script(self, harness, twin):
        client, queue, static = harness
        res = _render(client, SLUG)

        (task,) = queue.pushed
        assert task["engine"] == "cadquery"
        assert Path(task["scad_path"]).name == "main.py"
        assert task["scad_filename"] == "main.py"
        assert _extents(static, res) == [30.0, 20.0, 5.0]

    def test_fork_renders_its_edited_graph(self, harness, twin):
        client, queue, static = harness
        before = _snapshot(twin)
        fork = _fork(client, SLUG, FORK)

        res = client.put(f"/api/projects/{FORK}/files/{GRAPH}", json={"content": json.dumps(_graph(30.0))})
        assert res.status_code == 200, res.get_json()

        res = _render(client, FORK)
        (task,) = queue.pushed
        assert task["engine"] == "graph"
        assert Path(task["scad_path"]).resolve() == (fork / GRAPH).resolve()
        assert task["scad_filename"] == GRAPH
        assert _extents(static, res) == [30.0, 30.0, 5.0]

        # Manifest parameters still drive the graph.
        assert _extents(static, _render(client, FORK, width=50)) == [50.0, 30.0, 5.0]
        # The commons copy was never written.
        assert _snapshot(twin) == before

    def test_fork_render_cache_follows_the_graph(self, harness, twin):
        from services.engine.render_orchestrator import extract_render_payload

        client, queue, static = harness
        _fork(client, SLUG, FORK)
        request = {"project": FORK, "mode": "plate", "parameters": {}}

        with client.application.test_request_context():
            first = extract_render_payload(request)
        assert _extents(static, _render(client, FORK)) == [30.0, 20.0, 5.0]
        assert _render(client, FORK).headers["X-Cache"] == "HIT"

        client.put(f"/api/projects/{FORK}/files/{GRAPH}", json={"content": json.dumps(_graph(40.0))})
        with client.application.test_request_context():
            second = extract_render_payload(request)
        assert second["scad_content_hash"] != first["scad_content_hash"]
        assert second["stl_prefix"] != first["stl_prefix"]

        res = _render(client, FORK)
        assert res.headers["X-Cache"] == "MISS"
        assert _extents(static, res) == [30.0, 40.0, 5.0]
        assert len(queue.pushed) == 2  # the HIT queued nothing

    def test_fork_binding_edit_reaches_the_render(self, harness, twin):
        """Bindings validate against the fork's graph, re-key the cache and reach the worker."""
        client, _queue, static = harness
        _fork(client, SLUG, FORK)
        assert _extents(static, _render(client, FORK, width=50)) == [50.0, 20.0, 5.0]

        res = client.put(f"/api/projects/{FORK}/manifest/bindings", json={"bindings": {"width": "plate.d"}})
        assert res.status_code == 200, res.get_json()

        res = _render(client, FORK, width=50)
        assert res.headers["X-Cache"] == "MISS"
        assert _extents(static, res) == [50.0, 50.0, 5.0]

    def test_fork_render_revision_follows_its_sources(self, harness, twin, monkeypatch):
        """The Studio keys its persistent cache on X-Render-Revision; a save must move it."""
        client, _queue, _static = harness
        monkeypatch.setenv("RENDER_BUILD_ID", "release-one")
        _fork(client, SLUG, FORK)

        commons = client.get(f"/api/projects/{SLUG}/manifest").headers["X-Render-Revision"]
        before = client.get(f"/api/projects/{FORK}/manifest").headers["X-Render-Revision"]
        client.put(f"/api/projects/{FORK}/files/{GRAPH}", json={"content": json.dumps(_graph(30.0))})
        after = client.get(f"/api/projects/{FORK}/manifest").headers["X-Render-Revision"]

        assert commons == "release-one"
        assert before.startswith("release-one+src.") and after.startswith("release-one+src.")
        assert before != after

    def test_commons_twin_ignores_a_graph_edit_on_disk(self, harness, twin):
        """Even if the commons graph changed, the commons renders main.py."""
        client, queue, static = harness
        (twin / GRAPH).write_text(json.dumps(_graph(70.0)))
        res = _render(client, SLUG)
        assert queue.pushed[0]["engine"] == "cadquery"
        assert _extents(static, res) == [30.0, 20.0, 5.0]

    def test_fork_with_a_missing_graph_is_a_visible_error(self, harness, twin):
        client, queue, _static = harness
        fork = _fork(client, SLUG, FORK)
        (fork / GRAPH).unlink()

        res = client.post("/api/render", json={"project": FORK, "mode": "plate", "parameters": {}})
        assert res.status_code == 400
        assert "does not exist" in res.get_json()["error"]
        assert queue.pushed == []  # never fell back to main.py

    def test_fork_manifest_names_the_fork(self, harness, twin):
        client, _queue, _static = harness
        _fork(client, SLUG, FORK)
        res = client.get(f"/api/projects/{FORK}/manifest")
        assert res.get_json()["project"]["slug"] == FORK


# ── Acceptance: the commons' bed-extrusion-mount twin ──────────────────────────

ACCEPT_SLUG = "bed-extrusion-mount"
ACCEPT_FORK = "my-bed-extrusion-mount"
ACCEPT_GRAPH = "bed-mount.graph.json"


def _commons_twin_dir() -> Path | None:
    candidates = []
    if os.environ.get("Y4D_TWIN_COMMONS_DIR"):
        candidates.append(Path(os.environ["Y4D_TWIN_COMMONS_DIR"]) / ACCEPT_SLUG)
    candidates.append(REPO_ROOT / "projects" / ACCEPT_SLUG)
    for cart in candidates:
        manifest = cart / "project.json"
        if (cart / ACCEPT_GRAPH).is_file() and manifest.is_file():
            modes = json.loads(manifest.read_text()).get("modes", [])
            if any(m.get("graph_file") == ACCEPT_GRAPH for m in modes):
                return cart
    return None


@pytest.mark.skipif(_commons_twin_dir() is None, reason="the commons bed-extrusion-mount graph twin is not present")
class TestCommonsTwinAcceptance:
    @pytest.fixture
    def commons_twin(self, tmp_path):
        cart = tmp_path / ACCEPT_SLUG
        shutil.copytree(_commons_twin_dir(), cart)
        return cart

    def test_widened_crossbar_renders_in_the_fork_only(self, harness, commons_twin):
        client, queue, static = harness
        before = _snapshot(commons_twin)

        commons = _render(client, ACCEPT_SLUG, mode="bed_mount")
        assert queue.pushed[-1]["engine"] == "cadquery"
        assert Path(queue.pushed[-1]["scad_path"]).name == "main.py"
        assert _extents(static, commons) == [44.5, 35.5, 6.5]

        fork = _fork(client, ACCEPT_SLUG, ACCEPT_FORK)
        document = json.loads((fork / ACCEPT_GRAPH).read_text())
        (node,) = [n for n in document["nodes"] if n["id"] == "crossbar_blank"]
        node["params"]["w"] = {"expr": node["params"]["w"]["expr"] + " + 10"}
        res = client.put(f"/api/projects/{ACCEPT_FORK}/files/{ACCEPT_GRAPH}",
                         json={"content": json.dumps(document, indent=2)})
        assert res.status_code == 200, res.get_json()

        edited = _render(client, ACCEPT_FORK, mode="bed_mount")
        assert queue.pushed[-1]["engine"] == "graph"
        assert Path(queue.pushed[-1]["scad_path"]).name == ACCEPT_GRAPH
        assert _extents(static, edited) == [54.5, 35.5, 6.5]
        assert edited.get_json()["parts"][0]["url"] != commons.get_json()["parts"][0]["url"]

        # The commons still renders main.py, unchanged.
        again = _render(client, ACCEPT_SLUG, mode="bed_mount")
        assert _extents(static, again) == [44.5, 35.5, 6.5]
        assert _snapshot(commons_twin) == before
