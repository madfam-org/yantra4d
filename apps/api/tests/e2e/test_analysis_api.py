"""Tests for geometry analysis API routes."""
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
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])
    monkeypatch.setattr(Config, "STATIC_DIR", tmp_path / "static")

    (tmp_path / "static").mkdir()

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test", "slug": "my-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    # Patch the module-level STATIC_FOLDER string that was computed at import
    # time from Config.STATIC_DIR. Without this, _find_latest_render searches
    # the wrong directory when the analysis module was already imported.
    import routes.engine.analysis as analysis_mod
    monkeypatch.setattr(analysis_mod, "STATIC_FOLDER", str(tmp_path / "static"))

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestThicknessAnalysis:
    def test_no_render_returns_409(self, client):
        """When no rendered mesh exists, the endpoint returns 409."""
        res = client.post("/api/projects/my-project/analyze/thickness")
        assert res.status_code == 409

    @patch("routes.engine.analysis.compute_wall_thickness")
    def test_analysis_success(self, mock_compute, client, tmp_path):
        """Successful thickness analysis returns 200 with analysis data."""
        # Create a fake rendered mesh file matching the naming convention:
        # {slug}_{STL_PREFIX}{hash}_{part}.{ext}
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.return_value = {
            "thicknesses": [1.0, 0.5, 1.5],
            "points": [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
            "min": 0.5,
            "max": 1.5,
            "mean": 1.0,
            "thin_wall_count": 1,
            "sample_count": 3,
            "valid_hits": 3,
        }

        res = client.post("/api/projects/my-project/analyze/thickness")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["project"] == "my-project"
        assert "analysis" in data
        assert data["analysis"]["thin_wall_count"] == 1

    @patch("routes.engine.analysis.compute_wall_thickness")
    def test_custom_sample_count(self, mock_compute, client, tmp_path):
        """A custom sample_count is forwarded to the analyzer."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.return_value = {
            "thicknesses": [], "points": [], "min": float("inf"),
            "max": float("inf"), "mean": float("inf"),
            "thin_wall_count": 0, "sample_count": 100, "valid_hits": 0,
        }

        res = client.post(
            "/api/projects/my-project/analyze/thickness",
            json={"sample_count": 100},
        )
        assert res.status_code == 200
        mock_compute.assert_called_once()
        # Verify the sample_count keyword argument
        call_kwargs = mock_compute.call_args
        assert call_kwargs[1]["sample_count"] == 100

    def test_nonexistent_project(self, client):
        """A project with no rendered mesh returns 409 (no render found)."""
        res = client.post("/api/projects/nonexistent/analyze/thickness")
        # The route does not check project directory existence --
        # it only searches STATIC_DIR for matching render files.
        # A slug that passes validation but has no renders yields 409.
        assert res.status_code == 409

    @patch("routes.engine.analysis.compute_wall_thickness")
    def test_analysis_error(self, mock_compute, client, tmp_path):
        """A RuntimeError from compute_wall_thickness yields 500."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.side_effect = RuntimeError("mesh parsing failed")

        res = client.post("/api/projects/my-project/analyze/thickness")
        assert res.status_code == 500


class TestOverhangAnalysis:
    def test_no_render_returns_409(self, client):
        """When no rendered mesh exists, the endpoint returns 409."""
        res = client.post("/api/projects/my-project/analyze/overhang")
        assert res.status_code == 409

    @patch("routes.engine.analysis.compute_overhang_angles")
    def test_analysis_success(self, mock_compute, client, tmp_path):
        """Successful overhang analysis returns 200 with analysis data."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.return_value = {
            "angles": [30.0, 50.0, 70.0],
            "points": [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
            "threshold_deg": 45.0,
            "overhang_count": 2,
            "sample_count": 3,
            "min_angle": 30.0,
            "max_angle": 70.0,
            "mean_angle": 50.0,
        }

        res = client.post("/api/projects/my-project/analyze/overhang")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["project"] == "my-project"
        assert "analysis" in data
        assert data["analysis"]["overhang_count"] == 2

    @patch("routes.engine.analysis.compute_overhang_angles")
    def test_custom_threshold_deg(self, mock_compute, client, tmp_path):
        """A custom threshold_deg is forwarded to the analyzer."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.return_value = {
            "angles": [], "points": [], "threshold_deg": 60.0,
            "overhang_count": 0, "sample_count": 0,
            "min_angle": 0, "max_angle": 0, "mean_angle": 0,
        }

        res = client.post(
            "/api/projects/my-project/analyze/overhang",
            json={"threshold_deg": 60},
        )
        assert res.status_code == 200
        call_kwargs = mock_compute.call_args
        assert call_kwargs[1]["threshold_deg"] == 60

    @patch("routes.engine.analysis.compute_overhang_angles")
    def test_custom_sample_count(self, mock_compute, client, tmp_path):
        """A custom sample_count is forwarded to the analyzer."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.return_value = {
            "angles": [], "points": [], "threshold_deg": 45.0,
            "overhang_count": 0, "sample_count": 200,
            "min_angle": 0, "max_angle": 0, "mean_angle": 0,
        }

        res = client.post(
            "/api/projects/my-project/analyze/overhang",
            json={"sample_count": 200},
        )
        assert res.status_code == 200
        call_kwargs = mock_compute.call_args
        assert call_kwargs[1]["sample_count"] == 200

    def test_nonexistent_project(self, client):
        """A project with no rendered mesh returns 409."""
        res = client.post("/api/projects/nonexistent/analyze/overhang")
        assert res.status_code == 409

    @patch("routes.engine.analysis.compute_overhang_angles")
    def test_analysis_error(self, mock_compute, client, tmp_path):
        """A RuntimeError from compute_overhang_angles yields 500."""
        static_dir = tmp_path / "static"
        mesh_file = static_dir / "my-project_preview_abc123_main.stl"
        mesh_file.write_bytes(b"fake stl")

        mock_compute.side_effect = RuntimeError("mesh parsing failed")

        res = client.post("/api/projects/my-project/analyze/overhang")
        assert res.status_code == 500
