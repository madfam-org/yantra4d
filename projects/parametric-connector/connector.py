import cadquery as cq
import json
import argparse

def build(params):
    pipe_od_mm = float(params.get('pipe_od_mm', 21.3))
    connector_type = params.get('connector_type', "elbow")
    wall_thickness_mm = float(params.get('wall_thickness_mm', 3.0))
    insertion_depth_mm = float(params.get('insertion_depth_mm', 20.0))
    
    socket_od = pipe_od_mm + (wall_thickness_mm * 2.0)
    socket_length = insertion_depth_mm + wall_thickness_mm
    offset = (socket_od / 2.0) - wall_thickness_mm
    
    # Core sphere
    res = cq.Workplane("XY").sphere(socket_od / 2.0)
    
    # Base socket arm (oriented along +Z, starting from Z=0)
    arm_solid = (
        cq.Workplane("XY")
        .circle(socket_od / 2.0)
        .extrude(socket_length)
        .faces(">Z")
        .workplane()
        .circle((pipe_od_mm + 0.5) / 2.0)
        .cutBlind(-insertion_depth_mm)
    )
    
    def add_arm(vec=(0,0,1)):
        rx, ry, _rz = 0, 0, 0
        if vec == (0,0,-1): 
            rx = 180
        elif vec == (1,0,0): 
            ry = 90
        elif vec == (-1,0,0): 
            ry = -90
        elif vec == (0,1,0): 
            rx = -90
        elif vec == (0,-1,0): 
            rx = 90
            
        arm = arm_solid.rotate((0,0,0), (1,0,0), rx).rotate((0,0,0), (0,1,0), ry)
        arm = arm.translate((vec[0]*offset, vec[1]*offset, vec[2]*offset))
        return arm

    arms = []
    
    # Determine axes based on connector type
    # Fixed the elbow having 3 arms SCAD bug!
    axes = [(1,0,0)] # All connectors have X+
    
    if connector_type == "elbow":
        axes.append((0,1,0)) # Y+
    elif connector_type == "tee":
        axes.extend([(-1,0,0), (0,1,0)]) # X-, Y+
    elif connector_type == "cross":
        axes.extend([(-1,0,0), (0,0,1), (0,0,-1)]) # X-, Z+, Z-
    elif connector_type == "3-way-corner":
        axes.extend([(0,1,0), (0,0,1)]) # Y+, Z+
    elif connector_type == "4-way-corner":
        axes.extend([(-1,0,0), (0,1,0), (0,0,1)]) # X-, Y+, Z+
    elif connector_type == "5-way":
        axes.extend([(-1,0,0), (0,1,0), (0,0,1), (0,0,-1)]) # X-, Y+, Z+, Z-
    elif connector_type == "6-way":
        axes.extend([(-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]) # All 6
        
    for vec in axes:
        arms.append(add_arm(vec))
        
    for arm in arms:
        res = res.union(arm)
        
    return res.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    result_geometry = build(params)
    
    if args.out:
        cq.exporters.export(result_geometry, args.out)
