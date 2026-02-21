import cadquery as cq
import json
import argparse

def build(params):
    BU = 10.0
    HOLE_D = 4.2
    
    length_units = int(params.get('length_units', 4))
    width_units = int(params.get('width_units', 1))
    height_units = int(params.get('height_units', 1))
    holes_x = params.get('holes_x', True)
    holes_y = params.get('holes_y', True)
    holes_z = params.get('holes_z', True)
    
    l_mm = length_units * BU
    w_mm = width_units * BU
    h_mm = height_units * BU
    
    # Beam body
    beam = cq.Workplane("XY").box(l_mm, w_mm, h_mm)
    
    try:
        beam = beam.edges().chamfer(0.5)
    except Exception:
        pass
        
    # Z Holes
    if holes_z:
        for i in range(length_units):
            for j in range(width_units):
                x = -l_mm/2.0 + i*BU + BU/2.0
                y = -w_mm/2.0 + j*BU + BU/2.0
                hole = cq.Workplane("XY").circle(HOLE_D/2.0).extrude(h_mm + 2).translate((x, y, - (h_mm/2.0 + 1)))
                beam = beam.cut(hole)
    # X Holes
    if holes_x:
        for j in range(width_units):
            for k in range(height_units):
                y = -w_mm/2.0 + j*BU + BU/2.0
                z = -h_mm/2.0 + k*BU + BU/2.0
                # YZ plane pushes along X
                hole = cq.Workplane("YZ").circle(HOLE_D/2.0).extrude(l_mm + 2).translate((- (l_mm/2.0 + 1), y, z))
                beam = beam.cut(hole)
    # Y Holes
    if holes_y:
        for i in range(length_units):
            for k in range(height_units):
                x = -l_mm/2.0 + i*BU + BU/2.0
                z = -h_mm/2.0 + k*BU + BU/2.0
                # XZ plane pushes along Y (watch out, XZ extrudes in -Y in CQ, but since we center it we just ensure it goes through)
                hole = cq.Workplane("XZ").circle(HOLE_D/2.0).extrude(w_mm + 2).translate((x, w_mm/2.0 + 1, z))
                beam = beam.cut(hole)
                
    return beam.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
