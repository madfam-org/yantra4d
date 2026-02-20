import cadquery as cq

# Parameters will be injected by the runner
mount_width = globals().get('mount_width', 40.0)
bolt_spacing = globals().get('bolt_spacing', 20.0)
bolt_size = globals().get('bolt_size', 1)

bolt_d = 3.2 if bolt_size == 0 else (4.2 if bolt_size == 1 else 5.2)

# CDG Constants (TS35)
RAIL_WIDTH = 35.0
RAIL_DEPTH = 7.5
LIP_THICKNESS = 1.0

# 1. Main Body
body = cq.Workplane("XY").box(mount_width, RAIL_WIDTH + 10, 8).translate((0, 0, 4))

# 2. DIN Rail Cutout
# OpenSCAD coordinates translated to CadQuery YZ profile (extruded along X)
cutout = (
    cq.Workplane("YZ")
    .polyline([(17.75, -0.1), (-17.75, -0.1), (-16.5, 7.4), (16.5, 7.4)])
    .close()
    .extrude(mount_width / 2.0, both=True)
)

# 3. Locking Lip (Fixed Top)
lip1 = (
    cq.Workplane("YZ")
    .polyline([(20.5, 3), (23.5, 3), (22.5, 6), (21.5, 6)])
    .close()
    .extrude(mount_width / 2.0, both=True)
)

# 4. Spring Lip (Flexible Bottom)
lip2 = (
    cq.Workplane("YZ")
    .polyline([(-23.5, 3), (-20.5, 3), (-21.5, 6), (-22.5, 6)])
    .close()
    .extrude(mount_width / 2.0, both=True)
)

clip = body.union(lip1).clean().union(lip2).clean().cut(cutout).clean()

# 5. Mounting Holes
holes = (
    cq.Workplane("XY")
    .pushPoints([(-bolt_spacing / 2.0, 0), (bolt_spacing / 2.0, 0)])
    .circle(bolt_d / 2.0)
    .extrude(20)
    .translate((0, 0, -2))
)

result = clip.cut(holes).clean()
