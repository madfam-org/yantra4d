"""Tests for overhang angle analyzer."""
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.geometry.overhang_analyzer import (
    compute_overhang_angles,
    _empty_result,
    DEFAULT_OVERHANG_THRESHOLD_DEG,
)


class TestEmptyResult:
    def test_returns_correct_structure(self):
        result = _empty_result(45)
        assert result["angles"] == []
        assert result["points"] == []
        assert result["threshold_deg"] == 45.0
        assert result["overhang_count"] == 0
        assert result["sample_count"] == 0
        assert result["min_angle"] == 0.0
        assert result["max_angle"] == 0.0
        assert result["mean_angle"] == 0.0

    def test_uses_provided_threshold(self):
        result = _empty_result(30)
        assert result["threshold_deg"] == 30.0

    def test_default_threshold_constant(self):
        assert DEFAULT_OVERHANG_THRESHOLD_DEG == 45


class TestComputeOverhangAngles:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            compute_overhang_angles("/nonexistent/path.stl")

    @patch("services.geometry.overhang_analyzer.trimesh")
    def test_empty_scene(self, mock_trimesh):
        """Empty Scene geometry returns empty result."""
        mock_scene = MagicMock()
        mock_scene.geometry = {}
        mock_trimesh.load.return_value = mock_scene
        mock_trimesh.Scene = type(mock_scene)

        with patch.object(Path, "exists", return_value=True):
            result = compute_overhang_angles("/fake/path.stl")
            assert result["angles"] == []
            assert result["overhang_count"] == 0
            assert result["sample_count"] == 0

    @patch("services.geometry.overhang_analyzer.trimesh")
    def test_mesh_with_no_faces(self, mock_trimesh):
        """Mesh with no faces returns empty result."""
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([])
        # Not a Scene, so it goes straight to the face check
        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry  # ensure isinstance(Scene) fails

        with patch.object(Path, "exists", return_value=True):
            result = compute_overhang_angles("/fake/path.stl")
            assert result["angles"] == []

    @patch("services.geometry.overhang_analyzer.trimesh")
    def test_upward_facing_normals(self, mock_trimesh):
        """Faces pointing straight up have 0 overhang angle."""
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])
        # Normal pointing straight up: angle from Z-up = 0°
        # overhang_angle = max(0, 0 - 90) = 0
        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        face_indices = np.array([0, 0])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = np.array([[0.0, 0.0, 1.0]])

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_overhang_angles(
                "/fake/path.stl", sample_count=2, threshold_deg=45
            )

        assert len(result["angles"]) == 2
        assert len(result["points"]) == 2
        assert result["threshold_deg"] == 45
        assert result["sample_count"] == 2
        # Normal pointing up → angle_from_up = 0° → overhang = max(0, 0-90) = 0
        assert all(a == 0.0 for a in result["angles"])
        assert result["overhang_count"] == 0
        assert result["min_angle"] == 0.0
        assert result["max_angle"] == 0.0

    @patch("services.geometry.overhang_analyzer.trimesh")
    def test_downward_facing_normals(self, mock_trimesh):
        """Faces pointing straight down have 90 overhang angle."""
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])
        # Normal pointing straight down: angle from Z-up = 180°
        # overhang_angle = max(0, 180 - 90) = 90
        points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        face_indices = np.array([0, 0, 0])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = np.array([[0.0, 0.0, -1.0]])

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_overhang_angles(
                "/fake/path.stl", sample_count=3, threshold_deg=45
            )

        assert len(result["angles"]) == 3
        # Normal pointing down → angle_from_up = 180° → overhang = 90°
        assert all(abs(a - 90.0) < 0.01 for a in result["angles"])
        assert result["overhang_count"] == 3
        assert result["max_angle"] == pytest.approx(90.0, abs=0.01)

    @patch("services.geometry.overhang_analyzer.trimesh")
    def test_horizontal_normals(self, mock_trimesh):
        """Horizontal faces (normal perpendicular to Z) have 0 overhang angle."""
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])
        # Normal pointing sideways: angle from Z-up = 90°
        # overhang_angle = max(0, 90 - 90) = 0
        points = np.array([[0.0, 0.0, 0.0]])
        face_indices = np.array([0])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = np.array([[1.0, 0.0, 0.0]])

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_overhang_angles(
                "/fake/path.stl", sample_count=1, threshold_deg=45
            )

        # Horizontal normal → angle_from_up = 90° → overhang = 0°
        assert result["angles"][0] == pytest.approx(0.0, abs=0.01)
        assert result["overhang_count"] == 0
