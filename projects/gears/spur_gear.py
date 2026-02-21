import cadquery as cq
import json
import argparse
import math

def build(params):
    teeth_count = int(params.get('teeth_count', 20))
    module_size = float(params.get('module_size', 2.0))
    thickness = float(params.get('thickness', 5.0))
    bore_diameter = float(params.get('bore_diameter', 5.0))
    
    R_pitch = module_size * teeth_count / 2.0
    R_outer = R_pitch + module_size
    R_root = R_pitch - 1.25 * module_size
    
    angle_per_tooth = 360.0 / teeth_count
    tooth_width_angle = angle_per_tooth / 2.0
    
    pts = []
    for i in range(teeth_count):
        base_angle = i * angle_per_tooth
        
        # Root start
        a1 = math.radians(base_angle - tooth_width_angle/2)
        pts.append((R_root * math.cos(a1), R_root * math.sin(a1)))
        
        # Outer start
        a2 = math.radians(base_angle - tooth_width_angle/5)
        pts.append((R_outer * math.cos(a2), R_outer * math.sin(a2)))
        
        # Outer end
        a3 = math.radians(base_angle + tooth_width_angle/5)
        pts.append((R_outer * math.cos(a3), R_outer * math.sin(a3)))
        
        # Root end
        a4 = math.radians(base_angle + tooth_width_angle/2)
        pts.append((R_root * math.cos(a4), R_root * math.sin(a4)))
        
    gear_profile = cq.Workplane("XY").polyline(pts).close()
    
    gear = gear_profile.extrude(thickness)
    
    if bore_diameter > 0:
        bore = cq.Workplane("XY").circle(bore_diameter / 2.0).extrude(thickness + 2).translate((0,0,-1))
        gear = gear.cut(bore)
        
    return gear.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
