import cadquery as cq
import json
import argparse

def build(params):
    jaw_width_inch = float(params.get('jaw_width', 6.0))
    face_pattern = int(params.get('face_pattern', 0))
    magnet_pockets = bool(params.get('magnet_pockets', True))
    jaw_height_inch = float(params.get('jaw_height', 1.735)) # Using defaults from json, scad had 1.25 hardcoded but params allow it
    jaw_thickness_inch = float(params.get('jaw_thickness', 0.75))
    int(params.get('vise_model', 0))
    
    width_mm = jaw_width_inch * 25.4
    height_mm = jaw_height_inch * 25.4
    thickness_mm = jaw_thickness_inch * 25.4
    
    bolt_spacing = 3.875 * 25.4
    bolt_head_d = 14.0
    bolt_shaft_d = 9.0
    
    # 1. Main Body
    # Origin at center
    jaw = cq.Workplane("XY").box(width_mm, thickness_mm, height_mm)
    
    # 2. Face Pattern (on FWD face <Y)
    if face_pattern == 1:
        # Prismatic additive
        prism = (
            cq.Workplane("YZ")
            .polyline([(-thickness_mm/2, -5), (-thickness_mm/2 - 5, 0), (-thickness_mm/2, 5)])
            .close()
            .extrude(width_mm/2, both=True)
        )
        jaw = jaw.union(prism).clean()
    elif face_pattern == 2:
        # Simplified Grid (just extruded ribs to represent knurling and keep generation fast)
        ribs_h = (
            cq.Workplane("XZ", origin=(0, -thickness_mm/2, 0))
            .pushPoints([(0, y) for y in range(int(-height_mm/2)+5, int(height_mm/2), 5)])
            .rect(width_mm, 1)
            .extrude(-1)
        )
        ribs_v = (
            cq.Workplane("XZ", origin=(0, -thickness_mm/2, 0))
            .pushPoints([(x, 0) for x in range(int(-width_mm/2)+5, int(width_mm/2), 5)])
            .rect(1, height_mm)
            .extrude(-1)
        )
        jaw = jaw.union(ribs_h).union(ribs_v)
        
    # 3. Mounting Holes (Tapered cylinder from BACK face >Y to FWD face)
    # Using XZ plane at Y = thickness/2, extruding in -Y
    base_cone = (
        cq.Workplane("XZ")
        .circle(bolt_head_d/2)
        .workplane(offset=-(thickness_mm+1))
        .circle(bolt_shaft_d/2)
        .loft()
    )
    cone1 = base_cone.translate((bolt_spacing/2, thickness_mm/2, 0))
    cone2 = base_cone.translate((-bolt_spacing/2, thickness_mm/2, 0))
    jaw = jaw.cut(cone1).cut(cone2).clean()
    
    # 4. Magnet Pockets (on BACK face >Y)
    if magnet_pockets:
        jaw = (
            jaw.faces(">Y")
            .workplane()
            .pushPoints([(0, height_mm/3), (0, -height_mm/3)])
            .hole(diameter=10.2, depth=3.0)
        )
        
    return jaw

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
