import cadquery as cq
import math

# Globals injected by Yantra4D Environment
finger_length = 65.0
base_radius = 35.0
flexure_thickness = 1.2
finger_count = int(globals().get("finger_count", 3))
target_part = "housing"

def build_housing():
    # Rigid mounting base
    base = cq.Workplane("XY").cylinder(height=10, radius=base_radius)
    # Add a recessed mounting hole
    base = base.faces(">Z").hole(15, 10)
    
    # Outer attachment points
    actuator_hooks = cq.Workplane("XY")
    for i in range(finger_count):
        angle = (360.0 / finger_count) * i
        hook = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 5, 0, 10))
            .box(10, 15, 10)
        )
        actuator_hooks = actuator_hooks.union(hook)
        
    return base.union(actuator_hooks)

def build_skeleton():
    # The rigid phalanges of the fingers
    skeleton = cq.Workplane("XY")
    
    for i in range(finger_count):
        angle = (360.0 / finger_count) * i
        # Base Phalanx
        phalanx1 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius, 0, 15 + finger_length * 0.2))
            .box(8, 12, finger_length * 0.4)
        )
        # Distal Phalanx
        phalanx2 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 5, 0, 15 + finger_length * 0.8))
            .box(6, 10, finger_length * 0.3)
        )
        skeleton = skeleton.union(phalanx1).union(phalanx2)
        
    return skeleton

def build_flexure():
    # The TPU hinges connecting housing -> phalanx1 -> phalanx2
    hinges = cq.Workplane("XY")
    
    for i in range(finger_count):
        angle = (360.0 / finger_count) * i
        
        # Proximal Hinge
        h1 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 2, 0, 12))
            .box(flexure_thickness, 10, 5)
        )
        # Distal Hinge
        h2 = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 2, 0, 15 + finger_length * 0.5))
            .box(flexure_thickness, 8, 5)
        )
        hinges = hinges.union(h1).union(h2)
        
    return hinges

def build_grip_pad():
    # High friction TPU pads mapped to the inner face of the fingers
    pads = cq.Workplane("XY")
    
    for i in range(finger_count):
        angle = (360.0 / finger_count) * i
        pad = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, angle))
            .transformed(offset=cq.Vector(base_radius - 7, 0, 15 + finger_length * 0.6))
            .box(4, 10, finger_length * 0.6)
            .edges("|Z").fillet(2) # smooth edges for gripping
        )
        pads = pads.union(pad)
        
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
