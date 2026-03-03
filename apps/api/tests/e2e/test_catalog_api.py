"""Tests for NopSCADlib catalog API routes."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestListCatalogCategories:
    @patch("routes.projects.catalog.list_categories")
    def test_returns_categories(self, mock_list, client):
        mock_list.return_value = ["ball_bearings", "fans", "pulleys"]
        res = client.get("/api/catalog/nopscadlib")
        assert res.status_code == 200
        data = res.get_json()
        assert data["categories"] == ["ball_bearings", "fans", "pulleys"]

    @patch("routes.projects.catalog.list_categories")
    def test_empty_categories(self, mock_list, client):
        mock_list.return_value = []
        res = client.get("/api/catalog/nopscadlib")
        assert res.status_code == 200
        assert res.get_json()["categories"] == []


class TestGetCatalogCategory:
    @patch("routes.projects.catalog.get_catalog")
    def test_valid_category(self, mock_catalog, client):
        mock_catalog.return_value = [
            {"id": "608", "label": "608 (8x22x7mm)", "category": "ball_bearings",
             "specs": {"bore_diameter": 8}, "parameters": {"bore_diameter": 8},
             "supplier_search": "ball bearing 608"},
        ]
        res = client.get("/api/catalog/nopscadlib/ball_bearings")
        assert res.status_code == 200
        data = res.get_json()
        assert data["category"] == "ball_bearings"
        assert data["count"] == 1
        assert data["components"][0]["id"] == "608"

    @patch("routes.projects.catalog.get_catalog")
    def test_nonexistent_category(self, mock_catalog, client):
        mock_catalog.return_value = None
        res = client.get("/api/catalog/nopscadlib/nonexistent")
        assert res.status_code == 404
