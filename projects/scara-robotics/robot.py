import cadquery as cq
import math

# Parameters (Yantra4D injects these)
num_teeth = globals().get('num_teeth', 100)
gear_module = globals().get('gear_module', 0.5)
bore_diameter = globals().get('bore_diameter', 5.0)
render_mode = globals().get('render_mode', 0)

# Derived
flex_teeth = num_teeth - 2
pitch_diam = gear_module * num_teeth
flex_pitch_diam = gear_module * flex_teeth
thickness = 10.0
tooth_w = gear_module * 0.8
tooth_h = gear_module * 4.0 # 2.0mm depth

def add_discrete_teeth(base, n, r, w, h, t):
    """Add box teeth around a circle."""
    for i in range(n):
        angle = i * (360.0 / n)
        rad = math.radians(angle)
        x = r * math.cos(rad)
        y = r * math.sin(rad)
        # Create a tooth box and rotate then translate
        tooth = (
            cq.Workplane("XY")
            .box(h, w, t)
            .rotate((0, 0, 0), (0, 0, 1), angle)
            .translate((x, y, 0))
        )
        base = base.union(tooth)
    return base

def wave_generator():
    r_base = (flex_pitch_diam - (gear_module * 2)) / 2.0
    # Use polygon for parity with OpenSCAD $fn
    res = (
        cq.Workplane("XY")
        .polygon(128, 2*r_base, circumscribed=False)
        .extrude((thickness - 2.0)/2.0, both=True)
    )
    # Bore (using polygon for parity) 
    res = res.faces(">Z").workplane().polygon(128, bore_diameter, circumscribed=False).cutThruAll()
    return res

def flexspline():
    r_body = (flex_pitch_diam - 0.1) / 2.0
    # Core Body (Polygon for parity)
    res = cq.Workplane("XY").polygon(128, 2*r_body, circumscribed=False).extrude(thickness/2.0, both=True)
    # Discrete Teeth
    res = add_discrete_teeth(res, flex_teeth, flex_pitch_diam/2.0, tooth_w, tooth_h, thickness)
    
    # Subtraction (Cup)
    inner_d = (flex_pitch_diam - (gear_module * 4))
    res = res.cut(cq.Workplane("XY").polygon(128, inner_d, circumscribed=False).extrude((thickness + 0.1)/2.0, both=True))
    
    # Flange
    flange_d = (flex_pitch_diam + 10)
    flange = (
        cq.Workplane("XY")
        .workplane(offset=-thickness/2.0)
        .polygon(128, flange_d, circumscribed=False)
        .extrude(-2.0)
    )
    return res.union(flange)

def circular_spline():
    outer_d = (pitch_diam + 15)
    inner_d = (pitch_diam + 0.1)
    
    # Outer Ring
    res = cq.Workplane("XY").polygon(128, outer_d, circumscribed=False).extrude(thickness/2.0, both=True)
    
    # Subtract Internal Gear Volume
    hole = cq.Workplane("XY").polygon(128, inner_d, circumscribed=False).extrude((thickness + 1.0)/2.0, both=True)
    # Internal Teeth
    hole = add_discrete_teeth(hole, num_teeth, pitch_diam/2.0, tooth_w, tooth_h, thickness + 1.0)
    
    return res.cut(hole)

# Rendering logic
parts = []
if render_mode == 0 or render_mode == 1:
    parts.append(wave_generator())
if render_mode == 0 or render_mode == 2:
    parts.append(flexspline())
if render_mode == 0 or render_mode == 3:
    parts.append(circular_spline())

# Final Result
if len(parts) > 1:
    result = parts[0]
    for p in parts[1:]:
        result = result.union(p)
else:
    result = parts[0]
