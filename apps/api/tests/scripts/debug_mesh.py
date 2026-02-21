import trimesh
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_mesh.py <stl_file>")
        sys.exit(1)
        
    mesh_path = sys.argv[1]
    mesh = trimesh.load(mesh_path)
    
    # Split bodies
    bodies = mesh.split()
    print(f"Total bodies: {len(bodies)}")
    
    for i, body in enumerate(bodies):
        print(f"--- Body {i} ---")
        print(f"Volume: {body.volume:.2f}")
        print(f"Faces: {len(body.faces)}")
        bounds = body.bounds
        print(f"Bounds Min: {bounds[0]}")
        print(f"Bounds Max: {bounds[1]}")
        center = body.centroid
        print(f"Centroid: {center}")
        # Check if inverted
        if body.volume < 0:
            print("WARNING: Negative volume (Inverted)")

if __name__ == "__main__":
    main()
