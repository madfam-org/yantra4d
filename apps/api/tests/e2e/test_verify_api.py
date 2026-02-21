"""Tests for verify API route."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path):
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestVerifyAPI:
    def test_verify_no_stls(self, client):
        """Verify with no rendered STLs returns expected structure."""
        res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert "status" in data
        assert "output" in data
        assert "passed" in data

    def test_verify_default_mode(self, client):
        """Verify without explicit mode falls back to first mode."""
        res = client.post("/api/verify", json={"project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["parts_checked"] == 1

    def test_verify_with_stl(self, client, tmp_path, monkeypatch):
        """Verify with actual STL file runs verification script."""
        from unittest.mock import patch, MagicMock
        import routes.verify as verify_mod

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(verify_mod, "STATIC_FOLDER", str(static_dir))

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "All checks passed\n===JSON===\n{\"passed\": true}"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("routes.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is True
            assert data["status"] == "success"

    def test_verify_script_failure(self, client, tmp_path, monkeypatch):
        """Verify with failing script returns failure status."""
        from unittest.mock import patch, MagicMock
        import routes.verify as verify_mod

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(verify_mod, "STATIC_FOLDER", str(static_dir))

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "Check failed"
        mock_result.stderr = ""
        mock_result.returncode = 1

        with patch("routes.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is False

    def test_verify_script_timeout(self, client, tmp_path, monkeypatch):
        """Verify with timeout returns error."""
        from unittest.mock import patch
        import subprocess
        import routes.verify as verify_mod

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(verify_mod, "STATIC_FOLDER", str(static_dir))

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        with patch("routes.verify.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="verify", timeout=120)):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is False
            assert "timed out" in data["output"].lower()

    def test_verify_invalid_json_output(self, client, tmp_path, monkeypatch):
        """Verify with malformed JSON output falls back gracefully."""
        from unittest.mock import patch, MagicMock
        import routes.verify as verify_mod

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(verify_mod, "STATIC_FOLDER", str(static_dir))

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "All ok\n===JSON===\nnot valid json"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("routes.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is True
