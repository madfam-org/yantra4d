"""Tests for GitHub import API routes."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "GITHUB_IMPORT_ENABLED", True)

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestValidateEndpoint:
    @patch("routes.github.validate_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_validate_success(self, mock_token, mock_validate, client):
        mock_validate.return_value = {
            "valid": True,
            "scad_files": [{"path": "main.scad", "name": "main.scad", "size": 100}],
            "has_manifest": False,
            "manifest": None,
        }
        res = client.post("/api/github/validate", json={"repo_url": "https://github.com/u/r"})
        assert res.status_code == 200

    @patch("routes.github.validate_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_validate_invalid_repo(self, mock_token, mock_validate, client):
        mock_validate.return_value = {"valid": False, "error": "Not found"}
        res = client.post("/api/github/validate", json={"repo_url": "https://github.com/u/r"})
        assert res.status_code == 400

    def test_validate_missing_url(self, client):
        res = client.post("/api/github/validate", json={})
        assert res.status_code == 400

    def test_validate_disabled(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "GITHUB_IMPORT_ENABLED", False)
        res = client.post("/api/github/validate", json={"repo_url": "https://github.com/u/r"})
        assert res.status_code == 403


class TestImportEndpoint:
    @patch("routes.github.import_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_import_success(self, mock_token, mock_import, client):
        mock_import.return_value = {"success": True, "slug": "new-proj"}
        res = client.post("/api/github/import", json={
            "repo_url": "https://github.com/u/r",
            "slug": "new-proj",
            "manifest": {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test"}},
        })
        assert res.status_code == 201

    def test_import_missing_slug(self, client):
        res = client.post("/api/github/import", json={
            "repo_url": "https://github.com/u/r",
            "manifest": {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", }},
        })
        assert res.status_code == 400

    def test_import_invalid_slug(self, client):
        res = client.post("/api/github/import", json={
            "repo_url": "https://github.com/u/r",
            "slug": "INVALID SLUG",
            "manifest": {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", }},
        })
        assert res.status_code == 400

    def test_import_missing_manifest(self, client):
        res = client.post("/api/github/import", json={
            "repo_url": "https://github.com/u/r",
            "slug": "new-proj",
        })
        assert res.status_code == 400

    def test_import_missing_url(self, client):
        res = client.post("/api/github/import", json={
            "slug": "new-proj",
            "manifest": {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", }},
        })
        assert res.status_code == 400

    @patch("routes.github.import_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_import_failure(self, mock_token, mock_import, client):
        mock_import.return_value = {"success": False, "error": "Already exists"}
        res = client.post("/api/github/import", json={
            "repo_url": "https://github.com/u/r",
            "slug": "new-proj",
            "manifest": {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", }},
        })
        assert res.status_code == 400


class TestSyncEndpoint:
    @patch("routes.github.sync_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_sync_success(self, mock_token, mock_sync, client):
        mock_sync.return_value = {"success": True, "updated_files": ["main.scad"]}
        res = client.post("/api/github/sync", json={"slug": "test-project"})
        assert res.status_code == 200

    @patch("routes.github.sync_repo")
    @patch("routes.github.get_github_token", return_value=None)
    def test_sync_failure(self, mock_token, mock_sync, client):
        mock_sync.return_value = {"success": False, "error": "No metadata"}
        res = client.post("/api/github/sync", json={"slug": "test-project"})
        assert res.status_code == 400

    def test_sync_missing_slug(self, client):
        res = client.post("/api/github/sync", json={})
        assert res.status_code == 400
