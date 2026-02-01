"""
Manifest-driven geometric verification engine.

Usage:
    python verify_design.py <stl_path> [<config_json>]

When config_json is omitted, uses built-in DEFAULTS (backward compat).
Outputs human-readable lines followed by ===JSON=== structured data.
"""
import json
import sys

import numpy as np
import trimesh

# ---------------------------------------------------------------------------
# Default configuration (mirrors full stages config with all checks enabled)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "stages": {
        "geometry": {
            "checks": {
                "watertight": {"enabled": True},
                "body_count": {"enabled": True, "expected": 1},
                "dimensions": {
                    "enabled": True,
                    "xy_tolerance_mm": 0.5,
                    "z_ratio_min": 0.9,
                    "z_ratio_max": 1.1,
                },
                "facet_count": {"enabled": True, "min_facets": 400},
            }
        },
        "printability": {
            "checks": {
                "thin_wall": {"enabled": True, "min_thickness_mm": 0.8},
                "overhang": {"enabled": True, "max_angle_deg": 45},
                "min_feature_size": {"enabled": True, "min_size_mm": 0.4},
            }
        },
        "assembly_fit": {
            "checks": {
                "collision": {
                    "enabled": True,
                    "transform": {"rotate_x_deg": 180, "rotate_z_deg": 90},
                }
            }
        },
    }
}

# ---------------------------------------------------------------------------
# Check functions — signature: (mesh, cfg: dict) -> (passed: bool, info: str)
# ---------------------------------------------------------------------------


def check_watertight(mesh, cfg):
    if mesh.is_watertight:
        return True, "watertight"
    return False, "mesh is NOT watertight"


def check_body_count(mesh, cfg):
    expected = cfg.get("expected", 1)
    bodies = mesh.split()
    count = len(bodies)
    if count == expected:
        return True, f"{count} body"
    details = "; ".join(f"body {i}: vol {b.volume:.2f}" for i, b in enumerate(bodies))
    return False, f"{count} bodies (expected {expected}). {details}"


def check_dimensions(mesh, cfg):
    extents = mesh.extents
    xy_tol = cfg.get("xy_tolerance_mm", 0.5)
    z_min_ratio = cfg.get("z_ratio_min", 0.9)
    z_max_ratio = cfg.get("z_ratio_max", 1.1)

    xy_max = max(extents[:2])
    xy_min = min(extents[:2])
    xy_ok = np.isclose(xy_max, xy_min, atol=xy_tol)
    z_ok = xy_max * z_min_ratio < extents[2] < xy_max * z_max_ratio

    dims = f"{extents[0]:.1f}x{extents[1]:.1f}x{extents[2]:.1f}mm"
    if xy_ok and z_ok:
        return True, dims
    return False, f"out of range: {dims}"


def check_facet_count(mesh, cfg):
    min_facets = cfg.get("min_facets", 400)
    count = len(mesh.faces)
    if count >= min_facets:
        return True, f"{count} facets"
    return False, f"{count} facets (min {min_facets})"


def check_thin_wall(mesh, cfg):
    min_thickness = cfg.get("min_thickness_mm", 0.8)
    # Sample face centroids, cast rays inward along inverted normals
    n_samples = min(500, len(mesh.faces))
    rng = np.random.default_rng(42)
    indices = rng.choice(len(mesh.faces), size=n_samples, replace=False)

    centroids = mesh.triangles_center[indices]
    normals = mesh.face_normals[indices]
    # Ray direction: inward (opposite of face normal)
    directions = -normals

    locations, ray_indices, _ = mesh.ray.intersects_location(
        ray_origins=centroids + directions * 0.001,  # small offset to avoid self-hit
        ray_directions=directions,
    )

    if len(locations) == 0:
        return True, f"no inward hits (threshold {min_thickness:.1f}mm)"

    # Compute distances from origin to hit
    origin_points = centroids[ray_indices]
    distances = np.linalg.norm(locations - origin_points, axis=1)

    min_dist = float(np.min(distances)) if len(distances) > 0 else float("inf")
    thin_count = int(np.sum(distances < min_thickness))
    thin_ratio = thin_count / n_samples

    if min_dist >= min_thickness:
        return True, f"min {min_dist:.1f}mm (threshold {min_thickness:.1f}mm)"
    return False, f"min {min_dist:.1f}mm < {min_thickness:.1f}mm ({thin_ratio:.0%} thin faces)"


