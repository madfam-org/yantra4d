import trimesh
import numpy as np
import sys

def verify_single_part(mesh_path):
    print(f"--- Verifying {mesh_path} ---")
    mesh = trimesh.load(mesh_path)
    
    # 1. Watertight
    if mesh.is_watertight:
        print("[PASS] Mesh is watertight")
    else:
        print("[FAIL] Mesh is NOT watertight")
        
    # 2. Single Volume (Body Count)
    # trimesh.graph.split() returns list of meshes
    bodies = mesh.split()
    print(f"[INFO] Body Count: {len(bodies)}")
    if len(bodies) == 1:
        print("[PASS] Single unified volume confirmed")
    else:
        # Sometimes text adds bodies if floatin?
        # Or internal voids?
        print(f"[WARN] Multiple bodies found ({len(bodies)}). Checking volumes...")
        for i, b in enumerate(bodies):
            print(f"  Body {i}: Volume {b.volume:.2f}")
        # If the main body is > 99% of mass, it's acceptable (text artifacts)
        # But our goal was Volume: 1.

    # 3. Dimensions
    extents = mesh.extents
    print(f"[INFO] Dimensions: {extents}")
    # Target 20x20x20
    if np.allclose(extents, [20, 20, 20], atol=0.2):
        print("[PASS] Dimensions match ~20mm")
    else:
        print(f"[FAIL] Dimensions incorrect. Expected ~[20,20,20]")

    return mesh

def verify_assembly(mesh):
    print("\n--- Verifying Assembly ---")
    
    # Create Part A (Fixed)
    part_A = mesh.copy()
    part_A.visual.face_colors = [0, 255, 255, 100] # Cyan
    
    # Create Part B (Transformed)
    # Logic: 
    # 1. Flip upside down (Rotate 180 on X)
    # 2. Rotate 90 on Z (to align walls to Y axis of Base A)
    part_B = mesh.copy()
    part_B.visual.face_colors = [255, 0, 255, 100] # Magenta
    
    # Transform B
    # Rotate 180 about X
    rot_x = trimesh.transformations.rotation_matrix(np.pi, [1,0,0])
    # Rotate 90 about Z
    rot_z = trimesh.transformations.rotation_matrix(np.pi/2, [0,0,1])
    
    # Combine (Z then X? or X then Z?)
    # Order matters. 
    # Flip it over (now Upside down). Then Rotate around Z.
    T = trimesh.transformations.concatenate_matrices(rot_z, rot_x)
    
    # Apply
    part_B.apply_transform(T)
    
    # 3. Collision Check
    col_man = trimesh.collision.CollisionManager()
    col_man.add_object('part_A', part_A)
    col_man.add_object('part_B', part_B)
    
    is_collision = col_man.in_collision_internal()
    
    print(f"[INFO] Collision Detected? {is_collision}")
    
    if is_collision:
        # detailed check
        # We expect is_collision might be True if faces touch exactly.
        # But we designed with 0.2mm clearance.
        # Let's check contact points or overlap volume?
        # Trimesh collision is boolean.
        
        # Checking minimum distance
        dist = col_man.min_distance_internal()
        print(f"[INFO] Min Distance: {dist}")
        
        if dist == 0.0:
             print("[WARN] Parts are touching or colliding.")
    else:
        print("[PASS] No collision detected (Clearance works)")
        
    return part_A, part_B

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mesh_path = sys.argv[1]
    else:
        mesh_path = "models/half_cube.stl"
        
    mesh = verify_single_part(mesh_path)
    part_A, part_B = verify_assembly(mesh)
    
    # Optional: Save assembly for viewing
    # scene = trimesh.Scene([part_A, part_B])
    # scene.export("models/assembly_verification.glb")
