"""
Wall Thickness Analyzer
Computes per-point wall thickness by casting rays inward from the mesh
surface and measuring the distance to the opposing wall.

Uses trimesh for mesh loading and ray casting (backed by embree when
available, falling back to the pure-Python ray engine otherwise).
"""
import logging
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

# Minimum printable wall thickness (mm).  Points thinner than this are
# flagged in the ``thin_wall_count`` metric.
THIN_WALL_THRESHOLD_MM = 0.8

# Small offset applied along the inverted normal so the ray origin sits
# just inside the surface and does not self-intersect on the source face.
RAY_ORIGIN_OFFSET = 1e-4


def compute_wall_thickness(
    mesh_path: str | Path,
    sample_count: int = 5000,
) -> dict[str, Any]:
    """Analyse wall thickness of a mesh file.

    Parameters
    ----------
    mesh_path:
        Absolute path to an STL, GLB, or other trimesh-supported mesh file.
    sample_count:
        Number of surface points to sample.  Higher values give more
        accurate statistics at the cost of compute time.

    Returns
    -------
    dict with keys:
        thicknesses  - list[float]          per-point thickness (mm)
        points       - list[[x, y, z]]      sample coordinates
        min          - float                 minimum thickness
        max          - float                 maximum thickness
        mean         - float                 arithmetic mean
        thin_wall_count - int               count of samples below THIN_WALL_THRESHOLD_MM
    """
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    scene_or_mesh = trimesh.load(str(mesh_path))

    # If the loader returns a Scene (e.g. from GLB), collapse to a single
    # mesh so we have a unified surface for ray casting.
    if isinstance(scene_or_mesh, trimesh.Scene):
        if len(scene_or_mesh.geometry) == 0:
            return _empty_result()
        mesh = trimesh.util.concatenate(list(scene_or_mesh.geometry.values()))
    else:
        mesh = scene_or_mesh

    if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        return _empty_result()

    # Sample points uniformly on the surface together with their face normals.
    points, face_indices = mesh.sample(sample_count, return_index=True)
    normals = mesh.face_normals[face_indices]

    # Ray origins are nudged slightly inward (opposite to the outward normal)
    # so the ray does not immediately intersect the originating face.
    ray_origins = points - normals * RAY_ORIGIN_OFFSET
    ray_directions = -normals  # cast inward

    # Perform batch ray-mesh intersection.
    locations, index_ray, _index_tri = mesh.ray.intersects_location(
        ray_origins=ray_origins,
        ray_directions=ray_directions,
        multiple_hits=False,
    )

    # Build a thickness value for every sample point.  Points whose inward
    # ray did not hit the opposing wall are recorded as np.inf (open /
    # single-wall geometry).
    thicknesses = np.full(sample_count, np.inf, dtype=np.float64)

    if len(locations) > 0:
        distances = np.linalg.norm(locations - ray_origins[index_ray], axis=1)
        thicknesses[index_ray] = distances

    # Compute statistics only over finite (valid hit) thicknesses.
    finite_mask = np.isfinite(thicknesses)
    finite_vals = thicknesses[finite_mask]

    if len(finite_vals) == 0:
        stats_min = float("inf")
        stats_max = float("inf")
        stats_mean = float("inf")
        thin_count = 0
    else:
        stats_min = float(np.min(finite_vals))
        stats_max = float(np.max(finite_vals))
        stats_mean = float(np.mean(finite_vals))
        thin_count = int(np.sum(finite_vals < THIN_WALL_THRESHOLD_MM))

    return {
        "thicknesses": thicknesses.tolist(),
        "points": points.tolist(),
        "min": stats_min,
        "max": stats_max,
        "mean": stats_mean,
        "thin_wall_count": thin_count,
        "sample_count": sample_count,
        "valid_hits": int(finite_mask.sum()),
    }


def _empty_result() -> dict[str, Any]:
    """Return the canonical empty-mesh result dict."""
    return {
        "thicknesses": [],
        "points": [],
        "min": float("inf"),
        "max": float("inf"),
        "mean": float("inf"),
        "thin_wall_count": 0,
        "sample_count": 0,
        "valid_hits": 0,
    }
