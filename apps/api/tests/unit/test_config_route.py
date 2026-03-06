"""Tests for the legacy /api/config endpoint and its deprecation headers."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project manifest directly in tmp_path (single-project mode)."""
    manifest = {
        "project": {
            "name": "Config Test Project",
            "slug": "config-test",
            "version": "1.0.0",
            "description": {"en": "Test project for config route"},
            "thumbnail": "thumb.png",
            "tags": ["test"],
            "difficulty": "beginner",
        },
        "modes": [
            {
                "id": "default",
                "scad_file": "main.scad",
                "label": {"en": "Default"},
                "parts": ["body"],
                "estimate": {"base_units": 1, "formula": "constant"},
            }
        ],
        "parts": [
            {
                "id": "body",
                "render_mode": 0,
                "label": {"en": "Body"},
                "default_color": "#3498db",
            }
        ],
        "parameters": [],
        "estimate_constants": {
            "base_time": 5,
            "per_unit": 2,
            "per_part": 8,
            "fn_factor": 48,
            "wasm_multiplier": 3,
            "warning_threshold_seconds": 60,
        },
    }
    (tmp_path / "project.json").write_text(json.dumps(manifest))
    (tmp_path / "main.scad").write_text("cube(10);")
    return tmp_path


@pytest.fixture
def client(project_dir, monkeypatch):
    from config import Config

    monkeypatch.setattr(Config, "SCAD_DIR", project_dir)
    monkeypatch.setattr(Config, "MULTI_PROJECT", False)
    monkeypatch.setattr(Config, "STATIC_DIR", project_dir / "static")
    (project_dir / "static").mkdir(exist_ok=True)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestConfigEndpoint:
    """Tests for GET /api/config response body."""

    def test_returns_200(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200

    def test_response_contains_expected_keys(self, client):
        data = client.get("/api/config").get_json()
        assert "parts_map" in data
        assert "mode_map" in data
        assert "estimate_constants" in data

    def test_parts_map_is_dict(self, client):
        data = client.get("/api/config").get_json()
        assert isinstance(data["parts_map"], dict)

    def test_mode_map_is_dict(self, client):
        data = client.get("/api/config").get_json()
        assert isinstance(data["mode_map"], dict)

    def test_estimate_constants_is_dict(self, client):
        data = client.get("/api/config").get_json()
        assert isinstance(data["estimate_constants"], dict)


class TestConfigDeprecationHeaders:
    """Tests that the legacy /api/config endpoint returns proper deprecation headers."""

    def test_deprecation_header_present(self, client):
        resp = client.get("/api/config")
        assert resp.headers.get("Deprecation") == "true"

    def test_sunset_header_present(self, client):
        resp = client.get("/api/config")
        assert resp.headers.get("Sunset") == "2026-06-01"

    def test_link_header_points_to_successor(self, client):
        resp = client.get("/api/config")
        link = resp.headers.get("Link")
        assert link is not None
        assert "</api/manifest>" in link
        assert 'rel="successor-version"' in link
