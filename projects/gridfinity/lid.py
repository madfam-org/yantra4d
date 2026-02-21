import cadquery as cq
import json
import argparse

def build(params):
    width_units = int(params.get('width_units', 2))
    depth_units = int(params.get('depth_units', 1))
    
    pitch = 42.0
    corner_radius = 3.75
    
    total_w = width_units * pitch - 1.0
    total_d = depth_units * pitch - 1.0
    total_h = 2.0
    
    lid = (
        cq.Workplane("XY")
        .box(total_w, total_d, total_h)
        .edges("|Z")
        .fillet(corner_radius)
        .translate((0, 0, total_h/2.0))
    )
    
    return lid.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
