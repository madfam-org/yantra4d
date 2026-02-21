import cadquery as cq
import json
import argparse
import random
import math

def build(params):
    circumference_top = float(params.get('circumference_top', 350.0))
    circumference_bottom = float(params.get('circumference_bottom', 250.0))
    length = float(params.get('length', 300.0))
    voronoi_density = int(params.get('voronoi_density', 10))
    wall_thickness = float(params.get('wall_thickness', 4.0))
    
    r_upper = circumference_top / (2.0 * math.pi)
    r_lower = circumference_bottom / (2.0 * math.pi)
    
    # 1. Outer Shell
    outer = cq.Solid.makeCone(r_lower + wall_thickness, r_upper + wall_thickness, length)
    
    # 2. Inner Cavity
    # It starts at Z = wall_thickness and goes to length + 1
    # Height of inner cone = length + 1 - wall_thickness
    h_inner = length + 1.0 - wall_thickness
    inner = cq.Solid.makeCone(r_lower, r_upper, h_inner).translate((0, 0, wall_thickness))
    
    socket = cq.Workplane("XY").add(outer).cut(inner)
    
    # 3. Voronoi Ventilation (Approximated with spherical cuts)
    random.seed(int(r_upper * length)) # Deterministic seed
    
    spheres = []
    for i in range(voronoi_density * 2):
        z = random.uniform(20.0, length - 20.0)
        ang = random.uniform(0.0, 360.0)
        rad = random.uniform(5.0, 15.0)
        
        # Interpolate radius at height z
        t = z / length
        r_at_z = (r_lower + wall_thickness) * (1.0 - t) + (r_upper + wall_thickness) * t
        
        x = r_at_z * math.cos(math.radians(ang))
        y = r_at_z * math.sin(math.radians(ang))
        
        sphere = cq.Solid.makeSphere(rad).translate((x, y, z))
        spheres.append(sphere)
        
    for s in spheres:
        socket = socket.cut(s)
        
    # 4. Distal Hardware Mounting Holes
    # Central hole
    center_hole = cq.Solid.makeCylinder(6.0 / 2.0, 10.0).translate((0, 0, -1.0))
    socket = socket.cut(center_hole)
    
    # 4x M4 holes at r=15
    for a in [0, 90, 180, 270]:
        x = 15.0 * math.cos(math.radians(a))
        y = 15.0 * math.sin(math.radians(a))
        hole = cq.Solid.makeCylinder(4.0 / 2.0, 10.0).translate((x, y, -1.0))
        socket = socket.cut(hole)
        
    return socket.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
