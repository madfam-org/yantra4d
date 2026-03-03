"""Tests for printer integration API routes."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()

    printers_dir = tmp_path / "printers"
    printers_dir.mkdir()

    # Valid printer config
    (printers_dir / "test-printer.json").write_text(json.dumps({
        "hardware": {"name": "Test Printer", "brand": "Generic", "model": "X1",
                      "bed_x_mm": 220, "bed_y_mm": 220, "bed_z_mm": 250},
        "connection": {"type": "octoprint", "base_url": "http://localhost:5555",
                       "api_key": "test-key"},
    }))

    # Example printer (should be skipped)
    (printers_dir / "example-default.json").write_text(json.dumps({
        "hardware": {"name": "Example"},
        "connection": {"type": "octoprint", "base_url": "http://example"},
    }))

    import routes.integrations.printer as printer_mod
    monkeypatch.setattr(printer_mod, "PRINTERS_DIR", printers_dir)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestListPrinters:
    def test_lists_valid_printers(self, client):
        res = client.get("/api/printers")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["printers"]) == 1
        assert data["printers"][0]["id"] == "test-printer"
        assert data["printers"][0]["name"] == "Test Printer"

    def test_skips_example_printers(self, client):
        res = client.get("/api/printers")
        data = res.get_json()
        ids = [p["id"] for p in data["printers"]]
        assert "example-default" not in ids

    def test_empty_printers_dir(self, client, tmp_path, monkeypatch):
        import routes.integrations.printer as printer_mod
        empty = tmp_path / "empty-printers"
        empty.mkdir()
        monkeypatch.setattr(printer_mod, "PRINTERS_DIR", empty)
        res = client.get("/api/printers")
        assert res.status_code == 200
        assert res.get_json()["printers"] == []


class TestGetPrinterStatus:
    def test_unknown_printer_returns_404(self, client):
        res = client.get("/api/printers/nonexistent-abc/status")
        assert res.status_code == 404

    def test_traversal_attempt_returns_400(self, client):
        res = client.get("/api/printers/../etc/status")
        assert res.status_code in (400, 404)

    def test_invalid_printer_id_returns_400(self, client):
        res = client.get("/api/printers/x/status")  # too short
        assert res.status_code == 400

    @patch("routes.integrations.printer._get_client")
    def test_valid_printer_returns_status(self, mock_client, client):
        mock_mod = MagicMock()
        mock_mod.get_status.return_value = {"state": "Operational", "temperatures": {}}
        mock_client.return_value = mock_mod

        res = client.get("/api/printers/test-printer/status")
        assert res.status_code == 200
        data = res.get_json()
        assert data["printer_id"] == "test-printer"
        assert data["state"] == "Operational"


class TestDispatchPrint:
    def test_missing_file_path_returns_400(self, client):
        res = client.post("/api/printers/test-printer/print",
                          json={})
        assert res.status_code == 400
        assert "file_path" in res.get_json()["error"]

    def test_traversal_file_path_returns_400(self, client):
        res = client.post("/api/printers/test-printer/print",
                          json={"file_path": "/etc/passwd"})
        assert res.status_code == 400
        assert "Invalid" in res.get_json()["error"]

    def test_invalid_printer_id_returns_400(self, client):
        res = client.post("/api/printers/ab/print",
                          json={"file_path": "test.stl"})
        assert res.status_code == 400

    def test_unknown_printer_returns_404(self, client):
        res = client.post("/api/printers/nonexistent-abc/print",
                          json={"file_path": "test.stl"})
        assert res.status_code == 404

    @patch("routes.integrations.printer._get_client")
    def test_successful_dispatch(self, mock_client, client, tmp_path):
        # Create a real file in STATIC_DIR
        static_dir = tmp_path / "static"
        (static_dir / "test.stl").write_bytes(b"solid test")

        mock_mod = MagicMock()
        mock_mod.upload_file.return_value = "remote_test.stl"
        mock_mod.start_print.return_value = None
        mock_client.return_value = mock_mod

        res = client.post("/api/printers/test-printer/print",
                          json={"file_path": "test.stl"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "printing"
        assert data["printer_id"] == "test-printer"


class TestCancelPrint:
    def test_unknown_printer_returns_404(self, client):
        res = client.delete("/api/printers/nonexistent-abc/print")
        assert res.status_code == 404

    def test_invalid_printer_id_returns_400(self, client):
        res = client.delete("/api/printers/ab/print")
        assert res.status_code == 400

    @patch("routes.integrations.printer._get_client")
    def test_successful_cancel(self, mock_client, client):
        mock_mod = MagicMock()
        mock_mod.cancel_print.return_value = None
        mock_client.return_value = mock_mod

        res = client.delete("/api/printers/test-printer/print")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "cancelled"
