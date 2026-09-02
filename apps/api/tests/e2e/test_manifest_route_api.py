"""Tests for manifest route API."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [{"id": "size", "type": "number", "default": 20, "min": 5, "max": 100, "label": {"en": "Size"}}],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    # /api/manifest with no slug falls back to SCAD_DIR
    monkeypatch.setattr(Config, "SCAD_DIR", project_dir)
    monkeypatch.setattr(Config, "MULTI_PROJECT", False)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestManifestRouteAPI:
    def test_get_manifest(self, client):
        res = client.get("/api/manifest")
        assert res.status_code == 200
        data = res.get_json()
        assert "project" in data
        assert "modes" in data
        assert "parameters" in data
        assert data["project"]["slug"] == "test-project"

    def test_multi_project_requires_slug(self, tmp_path, monkeypatch):
        from config import Config

        project_dir = tmp_path / "mp-project"
        project_dir.mkdir()
        (project_dir / "project.json").write_text('{"project":{"name":"X","slug":"x","version":"1.0.0","thumbnail":"t.png","tags":[],"difficulty":"beginner"},"modes":[],"parts":[],"parameters":[],"estimate_constants":{}}')
        monkeypatch.setattr(Config, "SCAD_DIR", project_dir)
        monkeypatch.setattr(Config, "MULTI_PROJECT", True)

        from app import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            res = c.get("/api/manifest")
            assert res.status_code == 400


class TestMissingProjectDisclosesNoPath:
    """A 404 for a project that is not there names the slug, not the filesystem.

    `manifest.py::load_manifest` interpolated the resolved `manifest_path` into
    the RuntimeError, and every manifest route answers a missing project with
    `{"error": str(e)}`. But `_resolve_project_dir` falls back to
    `Config.SCAD_DIR` for any slug it cannot resolve, so the body a caller got
    for "does-not-exist" was the deployment's absolute path *and* the name of
    the single-project fallback cartridge — in production, "gridfinity". Two
    disclosures the caller never asked about: the container layout, and a
    project slug that has nothing to do with the request.
    """

    MISSING = "does-not-exist"

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        """Multi-project mode with the fallback pointed at an empty cartridge dir.

        This is the production shape: `SCAD_DIR` names a directory with no
        `project.json`, so an unresolvable slug falls through to it and raises
        rather than silently serving the fallback's manifest.
        """
        from config import Config

        fallback = tmp_path / "gridfinity"
        fallback.mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])
        monkeypatch.setattr(Config, "SCAD_DIR", fallback)
        monkeypatch.setattr(Config, "MULTI_PROJECT", True)

        from app import create_app
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        self.tmp_path = tmp_path
        return flask_app.test_client()

    def _bodies(self, client):
        """Both manifest routes' 404 bodies, as `error` strings.

        The legacy route answers `make_response(json.dumps(...))`, which carries
        no JSON content type, so `get_json()` returns None for it — the body is
        decoded by hand rather than papering over that with a helper that only
        works on one of the two.
        """
        for res in (
            client.get(f"/api/manifest?project={self.MISSING}"),
            client.get(f"/api/projects/{self.MISSING}/manifest"),
        ):
            yield res, json.loads(res.get_data(as_text=True))["error"]

    def test_body_names_the_requested_slug(self, client):
        for res, body in self._bodies(client):
            assert res.status_code == 404
            assert self.MISSING in body

    def test_body_carries_no_filesystem_path_and_no_fallback_slug(self, client):
        for _res, body in self._bodies(client):
            assert "gridfinity" not in body, f"fallback cartridge leaked: {body}"
            assert "project.json" not in body, f"filesystem path leaked: {body}"
            assert str(self.tmp_path) not in body, f"filesystem path leaked: {body}"
            assert "/" not in body, f"path separator in a 404 body: {body}"

    def test_the_path_is_still_logged_server_side(self, client, caplog):
        """The operator keeps the useful half; the caller does not get it."""
        with caplog.at_level("ERROR", logger="manifest"):
            client.get(f"/api/manifest?project={self.MISSING}")

        assert any("project.json" in rec.getMessage() for rec in caplog.records)
