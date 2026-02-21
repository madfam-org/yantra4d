import cadquery as cq
import math
import json
import argparse

def add_discrete_teeth(base, n, r, w, h, t):
    """Add box teeth around a circle."""
    for i in range(n):
        angle = i * (360.0 / n)
        rad = math.radians(angle)
        x = r * math.cos(rad)
        y = r * math.sin(rad)
        tooth = (
            cq.Workplane("XY")
            .box(h, w, t)
            .rotate((0, 0, 0), (0, 0, 1), angle)
            .translate((x, y, 0))
        )
        base = base.union(tooth)
    return base

def wave_generator(flex_pitch_diam, gear_module, thickness, bore_diameter):
    r_base = (flex_pitch_diam - (gear_module * 2)) / 2.0
    res = (
        cq.Workplane("XY")
        .polygon(128, 2*r_base, circumscribed=False)
        .extrude((thickness - 2.0)/2.0, both=True)
    )
    res = res.faces(">Z").workplane().polygon(128, bore_diameter, circumscribed=False).cutThruAll()
    return res

def flexspline(flex_pitch_diam, gear_module, flex_teeth, tooth_w, tooth_h, thickness):
    r_body = (flex_pitch_diam - 0.1) / 2.0
    res = cq.Workplane("XY").polygon(128, 2*r_body, circumscribed=False).extrude(thickness/2.0, both=True)
    res = add_discrete_teeth(res, flex_teeth, flex_pitch_diam/2.0, tooth_w, tooth_h, thickness)
    
    inner_d = (flex_pitch_diam - (gear_module * 4))
    res = res.cut(cq.Workplane("XY").polygon(128, inner_d, circumscribed=False).extrude((thickness + 0.1)/2.0, both=True))
    
    flange_d = (flex_pitch_diam + 10)
    flange = (
        cq.Workplane("XY")
        .workplane(offset=-thickness/2.0)
        .polygon(128, flange_d, circumscribed=False)
        .extrude(-2.0)
    )
    return res.union(flange)

def circular_spline(pitch_diam, num_teeth, tooth_w, tooth_h, thickness):
    outer_d = (pitch_diam + 15)
    inner_d = (pitch_diam + 0.1)
    
    res = cq.Workplane("XY").polygon(128, outer_d, circumscribed=False).extrude(thickness/2.0, both=True)
    
    hole = cq.Workplane("XY").polygon(128, inner_d, circumscribed=False).extrude((thickness + 1.0)/2.0, both=True)
    hole = add_discrete_teeth(hole, num_teeth, pitch_diam/2.0, tooth_w, tooth_h, thickness + 1.0)
    
    return res.cut(hole)

def build(params, part="all"):
    num_teeth = int(params.get('num_teeth', 100))
    gear_module = float(params.get('module', 0.5))
    bore_diameter = float(params.get('bore_diameter', 5.0))
    
    flex_teeth = num_teeth - 2
    pitch_diam = gear_module * num_teeth
    flex_pitch_diam = gear_module * flex_teeth
    thickness = 10.0
    tooth_w = gear_module * 0.8
    tooth_h = gear_module * 4.0 # 2.0mm depth
    
    wg = wave_generator(flex_pitch_diam, gear_module, thickness, bore_diameter)
    fs = flexspline(flex_pitch_diam, gear_module, flex_teeth, tooth_w, tooth_h, thickness)
    cs = circular_spline(pitch_diam, num_teeth, tooth_w, tooth_h, thickness)
    
    if part == "wave_generator":
        return wg.clean()
    elif part == "flexspline":
        return fs.clean()
    elif part == "circular_spline":
        return cs.clean()
        
    res = wg.union(fs).union(cs)
    return res.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--part", type=str, default="all")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params, part=args.part)
    
    if args.out:
        cq.exporters.export(res, args.out)
