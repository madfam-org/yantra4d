"""Tests for download endpoints."""
import json
from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def tmp_projects(tmp_path):
    """Create a temp project dir with a manifest and files."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    manifest = {
        "project": {"name": "Test", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "single", "scad_file": "main.scad", "label": "Single", "parts": ["body"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "body", "render_mode": 1, "label": "Body", "default_color": "#FF0000"}],
        "parameters": [],
        "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    exports_dir = project_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "test.stl").write_bytes(b"solid test\nendsolid")

    return tmp_path


@pytest.fixture
def app(tmp_projects):
    with patch("config.Config.PROJECTS_DIR", tmp_projects), \
         patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
         patch("config.Config.AUTH_ENABLED", False):
        (tmp_projects / "static").mkdir(exist_ok=True)
        application = create_app()
        application.config["TESTING"] = True
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


class TestStlDownload:
    def test_returns_file_when_public(self, client):
        resp = client.get("/api/projects/test-project/download/stl/test.stl")
        assert resp.status_code == 200

    def test_returns_401_when_gated_no_token(self, tmp_projects):
        """When download_stl requires auth and no token is present."""
        manifest_path = tmp_projects / "test-project" / "project.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["access_control"] = {"download_stl": "authenticated"}
        manifest_path.write_text(json.dumps(manifest))

        with patch("config.Config.PROJECTS_DIR", tmp_projects), \
             patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
             patch("config.Config.AUTH_ENABLED", True):
            app = create_app()
            app.config["TESTING"] = True
            client = app.test_client()
            # Clear manifest cache
            import manifest as m
            m._manifest_cache.clear()

            resp = client.get("/api/projects/test-project/download/stl/test.stl")
            assert resp.status_code == 401

    def test_rejects_path_traversal(self, client):
        # Flask routing sanitizes .. in URL path segments → 404
        resp = client.get("/api/projects/test-project/download/stl/../../../etc/passwd")
        assert resp.status_code == 404

    def test_returns_404_for_missing_file(self, client):
        resp = client.get("/api/projects/test-project/download/stl/nonexistent.stl")
        assert resp.status_code == 404


class TestScadDownload:
    def test_returns_file_when_public_and_allowed(self, client):
        resp = client.get("/api/projects/test-project/download/scad/main.scad")
        assert resp.status_code == 200

    def test_rejects_path_traversal(self, client):
        # Flask routing sanitizes .. in URL path segments → 404
        resp = client.get("/api/projects/test-project/download/scad/../../etc/passwd")
        assert resp.status_code == 404

    def test_rejects_unlisted_file(self, client):
        resp = client.get("/api/projects/test-project/download/scad/secret.scad")
        assert resp.status_code == 403
