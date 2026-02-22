import cadquery as cq
import math

def cdg_vesa_pattern(standard="MIS-D 100", center=True):
    specs = {
        "MIS-D 75": (75, 75, 4),
        "MIS-D 100": (100, 100, 4),
        "MIS-E": (200, 100, 4)
    }
    sx, sy, d = specs.get(standard, (100, 100, 4))
    ox = -sx/2 if center else 0
    oy = -sy/2 if center else 0
    return [(ox, oy), (ox+sx, oy), (ox, oy+sy), (ox+sx, oy+sy)], d

def cdg_french_cleat(length=100, height=30, depth=15, angle=45):
    rad = math.radians(angle)
    pts = [
        (0, 0),
        (depth, 0),
        (depth, height),
        (depth - (height * math.tan(rad)), height)
    ]
    profile = cq.Workplane("YZ").polyline(pts).close()
    cleat = profile.extrude(length)
    cleat = cleat.translate((-length/2, -height/2, 0))
    return cleat.clean()

def cdg_standoff_barrel(h=20, d=12, thread_d=4):
    return cq.Workplane("XY").circle(d/2).extrude(h).faces(">Z").hole(thread_d, depth=h)

def cdg_standoff_set(spacing_x=100, spacing_y=100, h=25):
    sx = spacing_x / 2
    sy = spacing_y / 2
    pts = [(-sx, -sy), (sx, -sy), (-sx, sy), (sx, sy)]
    base = cq.Workplane("XY").pushPoints(pts)
    standoffs = base.circle(12/2).extrude(h).faces(">Z").hole(4, depth=h)
    return standoffs.clean()
