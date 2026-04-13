import cadquery as cq
import math

# Globals injected by Yantra4D Environment
finger_length = 65.0
base_radius = 35.0
flexure_thickness = 1.2
finger_count = int(globals().get("finger_count", 3))
target_part = globals().get("target_part", "housing")
# Advanced Params
phalanx_width = 18.0

# Coordinate Math Helpers for radially symmetrical placement
def get_finger_angle(i, total):
    return (360.0 / total) * i

def build_housing():
    """Generates a proper UR5-compliant tapered robotic wrist mounting flange."""
    
    # Tapered core
    base = (
        cq.Workplane("XY")
        .circle(base_radius + 5)
        .workplane(offset=15)
        .circle(base_radius)
        .loft(combine=True)
    )
    
    # 6-bolt universal mounting pattern (Standard ISO9409-1-50-4-M6 style but scalable)
    bolt_circle = base_radius - 12
    bolt_rad = 3.2 # M6 clearance
    
    # Cut central hollow drive tube for actuator rod
    base = base.faces(">Z").hole(18, depth=15)
    
    # Radial bolt pattern
    bolt_pattern = (
        cq.Workplane("XY")
        .polarArray(bolt_circle, 0, 360, 6)
        .circle(bolt_rad)
        .extrude(15)
    )
    base = base.cut(bolt_pattern)
    
    # Outer attachment points (Tendon guide channels merging into knuckles)
    hooks = cq.Workplane("XY")
    for i in range(finger_count):
        angle = get_finger_angle(i, finger_count)
        hook = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 5, 0, 15))
            .box(15, phalanx_width, 10, centered=(True, True, False))
            .edges(">Z or <Z").fillet(2) # smooth fillet for tendon routing
        )
        hooks = hooks.union(hook)
        
    return base.union(hooks)

def build_skeleton():
    """Generates the rigid phalanges with organic tapers and stress-relief cutouts."""
    skeleton = cq.Workplane("XY")
    
    for i in range(finger_count):
        angle = get_finger_angle(i, finger_count)
        
        # Proximal Phalanx
        prox_len = finger_length * 0.45
        prox_start = 22 # Z offset from ground
        
        phalanx1 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 2, 0, prox_start))
            .box(10, phalanx_width - 2, prox_len, centered=(True,True,False))
            .edges("|Z").fillet(3)  # Round vertical corners
        )
        
        # Weight/stress relief cutout in proximal phalanx
        cutout = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 2, 0, prox_start + 5))
            .box(12, phalanx_width - 10, prox_len - 10, centered=(True,True,False))
        )
        phalanx1 = phalanx1.cut(cutout)
        
        # Distal Phalanx (Tapered)
        dist_len = finger_length * 0.35
        dist_start = prox_start + prox_len + 6 # gap for hinge
        
        phalanx2 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 5, 0, dist_start))
            .rect(8, phalanx_width - 4)
            .workplane(offset=dist_len)
            .rect(5, 8) # taper down to a fingertip
            .loft(combine=True)
        )
        # Add a fingernail grab point
        fingernail = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius, 0, dist_start + dist_len))
            .sphere(4)
        )
        
        skeleton = skeleton.union(phalanx1).union(phalanx2).union(fingernail)
        
    return skeleton

