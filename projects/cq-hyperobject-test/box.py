import cadquery as cq

# Parameters will be injected by the runner
width = globals().get('width', 10.0)
length = globals().get('length', 10.0)
height = globals().get('height', 10.0)

# Create a box
result = cq.Workplane("XY").box(width, length, height)
