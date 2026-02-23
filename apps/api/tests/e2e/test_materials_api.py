"""E2E tests for the /api/materials endpoints."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def app():
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# GET /api/materials
# ---------------------------------------------------------------------------
class TestListMaterials:
    @patch("routes.core.materials.discover_materials")
    def test_returns_materials_list(self, mock_discover, client):
        """Returns JSON array of discovered materials."""
        mock_discover.return_value = [
            {"material": {"slug": "pla", "name": "PLA"}},
            {"material": {"slug": "petg", "name": "PETG"}},
        ]
        res = client.get("/api/materials")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["material"]["slug"] == "pla"

    @patch("routes.core.materials.discover_materials")
    def test_empty_materials(self, mock_discover, client):
        """Returns empty list when no materials are discovered."""
        mock_discover.return_value = []
        res = client.get("/api/materials")
        assert res.status_code == 200
        assert res.get_json() == []

    @patch("routes.core.materials.discover_materials")
    def test_cache_control_header(self, mock_discover, client):
        """Response includes Cache-Control header with max-age."""
        mock_discover.return_value = []
        res = client.get("/api/materials")
        assert res.status_code == 200
        cache_header = res.headers.get("Cache-Control", "")
        assert "max-age" in cache_header

    @patch("routes.core.materials.discover_materials")
    def test_error_returns_500(self, mock_discover, client):
        """Internal exception results in 500 with error payload."""
        mock_discover.side_effect = Exception("disk error")
        res = client.get("/api/materials")
        assert res.status_code == 500
        data = res.get_json()
        assert data["status"] == "error"
        assert "disk error" in data["error"]


# ---------------------------------------------------------------------------
# GET /api/materials/<slug>
# ---------------------------------------------------------------------------
class TestGetMaterialBySlug:
    @patch("routes.core.materials.get_material")
    def test_found_returns_material(self, mock_get, client):
        """Returns material dict when slug is valid."""
        mock_get.return_value = {"material": {"slug": "pla", "name": "PLA"}}
        res = client.get("/api/materials/pla")
        assert res.status_code == 200
        data = res.get_json()
        assert data["material"]["slug"] == "pla"

    @patch("routes.core.materials.get_material")
    def test_not_found_returns_404(self, mock_get, client):
        """Returns 404 when slug does not match any material."""
        mock_get.side_effect = RuntimeError("Material manifest 'unknown' not found.")
        res = client.get("/api/materials/unknown")
        assert res.status_code == 404
        data = res.get_json()
        assert data["status"] == "error"
        assert "not found" in data["error"]

    @patch("routes.core.materials.get_material")
    def test_cache_control_on_detail(self, mock_get, client):
        """Detail endpoint includes Cache-Control header."""
        mock_get.return_value = {"material": {"slug": "pla", "name": "PLA"}}
        res = client.get("/api/materials/pla")
        cache_header = res.headers.get("Cache-Control", "")
        assert "max-age" in cache_header
