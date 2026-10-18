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
        assert res.status_code == 409
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"] == "not_rendered"
        assert "not been rendered yet" in data["message"]

    def test_verify_default_mode(self, client):
        """Verify without explicit mode falls back to first mode."""
        res = client.post("/api/verify", json={"project": "test-project"})
        assert res.status_code == 409
        data = res.get_json()
        assert data["error"] == "not_rendered"

    def test_verify_with_stl(self, client, tmp_path, monkeypatch):
        """Verify with actual STL file runs verification script."""
        from unittest.mock import MagicMock, patch

        from config import Config

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        # The route resolves the part's STL through the artifact store, which
        # reads Config.STATIC_DIR at call time — no import-time string to patch.
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "All checks passed\n===JSON===\n{\"passed\": true}"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("routes.engine.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is True
            assert data["status"] == "success"

    def test_verify_script_failure(self, client, tmp_path, monkeypatch):
        """Verify with failing script returns failure status."""
        from unittest.mock import MagicMock, patch

        from config import Config

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        # The route resolves the part's STL through the artifact store, which
        # reads Config.STATIC_DIR at call time — no import-time string to patch.
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "Check failed"
        mock_result.stderr = ""
        mock_result.returncode = 1

        with patch("routes.engine.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is False

    def test_verify_script_timeout(self, client, tmp_path, monkeypatch):
        """Verify with timeout returns error."""
        import subprocess
        from unittest.mock import patch

        from config import Config

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        # The route resolves the part's STL through the artifact store, which
        # reads Config.STATIC_DIR at call time — no import-time string to patch.
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        with patch("routes.engine.verify.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="verify", timeout=120)):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is False
            assert "timed out" in data["output"].lower()

    def test_verify_invalid_json_output(self, client, tmp_path, monkeypatch):
        """Verify with malformed JSON output falls back gracefully."""
        from unittest.mock import MagicMock, patch

        from config import Config

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        # The route resolves the part's STL through the artifact store, which
        # reads Config.STATIC_DIR at call time — no import-time string to patch.
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

        stl_path = static_dir / "test-project_preview_main.stl"
        stl_path.write_bytes(b"solid\nendsolid\n")

        mock_result = MagicMock()
        mock_result.stdout = "All ok\n===JSON===\nnot valid json"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("routes.engine.verify.subprocess.run", return_value=mock_result):
            res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["passed"] is True


# Geometry checks only: an icosphere has downward faces, so the default
# printability stage (overhang) would fail it for reasons unrelated to the path.
GEOMETRY_ONLY = {
    "stages": {
        "geometry": {
            "checks": {
                "watertight": {"enabled": True},
                "body_count": {"enabled": True, "expected": 1},
                "facet_count": {"enabled": True, "min_facets": 400},
            }
        }
    }
}


class TestVerifyRunsTheRealScript:
    """No subprocess mock: the route launches the configured verifier on a real STL.

    The mocked tests above pass whatever VERIFY_SCRIPT names, which is how a
    stale path shipped. Only trimesh + numpy are needed (no OpenSCAD, no
    CadQuery): the STL is generated here, not rendered.
    """

    def _stage(self, tmp_path, monkeypatch, mesh):
        from config import Config

        project_json = tmp_path / "test-project" / "project.json"
        manifest = json.loads(project_json.read_text())
        manifest["verification"] = GEOMETRY_ONLY
        project_json.write_text(json.dumps(manifest))

        static_dir = tmp_path / "static"
        static_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
        mesh.export(static_dir / "test-project_preview_main.stl")

    def test_known_good_stl_passes(self, client, tmp_path, monkeypatch):
        trimesh = pytest.importorskip("trimesh")
        self._stage(tmp_path, monkeypatch, trimesh.creation.icosphere(subdivisions=3, radius=10.0))

        res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})

        assert res.status_code == 200
        data = res.get_json()
        assert data["passed"] is True, data["output"]
        assert data["status"] == "success"
        assert data["parts_checked"] == 1
        assert "[PASS] watertight: watertight" in data["output"]
        assert "[PASS] body_count: 1 body" in data["output"]
        assert "[PASS] facet_count: 1280 facets" in data["output"]

    def test_two_bodies_fail_the_body_count(self, client, tmp_path, monkeypatch):
        trimesh = pytest.importorskip("trimesh")
        a = trimesh.creation.icosphere(subdivisions=3, radius=5.0)
        b = trimesh.creation.icosphere(subdivisions=3, radius=5.0)
        b.apply_translation([30.0, 0.0, 0.0])
        self._stage(tmp_path, monkeypatch, trimesh.util.concatenate([a, b]))

        res = client.post("/api/verify", json={"mode": "default", "project": "test-project"})

        assert res.status_code == 200
        data = res.get_json()
        assert data["passed"] is False
        assert data["status"] == "failure"
        assert "[FAIL] body_count: 2 bodies (expected 1)" in data["output"]
