import cadquery as cq
import json
import argparse

def build(params):
    width_units = int(params.get('width_units', 2))
    depth_units = int(params.get('depth_units', 1))
    height_units = int(params.get('height_units', 3))
    cup_floor_thickness = float(params.get('cup_floor_thickness', 0.7))
    
    pitch = 42.0
    zpitch = 7.0
    corner_radius = 3.75
    
    total_w = width_units * pitch - 0.5
    total_d = depth_units * pitch - 0.5
    total_h = height_units * zpitch
    
    # Core geometry
    # offset to center it properly (the SCAD is centered on X/Y and +Z on Z)
    # CQ box is centered by default, so we translate Z by total_h/2
    cup = (
        cq.Workplane("XY")
        .box(total_w, total_d, total_h)
        .edges("|Z")
        .fillet(corner_radius)
        .translate((0, 0, total_h/2.0))
    )
    
    # Inner scoop
    # The inner box is W-2.4, D-2.4, H
    # The SCAD says p1 = [-..., -..., 0], and it's shifted up by cup_floor_thickness.
    inner_w = total_w - 2.4
    inner_d = total_d - 2.4
    inner = (
        cq.Workplane("XY")
        .box(inner_w, inner_d, total_h)
        .edges("|Z")
        .fillet(corner_radius)
        .translate((0, 0, total_h/2.0 + cup_floor_thickness))
    )
    
    cup = cup.cut(inner)
    
    # Bottom profile (interface)
    # Grid of prismoids to cut from the bottom
    # SCAD: size1=[39.2, 39.2] (bottom), size2=[42, 42] (top), h=5, shifted down by 0.1
    # CQ makePrism is a bit different, easiest is a swept loft or just use an inverted pyramid
    # Actually, a simple cut from the base is a chamfered box or a loft.
    # We can create a base prismoid:
    # A loft between two rectangles.
    prismoid = (
        cq.Workplane("XY", origin=(0,0,-0.1))
        .rect(39.2, 39.2)
        .workplane(offset=5.0)
        .rect(42.0, 42.0)
        .loft(combine=True)
    )
    # Fillet vertical edges
    try:
        prismoid = prismoid.edges("|Z").fillet(corner_radius - 0.1)
    except Exception:
        pass
    
    start_x = -total_w/2.0 + pitch/2.0
    start_y = -total_d/2.0 + pitch/2.0
    
    for x in range(width_units):
        for y in range(depth_units):
            cx = start_x + x * pitch
            cy = start_y + y * pitch
            cup = cup.cut(prismoid.translate((cx, cy, 0)))
            
    return cup.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
