"""
Finite Element Analysis (FEA) Stress Analyzer Foundation.
Currently implements a geometric heuristic to mock Von Mises stress 
fields for frontend visualization pipelines before linking to deep solvers.
"""
import logging
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

def compute_stress_field(
    mesh_path: str | Path,
    force_vector: tuple[float, float, float] = (0.0, -10.0, 0.0),
) -> dict[str, Any]:
    """Analyse stress tensors over a mesh file (Foundation Mock).

    Parameters
    ----------
    mesh_path:
        Absolute path to an STL, GLB, or other trimesh-supported mesh file.
    force_vector:
        The simulated directional applied force.

    Returns
    -------
    dict with keys:
        stresses - list[float]          mock Von Mises stress (MPa) matching vertex indices
        points   - list[[x, y, z]]      vertex coordinates
        min      - float                minimum stress
        max      - float                maximum stress
        mean     - float                arithmetic mean
        count    - int                  vertex count
    """
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    scene_or_mesh = trimesh.load(str(mesh_path))

    if isinstance(scene_or_mesh, trimesh.Scene):
        if len(scene_or_mesh.geometry) == 0:
            return _empty_result()
        mesh = trimesh.util.concatenate(list(scene_or_mesh.geometry.values()))
    else:
        mesh = scene_or_mesh

    if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0:
        return _empty_result()

    vertices = mesh.vertices
    
    # Foundation heuristic: Mock stress fields dynamically based on geometry.
    centroid = mesh.centroid
    dist = np.linalg.norm(vertices - centroid, axis=1)
    
    max_d = np.max(dist) if np.max(dist) > 0 else 1.0
    normalized_dist = dist / max_d
    
    # Sine modulation based on the force vector axis just to make the heatmap look realistic
    wave = np.sin(vertices[:, 0] * 0.8) * 0.3 + np.cos(vertices[:, 1] * 0.5) * 0.2
    
    # Shift towards edges + wave perturbation
    stresses = np.abs(normalized_dist + wave) * 120.0
    
    stats_min = float(np.min(stresses))
    stats_max = float(np.max(stresses))
    stats_mean = float(np.mean(stresses))

    return {
        "stresses": stresses.tolist(),
        "points": vertices.tolist(),
        "min": stats_min,
        "max": stats_max,
        "mean": stats_mean,
        "count": len(vertices),
    }

def _empty_result() -> dict[str, Any]:
    return {
        "stresses": [],
        "points": [],
        "min": 0.0,
        "max": 0.0,
        "mean": 0.0,
        "count": 0,
    }
