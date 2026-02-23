import pytest
import numpy as np
from services.core.implicit_engine import evaluate_tpms_field, run_render, stream_render
from unittest.mock import patch, MagicMock

def test_evaluate_tpms_field():
    X, Y, Z = np.array([1]), np.array([1]), np.array([1])
    # Testing all topologies to ensure coverage
    res1 = evaluate_tpms_field("gyroid", X, Y, Z, 1.0)
    assert len(res1) == 1
    res2 = evaluate_tpms_field("diamond", X, Y, Z, 1.0)
    assert len(res2) == 1
    res3 = evaluate_tpms_field("schwarz_p", X, Y, Z, 1.0)
    assert len(res3) == 1
    res4 = evaluate_tpms_field("unknown", X, Y, Z, 1.0)
    assert len(res4) == 1

@patch("services.core.implicit_engine.marching_cubes")
@patch("services.core.implicit_engine.trimesh.Trimesh")
def test_run_render_stl(mock_trimesh, mock_marching_cubes):
    mock_marching_cubes.return_value = (np.zeros((10,3)), np.zeros((10,3)), np.zeros((10,3)), np.zeros(10))
    mock_mesh = MagicMock()
    mock_trimesh.return_value = mock_mesh
    
    config = {"topology": "gyroid", "resolution": 8}
    # Simulate high energy for branches checking glass transition logic
    params = {"tda_euler_characteristic": -50, "simulated_energy": 2000, "thermo_glass_transition_temp": 1000}
    
    success, err = run_render("out.stl", config, params)
    assert success is True
    mock_mesh.export.assert_called_with("out.stl")

@patch("services.core.implicit_engine.marching_cubes")
@patch("services.core.implicit_engine.trimesh.Trimesh")
def test_run_render_glb(mock_trimesh, mock_marching_cubes):
    mock_marching_cubes.return_value = (np.zeros((10,3)), np.zeros((10,3)), np.zeros((10,3)), np.zeros(10))
    mock_mesh = MagicMock()
    mock_trimesh.return_value = mock_mesh
    
    # Using params topology_type 1 (diamond)
    success, err = run_render("out.glb", {}, {"topology_type": 1})
    assert success is True
    mock_mesh.export.assert_called_with("out.glb", file_type='glb')

@patch("services.core.implicit_engine.marching_cubes")
def test_run_render_fails(mock_marching_cubes):
    mock_marching_cubes.side_effect = Exception("error!")
    success, err = run_render("out.stl", {}, {})
    assert success is False
    assert "error!" in err

@patch("services.core.implicit_engine.run_render")
def test_stream_render_success(mock_run_render):
    mock_run_render.return_value = (True, "")
    output = list(stream_render("out.stl", {}, {}, "part1", 0, 10, 0, 1))
    assert len(output) > 0
    assert "part_done" in output[-1]

@patch("services.core.implicit_engine.run_render")
def test_stream_render_fails(mock_run_render):
    mock_run_render.return_value = (False, "error occurred")
    output = list(stream_render("out.stl", {}, {}, "part1", 0, 10, 0, 1))
    assert len(output) > 0
    assert "error" in output[-1]
