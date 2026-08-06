"""Tests for wall thickness analyzer."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services.geometry.thickness_analyzer import (
    RAY_ORIGIN_OFFSET,
    THIN_WALL_THRESHOLD_MM,
    _empty_result,
    compute_wall_thickness,
)


class TestEmptyResult:
    def test_returns_correct_structure(self):
        result = _empty_result()
        assert result["thicknesses"] == []
        assert result["points"] == []
        assert result["min"] == float("inf")
        assert result["max"] == float("inf")
        assert result["mean"] == float("inf")
        assert result["thin_wall_count"] == 0
        assert result["sample_count"] == 0
        assert result["valid_hits"] == 0

    def test_constants(self):
        assert THIN_WALL_THRESHOLD_MM == 0.8
        assert RAY_ORIGIN_OFFSET == 1e-4


class TestComputeWallThickness:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            compute_wall_thickness("/nonexistent/path.stl")

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_empty_scene(self, mock_trimesh):
        """Empty Scene geometry returns empty result."""
        mock_scene = MagicMock()
        mock_scene.geometry = {}
        mock_trimesh.load.return_value = mock_scene
        mock_trimesh.Scene = type(mock_scene)

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/path.glb")
            assert result["thicknesses"] == []
            assert result["thin_wall_count"] == 0
            assert result["sample_count"] == 0
            assert result["valid_hits"] == 0

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_mesh_with_no_faces(self, mock_trimesh):
        """Mesh with no faces returns empty result."""
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([])
        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry  # ensure isinstance(Scene) fails

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/path.stl")
            assert result["thicknesses"] == []

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_uniform_thickness(self, mock_trimesh):
        """All rays hit at the same distance — uniform wall."""
        sample_count = 4
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])

        points = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=np.float64)
        face_indices = np.array([0, 0, 0, 0])
        normals = np.array([[0, 0, 1.0]])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = normals

        # All rays hit 2mm inward
        hit_origins = points - normals[face_indices] * RAY_ORIGIN_OFFSET
        hit_locations = hit_origins + np.array([[0, 0, -2.0]])
        index_ray = np.arange(sample_count)
        index_tri = np.zeros(sample_count, dtype=int)

        mock_mesh.ray.intersects_location.return_value = (hit_locations, index_ray, index_tri)

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/path.stl", sample_count=sample_count)

        assert result["sample_count"] == sample_count
        assert result["valid_hits"] == sample_count
        assert result["min"] == pytest.approx(2.0, abs=0.01)
        assert result["max"] == pytest.approx(2.0, abs=0.01)
        assert result["mean"] == pytest.approx(2.0, abs=0.01)
        assert result["thin_wall_count"] == 0
        assert len(result["thicknesses"]) == sample_count
        assert len(result["points"]) == sample_count

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_varying_thickness_with_thin_walls(self, mock_trimesh):
        """Mix of thick and thin wall hits flags thin walls correctly."""
        sample_count = 3
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])

        points = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=np.float64)
        face_indices = np.array([0, 0, 0])
        normals = np.array([[0, 0, 1.0]])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = normals

        # Ray 0: hits at 0.5mm (thin), Ray 1: hits at 3.0mm, Ray 2: hits at 0.3mm (thin)
        ray_origins = points - normals[face_indices] * RAY_ORIGIN_OFFSET
        hit_locations = np.array([
            ray_origins[0] + [0, 0, -0.5],
            ray_origins[1] + [0, 0, -3.0],
            ray_origins[2] + [0, 0, -0.3],
        ])
        index_ray = np.array([0, 1, 2])
        index_tri = np.zeros(3, dtype=int)

        mock_mesh.ray.intersects_location.return_value = (hit_locations, index_ray, index_tri)

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/path.stl", sample_count=sample_count)

        assert result["valid_hits"] == 3
        assert result["thin_wall_count"] == 2  # 0.5 and 0.3 are below 0.8
        assert result["min"] == pytest.approx(0.3, abs=0.01)
        assert result["max"] == pytest.approx(3.0, abs=0.01)

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_all_rays_miss(self, mock_trimesh):
        """When no rays hit, all thicknesses are inf."""
        sample_count = 3
        mock_mesh = MagicMock()
        mock_mesh.faces = np.array([[0, 1, 2]])

        points = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=np.float64)
        face_indices = np.array([0, 0, 0])
        normals = np.array([[0, 0, 1.0]])
        mock_mesh.sample.return_value = (points, face_indices)
        mock_mesh.face_normals = normals

        # No intersections
        mock_mesh.ray.intersects_location.return_value = (
            np.empty((0, 3)),
            np.array([], dtype=int),
            np.array([], dtype=int),
        )

        mock_trimesh.Scene = type(MagicMock())
        mock_trimesh.load.return_value = mock_mesh
        del mock_mesh.geometry

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/path.stl", sample_count=sample_count)

        assert result["valid_hits"] == 0
        assert result["min"] == float("inf")
        assert result["max"] == float("inf")
        assert result["mean"] == float("inf")
        assert result["thin_wall_count"] == 0

    @patch("services.geometry.thickness_analyzer.trimesh")
    def test_multi_geometry_glb_scene(self, mock_trimesh):
        """A GLB with multiple geometries is concatenated before analysis."""
        mock_mesh_a = MagicMock()
        mock_mesh_b = MagicMock()
        mock_scene = MagicMock()
        mock_scene.geometry = {"a": mock_mesh_a, "b": mock_mesh_b}
        mock_trimesh.load.return_value = mock_scene
        mock_trimesh.Scene = type(mock_scene)

        # The concatenated mesh
        concat_mesh = MagicMock()
        concat_mesh.faces = np.array([[0, 1, 2]])
        points = np.array([[0, 0, 0]], dtype=np.float64)
        face_indices = np.array([0])
        concat_mesh.sample.return_value = (points, face_indices)
        concat_mesh.face_normals = np.array([[0, 0, 1.0]])

        # One hit at 1.5mm
        ray_origins = points - concat_mesh.face_normals[face_indices] * RAY_ORIGIN_OFFSET
        hit_locations = ray_origins + np.array([[0, 0, -1.5]])
        concat_mesh.ray.intersects_location.return_value = (
            hit_locations, np.array([0]), np.array([0]),
        )

        mock_trimesh.util.concatenate.return_value = concat_mesh

        with patch.object(Path, "exists", return_value=True):
            result = compute_wall_thickness("/fake/scene.glb", sample_count=1)

        mock_trimesh.util.concatenate.assert_called_once()
        assert result["valid_hits"] == 1
        assert result["min"] == pytest.approx(1.5, abs=0.01)
