"""E2E tests for GET /api/projects/<slug>/graph — the public, read-only graph view.

The route serves exactly one file per request: the ``.graph.json`` the manifest
names for the requested mode. These tests stage real cartridges on disk (a
graph-engine cartridge, a script with a graph twin, a fork of that twin, a
script-only cartridge and a private one) and drive the real route.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

GRAPH_SLUG = "flange-demo"
TWIN_SLUG = "twin-demo"
FORK_SLUG = "my-twin-demo"
SCRIPT_SLUG = "script-demo"
PRIVATE_SLUG = "client-graph"

GRAPH_DOC = {
    "version": "1.0.0",
    "units": "mm",
    "nodes": [
        {"id": "outline", "type": "profile_circle", "params": {"r": 45}},
        {"id": "plate", "type": "extrude", "inputs": {"profile": "outline"}, "params": {"height": 8}},
    ],
    "outputs": {"flange": "plate"},
}


def _mode(mode_id, scad_file, **extra):
    return {
        "id": mode_id, "scad_file": scad_file, "label": {"en": mode_id},
        "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}, **extra,
    }


def _manifest(slug, modes, engine=None, **extra):
    manifest = {
        "project": {
            "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
            "name": slug, "slug": slug, "version": "1.0.0",
        },
        "modes": modes,
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [{
            "id": "plate_radius", "type": "slider", "default": 45, "min": 20, "max": 80,
            "label": {"en": "Plate radius"}, "binding": "outline.r",
        }],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        **extra,
    }
    if engine:
        manifest["project"]["engine"] = engine
    return manifest


def _write(project: Path, manifest: dict, files: dict[str, str]):
    project.mkdir(parents=True, exist_ok=True)
    (project / "project.json").write_text(json.dumps(manifest))
    for name, text in files.items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text(text)


@pytest.fixture
def tree(tmp_path, user_projects_dir):
    graph_text = json.dumps(GRAPH_DOC, indent=2)
    _write(tmp_path / GRAPH_SLUG, _manifest(GRAPH_SLUG, [
        _mode("flange", "flange.graph.json", engine="graph"),
        _mode("blank", "flange.graph.json", engine="graph"),
    ], engine="graph"), {"flange.graph.json": graph_text})

    twin_modes = [_mode("drive", "main.py", graph_file="drive.graph.json")]
    _write(tmp_path / TWIN_SLUG, _manifest(TWIN_SLUG, twin_modes, engine="cadquery"),
           {"main.py": "# cadquery\n", "drive.graph.json": graph_text})

    _write(user_projects_dir / FORK_SLUG, _manifest(FORK_SLUG, twin_modes, engine="cadquery"),
           {"main.py": "# cadquery\n", "drive.graph.json": graph_text,
            "project.meta.json": json.dumps({"source": {"type": "fork", "slug": TWIN_SLUG}})})

    _write(tmp_path / SCRIPT_SLUG, _manifest(SCRIPT_SLUG, [_mode("default", "main.scad")]),
           {"main.scad": "cube(10);\n"})

    _write(tmp_path / PRIVATE_SLUG, _manifest(
        PRIVATE_SLUG, [_mode("flange", "flange.graph.json", engine="graph")],
        engine="graph", access_control={"view": "private"},
    ), {"flange.graph.json": graph_text})

    (tmp_path / "secret.graph.json").write_text('{"secret": true}')
    return {"root": tmp_path, "graph_text": graph_text}


@pytest.fixture
def client(tree):
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _get(client, slug=GRAPH_SLUG, mode="flange", **kwargs):
    query = f"?mode={mode}" if mode is not None else ""
    return client.get(f"/api/projects/{slug}/graph{query}", **kwargs)


def _rewrite_manifest(root: Path, slug: str, manifest: dict):
    (root / slug / "project.json").write_text(json.dumps(manifest))
    import manifest as manifest_mod
    manifest_mod.invalidate_cache(slug)


class TestGraphMode:
    def test_200_signed_out(self, client):
        assert _get(client).status_code == 200

    def test_contract(self, client, tree):
        body = _get(client).get_json()

        assert body == {
            "mode": "flange", "path": "flange.graph.json", "role": "source",
            "script": None, "content": tree["graph_text"],
        }

    def test_content_is_the_file_verbatim(self, client, tree):
        assert json.loads(_get(client).get_json()["content"]) == GRAPH_DOC

    def test_every_graph_mode_is_served(self, client):
        assert _get(client, mode="blank").get_json()["path"] == "flange.graph.json"


class TestGraphTwin:
    def test_curated_twin_is_served_as_a_twin(self, client):
        body = _get(client, slug=TWIN_SLUG, mode="drive").get_json()

        assert body["path"] == "drive.graph.json"
        assert body["role"] == "twin"
        assert body["script"] == "main.py"

    def test_a_forks_twin_is_its_render_source(self, client):
        body = _get(client, slug=FORK_SLUG, mode="drive").get_json()

        assert body["role"] == "source"
        assert body["script"] is None


class TestRefusals:
    def test_mode_is_required(self, client):
        res = _get(client, mode=None)

        assert res.status_code == 400
        assert res.get_json()["error_code"] == "mode_required"

    def test_unknown_mode_404(self, client):
        res = _get(client, mode="nope")

        assert res.status_code == 404
        assert res.get_json()["error_code"] == "mode_not_found"

    def test_script_mode_is_not_a_graph(self, client):
        res = _get(client, slug=SCRIPT_SLUG, mode="default")

        assert res.status_code == 404
        assert res.get_json()["error_code"] == "not_a_graph_mode"

    def test_unknown_slug_404(self, client):
        res = _get(client, slug="no-such-cartridge")

        assert res.status_code == 404

    def test_malformed_slug_400(self, client):
        assert _get(client, slug="NotASlug!").status_code == 400

    def test_the_mode_parameter_never_names_a_path(self, client):
        res = _get(client, mode="../secret.graph.json")

        assert res.status_code == 404
        assert "secret" not in res.get_data(as_text=True)

    def test_a_graph_file_outside_the_cartridge_is_never_read(self, client, tree):
        modes = [_mode("drive", "main.py", graph_file="../secret.graph.json")]
        _rewrite_manifest(tree["root"], TWIN_SLUG, _manifest(TWIN_SLUG, modes, engine="cadquery"))

        res = _get(client, slug=TWIN_SLUG, mode="drive")

        assert res.status_code == 404
        assert res.get_json()["error_code"] == "graph_unavailable"
        assert "secret" not in res.get_data(as_text=True)

    def test_a_graph_scad_file_outside_the_cartridge_is_never_read(self, client, tree):
        modes = [_mode("flange", "../secret.graph.json", engine="graph")]
        _rewrite_manifest(tree["root"], GRAPH_SLUG, _manifest(GRAPH_SLUG, modes, engine="graph"))

        res = _get(client)

        assert res.status_code == 404
        assert "secret" not in res.get_data(as_text=True)

    def test_a_missing_graph_file_404(self, client, tree):
        (tree["root"] / TWIN_SLUG / "drive.graph.json").unlink()

        res = _get(client, slug=TWIN_SLUG, mode="drive")

        assert res.status_code == 404
        assert res.get_json()["error_code"] == "graph_unavailable"

    def test_an_oversized_graph_413(self, client, monkeypatch):
        import routes.projects.projects as mod
        monkeypatch.setattr(mod, "MAX_GRAPH_VIEW_BYTES", 8)

        res = _get(client)

        assert res.status_code == 413
        assert res.get_json()["error_code"] == "graph_too_large"


class TestAccess:
    def test_a_private_cartridge_stays_private(self, client):
        res = _get(client, slug=PRIVATE_SLUG)

        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"
        assert "nodes" not in res.get_data(as_text=True)

    def test_no_tier_is_required(self, client, monkeypatch):
        """Auth on, no token: a public cartridge's graph is still served."""
        from config import Config
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)

        assert _get(client).status_code == 200


