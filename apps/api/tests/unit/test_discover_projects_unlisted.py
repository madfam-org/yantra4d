"""Tests for unlisted project filtering in discover_projects and public listing."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _create_project(base_dir, slug, *, unlisted=False):
    """Helper to create a minimal project directory with manifest."""
    project_dir = base_dir / slug
    project_dir.mkdir()
    manifest = {
        "project": {
            "name": slug.replace("-", " ").title(),
            "slug": slug,
            "version": "1.0.0",
            "thumbnail": "thumb.png",
            "tags": ["test"],
            "difficulty": "beginner",
        },
        "modes": [
            {
                "id": "default",
                "scad_file": "main.scad",
                "label": {"en": "Default"},
                "parts": ["main"],
                "estimate": {"base_units": 1, "formula": "constant"},
            }
        ],
        "parts": [
            {"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}
        ],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    if unlisted:
        manifest["project"]["unlisted"] = True
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    return project_dir


@pytest.fixture(autouse=True)
def disable_auth():
    with patch("config.Config.AUTH_ENABLED", False):
        yield


@pytest.fixture
def app(tmp_path):
    _create_project(tmp_path, "visible-project")
    _create_project(tmp_path, "hidden-project", unlisted=True)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestUnlistedFiltering:
    def test_discover_projects_includes_unlisted_flag(self, client):
        """discover_projects() propagates the unlisted field."""
        from manifest import discover_projects
        projects = discover_projects()
        slugs = {p["slug"]: p for p in projects}
        assert "visible-project" in slugs
        assert "hidden-project" in slugs
        assert slugs["visible-project"].get("unlisted") is False
        assert slugs["hidden-project"].get("unlisted") is True

    def test_public_listing_excludes_unlisted(self, client):
        """GET /api/projects excludes unlisted projects."""
        res = client.get("/api/projects")
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.get_json()]
        assert "visible-project" in slugs
        assert "hidden-project" not in slugs

    def test_unlisted_manifest_accessible_directly(self, client):
        """GET /api/projects/<slug>/manifest works for unlisted projects."""
        res = client.get("/api/projects/hidden-project/manifest")
        assert res.status_code == 200
        assert res.get_json()["project"]["slug"] == "hidden-project"

    def test_public_listing_with_stats_excludes_unlisted(self, client):
        """GET /api/projects?stats=1 also excludes unlisted projects."""
        res = client.get("/api/projects?stats=1")
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.get_json()]
        assert "visible-project" in slugs
        assert "hidden-project" not in slugs
