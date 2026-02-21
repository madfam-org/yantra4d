import cadquery as cq
import json
import argparse

def get_nema_dims(size):
    # Returns (face_w, hole_spacing, shaft_hole_d, screw_d)
    if size == 23:
        return (56.4, 47.14, 38.1, 5.5)
    elif size == 34:
        return (86.0, 69.6, 73.0, 5.5)
    else:  # Default to 17
        return (42.3, 31.0, 22.0, 3.0)

def build(params):
    nema_size = int(params.get('nema_size', 17))
    wall_thickness = float(params.get('wall_thickness', 4))
    base_thickness = float(params.get('base_thickness', 5))
    mounting_style = int(params.get('mounting_style', 0))
    
    face_w, hole_spacing, shaft_hole_d, screw_d = get_nema_dims(nema_size)
    
    plate_size = face_w + (wall_thickness * 2.0)
    bracket_height = face_w if mounting_style == 1 else 0
    
    mount_hole_d = 5.0
    mount_hole_spacing = plate_size - 10.0
    
    # 1. Base Plate
    # Create the base flat plate on XY plane
    # The SCAD anchor was BOT, meaning it sits on Z=0 and extends up.
    # In CQ, box is centered by default. We can extrude from Z=0 up.
    
    plate = (
        cq.Workplane("XY")
        .rect(plate_size, plate_size)
        .extrude(base_thickness)
    )
    
    # Center shaft hole
    plate = plate.faces(">Z").workplane().circle((shaft_hole_d + 1) / 2.0).cutThruAll()
    
    # 4 Motor Holes
    motor_holes_pts = [
        (hole_spacing/2, hole_spacing/2),
        (hole_spacing/2, -hole_spacing/2),
        (-hole_spacing/2, hole_spacing/2),
        (-hole_spacing/2, -hole_spacing/2)
    ]
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(motor_holes_pts)
        .circle((screw_d + 0.3) / 2.0)
        .cutThruAll()
    )
    
    # 4 Mounting Holes
    mount_holes_pts = [
        (mount_hole_spacing/2, mount_hole_spacing/2),
        (mount_hole_spacing/2, -mount_hole_spacing/2),
        (-mount_hole_spacing/2, mount_hole_spacing/2),
        (-mount_hole_spacing/2, -mount_hole_spacing/2)
    ]
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(mount_holes_pts)
        .circle(mount_hole_d / 2.0)
        .cutThruAll()
    )
    
    result = plate
    
    # 2. L-Bracket Vertical Wall
    if mounting_style == 1:
        # Create a vertical wall extending up from the base
        # It's at Y = -plate_size/2 + wall_thickness/2
        # Width = plate_size (X), depth = wall_thickness (Y), height = bracket_height + base_thickness (Z)
        
        # We can build it on XY and move it, or just use a box
        v_wall = (
            cq.Workplane("XY")
            .box(plate_size, wall_thickness, bracket_height + base_thickness)
            .translate((0, -plate_size/2.0 + wall_thickness/2.0, (bracket_height + base_thickness)/2.0))
        )
        
        # Lightening hole in the vertical wall
        # Translated to the center of the vertical wall
        lh_d = bracket_height * 0.5
        v_wall = (
            v_wall.faces(">Y").workplane()
            .circle(lh_d / 2.0)
            .cutThruAll()
        )
        
        result = result.union(v_wall).clean()
        
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