class TestCaching:
    def test_public_revalidates(self, client):
        res = _get(client)

        assert res.headers["Cache-Control"] == "public, no-cache"
        assert res.headers["ETag"]

    def test_304_on_matching_if_none_match(self, client):
        etag = _get(client).headers["ETag"].strip('"')

        res = _get(client, headers={"If-None-Match": f'"{etag}"'})

        assert res.status_code == 304
        assert res.get_data() == b""

    def test_editing_the_graph_changes_the_etag(self, client, tree):
        before = _get(client).headers["ETag"]
        (tree["root"] / GRAPH_SLUG / "flange.graph.json").write_text(json.dumps({**GRAPH_DOC, "units": "in"}))

        assert _get(client).headers["ETag"] != before


class TestRateLimit:
    def test_the_route_carries_its_own_limit(self, tree):
        """Rate-limit headers prove the decorator is registered with its value.

        The conftest fixture disables the limiter before create_app(), which
        skips hook registration, so re-init the limiter on a fresh app (the
        pattern test_animations_api.py uses).
        """
        from app import create_app
        from extensions import limiter

        app = create_app()
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = True
        limiter.enabled = True
        limiter.init_app(app)
        try:
            res = app.test_client().get(f"/api/projects/{GRAPH_SLUG}/graph?mode=flange")
            assert res.status_code == 200
            assert res.headers.get("X-RateLimit-Limit") == "500"
        finally:
            limiter.enabled = False
