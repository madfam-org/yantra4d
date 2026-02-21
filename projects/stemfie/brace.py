import cadquery as cq
import json
import argparse

def build(params):
    BU = 10.0
    HOLE_D = 4.2
    
    arm_a_units = int(params.get('arm_a_units', 3))
    arm_b_units = int(params.get('arm_b_units', 3))
    thickness_units = int(params.get('thickness_units', 1))
    holes_enabled = params.get('holes_enabled', True)
    
    th = thickness_units * (BU / 4.0)
    
    arm_a_len = arm_a_units * BU
    arm_b_len = arm_b_units * BU
    
    # Arm A
    arm_a = cq.Workplane("XY").box(arm_a_len, BU, th).translate((arm_a_len/2.0 - BU/2.0, 0, 0))
    # Arm B
    arm_b = cq.Workplane("XY").box(BU, arm_b_len, th).translate((0, arm_b_len/2.0 - BU/2.0, 0))
    
    brace = arm_a.union(arm_b)
    
    try:
        brace = brace.edges().chamfer(0.5)
    except Exception:
        pass
        
    if holes_enabled:
        for i in range(arm_a_units):
            cx = i * BU
            hole = cq.Workplane("XY").circle(HOLE_D/2.0).extrude(th + 2).translate((cx, 0, -(th/2.0 + 1)))
            brace = brace.cut(hole)
        for j in range(1, arm_b_units):
            cy = j * BU
            hole = cq.Workplane("XY").circle(HOLE_D/2.0).extrude(th + 2).translate((0, cy, -(th/2.0 + 1)))
            brace = brace.cut(hole)
            
    return brace.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
