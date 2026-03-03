"""
Overhang Angle Analyzer
Computes per-face overhang angles relative to the build direction (Z-up).
Surfaces exceeding the threshold angle require support material during printing.

Uses trimesh for mesh loading and face normal computation.
"""
import logging
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

# Default overhang threshold in degrees — faces steeper than this from
# vertical (i.e. more than this many degrees from the Z-up build direction)
# typically require support material.
DEFAULT_OVERHANG_THRESHOLD_DEG = 45

# Build direction vector (Z-up)
BUILD_DIRECTION = np.array([0.0, 0.0, 1.0])


def compute_overhang_angles(
    mesh_path: str | Path,
    sample_count: int = 5000,
    threshold_deg: float = DEFAULT_OVERHANG_THRESHOLD_DEG,
) -> dict[str, Any]:
    """Analyse overhang angles of a mesh file.

    For each sampled surface point, the angle between the face normal and
    the build direction (Z-up) is computed.  Angles > threshold indicate
    overhang surfaces that need support.

    Parameters
    ----------
    mesh_path:
        Absolute path to an STL, GLB, or other trimesh-supported mesh file.
    sample_count:
        Number of surface points to sample.
    threshold_deg:
        Overhang angle threshold in degrees (default 45).

    Returns
    -------
    dict with keys:
        angles       - list[float]          per-point angle from build dir (degrees)
        points       - list[[x, y, z]]      sample coordinates
        threshold_deg - float               threshold used
        overhang_count - int                count of samples exceeding threshold
        min_angle    - float                minimum angle
        max_angle    - float                maximum angle
        mean_angle   - float                arithmetic mean angle
    """
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    scene_or_mesh = trimesh.load(str(mesh_path))

    if isinstance(scene_or_mesh, trimesh.Scene):
        if len(scene_or_mesh.geometry) == 0:
            return _empty_result(threshold_deg)
        mesh = trimesh.util.concatenate(list(scene_or_mesh.geometry.values()))
    else:
        mesh = scene_or_mesh

    if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        return _empty_result(threshold_deg)

    # Sample points uniformly on the surface together with their face indices.
    points, face_indices = mesh.sample(sample_count, return_index=True)
    normals = mesh.face_normals[face_indices]

    # Compute angle between each face normal and the build direction.
    # angle = arccos(dot(normal, build_dir))
    # This gives the angle from vertical — 0° = pointing up, 90° = horizontal,
    # 180° = pointing down (full overhang).
    dots = np.clip(np.dot(normals, BUILD_DIRECTION), -1.0, 1.0)
    angles_rad = np.arccos(dots)
    angles_deg = np.degrees(angles_rad)

    # Overhang = angle > (90 + threshold) from build direction
    # Actually, the conventional definition: a face is an overhang if the angle
    # between the face normal and the DOWNWARD direction is < threshold.
    # Equivalently: angle from Z-up > (180 - threshold).
    # But the more practical metric for AM: the face angle from vertical.
    # Faces where the normal points downward (angle > 90°) are overhangs.
    # The severity increases as angle approaches 180°.
    # Standard: overhang_angle = angle_from_up - 90 (for downward-facing surfaces)
    # Simpler: just report the angle from Z-up directly. Overhang = angle > (90 + threshold)
    # is one convention, but most slicers define overhang as the angle of the surface
    # from horizontal. Let's use the slicer convention:
    # surface_angle_from_horizontal = 90 - angle_from_up  (for angle_from_up < 90)
    # For downward faces (angle_from_up > 90): these are always overhangs.
    #
    # Simplest: report overhang_angle = max(0, angle_from_up - 90).
    # This gives 0° for upward-facing, 45° for 45° from horizontal, 90° for straight down.
    overhang_angles = np.maximum(0, angles_deg - 90)

    threshold = float(threshold_deg)
    overhang_mask = overhang_angles > threshold
    overhang_count = int(np.sum(overhang_mask))

    return {
        "angles": overhang_angles.tolist(),
        "points": points.tolist(),
        "threshold_deg": threshold,
        "overhang_count": overhang_count,
        "min_angle": float(np.min(overhang_angles)),
        "max_angle": float(np.max(overhang_angles)),
        "mean_angle": float(np.mean(overhang_angles)),
        "sample_count": sample_count,
    }


def _empty_result(threshold_deg: float) -> dict[str, Any]:
    """Return the canonical empty-mesh result dict."""
    return {
        "angles": [],
        "points": [],
        "threshold_deg": float(threshold_deg),
        "overhang_count": 0,
        "min_angle": 0.0,
        "max_angle": 0.0,
        "mean_angle": 0.0,
        "sample_count": 0,
    }
