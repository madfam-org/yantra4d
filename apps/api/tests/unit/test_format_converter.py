"""Unit tests for STL→GLB format converter."""
from unittest.mock import patch, MagicMock

from services.engine.format_converter import stl_to_glb


class TestStlToGlb:
    """Tests for stl_to_glb conversion function."""

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_glb_success(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = stl_to_glb("/tmp/input.stl", "/tmp/output.glb")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/input.stl", file_type="stl")
        mock_mesh.export.assert_called_once_with("/tmp/output.glb", file_type="glb")

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_glb_failure_returns_false(self, mock_trimesh):
        mock_trimesh.load.side_effect = Exception("File not found")

        result = stl_to_glb("/tmp/missing.stl", "/tmp/output.glb")

        assert result is False
