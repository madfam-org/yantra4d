import cadquery as cq
import json
import argparse

def build(params):
    width_units = int(params.get('width_units', 2))
    depth_units = int(params.get('depth_units', 2))
    bp_enable_screws = params.get('bp_enable_screws', False)
    bp_corner_radius = float(params.get('bp_corner_radius', 3.75))
    
    pitch = 42.0
    overall_z = 5.0
    
    total_w = width_units * pitch
    total_d = depth_units * pitch
    
    # Baseplate Profile
    bp = (
        cq.Workplane("XY")
        .box(total_w, total_d, overall_z)
        .edges("|Z")
        .fillet(bp_corner_radius)
        .translate((0, 0, overall_z/2.0))
    )
    
    # Top prismoid indents
    # size1=[39.2, 39.2], size2=[42, 42], h=5. The baseplate cuts these out at the top.
    # SCAD says: down(5) prismoid() starting from overall_z. So it goes from Z=0 to Z=5.
    # It cuts out the volume representing the cup bottom.
    prismoid = (
        cq.Workplane("XY", origin=(0,0,-0.1))
        .rect(39.2, 39.2)
        .workplane(offset=5.2)
        .rect(42.0, 42.0)
        .loft(combine=True)
    )
    try:
        prismoid = prismoid.edges("|Z").fillet(bp_corner_radius - 0.1)
    except Exception:
        pass
    
    start_x = -total_w/2.0 + pitch/2.0
    start_y = -total_d/2.0 + pitch/2.0
    
    for x in range(width_units):
        for y in range(depth_units):
            cx = start_x + x * pitch
            cy = start_y + y * pitch
            bp = bp.cut(prismoid.translate((cx, cy, 0)))
            
            if bp_enable_screws:
                hole = cq.Workplane("XY").circle(3.2/2.0).extrude(10).translate((cx, cy, -1))
                bp = bp.cut(hole)
                
    return bp.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
