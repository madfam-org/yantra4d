"""Tests for the BOM cart endpoint (ForgeSight pricing integration)."""
import json
import pytest
from unittest.mock import patch

from services.integrations.forgesight import Quote, QuoteItem


MOCK_MANIFEST = {
    "project": {"name": "Test Project", "slug": "test-project"},
    "modes": [{"id": "main", "scad_file": "main.scad", "parts": ["body"]}],
    "parameters": [
        {"id": "width", "type": "slider", "default": 10, "min": 1, "max": 100},
        {"id": "count", "type": "slider", "default": 4, "min": 1, "max": 20},
    ],
    "bom": {
        "hardware": [
            {
                "id": "bolt",
                "label": {"en": "M3 Bolt", "es": "Tornillo M3"},
                "quantity_formula": "count * 2",
                "unit": "pcs",
                "supplier_url": "https://example.com/bolts",
            },
            {
                "id": "nut",
                "label": "M3 Nut",
                "quantity_formula": "count * 2",
                "unit": "pcs",
            },
        ]
    },
}


@pytest.fixture
def app(tmp_path):
    """Create test Flask app with a mock project directory."""
    import os
    # Create test project directory
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    (project_dir / "project.json").write_text(json.dumps(MOCK_MANIFEST))

    os.environ["PROJECTS_DIR"] = str(tmp_path)
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    from app import create_app
    app = create_app()
    app.config["TESTING"] = True

    yield app

    os.environ.pop("PROJECTS_DIR", None)


@pytest.fixture
def client(app):
    return app.test_client()


class TestCartEndpoint:
    """Test POST /api/projects/<slug>/bom/cart."""

    @patch("routes.projects.cart.forgesight_client")
    def test_returns_enriched_bom_with_pricing(self, mock_fs, client):
        mock_fs.get_quote.return_value = Quote(
            items=[
                QuoteItem(part_name="M3 Bolt", quantity=8, unit_price=0.12, lead_time_days=3, available=True),
                QuoteItem(part_name="M3 Nut", quantity=8, unit_price=0.08, lead_time_days=3, available=True),
            ],
            total_price=1.60,
            currency="USD",
            valid_until="2026-04-16",
        )

        resp = client.post(
            "/api/projects/test-project/bom/cart",
            json={},
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_price"] == 1.60
        assert data["currency"] == "USD"
        assert data["error"] is None
        assert len(data["items"]) == 2
        assert data["items"][0]["unit_price"] == 0.12
        assert data["items"][0]["available"] is True

    @patch("routes.projects.cart.forgesight_client")
    def test_returns_null_pricing_when_forgesight_unavailable(self, mock_fs, client):
        mock_fs.get_quote.return_value = Quote(
            items=[],
            error="ForgeSight integration not configured",
        )

        resp = client.post(
            "/api/projects/test-project/bom/cart",
            json={},
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["error"] is not None
        assert data["total_price"] is None
        for item in data["items"]:
            assert item["unit_price"] is None
            assert item["available"] is False

    @patch("routes.projects.cart.forgesight_client")
    def test_applies_parameter_overrides(self, mock_fs, client):
        mock_fs.get_quote.return_value = Quote(items=[], error=None)

        resp = client.post(
            "/api/projects/test-project/bom/cart",
            json={"parameter_overrides": {"count": 10}},
            content_type="application/json",
        )

        assert resp.status_code == 200
        # Verify the quote was called with quantity=20 (count=10 * 2)
        call_args = mock_fs.get_quote.call_args[0][0]
        assert call_args[0]["quantity"] == 20

    def test_returns_404_for_nonexistent_project(self, client):
        resp = client.post(
            "/api/projects/nonexistent/bom/cart",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 404

    @patch("routes.projects.cart.forgesight_client")
    def test_returns_404_for_project_without_bom(self, mock_fs, client, tmp_path):
        # Create a project without BOM
        no_bom_dir = tmp_path / "no-bom"
        no_bom_dir.mkdir()
        (no_bom_dir / "project.json").write_text(json.dumps({
            "project": {"name": "No BOM", "slug": "no-bom"},
            "parameters": [],
        }))

        resp = client.post(
            "/api/projects/no-bom/bom/cart",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 404
