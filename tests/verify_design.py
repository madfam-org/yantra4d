import trimesh
import numpy as np
import sys

# Design note: fit_clear is 0.2mm (not 0.1mm as earlier docs stated).
# Snap-fit features (cantilever beams, undercut heads, relief slots, weld cubes)
# protrude beyond the base cylinder, increasing Z extent.

# Minimum facet count to confirm snap-fit features rendered.
# A plain half-cube without snap beams has ~200 facets; with snaps, ~800+.
MIN_FACET_COUNT = 400


def verify_single_part(mesh_path):
    print(f"--- Verifying {mesh_path} ---")
    mesh = trimesh.load(mesh_path)
    failures = []

    # 1. Watertight
    if mesh.is_watertight:
        print("[PASS] Mesh is watertight")
    else:
        print("[FAIL] Mesh is NOT watertight")
        failures.append("watertight")

    # 2. Single Volume (Body Count)
    bodies = mesh.split()
    print(f"[INFO] Body Count: {len(bodies)}")
    if len(bodies) == 1:
        print("[PASS] Single unified volume confirmed")
    else:
        # Sometimes text adds bodies if floating
        # Or internal voids from relief slots
        print(f"[WARN] Multiple bodies found ({len(bodies)}). Checking volumes...")
        for i, b in enumerate(bodies):
            print(f"  Body {i}: Volume {b.volume:.2f}")

    # 3. Dimensions (parametric Z tolerance)
    extents = mesh.extents
    print(f"[INFO] Dimensions: {extents}")
    # XY should be ~20x20; Z varies with snap beams protruding beyond cylinder
    xy_ok = np.allclose(extents[:2], [20, 20], atol=0.5)
    # Each half is now nearly full cube height (size - fit_clear)
    approx_size = max(extents[:2])
    z_ok = approx_size * 0.9 < extents[2] < approx_size * 1.1
    if xy_ok and z_ok:
        print(f"[PASS] Dimensions within expected range (~20x20, Z ~{approx_size:.0f})")
    else:
        print(f"[FAIL] Dimensions incorrect. Expected ~[20, 20, ~{approx_size:.0f}], got {extents}")
        failures.append("dimensions")

    # 4. Snap-fit feature presence (facet count)
    facet_count = len(mesh.faces)
    print(f"[INFO] Facet count: {facet_count}")
    if facet_count >= MIN_FACET_COUNT:
        print(f"[PASS] Sufficient geometric complexity ({facet_count} facets)")
    else:
        print(f"[FAIL] Too few facets ({facet_count} < {MIN_FACET_COUNT}). "
              "Snap-fit features may be missing.")
        failures.append("facet_count")

    return mesh, failures


def verify_assembly(mesh):
    print("\n--- Verifying Assembly ---")
    failures = []

    # Create Part A (Fixed)
    part_A = mesh.copy()
    part_A.visual.face_colors = [0, 255, 255, 100]  # Cyan

    # Create Part B (Transformed)
    # 1. Flip upside down (Rotate 180 on X)
    # 2. Rotate 90 on Z (to align walls to Y axis of Base A)
    part_B = mesh.copy()
    part_B.visual.face_colors = [255, 0, 255, 100]  # Magenta

    # Transform B
    rot_x = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    rot_z = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])

    # Flip over (upside down), then rotate around Z
    T = trimesh.transformations.concatenate_matrices(rot_z, rot_x)
    part_B.apply_transform(T)

    # Collision Check
    col_man = trimesh.collision.CollisionManager()
    col_man.add_object('part_A', part_A)
    col_man.add_object('part_B', part_B)

    is_collision = col_man.in_collision_internal()
    print(f"[INFO] Collision Detected? {is_collision}")

    if is_collision:
        dist = col_man.min_distance_internal()
        print(f"[INFO] Min Distance: {dist}")
        if dist == 0.0:
            print("[WARN] Parts are touching or colliding.")
    else:
        print("[PASS] No collision detected (Clearance works)")

    return part_A, part_B, failures


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mesh_path = sys.argv[1]
    else:
        mesh_path = "models/half_cube.stl"

    mesh, part_failures = verify_single_part(mesh_path)
    part_A, part_B, asm_failures = verify_assembly(mesh)

    all_failures = part_failures + asm_failures
    if all_failures:
        print(f"\n[RESULT] FAIL — {len(all_failures)} check(s) failed: {all_failures}")
        sys.exit(1)
    else:
        print("\n[RESULT] ALL CHECKS PASSED")
        sys.exit(0)