def build_flexure():
    """Parametric V-Notch living hinges that are infinitely simulated by the optimizer."""
    hinges = cq.Workplane("XY")
    
    prox_len = finger_length * 0.45
    prox_start = 22
    
    for i in range(finger_count):
        angle = get_finger_angle(i, finger_count)
        
        # H1: Wrist to Proximal (Thicker)
        # We build a solid block and carve out massive elliptical scoops to create the V-Notch waist
        block1 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 5, 0, 15))
            .box(12, phalanx_width - 2, prox_start - 15, centered=(True,True,False))
        )
        
        # Carve to waist
        # To make a waist of `flexure_thickness`, we must cut from both sides
        cut_depth = (12.0 - flexure_thickness) / 2.0
        
        # Front scoop (Inner face)
        scoop1 = (
            cq.Workplane("XZ", origin=(0,0,0))
            .transformed(rotate=cq.Vector(0, 90, 0))
            .transformed(rotate=cq.Vector(0, 0, -angle)) # align locally
            .transformed(offset=cq.Vector(-(15 + 3.5), 0, (base_radius - 5) - 6 + cut_depth))
            .cylinder(height=phalanx_width + 5, radius=4, dir=(0,1,0))
        )
        # Rear scoop (Outer face)
        scoop2 = (
            cq.Workplane("XZ", origin=(0,0,0))
            .transformed(rotate=cq.Vector(0, 90, 0))
            .transformed(rotate=cq.Vector(0, 0, -angle))
            .transformed(offset=cq.Vector(-(15 + 3.5), 0, (base_radius - 5) + 6 - cut_depth))
            .cylinder(height=phalanx_width + 5, radius=4, dir=(0,1,0))
        )
        h1 = block1.cut(scoop1).cut(scoop2)
        
        # H2: Proximal to Distal (Slightly more flexible waist)
        block2 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 3, 0, prox_start + prox_len))
            .box(10, phalanx_width - 4, 6, centered=(True,True,False))
        )
        
        cut_depth2 = (10.0 - (flexure_thickness * 0.8)) / 2.0
        h2_z = prox_start + prox_len + 3.0
        
        scoop3 = (
            cq.Workplane("XZ", origin=(0,0,0))
            .transformed(rotate=cq.Vector(0, 90, 0))
            .transformed(rotate=cq.Vector(0, 0, -angle))
            .transformed(offset=cq.Vector(-h2_z, 0, (base_radius - 3) - 5 + cut_depth2))
            .cylinder(height=phalanx_width + 5, radius=3, dir=(0,1,0))
        )
        scoop4 = (
            cq.Workplane("XZ", origin=(0,0,0))
            .transformed(rotate=cq.Vector(0, 90, 0))
            .transformed(rotate=cq.Vector(0, 0, -angle))
            .transformed(offset=cq.Vector(-h2_z, 0, (base_radius - 3) + 5 - cut_depth2))
            .cylinder(height=phalanx_width + 5, radius=3, dir=(0,1,0))
        )
        h2 = block2.cut(scoop3).cut(scoop4)
        
        hinges = hinges.union(h1).union(h2)
        
    return hinges

def build_grip_pad():
    """Generates texturized TPU frictional rib pads for the inner distal face."""
    pads = cq.Workplane("XY")
    
    prox_len = finger_length * 0.45
    prox_start = 22
    dist_len = finger_length * 0.35
    dist_start = prox_start + prox_len + 6
    
    for i in range(finger_count):
        angle = get_finger_angle(i, finger_count)
        
        # Base flat pad wrapping the inner face
        pad_base = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 9.5, 0, dist_start + 2))
            .box(3, phalanx_width - 6, dist_len - 4, centered=(True,True,False))
            .edges("|Z").fillet(1.0)
        )
        
        # Generative Ribbing Loop
        total_ribs = int((dist_len - 8) / 4)
        for r in range(total_ribs):
            rib_z = dist_start + 4 + (r * 4)
            rib = (
                cq.Workplane("XY")
                .transformed(rotate=cq.Vector(0, 0, angle))
                .transformed(offset=cq.Vector(base_radius - 12, 0, rib_z))
                .box(2.5, phalanx_width - 8, 2)
                .edges(">X").fillet(0.5)
            )
            pad_base = pad_base.union(rib)
            
        pads = pads.union(pad_base)
        
    return pads

# Orchestrator Dispatch
if target_part == "skeleton":
    result = build_skeleton()
elif target_part == "flexure":
    result = build_flexure()
elif target_part == "grip_pad":
    result = build_grip_pad()
else:
    result = build_housing()
