"""
Finite Element Analysis (FEA) stress analyzer foundation.

This module keeps a deterministic, geometry-derived stress proxy while we work
toward a production-grade structural solver integration.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

logger = logging.getLogger(__name__)


def _safe_normalize(values: np.ndarray) -> np.ndarray:
    """Normalize numeric vector to [0, 1] with zero-safe guardrails."""
    if values.size == 0:
        return values.astype(float)

    min_v = float(np.min(values))
    max_v = float(np.max(values))
    span = max_v - min_v
    if not np.isfinite(span) or span <= 1e-12:
        return np.zeros_like(values, dtype=float)
    return (values - min_v) / span


def _safe_json_summary(mesh_path: Path, vertex_count: int) -> dict[str, Any]:
    """Return stable metadata that is safe to serialize."""
    return {
        "source": str(mesh_path),
        "vertex_count": int(vertex_count),
        "schema_version": "stress_proxy_v1",
        "approximation": True,
    }


def _collect_vertex_face_area_weights(mesh: trimesh.Trimesh, vertices: np.ndarray) -> np.ndarray:
    """Estimate local neighborhood area using face-area fan accumulation."""
    n = len(vertices)
    if n == 0:
        return np.zeros(0, dtype=float)

    faces = np.asarray(mesh.faces) if hasattr(mesh, "faces") else np.empty((0, 3), dtype=int)
    if faces.size == 0 or faces.ndim != 2 or faces.shape[1] < 3:
        return np.zeros(n, dtype=float)

    try:
        face_areas = np.asarray(mesh.area_faces, dtype=float).reshape(-1)
    except Exception:
        return np.zeros(n, dtype=float)

    if face_areas.size != faces.shape[0] or face_areas.size == 0:
        return np.zeros(n, dtype=float)

    flat_faces = faces.reshape(-1)
    flat_weights = np.repeat(face_areas, repeats=faces.shape[1], axis=0)

    area_accum = np.bincount(flat_faces, weights=flat_weights, minlength=n)
    vertex_hits = np.bincount(flat_faces, minlength=n).astype(float)
    return np.divide(area_accum, np.maximum(vertex_hits, 1.0))


def _collect_vertex_edge_density(vertices: np.ndarray, mesh: trimesh.Trimesh) -> np.ndarray:
    """Estimate edge-density proxy from mesh topology."""
    n = len(vertices)
    if n == 0:
        return np.zeros(0, dtype=float)

    if not hasattr(mesh, "edges_unique"):
        return np.zeros(n, dtype=float)

    edges = np.asarray(mesh.edges_unique)
    if edges.size == 0:
        return np.zeros(n, dtype=float)

    a = edges[:, 0]
    b = edges[:, 1]
    edge_lengths = np.linalg.norm(vertices[a] - vertices[b], axis=1)

    edge_accum = np.zeros(n, dtype=float)
    edge_count = np.zeros(n, dtype=float)
    np.add.at(edge_accum, a, edge_lengths)
    np.add.at(edge_accum, b, edge_lengths)
    np.add.at(edge_count, a, 1.0)
    np.add.at(edge_count, b, 1.0)

    return np.divide(edge_accum, np.maximum(edge_count, 1.0))


def _normalize_force_vector(force_vector: tuple[float, float, float]) -> tuple[np.ndarray, float]:
    force = np.asarray(force_vector, dtype=float)
    if force.shape != (3,):
        raise ValueError("force_vector must be a length-3 tuple")

    magnitude = float(np.linalg.norm(force))
    if magnitude <= 0:
        force = np.array([0.0, -1.0, 0.0], dtype=float)
        magnitude = 1.0

    return force / magnitude, magnitude


def compute_stress_field(
    mesh_path: str | Path,
    force_vector: tuple[float, float, float] = (0.0, -10.0, 0.0),
) -> dict[str, Any]:
    """Compute a deterministic stress field approximation for a rendered mesh."""
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    scene_or_mesh = trimesh.load(str(mesh_path))

    if isinstance(scene_or_mesh, trimesh.Scene):
        if len(scene_or_mesh.geometry) == 0:
            return _empty_result(mesh_path, 0)
        mesh = trimesh.util.concatenate(list(scene_or_mesh.geometry.values()))
    else:
        mesh = scene_or_mesh

    if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0:
        return _empty_result(mesh_path, 0)

    vertices = np.asarray(mesh.vertices, dtype=float)
    centroid = np.asarray(mesh.centroid, dtype=float)
    if centroid.shape != (3,):
        centroid = np.mean(vertices, axis=0)

    force_direction, force_magnitude = _normalize_force_vector(force_vector)
    force_signature = hashlib.sha1(
        json.dumps([float(v) for v in force_vector], sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]
    force_scale = min(1.5, max(0.6, 1.0 + (force_magnitude / 20.0)))

    radial = np.linalg.norm(vertices - centroid, axis=1)
    radial_term = _safe_normalize(radial)

    normals = np.asarray(mesh.vertex_normals, dtype=float)
    if normals.shape != vertices.shape:
        normals = np.repeat(
            np.asarray([0.0, 0.0, 1.0], dtype=float)[None, :],
            repeats=len(vertices),
            axis=0,
        )

    normal_term = np.abs(normals @ force_direction)
    normal_term = _safe_normalize(normal_term)
    area_term = _safe_normalize(_collect_vertex_face_area_weights(mesh, vertices))
    edge_term = _safe_normalize(_collect_vertex_edge_density(vertices, mesh))

    stress_field = (
        (0.42 * radial_term)
        + (0.27 * (1.0 - normal_term))
        + (0.19 * area_term)
        + (0.12 * edge_term)
    )

    stress_scale = 90.0 * force_scale
    stress_offset = 24.0 + (force_scale * 8.0)
    stresses = stress_offset + (stress_field * stress_scale)
    stresses = stresses + (force_magnitude * 0.0005) * radial_term

    try:
        logger.info(
            "Computed stress field for %s | vertices=%d | force_mag=%.3f",
            mesh_path,
            len(vertices),
            force_magnitude,
        )
    except Exception:
        pass

    stats_min = float(np.min(stresses))
    stats_max = float(np.max(stresses))
    stats_mean = float(np.mean(stresses))

    bounds = np.asarray(mesh.bounds, dtype=float)
    if bounds.ndim != 2 or bounds.shape != (2, 3):
        bounds = []
    else:
        bounds = bounds.tolist()

    return {
        "stresses": stresses.tolist(),
        "points": vertices.tolist(),
        "min": stats_min,
        "max": stats_max,
        "mean": stats_mean,
        "count": len(vertices),
        "summary": {
            **_safe_json_summary(mesh_path, len(vertices)),
            "force_magnitude": force_magnitude,
            "force_vector_signature": force_signature,
            "algorithm": "deterministic_geometry_proxy",
            "mesh_bounds": bounds,
            "signature_fields": [
                "radial_term",
                "normal_term",
                "area_term",
                "edge_term",
            ],
        },
    }


def _empty_result(mesh_path: Path | str, count: int) -> dict[str, Any]:
    """Return an empty proxy payload with stable schema for downstream callers."""
    return {
        "stresses": [],
        "points": [],
        "min": 0.0,
        "max": 0.0,
        "mean": 0.0,
        "count": int(count),
        "summary": {
            "source": str(mesh_path),
            "vertex_count": int(count),
            "schema_version": "stress_proxy_v1",
            "approximation": True,
            "status": "empty_mesh",
        },
    }
