import cadquery as cq
import json
import argparse

def build(params):
    diameter = float(params.get('diameter', 5.0))
    width = float(params.get('width', 0.0))
    height = float(params.get('height', 0.0))
    nut_style_id = int(params.get('nut_style_id', 0))
    
    nut_w = width if width > 0 else diameter * 1.7
    nut_h = height if height > 0 else diameter * 0.8
    nyloc_extra = nut_h * 0.3 if nut_style_id == 2 else 0.0
    
    total_h = nut_h + nyloc_extra
    
    # Outer shape
    wp = cq.Workplane("XY")
    
    if nut_style_id == 1:
        # Square
        nut = wp.rect(nut_w, nut_w).extrude(total_h)
    else:
        # Hex (or Hex + nyloc)
        nut = wp.polygon(6, nut_w).extrude(total_h)
        
    # Hole
    hole = wp.circle(diameter / 2.0).extrude(total_h + 1.0).translate((0,0,-0.5))
    
    nut = nut.cut(hole)
        
    # Nyloc top rounding (optional detailing)
    if nut_style_id == 2:
        try:
            nut = nut.edges(">Z and %LINE").fillet(nyloc_extra - 0.1)
        except Exception:
            pass
            
    return nut.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
