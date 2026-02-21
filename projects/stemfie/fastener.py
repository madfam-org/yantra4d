import cadquery as cq
import json
import argparse

def build(params):
    BU = 10.0
    HOLE_D = 4.2
    
    length_units = int(params.get('length_units', 2))
    fastener_type_id = int(params.get('fastener_type_id', 0))
    
    h_mm = length_units * BU
    
    # Shaft
    shaft = cq.Workplane("XY").circle((HOLE_D - 0.2)/2.0).extrude(h_mm)
    shaft = shaft.translate((0, 0, -h_mm/2.0))
    
    try:
        # For a cylinder, chamfering edges(">Z or <Z")
        shaft = shaft.edges(">Z or <Z").chamfer(0.5)
    except Exception:
        pass
        
    # Stop ring
    if fastener_type_id == 0:
        stop = cq.Workplane("XY").circle((HOLE_D + 1.5)/2.0).extrude(2.0)
        stop = stop.translate((0, 0, -1.0))
        try:
            stop = stop.edges(">Z or <Z").chamfer(0.5)
        except Exception:
            pass
        shaft = shaft.union(stop)
        
    return shaft.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