def check_overhang(mesh, cfg):
    max_angle = cfg.get("max_angle_deg", 45)
    normals = mesh.face_normals
    # Only consider downward-facing faces (normal.z < 0)
    downward = normals[:, 2] < 0
    if not np.any(downward):
        return True, f"no overhangs (threshold {max_angle}°)"

    down_normals = normals[downward]
    # Angle from vertical (Z-down): arccos(abs(nz))
    angles_rad = np.arccos(np.clip(np.abs(down_normals[:, 2]), 0, 1))
    angles_deg = np.degrees(angles_rad)
    worst = float(np.max(angles_deg))
    overhang_count = int(np.sum(angles_deg > max_angle))
    overhang_ratio = overhang_count / len(mesh.faces)

    if worst <= max_angle:
        return True, f"max {worst:.0f}° (threshold {max_angle}°)"
    return False, f"max {worst:.0f}° > {max_angle}° ({overhang_ratio:.0%} overhang faces)"


def check_min_feature_size(mesh, cfg):
    min_size = cfg.get("min_size_mm", 0.4)
    bodies = mesh.split()
    if len(bodies) > 1:
        # Check each body's bounding box min extent
        min_extent = float("inf")
        for body in bodies:
            ext = min(body.extents)
            if ext < min_extent:
                min_extent = ext
    else:
        # Single body: use overall min extent as proxy
        min_extent = float(min(mesh.extents))

    if min_extent >= min_size:
        return True, f"min {min_extent:.1f}mm (threshold {min_size:.1f}mm)"
    return False, f"min {min_extent:.1f}mm < {min_size:.1f}mm"


def check_collision(mesh, cfg):
    transform_cfg = cfg.get("transform", {"rotate_x_deg": 180, "rotate_z_deg": 90})
    rot_x_deg = transform_cfg.get("rotate_x_deg", 180)
    rot_z_deg = transform_cfg.get("rotate_z_deg", 90)

    part_a = mesh.copy()
    part_b = mesh.copy()

    rot_x = trimesh.transformations.rotation_matrix(np.radians(rot_x_deg), [1, 0, 0])
    rot_z = trimesh.transformations.rotation_matrix(np.radians(rot_z_deg), [0, 0, 1])
    T = trimesh.transformations.concatenate_matrices(rot_z, rot_x)
    part_b.apply_transform(T)

    col_man = trimesh.collision.CollisionManager()
    col_man.add_object("part_a", part_a)
    col_man.add_object("part_b", part_b)

    is_collision = col_man.in_collision_internal()
    if is_collision:
        return False, "parts collide after transform"
    return True, "no collision (clearance works)"


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------
CHECK_REGISTRY = {
    "watertight": check_watertight,
    "body_count": check_body_count,
    "dimensions": check_dimensions,
    "facet_count": check_facet_count,
    "thin_wall": check_thin_wall,
    "overhang": check_overhang,
    "min_feature_size": check_min_feature_size,
    "collision": check_collision,
}

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def run_verification(mesh, config):
    """Run all enabled checks from config, return structured results."""
    stages_cfg = config.get("stages", {})
    all_failures = []
    stages_result = {}

    for stage_id, stage in stages_cfg.items():
        checks = stage.get("checks", {})
        stage_results = {}
        print(f"--- {stage_id} ---")

        for check_id, check_cfg in checks.items():
            if not check_cfg.get("enabled", True):
                continue
            fn = CHECK_REGISTRY.get(check_id)
            if fn is None:
                print(f"[SKIP] {check_id}: unknown check")
                continue

            passed, info = fn(mesh, check_cfg)
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {check_id}: {info}")

            stage_results[check_id] = {"passed": passed, "info": info}
            if not passed:
                all_failures.append(f"{stage_id}.{check_id}")

        stages_result[stage_id] = stage_results

    overall = len(all_failures) == 0
    return {
        "passed": overall,
        "failures": all_failures,
        "stages": stages_result,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: verify_design.py <stl_path> [<config_json>]")
        sys.exit(2)

    mesh_path = sys.argv[1]

    if len(sys.argv) >= 3:
        config = json.loads(sys.argv[2])
    else:
        config = DEFAULTS

    mesh = trimesh.load(mesh_path)
    result = run_verification(mesh, config)

    print("===JSON===")
    print(json.dumps(result))

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
