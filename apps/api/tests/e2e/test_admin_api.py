"""Tests for admin API routes."""
import json
import sys
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def disable_auth():
    with patch("config.Config.AUTH_ENABLED", False):
        yield


@pytest.fixture
def app(tmp_path):
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [
            {"id": "single", "scad_file": "main.scad", "label": {"en": "Single"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}},
            {"id": "grid", "scad_file": "grid.scad", "label": {"en": "Grid"}, "parts": ["grid"], "estimate": {"base_units": 1, "formula": "grid", "formula_vars": ["rows", "cols"]}},
        ],
        "parts": [
            {"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"},
            {"id": "grid", "render_mode": 0, "label": {"en": "Grid"}, "default_color": "#ffffff"},
        ],
        "parameters": [
            {"id": "size", "type": "number", "default": 20, "min": 5, "max": 100, "label": {"en": "Size"}},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    (project_dir / "grid.scad").write_text("cube(5);")

    exports_dir = project_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "sample.stl").write_bytes(b"\x00" * 100)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestAdminAPI:
    def test_list_projects_enriched(self, client):
        res = client.get("/api/admin/projects")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) >= 1
        proj = data[0]
        assert proj["slug"] == "test-project"
        assert proj["has_manifest"] is True
        assert proj["scad_file_count"] == 2
        assert proj["has_exports"] is True
        assert proj["mode_count"] == 2
        assert proj["parameter_count"] == 1
        assert "modified_at" in proj

    def test_project_detail(self, client):
        res = client.get("/api/admin/projects/test-project")
        assert res.status_code == 200
        data = res.get_json()
        assert data["slug"] == "test-project"
        assert len(data["scad_files"]) == 2
        assert len(data["modes"]) == 2
        assert len(data["exports"]) == 1

    def test_project_detail_nonexistent(self, client):
        res = client.get("/api/admin/projects/nonexistent")
        assert res.status_code == 404
