"""Tests for admin API routes."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

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

    def test_patch_flags_set_is_demo(self, client):
        """PATCH /api/admin/projects/<slug>/flags sets is_demo in project.json."""
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={"is_demo": True},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["slug"] == "test-project"
        assert data["updated"]["is_demo"] is True

    def test_patch_flags_set_is_hyperobject(self, client):
        """PATCH sets is_hyperobject inside project.hyperobject."""
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={"is_hyperobject": True},
        )
        assert res.status_code == 200
        assert res.get_json()["updated"]["is_hyperobject"] is True

    def test_patch_flags_unknown_flag_rejected(self, client):
        """Unknown flags in body return 400."""
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={"bad_flag": True},
        )
        assert res.status_code == 400
        assert "Unknown flags" in res.get_json()["error"]

    def test_patch_flags_empty_body(self, client):
        """Empty JSON body returns 400 — no valid flags provided."""
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={},
        )
        assert res.status_code == 400
        assert "No valid flags" in res.get_json()["error"]

    def test_patch_flags_nonexistent_project(self, client):
        """PATCH on missing project returns 404."""
        res = client.patch(
            "/api/admin/projects/nonexistent/flags",
            json={"is_demo": True},
        )
        assert res.status_code == 404

    def test_list_projects_empty(self, client, monkeypatch):
        """When PROJECTS_DIR has no project subdirs with manifests, list returns no enriched projects."""
        import tempfile

        from config import Config
        with tempfile.TemporaryDirectory() as empty:
            monkeypatch.setattr(Config, "PROJECTS_DIR", Path(empty))
            res = client.get("/api/admin/projects")
            assert res.status_code == 200
            data = res.get_json()
            # Empty dir has no subdirs with project.json, so no enriched projects
            assert isinstance(data, list)
            assert all(p.get("has_manifest") is False for p in data)

    def test_project_detail_invalid_slug(self, client):
        """Slug with path traversal characters is rejected by require_valid_slug."""
        res = client.get("/api/admin/projects/../etc")
        assert res.status_code in (400, 404)

    def test_patch_flags_set_unlisted(self, client):
        """PATCH /api/admin/projects/<slug>/flags sets unlisted in project.json."""
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={"unlisted": True},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["slug"] == "test-project"
        assert data["updated"]["unlisted"] is True

    def test_unlisted_project_hidden_from_list(self, client, tmp_path):
        """After setting unlisted, project is excluded from GET /api/projects."""
        # Set the project as unlisted via the flags endpoint
        res = client.patch(
            "/api/admin/projects/test-project/flags",
            json={"unlisted": True},
        )
        assert res.status_code == 200

        # Clear manifest cache so discover_projects re-reads the updated manifest
        import manifest as manifest_mod
        manifest_mod.manifest_service._manifest_cache.clear()

        # The public listing should exclude the unlisted project
        res = client.get("/api/projects")
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.get_json()]
        assert "test-project" not in slugs

    def test_unlisted_project_still_accessible_directly(self, client, tmp_path):
        """An unlisted project's manifest is still accessible via direct slug."""
        # Set the project as unlisted
        client.patch(
            "/api/admin/projects/test-project/flags",
            json={"unlisted": True},
        )

        # Clear manifest cache
        import manifest as manifest_mod
        manifest_mod.manifest_service._manifest_cache.clear()

        # Direct access still works
        res = client.get("/api/projects/test-project/manifest")
        assert res.status_code == 200
        assert res.get_json()["project"]["slug"] == "test-project"


class TestTablacoPublicLink:
    """Tests for the tablaco public-link admin endpoint."""

    def test_public_link_url_format(self, client):
        """URL must use path-based format, not hash fragment."""
        res = client.get("/api/admin/projects/tablaco/public-link")
        assert res.status_code == 200
        data = res.get_json()
        assert "/project/tablaco" in data["public_url"]
        assert "mode=storefront" in data["public_url"]
        assert "#" not in data["public_url"]

    def test_public_link_includes_studio_url(self, client):
        """Response must include studio_url field."""
        res = client.get("/api/admin/projects/tablaco/public-link")
        assert res.status_code == 200
        data = res.get_json()
        assert "studio_url" in data
        assert "/project/tablaco" in data["studio_url"]
        assert "storefront" not in data["studio_url"]
